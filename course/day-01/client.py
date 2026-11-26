"""运行 python client.py --help 查看 GPU 服务调用方式。"""

import argparse
import json
import time
from pathlib import Path
from urllib.request import Request, urlopen


def read_chat_stream(lines):
    """读取 vLLM chat completions 的单行 JSON SSE 事件。"""
    for raw in lines:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line.startswith("data:"):
            continue
        data = line[5:].lstrip()
        if data == "[DONE]":
            return
        event = json.loads(data)
        if "error" in event:
            raise RuntimeError(f"推理服务返回错误: {event['error']}")
        for choice in event.get("choices", []):
            content = choice.get("delta", {}).get("content")
            if content:
                yield content
    raise ValueError("连接提前关闭，缺少 [DONE]")


def run(args, build_request):
    body = build_request(args.model, args.prompt, args.max_tokens)
    base = args.base_url.rstrip("/")
    with urlopen(f"{base}/v1/models", timeout=15) as response:
        available = [m["id"] for m in json.load(response)["data"]]
    if args.model not in available:
        raise ValueError(f"请求模型 {args.model} 未加载，服务端已列出 {available}")

    request = Request(f"{base}/v1/chat/completions", json.dumps(body).encode(),
                      headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    chunks = []
    with urlopen(request, timeout=120) as response:
        for text in read_chat_stream(response):
            if not chunks:
                first_text_ms = (time.perf_counter() - start) * 1000
            chunks.append(text)
            print(text, end="", flush=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if not chunks:
        raise ValueError("流已结束，但没有收到回答文本")
    print()
    record = {
        "available_models": available, "request": body, "answer": "".join(chunks),
        "done": True, "text_chunks": len(chunks),
        "first_text_ms": round(first_text_ms, 2), "end_to_end_ms": round(elapsed_ms, 2),
    }
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(f"首段正文 {first_text_ms:.1f} ms，总耗时 {elapsed_ms:.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="向已启动的 vLLM 发起一次流式对话")
    parser.add_argument("--model", required=True, help="/v1/models 列出的模型 ID")
    parser.add_argument("--prompt", default="用一句话解释什么是 KV Cache。")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--record", type=Path, help="成功结束时保存 JSON 记录")
    parser.add_argument("--reference", action="store_true", help="使用独立参考答案")
    args = parser.parse_args()
    if args.reference:
        from reference.request_body import build_request
    else:
        from starter.request_body import build_request
    run(args, build_request)
