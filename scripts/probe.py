#!/usr/bin/env python3
"""Client-side streaming observation. Print content timestamps and a final JSON result."""
import argparse
import http.client
import json
import os
import time
import urllib.error
import urllib.request

def observe(url, model, prompt, max_tokens, key="", show=False, timeout=120):
    begin = time.monotonic()
    record = {"status": None, "complete": False, "ttft_ms": None, "output_tokens": None,
              "prompt_tokens": None, "tpot_ms": None, "request_id": None}
    last_content = None
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "stream": True, "max_tokens": max_tokens,
               "stream_options": {"include_usage": True}}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions",
                                 json.dumps(payload).encode(), headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            record["status"] = response.status
            record["request_id"] = response.headers.get("X-Request-ID")
            for line in response:
                if not line.startswith(b"data:"):
                    continue
                data = line[5:].strip()
                if data == b"[DONE]":
                    record["complete"] = True
                    break
                event = json.loads(data)
                if event.get("error"):
                    record["error"] = str(event["error"])
                    break
                choices = event.get("choices") or []
                content = choices[0].get("delta", {}).get("content") if choices else None
                if content:
                    last_content = (time.monotonic() - begin) * 1000
                    if record["ttft_ms"] is None:
                        record["ttft_ms"] = last_content
                    if show:
                        print(f"{last_content:9.1f} ms  {content!r}", flush=True)
                usage = event.get("usage") or {}
                for dst, src in (("prompt_tokens","prompt_tokens"), ("output_tokens","completion_tokens")):
                    if src in usage:
                        record[dst] = usage[src]
    except urllib.error.HTTPError as exc:
        record["status"] = exc.code
        record["request_id"] = exc.headers.get("X-Request-ID")
        record["error"] = exc.reason
    except (OSError, ValueError, EOFError, http.client.HTTPException) as exc:
        record["error"] = str(exc)
    record["e2e_ms"] = (time.monotonic() - begin) * 1000
    if last_content is not None and (record["output_tokens"] or 0) > 1:
        record["tpot_ms"] = (last_content - record["ttft_ms"]) / (record["output_tokens"] - 1)
    return record

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument("--model", default="lab-model")
    p.add_argument("--prompt", default="用两句话解释云服务。")
    p.add_argument("--max-tokens", type=int, default=64)
    a = p.parse_args()
    result = observe(a.url, a.model, a.prompt, a.max_tokens, os.getenv("LAB_KEY",""), True)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["complete"] else 1)
