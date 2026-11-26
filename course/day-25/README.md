# Day 25 · 把排队、SLO 和扩缩容画在同一条时间线上

用户在等首 token 时，GPU 利用率可能很高也可能很低。把请求、引擎和 GPU 的观测对齐，再决定加卡能否帮忙。

**实验起点**　家庭 K3s 的 Day 24 服务与 Day 12 的 SLO/负载。核对 Prometheus、Grafana、DCGM 和指标适配器的可用状态，区分两节点物理容量与副本就绪状态。

## 动手要求

1. 读取当前 /metrics 的实际指标名，建立流量/失败、延迟分位、队列/KV、GPU 四组面板；按模型/副本对照单位、标签和直方图桶。
2. 回放逐渐增加再减小的负载，使用队列或 SLO 指标观察 1→2 副本的扩容过程，记录扩容触发、调度、加载、Ready 和首个请求的时刻。
3. 对比固定副本与扩缩容的 goodput、错误率和 GPU-hours；在自己的实验中重建一个 Pod，测故障到恢复。无额外卡时记录 Pending 原因。

## 当天验收

- [ ] 交付可导入的面板、查询表达式、采集配置和对齐后的时间线，能指出某次排队增长对应的服务延迟。
- [ ] 有适配器及 GPU 配额时记录真实弹性；缺少适配器时可另交模拟曲线，并将真实扩缩容标为待验。

延伸阅读 · [vLLM 指标](https://docs.vllm.ai/en/stable/usage/metrics/) · [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
