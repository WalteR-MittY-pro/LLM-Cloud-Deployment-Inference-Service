def attend(q, k, v, past=None):
    """q/k 已经旋转；沿序列轴追加历史，按绝对位置遮罩，返回 context 和紧凑 KV。"""
    raise NotImplementedError("Day 04：实现分组和带历史的因果注意力")
