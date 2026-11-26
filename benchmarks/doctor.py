"""Local read-only observation. Only an explicitly selected home context is queried."""

import csv
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from .profiles import load_profile

CAPABILITIES = (
    "cuda_execution",
    "nccl_collective",
    "gpu_p2p",
    "kv_transfer",
    "profiling_counters",
    "docker_gpu",
    "k8s_gpu_pod",
    "ssh_forwarding",
)


def probe(command, timeout=5):
    if not shutil.which(command[0]):
        return {"status": "not_available", "reason": "tool_missing"}
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "blocked", "reason": type(exc).__name__}
    if p.returncode:
        return {"status": "blocked", "exit_code": p.returncode}
    return {"status": "observed", "output": p.stdout.strip()}


def gpu_inventory(result):
    if result["status"] != "observed":
        return {k: v for k, v in result.items() if k != "output"}
    devices = []
    for row in csv.reader(result["output"].splitlines()):
        if len(row) != 4:
            return {"status": "blocked", "reason": "unexpected_gpu_fields"}
        name, total, free, driver = (s.strip() for s in row)
        devices.append({"name": name, "memory_mib": total, "free_mib": free, "driver": driver})
    return {"status": "observed", "reported_devices": devices}


def topology():
    result = probe(["nvidia-smi", "topo", "-m"])
    if result["status"] != "observed":
        return result
    # Keep the GPU-to-GPU matrix only. Drop NIC names, host addresses and legends.
    lines = [line.split() for line in result["output"].splitlines() if line.strip()]
    cols = [i for i, col in enumerate(lines[0] if lines else []) if re.fullmatch(r"GPU\d+", col)]
    matrix = {}
    for row in lines[1:]:
        if re.fullmatch(r"GPU\d+", row[0]):
            matrix[row[0]] = [
                row[i + 1]
                for i in cols
                if i + 1 < len(row) and re.fullmatch(r"X|NV\d+|SYS|NODE|PHB|PXB|PIX|SOC", row[i + 1])
            ]
    return {"status": "observed", "gpu_links": matrix}


def cluster_probe(context):
    if not context:
        return {"status": "untested"}
    result = probe(["kubectl", "--context", context, "--request-timeout=5s", "get", "nodes", "-o", "json"], 7)
    if result["status"] != "observed":
        return result
    try:
        nodes = []
        for item in json.loads(result["output"])["items"]:
            status = item["status"]
            nodes.append(
                {
                    "home_label": item["metadata"].get("labels", {}).get("inference-lab/gpu-home") == "true",
                    "ready": any(
                        x["type"] == "Ready" and x["status"] == "True" for x in status.get("conditions", [])
                    ),
                    "gpu_allocatable": status.get("allocatable", {}).get("nvidia.com/gpu", "0"),
                }
            )
        return {"status": "observed", "nodes": nodes}
    except (KeyError, ValueError, TypeError, AttributeError):
        return {"status": "blocked", "reason": "unexpected_nodes_response"}


def inspect(profile=None, kube_context=None, with_torch=True):
    plan = load_profile(profile)
    if kube_context and profile not in ("home-cluster", "hybrid"):
        raise ValueError("Kubernetes inspection requires an explicit home-cluster or hybrid profile")
    packages = {}
    for name in ("torch", "transformers", "vllm"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    torch_cuda = {"status": "untested"}
    if with_torch:
        if packages["torch"]:
            try:
                import torch

                torch_cuda = {
                    "status": "observed",
                    "available": torch.cuda.is_available(),
                    "count": torch.cuda.device_count(),
                    "cuda_build": torch.version.cuda,
                    "nccl_built": torch.distributed.is_nccl_available(),
                }
            except (ImportError, OSError, RuntimeError) as exc:
                torch_cuda = {"status": "blocked", "reason": type(exc).__name__}
        else:
            torch_cuda = {"status": "not_available"}
    home = profile in ("home-4070", "home-4080", "home-cluster", "hybrid")
    docker = (
        probe(["docker", "--host", "unix:///var/run/docker.sock", "info", "--format", "{{.ServerVersion}}"])
        if home or not plan
        else {"status": "untested"}
    )
    if docker.get("output") and not re.fullmatch(r"[\w.()+-]+", docker["output"]):
        docker = {"status": "observed"}
    k8s = {"status": "untested"}
    if kube_context:
        k8s = probe(
            ["kubectl", "--context", kube_context, "--request-timeout=3s", "auth", "can-i", "create", "pods"]
        )
    image = os.getenv("LAB_IMAGE_DIGEST", "").split("@")[-1]
    visibility = os.getenv("CUDA_VISIBLE_DEVICES")
    result = {
        "schema_version": 1,
        "kind": "environment_observation",
        "profile": profile,
        "target": plan,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "torch_cuda": torch_cuda,
        "platform": platform.system() + "-" + platform.machine(),
        "python": sys.version.split()[0],
        "wsl_hint": "microsoft" in platform.release().lower(),
        "container_hint": any(Path(p).exists() for p in ("/.dockerenv", "/run/.containerenv")),
        "packages": packages,
        "uv": probe(["uv", "--version"]),
        "visible_devices": visibility
        if visibility is None or re.fullmatch(r"[0-9, -]*", visibility)
        else "set (redacted)",
        "tools_on_path": {
            name: bool(shutil.which(name))
            for name in (
                "nvidia-smi",
                "nvcc",
                "docker",
                "kubectl",
                "helm",
                "k3s",
                "nsys",
                "ncu",
                "iperf3",
                "torchrun",
                "vllm",
            )
        },
        "gpus": gpu_inventory(
            probe(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,memory.free,driver_version",
                    "--format=csv,noheader,nounits",
                ]
            )
        ),
        "topology": topology(),
        "docker": docker,
        "cluster": cluster_probe(kube_context),
        "k8s_create_pods": k8s,
        "disk_free_bytes": shutil.disk_usage(Path.cwd()).free,
        "shm_bytes_total": shutil.disk_usage("/dev/shm").total if Path("/dev/shm").is_dir() else None,
        "image_digest": image if re.fullmatch(r"sha256:[0-9a-f]{64}", image) else None,
        "capabilities_requiring_smoke_tests": dict.fromkeys(CAPABILITIES, "untested"),
    }
    return result
