"""Day 01 参考实现，可用同一套测试验证。"""


def build_request(model: str, prompt: str, max_tokens: int) -> dict:
    if not model.strip() or not prompt.strip():
        raise ValueError("模型名和问题必须包含非空白字符")
    if max_tokens < 1:
        raise ValueError("输出 token 上限必须是正数")
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0,
        "chat_template_kwargs": {"enable_thinking": False},
    }
