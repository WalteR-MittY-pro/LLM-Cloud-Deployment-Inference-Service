# Day 04 · 让 Attention 复用历史 KV

**[先读本课的原理、图示、走读与自测](lesson.md)** · [实验记录协议](../../docs/experiment-protocol.md)

生成第 101 个 token 时，前 100 个 token 的 K/V 已算过。今天要让缓存省掉重算，并证明复用后输出仍然正确。

**实验起点**　复用 Day 03 的 Attention 和相同输入；在单 GPU 固定 dtype、batch 和 token 序列。

## 动手要求

1. 保留整段重算基线，另写支持 prefill 和单步 decode 的路径，沿序列轴追加 K/V，正确递增位置。标出 MHA、GQA、MQA 的 KV head 数。
2. 对同一固定序列逐位置比较两条路径的 logits。测 128、512、1024、2048 上下文，分开记录 prefill 与后续 decode。
3. 按 2 × 层数 × KV heads × head_dim × 序列长度 × batch × 每元素字节估算缓存，再记录峰值显存；解释权重、临时量与统计口径。

## 当天验收

- [ ] 交付缓存实现和逐位置正确性测试，给出精度与容差；验证两个请求不会串用缓存。
- [ ] 提供四种长度下的原始 GPU 时间与显存表，解释缓存节省了哪一步、仍要读哪些数据。

延伸阅读 · [Qwen3-4B 模型配置](https://huggingface.co/Qwen/Qwen3-4B/blob/main/config.json)
