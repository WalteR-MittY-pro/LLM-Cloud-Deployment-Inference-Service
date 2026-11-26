import json
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks import doctor

BASE = Path(__file__).resolve().parents[1]
manifest = runpy.run_path(str(BASE / "scripts/render_k8s.py"))["manifest"]

IMAGE = "vllm/vllm-openai@sha256:" + "a" * 64
REV = "b" * 40


class TestManifest(unittest.TestCase):
    def test_two_replicas_isolated(self):
        items = manifest(IMAGE, REV, REV)["items"]
        ns, dep, svc = items
        self.assertEqual(ns["metadata"]["name"], "inference-lab")
        self.assertEqual(dep["spec"]["replicas"], 2)
        pod = dep["spec"]["template"]["spec"]
        self.assertEqual(pod["containers"][0]["resources"]["limits"]["nvidia.com/gpu"], "1")
        self.assertEqual(pod["nodeSelector"]["inference-lab/gpu-home"], "true")
        self.assertEqual(pod["runtimeClassName"], "nvidia")
        self.assertEqual(
            pod["affinity"]["podAntiAffinity"]["requiredDuringSchedulingIgnoredDuringExecution"][0][
                "topologyKey"
            ],
            "kubernetes.io/hostname",
        )
        self.assertEqual(svc["spec"]["type"], "ClusterIP")
        self.assertFalse(pod["automountServiceAccountToken"])
        self.assertEqual(dep["spec"]["selector"]["matchLabels"], svc["spec"]["selector"])

    def test_course_revisions_and_boot_probes(self):
        revisions = json.loads((BASE.parents[1] / "course/day-01/config/revisions.json").read_text())
        for model, revision in revisions.items():
            container = manifest(model=model)["items"][1]["spec"]["template"]["spec"]["containers"][0]
            argv = container["args"]
            self.assertEqual(container["command"], ["vllm", "serve"])
            self.assertEqual(argv[0], model)
            self.assertEqual(argv[argv.index("--revision") + 1], revision)
            self.assertEqual(argv[argv.index("--tokenizer-revision") + 1], revision)
            self.assertIn("@sha256:", container["image"])
            self.assertEqual(container["startupProbe"]["httpGet"]["path"], "/health")
            self.assertEqual(container["readinessProbe"]["httpGet"]["port"], "http")

    def test_single_replica(self):
        self.assertEqual(manifest(IMAGE, REV, REV, 1)["items"][1]["spec"]["replicas"], 1)

    def test_reject_unpinned_or_invalid(self):
        for args in [("vllm/vllm-openai:latest", REV, REV), (IMAGE, "main", REV), (IMAGE, REV, "main")]:
            with self.assertRaises(ValueError):
                manifest(*args)
        with self.assertRaises(ValueError):
            manifest(IMAGE, REV, REV, 3)

    def test_reject_invalid_memory(self):
        with self.assertRaises(ValueError):
            manifest(IMAGE, REV, REV, memory_util=1.0)


class TestDoctor(unittest.TestCase):
    def test_inventory_is_not_capability(self):
        data = doctor.gpu_inventory({"status": "observed", "output": "NVIDIA H200, 143771, 140000, 555.42\n"})
        self.assertEqual(data["reported_devices"][0]["name"], "NVIDIA H200")
        self.assertNotIn("passed", json.dumps(data))

    def test_unavailable(self):
        with patch.object(doctor.shutil, "which", return_value=None):
            self.assertEqual(doctor.probe(["missing"])["status"], "not_available")

    def test_redacted_error(self):
        result = doctor.gpu_inventory({"status": "blocked", "output": "private", "exit_code": 1})
        self.assertNotIn("output", result)

    def test_cluster_read_only(self):
        payload = {
            "items": [
                {
                    "metadata": {"name": "private-name", "labels": {"inference-lab/gpu-home": "true"}},
                    "status": {
                        "allocatable": {"nvidia.com/gpu": "1"},
                        "conditions": [{"type": "Ready", "status": "True"}],
                    },
                }
            ]
        }
        with patch.object(
            doctor, "probe", return_value={"status": "observed", "output": json.dumps(payload)}
        ) as run:
            result = doctor.cluster_probe("home")
            self.assertEqual(run.call_args.args[0][1:3], ["--context", "home"])
            self.assertTrue(result["nodes"][0]["ready"])
            self.assertNotIn("private-name", json.dumps(result))

    def test_profiles_and_no_false_pass(self):
        profiles = list((BASE / "profiles").glob("*.json"))
        self.assertEqual(len(profiles), 6)
        for path in profiles:
            p = json.loads(path.read_text())
            self.assertEqual(p["id"], path.stem)
            self.assertEqual(p["verification"], "not_run")
            self.assertFalse(p["policy"]["allow_cloud_host_mutation"])
        p = json.loads((BASE / "profiles" / "cloud-h200-multi.json").read_text())
        with patch.object(doctor, "probe", return_value={"status": "not_available"}):
            report = doctor.inspect(p["id"], with_torch=False)
        self.assertTrue(all(v == "untested" for v in report["capabilities_requiring_smoke_tests"].values()))
        self.assertEqual(report["cluster"]["status"], "untested")


if __name__ == "__main__":
    unittest.main()
