#!/usr/bin/env python3
"""Score a single replay window. Refuse to invent in-quota labels or classify missing usage."""
import argparse
import json
import math
import sys
p=argparse.ArgumentParser()
p.add_argument("--ttft-ms",type=float,required=True)
p.add_argument("--tpot-ms",type=float,required=True)
a=p.parse_args()
rows=[json.loads(line) for line in sys.stdin if line.strip()]
if not rows:p.error("empty replay")
def good(r):
    speed=r["tpot_ms"]
    return (r["status"]==200 and r["complete"] and r["ttft_ms"] is not None
            and r["ttft_ms"]<=a.ttft_ms and (r["output_tokens"]==1 or (speed is not None and speed<=a.tpot_ms)))
def p95(xs):
    return sorted(xs)[math.ceil(len(xs)*.95)-1] if xs else None
seconds=max((r["start_ms"]+r["e2e_ms"]) for r in rows)/1000
print("window_s",round(seconds,3),"all_good_requests_per_s",round(sum(map(good,rows))/seconds,3))
for tenant in sorted({r["tenant"] for r in rows}):
    rr=[r for r in rows if r["tenant"]==tenant]
    under=[r for r in rr if r["in_quota"] is True]
    print(tenant,{"offered":len(rr),"good":sum(map(good,rr)),
        "429":sum(r["status"]==429 for r in rr),"incomplete_or_failed":sum(not r["complete"] for r in rr),
        "p95_completed_ttft_ms":p95([r["ttft_ms"] for r in rr if r["complete"] and r["ttft_ms"] is not None]),
        "p95_dispatch_lag_ms":p95([r["dispatch_lag_ms"] for r in rr]),
        "within_quota_good_over_offered":[sum(map(good,under)),len(under)] if under else None,
        "unlabelled":sum(r["in_quota"] is None for r in rr)})
