# Day 27 · 跟踪 llm-d 的端点选择

Kubernetes 能选中一个就绪端点，LLM 服务还想知道该端点正在排多少请求、缓存了哪些前缀。今天追踪一次额外的选择过程。

**实验起点**　固定 llm-d release；使用现有 Gateway、双副本 GPU 服务和足够的 namespace 权限。Day 28 主项目可选 Dynamo、llm-d 或最小自研 Router。

## 动手要求

1. 定位 InferencePool、Gateway、Endpoint Picker 和 scoring 插件的分工。沿一个请求画出候选端点建立、过滤、评分、转发的次序。
2. 用共享前缀和热点会话比较轮询、load-aware 和 prefix-aware 的目标端点；记录队列、命中与 TTFT，核对 EPP 的实际选择日志。
3. 如果无法部署集群级组件，用真实版本源码写一个可测的简化评分函数，给出候选端点输入和选中结果。汇总与 Dynamo 的状态来源、部署条件和可观察信号。

## 当天验收

- [ ] 交付一个能复现的路由实验或最小评分实现；分别标记源码推导、模拟选择与双副本真实转发。
- [ ] 为 Day 28 选定一个能接入双副本的后端，描述一条如何独立验证其决策的路径。

延伸阅读 · [llm-d 项目](https://github.com/llm-d/llm-d) · [Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/)
