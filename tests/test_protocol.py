import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from jsonschema import validate
from benchmarks.api_lab import load_workload
from benchmarks.lessons import ROOT
from benchmarks.metrics import goodput, summary, token_metrics
from benchmarks.performance import decode_seconds, gemm_flops, kv_bytes, roofline, transfer_seconds
from benchmarks.records import attempt, report


class ProtocolTests(unittest.TestCase):
    def test_estimates_and_counters(self):
        self.assertAlmostEqual(decode_seconds(32e9, 2, 4.8e12, 0.65), 1 / 48.75)
        self.assertEqual(kv_bytes(28, 8, 128, 1, 1, 2), 114688)
        self.assertEqual(gemm_flops(2, 3, 4), 48)
        self.assertEqual(roofline(100, 10, 1000, 5), 2)
        self.assertEqual(transfer_seconds(10, 5, 0.1), 2.1)
        self.assertIsNone(token_metrics([4])["tpot_ms"])
        self.assertEqual(token_metrics([4, 7, 10])["itl_ms"], [3, 3])
        self.assertEqual(summary([1, 2, 4, 9])["p95"], 9)
        rows = [
            dict(status="ok", ttft_ms=4, tpot_ms=3),
            dict(status="failed"),
            dict(status="ok", first_text_ms=1),
        ]
        self.assertEqual(goodput(rows, 2, 10, 5), 0.5)

    def test_workload_schema_and_unique(self):
        example = (ROOT / "benchmarks/datasets/first-chat.jsonl").read_text().splitlines()[0]
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "requests.jsonl"
            f.write_text(example + "\n" + example)
            with self.assertRaisesRegex(ValueError, "唯一"):
                load_workload(f)

    @patch("benchmarks.records.inspect", return_value={})
    def test_failed_attempt_and_retry(self, _):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(RuntimeError, "trial"):
                with attempt(root, "02", {}) as (bad, meta):
                    raise RuntimeError("trial")
            with attempt(root, "02", {}) as (ok, meta):
                pass
            self.assertNotEqual(bad, ok)
            for p, status, code in [(bad, "failed", 1), (ok, "ok", 0)]:
                m = json.loads((p / "run.json").read_text())
                validate(m, json.loads((ROOT / "benchmarks/schemas/run.json").read_text()))
                self.assertEqual((m["status"], m["exit_code"]), (status, code))
                self.assertEqual(report(p)["steady_attempts"], 0)
            self.assertIn("trial", (bad / "raw.log").read_text())


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"data":[{"id":"fixture"}]}')

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if payload["messages"][0]["content"] == "bad":
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"context length exceeded")
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'data: {"choices":[{"delta":{"role":"assistant"}}]}\n\n')
        self.wfile.write(b'data: {"choices":[{"delta":{"content":"two tokens"}}]}\n\n')
        if payload["messages"][0]["content"] == "stall":
            self.wfile.flush()
            time.sleep(1)
            return
        if payload["messages"][0]["content"] != "cut":
            self.wfile.write(b"data: [DONE]\n\n")


class CLITests(unittest.TestCase):
    def test_real_cli_loopback_success_and_partial_failure(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), APIHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / "work.jsonl"
                cmd = [
                    sys.executable,
                    "-m",
                    "benchmarks.run",
                    "lab",
                    "--day",
                    "01",
                    "--impl",
                    "reference",
                    "--level2",
                    "--model",
                    "fixture",
                    "--base-url",
                    f"http://127.0.0.1:{server.server_port}",
                    "--root",
                    tmp,
                    "--workload",
                    str(work),
                    "--warmup",
                    "0",
                    "--repeat",
                    "1",
                ]
                for prompt, expected in [("ok", 0), ("cut", 1), ("bad", 1), ("stall", 1)]:
                    work.write_text(
                        json.dumps(
                            dict(
                                request_id="r",
                                session_id="s",
                                arrival_ms=0,
                                output_token_budget=8,
                                prompt=prompt,
                            )
                        )
                    )
                    variant = [*cmd, "--timeout", "0.2"] if prompt == "stall" else cmd
                    p = subprocess.run(variant, cwd=ROOT, env=os.environ, capture_output=True, text=True)
                    self.assertEqual(p.returncode, expected, p.stderr)
                    run = Path(p.stdout.split("RUN=")[1].splitlines()[0])
                    row = json.loads((run / "requests.jsonl").read_text())
                    validate(row, json.loads((ROOT / "benchmarks/schemas/observation.json").read_text()))
                    if prompt == "bad":
                        self.assertIn("context length exceeded", row["error"])
                        self.assertEqual((run / "stream-0-0.sse").read_bytes(), b"context length exceeded")
                    else:
                        self.assertIsNotNone(row["first_text_ms"])
                    if prompt == "stall":
                        self.assertIn("timed out", row["error"])
                    self.assertIsNone(row["ttft_ms"])
                    self.assertEqual(json.loads((run / "run.json").read_text())["exit_code"], expected)
                    self.assertTrue((run / "stream-0-0.sse").is_file())
                self.assertEqual(len(list((Path(tmp) / "day-01").iterdir())), 4)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
