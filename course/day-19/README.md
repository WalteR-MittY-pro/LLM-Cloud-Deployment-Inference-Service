# Day 19 · 同一负载比较 TP1、TP2 与双副本

给你两张卡，应该拆一份模型还是各放一份？用同一批请求区分单请求加速、服务容量和每张卡的有效产出。

**实验起点**　`PROFILE=cloud-h200-multi`，同一容器内两张已分配 H200。优先 Qwen3-32B BF16，先确认单卡能放下权重与 KV。复用 Day 12 的[负载格式](../../benchmarks/schemas/workload.json)、阈值和[统计口径](../../docs/experiment-protocol.md)。

## 动手要求

1. 依次部署单卡单副本、双卡 TP2 单实例、两份 TP1 独立实例。记录设备、端口、模型 revision、KV 容量与启动命令。
2. 给双副本接轮询路由，保存请求 ID→实例映射，使用 Day 07/10 的同一请求集与到达顺序测量。保留脚本、模型设置和原始记录供 Day 28 复跑。
3. 对齐总卡数比较 TP2 与双副本，另用单卡作参照。统计 TTFT、TPOT、goodput/GPU、吞吐、GPU-hours 和错误；结合 Day 18 的通信数据解释变化。

已按上述三种配置分别启动服务后，可用 `make lab DAY=19 ENV=vllm PROFILE=cloud-h200-multi IMPL=reference ARGS="--model Qwen/Qwen3-32B"` 走同一 API 回放器。每组更换已就绪的端点并保留命令、卡分配和路由日志；回放器不启动 TP 或副本。

## 当天验收

- [ ] 提交三种配置和逐请求结果，两张卡上的轮询日志能证明两个副本都实际接到请求。
- [ ] 标出长上下文容量与服务吞吐分别由哪组支持；可选 72B TP2 容量实验单独列出。

延伸阅读 · [vLLM 并行与扩展](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
