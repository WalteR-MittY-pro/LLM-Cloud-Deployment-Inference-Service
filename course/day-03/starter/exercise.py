from mini_engine.model import attend


def decoder_block(layer, x, cos, sin, past, attention=attend):
    """组装 RMSNorm、Q/K norm、RoPE、GQA、两个残差、SwiGLU。
    从 layer 读取权重。调用传入的 attention；返回 (隐藏状态, 本层 KV)。
    """
    raise NotImplementedError("Day 03：实现一个 Qwen3 decoder block")
