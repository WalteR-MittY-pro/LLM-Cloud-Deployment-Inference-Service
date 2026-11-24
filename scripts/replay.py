#!/usr/bin/env python3
"""Replay an offered request trace. Output JSONL contains no key or prompt."""
import argparse
import concurrent.futures
import json
import os
import threading
import time
from probe import observe

p = argparse.ArgumentParser()
p.add_argument("trace", help="JSONL with at_ms, tenant (A/B), prompt, max_tokens, in_quota")
p.add_argument("--url", default="http://127.0.0.1:8080")
p.add_argument("--model", default="lab-model")
p.add_argument("--clients", type=int, default=100)
args = p.parse_args()
with open(args.trace) as src:
    rows = [json.loads(line) for line in src if line.strip()]
keys = {k: os.getenv("LAB_KEY_"+k,"") for k in ("A","B")}
if not rows or args.clients < 1 or any(r["tenant"] not in keys or r["at_ms"] < 0 for r in rows):
    p.error("invalid trace or client count")
rows.sort(key=lambda r: r["at_ms"])
lock = threading.Lock()
def run(row, index):
    start_ms = (time.monotonic()-origin)*1000
    result = observe(args.url,args.model,row["prompt"],row["max_tokens"],keys[row["tenant"]])
    result.update(i=index,tenant=row["tenant"],scheduled_ms=row["at_ms"],start_ms=start_ms,
                  dispatch_lag_ms=start_ms-row["at_ms"],in_quota=row["in_quota"],offered_class=row.get("offered_class"))
    with lock:
        print(json.dumps(result,ensure_ascii=False), flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=args.clients) as pool:
    origin = time.monotonic()
    pending = []
    for i,row in enumerate(rows):
        time.sleep(max(0, origin+row["at_ms"]/1000-time.monotonic()))
        pending.append(pool.submit(run,row,i))
    for f in pending:
        f.result()
