# Day 20 · 拆分 Prefill 与 Decode 并观察 KV 传输

把读取长 prompt 和持续生成拆到两张卡上，要先把 KV 从前者送到后者。传输成本能否被阶段隔离收益抵消？

**实验起点**　`cloud-h200-multi` 的两张授权 H200；沿用同一模型、两卡两聚合副本的基线。先核对平台支持的连接器、IPC 与实际传输路径，家庭 LAN 的传输成本另记。

## 动手要求

1. 选固定 release 的 vLLM 或 Dynamo 官方 P/D 示例；对齐模型、revision、dtype、KV 布局及 block size，记录连接器和实际使用的传输路径。
2. 跑通 1P1D 的一次真实流式请求，使两个 worker 日志能关联到同一请求；观察 KV 传输量、耗时和最终输出。
3. 用相同模型、负载和两张卡比较聚合双副本与 1P1D，分别测长输入/短输出和短输入/长输出的尾延迟、goodput。

## 当天验收

- [ ] 交付双 worker 可关联的日志、完整响应、基线与测量结果；估算 KV 字节并同实测比较。
- [ ] 连接器或拓扑阻塞时交付实际错误、已完成的聚合基线及待验条件，把 P/D 性能栏留空。可继续单卡 chunked prefill/prefix cache，或独立记录家庭 LAN 传输成本。

延伸阅读 · [vLLM 分离式 Prefill](https://docs.vllm.ai/en/stable/features/disagg_prefill/) · [DistServe 论文](https://arxiv.org/abs/2401.09670)
