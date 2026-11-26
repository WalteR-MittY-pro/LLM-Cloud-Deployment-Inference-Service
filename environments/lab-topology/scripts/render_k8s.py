#!/usr/bin/env python3
"""Render (never apply) a small two-node vLLM lab manifest as JSON."""

import argparse
import json
import re
from pathlib import Path

# Linux/amd64 manifest of vllm/vllm-openai:v0.34.0, resolved from the registry.
PINNED_IMAGE = "vllm/vllm-openai@sha256:cf5b2fdd087eb4f6d261736967cc5cde974bd22ff4df50365f8fa419b6b4c484"
REVISIONS = Path(__file__).resolve().parents[3] / "course/day-01/config/revisions.json"

NAMESPACE = "inference-lab"
LABELS = {"app.kubernetes.io/name": "vllm-home-lab"}


def manifest(
    image=PINNED_IMAGE,
    revision=None,
    tokenizer_revision=None,
    replicas=2,
    memory_util=0.8,
    model="Qwen/Qwen3-4B",
    max_model_len=4096,
    runtime="nvidia",
):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[0-9a-f]{64}", image):
        raise ValueError("Use a verified immutable image digest, e.g. repository@sha256:<64 hex>")
    revisions = json.loads(REVISIONS.read_text())
    if model not in revisions:
        raise ValueError("Use one of the course baseline models")
    revision = revisions[model] if revision is None else revision
    tokenizer_revision = revisions[model] if tokenizer_revision is None else tokenizer_revision
    for name, value in [("revision", revision), ("tokenizer_revision", tokenizer_revision)]:
        if not re.fullmatch("[0-9a-f]{40}", value):
            raise ValueError(f"{name} must be a verified 40-character commit hash")
    if replicas not in (1, 2):
        raise ValueError("Home lab supports one or two replicas")
    if not 0.1 <= memory_util <= 0.9 or not 128 <= max_model_len <= 8192:
        raise ValueError("Choose a conservative teaching memory/context setting")
    if runtime not in ("nvidia", "nvidia-cdi"):
        raise ValueError("Unknown NVIDIA runtime class")
    pod_spec = {
        "runtimeClassName": runtime,
        "nodeSelector": {"inference-lab/gpu-home": "true"},
        "affinity": {
            "podAntiAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": [
                    {"labelSelector": {"matchLabels": LABELS}, "topologyKey": "kubernetes.io/hostname"}
                ]
            }
        },
        "automountServiceAccountToken": False,
        "containers": [
            {
                "name": "vllm",
                "image": image,
                "command": ["vllm", "serve"],
                "args": [
                    model,
                    "--revision",
                    revision,
                    "--tokenizer-revision",
                    tokenizer_revision,
                    "--dtype",
                    "bfloat16",
                    "--max-model-len",
                    str(max_model_len),
                    "--max-num-seqs",
                    "8",
                    "--gpu-memory-utilization",
                    str(memory_util),
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "8000",
                ],
                "ports": [{"name": "http", "containerPort": 8000}],
                "resources": {
                    "requests": {"cpu": "2", "memory": "4Gi", "nvidia.com/gpu": "1"},
                    "limits": {"nvidia.com/gpu": "1"},
                },
                "startupProbe": {
                    "httpGet": {"path": "/health", "port": "http"},
                    "periodSeconds": 10,
                    "failureThreshold": 180,
                },
                "readinessProbe": {
                    "httpGet": {"path": "/health", "port": "http"},
                    "periodSeconds": 10,
                    "timeoutSeconds": 3,
                },
                "volumeMounts": [
                    {"name": "shm", "mountPath": "/dev/shm"},
                    {"name": "weights", "mountPath": "/model-cache"},
                ],
                "env": [{"name": "HF_HOME", "value": "/model-cache"}],
            }
        ],
        "volumes": [
            {"name": "shm", "emptyDir": {"medium": "Memory", "sizeLimit": "4Gi"}},
            {"name": "weights", "emptyDir": {}},
        ],
    }
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE}},
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "vllm-home-lab", "namespace": NAMESPACE},
                "spec": {
                    "replicas": replicas,
                    "strategy": {"type": "Recreate"},
                    "selector": {"matchLabels": LABELS},
                    "template": {"metadata": {"labels": LABELS}, "spec": pod_spec},
                },
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "vllm-home-lab", "namespace": NAMESPACE},
                "spec": {
                    "type": "ClusterIP",
                    "selector": LABELS,
                    "ports": [{"name": "http", "port": 8000, "targetPort": "http"}],
                },
            },
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", default=PINNED_IMAGE)
    p.add_argument("--revision")
    p.add_argument("--tokenizer-revision")
    p.add_argument("--replicas", type=int, default=2, choices=(1, 2))
    p.add_argument("--memory-util", type=float, default=0.8)
    p.add_argument("--max-model-len", type=int, default=4096)
    p.add_argument("--model", default="Qwen/Qwen3-4B")
    p.add_argument("--runtime", default="nvidia", choices=("nvidia", "nvidia-cdi"))
    a = p.parse_args()
    try:
        result = manifest(
            a.image,
            a.revision,
            a.tokenizer_revision,
            a.replicas,
            a.memory_util,
            a.model,
            a.max_model_len,
            a.runtime,
        )
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
