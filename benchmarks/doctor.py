import importlib.metadata
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def probe(command):
    if not shutil.which(command[0]):
        return {"status": "missing", "output": None}
    try:
        p = subprocess.run(command, text=True, capture_output=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "output": str(exc)}
    return {
        "status": "ok" if p.returncode == 0 else "unavailable",
        "output": (p.stdout.strip() or p.stderr).strip()[:4000],
    }


def inspect():
    packages = {}
    for name in ("torch", "transformers", "vllm"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    torch_cuda = None
    if packages["torch"]:
        try:
            import torch

            torch_cuda = {
                "available": torch.cuda.is_available(),
                "count": torch.cuda.device_count(),
                "cuda_build": torch.version.cuda,
            }
        except (ImportError, OSError) as exc:
            torch_cuda = {"error": str(exc)}
    return {
        "torch_cuda": torch_cuda,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "packages": packages,
        "uv": probe(["uv", "--version"]),
        "visible_devices": os.getenv("CUDA_VISIBLE_DEVICES"),
        "gpus": probe(
            ["nvidia-smi", "--query-gpu=index,name,driver_version,memory.free,memory.total", "--format=csv"]
        ),
        "topology": probe(["nvidia-smi", "topo", "-m"]),
        "docker": probe(["docker", "info", "--format", "{{.ServerVersion}}"]),
        "k8s_create_pods": probe(["kubectl", "--request-timeout=2s", "auth", "can-i", "create", "pods"]),
        "disk_free_bytes": shutil.disk_usage(Path.cwd()).free,
        "image_digest": os.getenv("LAB_IMAGE_DIGEST"),
    }
