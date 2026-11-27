def project(x, weight):
    """[B,S,H] × [H,O] → [B,S,O]；也支持非连续张量。"""
    return x@weight
