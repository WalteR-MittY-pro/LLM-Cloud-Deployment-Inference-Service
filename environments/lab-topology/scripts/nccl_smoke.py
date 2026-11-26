#!/usr/bin/env python3
"""Explicitly launched single-container NCCL correctness smoke test, not benchmark."""

import datetime
import json
import os
import torch
import torch.distributed as dist


def main():
    local_rank = int(os.environ["LOCAL_RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    local_world_size = int(os.environ["LOCAL_WORLD_SIZE"])
    if world_size != local_world_size or world_size not in (2, 3):
        raise RuntimeError("This lab only supports two or three allocated GPUs in one container")
    if torch.cuda.device_count() < local_world_size:
        raise RuntimeError("Insufficient CUDA-visible devices")
    if not dist.is_nccl_available():
        raise RuntimeError("NCCL backend unavailable")
    torch.cuda.set_device(local_rank)
    dist.init_process_group("nccl", timeout=datetime.timedelta(seconds=90))
    try:
        rank = dist.get_rank()
        x = torch.tensor([rank + 1.0], device=f"cuda:{local_rank}")
        dist.all_reduce(x)
        if x.item() != world_size * (world_size + 1) // 2:
            raise RuntimeError("AllReduce wrong value")
        print(
            json.dumps(
                {
                    "kind": "real_gpu_correctness",
                    "rank": rank,
                    "world_size": world_size,
                    "sum": x.item(),
                    "status": "passed",
                }
            ),
            flush=True,
        )
    finally:
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
