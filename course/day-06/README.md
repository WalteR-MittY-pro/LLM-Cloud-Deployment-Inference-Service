# Day 06 · 从 vLLM 的 HTTP 入口追到 GPU Forward

Day 05 的循环一次处理一个请求。服务同时面对多个用户时，接收请求、决定本轮执行谁、执行 forward 分别发生在哪里？

**实验起点**　使用 Day 01 安装的 vLLM 版本，取同一 release 的源码。准备一条短请求和对应服务日志。

## 动手要求

1. 从 chat completions 的路由开始，沿请求提交路径定位 EngineCore、Scheduler、KVCacheManager、Worker 和 ModelRunner。记录实际文件、符号、调用方向与进程边界。
2. 发送短请求，把请求 ID 或可关联时间点与服务日志对应起来。找出 waiting→running、分配 KV 块、采样结果返回的代码位置。
3. 从 GPU 执行路径反向追一次输出返回，单独标出源码能证明的边和日志实际观察到的边。

## 当天验收

- [ ] 提交固定 tag/commit 的调用图，每个关键跳转给出文件和符号；能从 HTTP 入口走到一次 forward 并回到响应。
- [ ] 用一个具体请求解释 API 进程、引擎调度和 GPU runner 各自在等什么。

延伸阅读 · [vLLM 架构](https://docs.vllm.ai/en/stable/design/arch_overview/)
