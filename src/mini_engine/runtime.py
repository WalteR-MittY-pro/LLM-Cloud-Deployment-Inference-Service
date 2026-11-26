"""单请求增量生成。每次 yield 一个实际采样到的 token ID。"""

import torch


def sample(logits, temperature=0.0, top_k=0, top_p=1.0, generator=None):
    if temperature < 0 or not 0 < top_p <= 1 or top_k < 0:
        raise ValueError("需要 temperature ≥ 0、top_k ≥ 0、0 < top_p ≤ 1")
    if temperature == 0:
        return logits.argmax(-1, keepdim=True)
    values, indices = (logits.float() / temperature).sort(descending=True)
    if top_k:
        values[..., top_k:] = -torch.inf
    probs = values.softmax(-1)
    # 保留累计概率首次越过 top_p 的 token。
    probs = probs.masked_fill(probs.cumsum(-1) - probs >= top_p, 0)
    return indices.gather(-1, torch.multinomial(probs, 1, generator=generator))


def generate(step, ids, budget, eos_ids, **sampling):
    if ids.size(0) != 1 or budget < 0:
        raise ValueError("生成循环只支持单请求和非负预算")
    cache = None
    for _ in range(budget):
        logits, cache = step(ids, cache)
        ids = sample(logits[:, -1], **sampling)
        token = ids.item()
        yield token
        if token in eos_ids:
            return
