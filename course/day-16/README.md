# Day 16 · 分开测量 Attention、图重放和编译

更换 Attention 后端、少发射 kernel、编译融合解决的是不同问题。把三个变化拆成独立对照，才能知道时间省在哪里。

**实验起点**　单 H200，固定同一 dtype、shape 和数值输入。复用 Day 14 的 trace。

## 动手要求

1. 比较朴素 causal attention 与 SDPA 可用后端，固定掩码并验输出；从 profiler 核实实际 dispatch 的 kernel。
2. 比较 eager 与 CUDA Graph replay，固定输入地址和形状，单列首次 capture。再单独比较 eager 与 torch.compile，分开首次编译和稳态。
3. 改变一个序列长度，观察重编译或图复用条件；用 tiling 和 online softmax 解释 Attention 中减少的显存读写。

## 当天验收

- [ ] 交付三组有数值校验的时间对照，其中首次和稳态独立列出。
- [ ] 为三种优化各给一个生效条件、一个限制和对应证据，并说明稠密 Attention 的计算量如何随序列长度增长。

延伸阅读 · [FlashAttention 论文](https://arxiv.org/abs/2205.14135) · [PyTorch SDPA](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention.html)
