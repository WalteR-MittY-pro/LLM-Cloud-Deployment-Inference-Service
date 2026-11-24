#!/usr/bin/env python3
"""Pipe actual retrieval output (including path/section) on stdin. No fixture fallback."""
import argparse
import os
import sys
from probe import observe
p=argparse.ArgumentParser()
p.add_argument("question")
p.add_argument("--url",default="http://127.0.0.1:8080")
p.add_argument("--model",default="lab-model")
a=p.parse_args()
evidence=sys.stdin.read().strip()
if not evidence:p.error("pipe actual CJMP search_docs/read_section output including source references")
prompt=f"根据以下检索资料回答问题，给出资料路径。资料不足请明确说明。\n问题：{a.question}\n资料：\n{evidence}"
res=observe(a.url,a.model,prompt,256,os.environ.get("LAB_KEY",""),show=True)
print("request_id:",res["request_id"],"complete:",res["complete"],"ttft_ms:",res["ttft_ms"])
raise SystemExit(0 if res["complete"] else 1)
