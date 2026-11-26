# Day 17 · 量化与投机解码的收益边界

显存变少之后服务是否更快？让 draft 多提议几个 token 后 target 是否更省时？用两组独立实验回答。

**实验起点**　H200 优先对照同源 BF16 与对应 FP8 权重；Ada 使用其支持的量化格式。沿用 Day 12 的负载与 SLO。

## 动手要求

1. 记录 checkpoint 来源、基座 revision、权重/激活/KV 各自的精度、实际后端。固定模型级别与任务集，比较显存、质量和不同并发下的延迟。
2. 在支持的版本上单独尝试 n-gram speculation，对重复度高和低的输入记录提议/接受 token 与验证开销；保持量化设置一致。
3. 按低/高并发比较两种开关，记录样本数、精度误差或固定题集得分，以及 GPU 时间。

## 当天验收

- [ ] 至少完成一组真实量化对照，交付 checkpoint、启动参数、原始测量与质量检查结果。
- [ ] 给出投机解码实验的接受率与延迟，或保留具体阻塞；汇总 Day 13–16 的正确性与 Ada/Hopper 对照完成情况。

延伸阅读 · [vLLM 投机解码](https://docs.vllm.ai/en/stable/features/speculative_decoding/) · [投机采样论文](https://arxiv.org/abs/2211.17192)
