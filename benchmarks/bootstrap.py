"""Day 00 explicitly requested checks, recorded by the regular experiment harness."""

import json
import subprocess
import sys

from .profiles import BASE


def nccl_smoke(gpus):
    worker = BASE / "scripts/nccl_smoke.py"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "torch.distributed.run",
            "--standalone",
            "--nnodes=1",
            f"--nproc-per-node={gpus}",
            str(worker),
        ],
        text=True,
        capture_output=True,
        timeout=150,
    )
    if result.returncode:
        # torchrun stderr may contain platform addresses and GPU UUIDs.
        raise RuntimeError(
            f"torchrun exited {result.returncode}; inspect rank diagnostics in the authorized container"
        )
    rows = []
    for line in result.stdout.splitlines():
        if line.startswith("{"):
            row = json.loads(line)
            if row.get("kind") == "real_gpu_correctness":
                rows.append(row)
    if sorted(row["rank"] for row in rows) != list(range(gpus)) or not all(
        row["world_size"] == gpus and row["sum"] == gpus * (gpus + 1) // 2 and row["status"] == "passed"
        for row in rows
    ):
        raise RuntimeError("Missing or invalid NCCL per-rank evidence")
    return sorted(rows, key=lambda row: row["rank"])


def run(args, path, meta):
    meta["source"] = "inventory"
    if args.smoke == "inventory":
        return
    cap = "cuda_execution" if args.smoke == "cuda" else "nccl_collective"
    states = meta["environment"]["capabilities_requiring_smoke_tests"]
    states[cap] = "blocked"
    if args.smoke == "nccl" and (args.profile != "cloud-h200-multi" or args.gpus not in (2, 3)):
        raise ValueError(
            "NCCL requires PROFILE=cloud-h200-multi and explicit --gpus 2 or 3 for allocated devices"
        )
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable in the selected environment")
    if args.smoke == "cuda":
        value = torch.arange(8, device="cuda").sum().item()
        if value != 28:
            raise RuntimeError(f"CUDA sum mismatch: {value}")
        evidence = {"sum": value}
    else:
        if torch.cuda.device_count() < args.gpus or not torch.distributed.is_nccl_available():
            raise RuntimeError("Insufficient visible CUDA devices or NCCL backend unavailable")
        evidence = {"ranks": nccl_smoke(args.gpus)}
    meta["smoke_evidence"] = evidence
    states[cap] = "passed"
    meta["source"] = "gpu_measured"
