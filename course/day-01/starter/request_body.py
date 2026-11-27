"""在这里完成 Day 01 的练习。"""


def build_request(model: str, prompt: str, max_tokens: int) -> dict:
    """构造单轮流式对话的 JSON 请求体，字段约定见当天 README。"""
    if max_tokens < 1:
        raise ValueError("max_tokens 必须大于 0")
    if not model.strip() or not prompt.strip():
        raise ValueError("模型名和问题必须包含非空白字符")

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    return body
