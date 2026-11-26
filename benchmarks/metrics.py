"""只从真正观测到的事件计算指标；所有时间统一用毫秒。"""

import math
import statistics
import time


def timed(fn, device):
    if device == "cuda":
        import torch

        start = torch.cuda.Event(enable_timing=True)
        end = torch.cuda.Event(enable_timing=True)
        start.record()
        result = fn()
        end.record()
        end.synchronize()
        return result, start.elapsed_time(end)
    start = time.perf_counter()
    result = fn()
    return result, (time.perf_counter() - start) * 1000


def token_metrics(times_ms):
    gaps = [b - a for a, b in zip(times_ms, times_ms[1:])]
    if any(x < 0 for x in times_ms) or any(x < 0 for x in gaps):
        raise ValueError("token 时间必须非负且单调")
    return {
        "ttft_ms": times_ms[0] if times_ms else None,
        "itl_ms": gaps,
        "tpot_ms": statistics.mean(gaps) if gaps else None,
    }


def summary(values):
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(values),
        "p50": statistics.median(values),
        "p95": ordered[math.ceil(0.95 * len(values)) - 1],
        "p99": ordered[math.ceil(0.99 * len(values)) - 1],
        "min": ordered[0],
        "max": ordered[-1],
    }


def goodput(rows, window_seconds, ttft_limit_ms, tpot_limit_ms):
    if window_seconds <= 0:
        raise ValueError("测量窗口必须为正")
    passed = [
        row
        for row in rows
        if row["status"] == "ok"
        and row.get("ttft_ms") is not None
        and row["ttft_ms"] <= ttft_limit_ms
        and row.get("tpot_ms") is not None
        and row["tpot_ms"] <= tpot_limit_ms
    ]
    return len(passed) / window_seconds
