# Day 03 · 手写 Decoder-only Transformer Forward

**[先读本课的原理、图示、走读与自测](lesson.md)** · [实验记录协议](../../docs/experiment-protocol.md)

给定一行 token ID，模型在哪一步把它变成对下一个 token 的打分？今天从 embedding 写到 logits，每次变形都标明轴的语义。

**实验起点**　先用随机权重的小模型；再加载与 Day 01 相同 revision 的 Qwen 小模型作为预训练对照。

## 动手要求

1. 实现 Embedding、RMSNorm、Q/K/V 投影、RoPE、因果 Attention、输出投影、残差和 SwiGLU；堆叠后接最终归一化与 LM head。
2. 写下 B、S、hidden、Q heads、KV heads、head_dim 各轴；核对缩放、旋转位置和 KV 分组。先跑 B=1，再跑 B>1。
3. 选一个能严格对齐的层，复制预训练参数、关闭 dropout，用同样输入和精度分别跑自己的实现和 Transformers，逐层找第一个偏差。

## 当天验收

- [ ] 交付 forward 实现、形状标注图和至少一个与预训练层的 assert_close 检查；说明哪些部分已对齐。
- [ ] 替换序列最后一个 token，验证更早位置的 logits 保持一致，并解释因果掩码。

延伸阅读 · [Transformers 源码](https://github.com/huggingface/transformers)
