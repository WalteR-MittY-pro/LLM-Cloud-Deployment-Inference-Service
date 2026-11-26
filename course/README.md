# 28 天课程

每天打开对应目录的 README，先读要回答的问题，再看动手要求与当天验收。Day 01–05 的 starter 留给学习者，reference 与数值测试独立。先读每课的推导与走读，再做实验；Day 06–28 保留逐日要求，实施批次和未测项见[课程审查](../docs/course-review.md)。

建议每天预留 6–8 小时，覆盖阅读、实现、实测和复盘。先用本机验证逻辑，再把同一份代码 clone 到分配的 GPU 服务器。每次实验记录代码 commit、环境/模型 revision、硬件与拓扑、负载、缓存状态、采样次数、原始输出及复现命令。CPU 模拟、单卡 GPU、多卡 GPU 和在线 Agent 的结果各自标明运行条件。

## 环境准备

[Day 00 · Infrastructure Bootstrap](day-00/README.md) 是 28 天主线以外的准备课。先在任一授权 GPU 完成 CUDA 和 Day 01 API 冒烟；家庭 K3s 与云端多卡可随后准备。家庭集群承担 Day 21–25、27，H200 容器承担 Day 18–20、26，Day 28 用两个已部署的 API 联接。见[逐日环境表](day-00/README.md#environment-map)。

## 模型与推理基础

- [Day 01 · 在自己的 GPU 上部署 Qwen](day-01/README.md)
- [Day 02 · 看懂张量的形状、布局和执行时间](day-02/README.md)
- [Day 03 · 手写 Decoder-only Transformer Forward](day-03/README.md)
- [Day 04 · 让 Attention 复用历史 KV](day-04/README.md)
- [Day 05 · 写出从提示词到流式输出的生成循环](day-05/README.md)

## 推理引擎与基准

- [Day 06 · 从 vLLM 的 HTTP 入口追到 GPU Forward](day-06/README.md)
- [Day 07 · 用离散事件模拟器比较批处理策略](day-07/README.md)
- [Day 08 · 实现 KV 块分配与回收](day-08/README.md)
- [Day 09 · 在 Nano-vLLM 跟踪一轮调度](day-09/README.md)
- [Day 10 · 用真实 token 测量前缀缓存](day-10/README.md)
- [Day 11 · 对照 SGLang 与 vLLM 的缓存管理](day-11/README.md)
- [Day 12 · 建立可复现的推理引擎基准](day-12/README.md)

## GPU 与算子优化

- [Day 13 · 写下第一个 CUDA Kernel](day-13/README.md)
- [Day 14 · 用时间线定位 Prefill 与 Decode 的瓶颈](day-14/README.md)
- [Day 15 · 用 Triton 融合算子并检验收益](day-15/README.md)
- [Day 16 · 分开测量 Attention、图重放和编译](day-16/README.md)
- [Day 17 · 量化与投机解码的收益边界](day-17/README.md)

## 多卡推理

- [Day 18 · 测量两张 H200 之间的 NCCL 通信](day-18/README.md)
- [Day 19 · 同一负载比较 TP1、TP2 与双副本](day-19/README.md)
- [Day 20 · 拆分 Prefill 与 Decode 并观察 KV 传输](day-20/README.md)

## 云原生部署与路由

- [Day 21 · 把单卡推理服务装进容器](day-21/README.md)
- [Day 22 · 用 Kubernetes 管理两个 CPU 服务副本](day-22/README.md)
- [Day 23 · 让 Kubernetes 把 GPU 分给推理 Pod](day-23/README.md)
- [Day 24 · 用 Helm、持久化存储和 Gateway 发布模型](day-24/README.md)
- [Day 25 · 把排队、SLO 和扩缩容画在同一条时间线上](day-25/README.md)
- [Day 26 · 在 Dynamo 追踪两个 Worker 的路由](day-26/README.md)
- [Day 27 · 跟踪 llm-d 的端点选择](day-27/README.md)

## 综合实验

- [Day 28 · 让两个推理副本服务一段 Agent 会话](day-28/README.md)

## 哪些成果会继续用

| 节点 | 可以交付的成果 |
| --- | --- |
| Day 05 | 有正确性测试的最小生成循环，能解释与复现 KV Cache |
| Day 12 | 引擎调用链、调度/块管理模拟、可复算的单卡基准 |
| Day 17 | CUDA 与 Triton 程序、正确性对照和 GPU profile |
| Day 20 | 双卡 NCCL 曲线、TP 与双副本对照、P/D 实测或阻塞证据 |
| Day 25 | GPU 容器、Kubernetes 服务、Helm 配置和监控面板 |
| Day 27 | 一种能解释目标端点选择的路由后端或最小实现 |
| Day 28 | 真实双副本上的 Agent 请求回放、策略对照和实验报告 |

Day 07 定下请求格式，Day 10 留下精确共享 token 前缀的输入，Day 12 固定衡量标准，Day 19 保存双副本的轮询配置。Day 28 在确认家庭与云端端点可达后，用同一批输入重跑路由，把服务日志与请求 ID 对齐后再下结论。
