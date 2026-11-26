def read_chat_stream(lines):
    """从 vLLM 单行 JSON SSE 事件中 yield 正文。识别服务错误与提前断流。"""
    raise NotImplementedError("Day 01 Level 2：亲手解析 SSE")


def open_stream(request, timeout, raw_log=None):
    """按给定的秒数建立 HTTP 响应，交给调用者关闭；HTTP 错误保留状态和响应正文。"""
    raise NotImplementedError("Day 01 Level 2：接入读超时并保留 HTTP 错误原因")
