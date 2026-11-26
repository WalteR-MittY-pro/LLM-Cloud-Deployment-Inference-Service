import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from unittest.mock import patch

from jsonschema import validate
from benchmarks import bootstrap, doctor
from benchmarks.api_lab import hybrid_endpoints
from benchmarks.lessons import ROOT
from benchmarks.records import report
from benchmarks.run import main
from test_protocol import APIHandler


def cli(*args):
    with patch.object(sys, "argv", ["lab", *args]), contextlib.redirect_stdout(io.StringIO()):
        main()


class ProfileTests(unittest.TestCase):
    def test_cloud_observation_without_admin_or_identifiers(self):
        calls = []

        def fake(cmd, *args):
            calls.append(cmd)
            return {"status": "blocked", "exit_code": 1}

        with (
            patch.object(doctor, "probe", side_effect=fake),
            patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "MIG-private-uuid"}),
        ):
            data = doctor.inspect("cloud-h200-multi", with_torch=False)
        validate(data, json.loads((ROOT / "benchmarks/schemas/environment.json").read_text()))
        self.assertFalse(any(cmd[0] in ("docker", "kubectl") for cmd in calls))
        self.assertEqual(data["target"]["target_gpu_count"], 2)
        self.assertEqual(data["gpus"]["status"], "blocked")
        self.assertNotIn("MIG-private", json.dumps(data))
        self.assertEqual(set(data["capabilities_requiring_smoke_tests"].values()), {"untested"})

    def test_context_policy_before_any_command(self):
        with patch.object(doctor, "probe") as probe:
            with self.assertRaises(ValueError):
                doctor.inspect("cloud-h200-single", kube_context="private.example", with_torch=False)
            probe.assert_not_called()
        with patch.object(doctor, "probe", return_value={"status": "not_available"}) as probe:
            doctor.inspect("home-cluster", with_torch=False)
            self.assertFalse(any(c.args[0][0] == "kubectl" for c in probe.call_args_list))

    def test_inventory_cuda_failure_and_historical_report(self):
        schema = json.loads((ROOT / "benchmarks/schemas/environment.json").read_text())
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(doctor, "probe", return_value={"status": "not_available"}),
        ):
            base = ["lab", "--root", tmp, "--day", "00", "--env", "cpu", "--profile", "cloud-h200-multi"]
            cli(*base)
            with (
                patch("torch.cuda.is_available", return_value=False),
                self.assertRaisesRegex(RuntimeError, "CUDA unavailable"),
            ):
                cli(*base, "--smoke", "nccl", "--gpus", "2")
            records = [json.loads(p.read_text()) for p in (Path(tmp) / "day-00").glob("*/run.json")]
            self.assertEqual(len(records), 2)
            for m in records:
                validate(m["environment"], schema)
                self.assertEqual((m["env"], m["profile"]), ("cpu", "cloud-h200-multi"))
                state = m["environment"]["capabilities_requiring_smoke_tests"]["nccl_collective"]
                self.assertEqual(state, "blocked" if m["exit_code"] else "untested")
                self.assertNotEqual(m["source"], "gpu_measured")
            first = next((Path(tmp) / "day-00").glob("*/run.json"))
            meta = json.loads(first.read_text())
            meta.pop("env")
            meta.pop("profile")
            first.write_text(json.dumps(meta))
            report(first.parent)
            self.assertIn("未指定", (first.parent / "report.md").read_text())

    def test_doctor_output_is_exclusive(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.object(doctor, "probe", return_value={"status": "not_available"}),
        ):
            out = Path(tmp) / "inventory.json"
            args = ["doctor", "--env", "cpu", "--profile", "home-4080", "--output", str(out)]
            cli(*args)
            saved = out.read_bytes()
            with self.assertRaises(FileExistsError):
                cli(*args)
            self.assertEqual(out.read_bytes(), saved)
            self.assertIsNone(json.loads(saved)["declared_allocated_gpu_count"])

    def test_rank_evidence_required_from_every_process(self):
        row = {"kind": "real_gpu_correctness", "world_size": 2, "sum": 3, "status": "passed", "rank": 0}
        result = subprocess.CompletedProcess([], 0, json.dumps(row) + "\n", "")
        with patch.object(bootstrap.subprocess, "run", return_value=result) as launch:
            with self.assertRaisesRegex(RuntimeError, "per-rank"):
                bootstrap.nccl_smoke(2)
            self.assertIn("--standalone", launch.call_args.args[0])
            self.assertNotIn("env", launch.call_args.kwargs)
            result.stdout += json.dumps(dict(row, rank=1))
            self.assertEqual([r["rank"] for r in bootstrap.nccl_smoke(2)], [0, 1])


class RoutedHandler(APIHandler):
    def do_GET(self):
        if self.server.redirect:
            self.send_response(302)
            self.send_header("Location", self.server.redirect)
            self.end_headers()
        else:
            super().do_GET()

    def do_POST(self):
        self.server.requests_seen += 1
        super().do_POST()


class HybridTests(unittest.TestCase):
    def test_disjoint_loopback_endpoints(self):
        self.assertEqual(list(hybrid_endpoints(8100, 18000, "cloud")), ["cloud"])
        for pair in [(1, 1), (-1, 2), (1, 65536)]:
            with self.assertRaises(ValueError):
                hybrid_endpoints(*pair, "round-robin")

    def test_two_routes_and_redirect_boundary(self):
        with contextlib.ExitStack() as stack, tempfile.TemporaryDirectory() as tmp:
            servers = []
            for _ in range(2):
                server = ThreadingHTTPServer(("127.0.0.1", 0), RoutedHandler)
                server.requests_seen = 0
                server.redirect = None
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                stack.callback(thread.join)
                stack.callback(server.server_close)
                stack.callback(server.shutdown)
                servers.append(server)
            args = [
                "lab",
                "--day",
                "28",
                "--profile",
                "hybrid",
                "--env",
                "cpu",
                "--impl",
                "reference",
                "--model",
                "fixture",
                "--root",
                tmp,
                "--warmup",
                "0",
                "--repeat",
                "1",
                "--home-port",
                str(servers[0].server_port),
                "--cloud-port",
                str(servers[1].server_port),
            ]
            with patch.object(doctor, "probe", return_value={"status": "not_available"}):
                cli(*args)
                self.assertEqual([s.requests_seen for s in servers], [1, 1])
                path = next((Path(tmp) / "day-28").iterdir())
                rows = [json.loads(line) for line in (path / "requests.jsonl").read_text().splitlines()]
                self.assertEqual([r["backend"] for r in rows], ["home", "cloud"])
                counts = json.loads((path / "metrics.json").read_text())["backends"]
                self.assertEqual([counts[k]["successes"] for k in ("home", "cloud")], [1, 1])
                self.assertTrue(all(r["ttft_ms"] is None for r in rows))
                servers[0].redirect = f"http://127.0.0.1:{servers[1].server_port}/v1/models"
                from urllib.error import HTTPError

                with self.assertRaises(HTTPError):
                    cli(*args)
                self.assertEqual([s.requests_seen for s in servers], [1, 1])
