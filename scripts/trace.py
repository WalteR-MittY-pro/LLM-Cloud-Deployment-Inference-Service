#!/usr/bin/env python3
"""Deterministic synthetic trace; lengths in tokens must be observed on the real tokenizer."""
import argparse
import json
p=argparse.ArgumentParser()
p.add_argument("mode",choices=["burst","steady","noisy"])
p.add_argument("--count",type=int,default=100)
p.add_argument("--rps",type=float,default=5)
a=p.parse_args()
if a.rps<=0 or a.count<=0:p.error("positive count/rps required")
for i in range(a.count):
    for extra in range(5 if a.mode=="noisy" and a.count//3<=i<2*a.count//3 else 1):
        tenant="A" if extra or i%2==0 else "B"
        long_input=(i+extra)%4==0
        text=("Explain scheduling and the source of latency. "*(240 if long_input else 4))
        print(json.dumps({"at_ms":0 if a.mode=="burst" else round(i*1000/a.rps),
                          "tenant":tenant,"prompt":f"Trial {i}-{extra}. "+text,
                          "max_tokens":128 if long_input else 32,
                          "offered_class":"surge" if extra else "base","in_quota":None}))
