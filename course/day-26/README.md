# Day 26 · 在 Dynamo 追踪两个 Worker 的路由

带长前缀的请求来到两个 worker，缓存多的那个也许已经很忙。找出 Dynamo 根据哪些状态做决定，决定后能否在日志中看到。

**实验起点**　两张 H200、固定 Dynamo release、两个各占一张卡的聚合 worker。复用 Day 10 的输入与 Day 19 的轮询基线。

## 动手要求

1. 从 frontend、router、worker、KV event 到 planner 画出控制路径，标注哪一层看到排队和缓存信息。
2. 按该版本示例部署两个聚合 worker，在相同缓存设置下比较轮询与 KV-aware 策略；记录请求 ID、目标 worker、命中统计和等待。
3. 若 Day 20 的 1P1D 已通且集群支持，复现到 Kubernetes，核实实际使用的连接器和传输路径；另列 P/D 结果。

## 当天验收

- [ ] 交付版本、配置、两个真实 worker 的请求证据与延迟/命中对照，能解释一个命中高但排队长的样本。
- [ ] 若平台阻塞，保留实际错误与 Day 19 的已测基线，注明未部署的 Dynamo 组件。

延伸阅读 · [NVIDIA Dynamo](https://github.com/ai-dynamo/dynamo)
