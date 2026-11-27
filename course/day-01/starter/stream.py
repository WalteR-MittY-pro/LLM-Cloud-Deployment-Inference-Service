import json
from urllib.error import HTTPError
from urllib.request import urlopen


def read_chat_stream(lines):
    """从 vLLM 单行 JSON SSE 事件中 yield 正文。识别服务错误与提前断流。"""

    for raw_line in lines:
        line = raw_line.decode("utf-8").rstrip("\r\n")
        if not line.startswith("data:"):
            continue

        payload = line.removeprefix("data:").lstrip()
        if payload == "[DONE]":
            return

        event = json.loads(payload)
        if "error" in event:
            raise RuntimeError(f"推理服务返回错误：{event['error']}")

        for choice in event.get("choices", []):
            content = choice.get("delta", {}).get("content")
            if content:
                yield content

    raise ValueError("响应中断，未收到 [DONE]；已收到的正文可能不完整")


def open_stream(request, timeout, raw_log=None):
    """服务器返回 HTTP 400 时，具体原因往往写在响应正文里。 
    比如终端默认只显示 HTTP Error 400: Bad Request，正文里却可能写着“输入长度超过模型上限”。
    `open_stream` 把这段正文读出来，按需保存原始字节，再把状态码和具体原因一起报给调用者。"""
    try:
        return urlopen(request, timeout=timeout)
    except HTTPError as error:
        # with error 的作用是读完后自动关闭这个 HTTP 错误响应。
        with error:
            detail = error.read(65536)
        if raw_log is not None:
            raw_log.write(detail)
        message = detail.decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {error.code}: {message}") from error
