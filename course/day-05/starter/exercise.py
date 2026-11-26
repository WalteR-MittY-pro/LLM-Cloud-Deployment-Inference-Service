def sample(logits, temperature=0.0, top_k=0, top_p=1.0, generator=None):
    """输入 [1,V]，返回 [1,1] 的 token ID。"""
    raise NotImplementedError("Day 05：实现 greedy 和带过滤的随机采样")


def generate(step, ids, budget, eos_ids, **sampling):
    """step(ids, past) 返回 logits 和新缓存；逐个 yield token，包括 EOS。"""
    raise NotImplementedError("Day 05：实现 prefill、增量 decode 和停止条件")
