from concurrent.futures import ThreadPoolExecutor
from argparse import Namespace
import hashlib
import json
from pathlib import Path
import sys
import time

from jsonschema import validate

from .lessons import ROOT, lesson
from .records import add_row


def load_workload(filename):
    schema = json.loads((ROOT / "benchmarks/schemas/workload.json").read_text())
    rows = [json.loads(line) for line in Path(filename).read_text().splitlines() if line.strip()]
    seen = set()
    for row in rows:
        validate(row, schema)
        if row["request_id"] in seen:
            raise ValueError("request_id 必须唯一")
        seen.add(row["request_id"])
    if not rows:
        raise ValueError("工作负载为空")
    return sorted(rows, key=lambda r: r["arrival_ms"])


def run(args, path, meta):
    sys.path.insert(0, str(ROOT / "course/day-01"))
    from client import run as chat, read_chat_stream, list_models

    build = lesson(1, args.impl, "request_body").build_request
    parse = lesson(1, args.impl, "stream").read_chat_stream if args.level2 else read_chat_stream
    rows = load_workload(args.workload)
    payload = Path(args.workload).read_bytes()
    (path / "workload.jsonl").write_bytes(payload)
    meta.update(
        source="api_observed",
        model=args.model,
        model_revision=args.model_revision,
        tokenizer_revision=args.tokenizer_revision,
        workload_sha256=hashlib.sha256(payload).hexdigest(),
    )
    available = list_models(args.base_url, args.timeout)
    failed = 0
    for repeat in range(args.warmup + args.repeat):
        phase = "warmup" if repeat < args.warmup else "steady"

        def request(i, row):
            obs = {
                "request_id": row["request_id"],
                "iteration": repeat,
                "phase": phase,
                "ttft_ms": None,
                "tpot_ms": None,
                "arrival_ms": row["arrival_ms"],
                "dispatch_ms": (time.perf_counter() - start) * 1000,
            }
            call = Namespace(
                model=args.model,
                prompt=row["prompt"],
                max_tokens=row["output_token_budget"],
                base_url=args.base_url,
                timeout=args.timeout,
                record=None,
            )
            tick = time.perf_counter()
            try:
                with (path / f"stream-{repeat}-{i}.sse").open("wb") as raw:
                    answer = chat(
                        call, build, parse, observation=obs, echo=False, raw_log=raw, available=available
                    )
                obs.update(status="ok", answer=answer["answer"], text_chunks=answer["text_chunks"])
            except Exception as exc:
                obs.update(
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    attempt_elapsed_ms=(time.perf_counter() - tick) * 1000,
                )
            return obs

        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            pending = []
            start = time.perf_counter()
            for i, row in enumerate(rows):
                deadline = start + row["arrival_ms"] / 1000
                time.sleep(max(0, deadline - time.perf_counter()))
                pending.append(pool.submit(request, i, row))
            observations = [f.result() for f in pending]
        seconds = time.perf_counter() - start
        for obs in observations:
            add_row(path, **obs)
        success = sum(obs["status"] == "ok" for obs in observations)
        failed += len(rows) - success
        meta.setdefault("windows", []).append(
            {"phase": phase, "seconds": seconds, "successful_requests_per_second": success / seconds}
        )
    if failed:
        raise RuntimeError(f"{failed} 次请求失败，见 requests.jsonl")
