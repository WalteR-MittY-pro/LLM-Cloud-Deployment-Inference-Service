# Day 09 · 在 Nano-vLLM 跟踪一轮调度

把昨天写的块表和前天写的队列放回一个可运行的小引擎，找到它们真正相遇的地方。

**实验起点**　固定 Nano-vLLM 的 commit，使用其支持的模型和独立环境，在单 GPU 先跑通自带示例。

## 动手要求

1. 沿 example、LLMEngine、Sequence、Scheduler、BlockManager、ModelRunner 追到 Attention，标出 prefill 和 decode 的分叉。
2. 只加一处每轮日志，记录序列 ID、当前阶段和分配/空闲块数。用两条不同长度的输入观察短请求何时离开。
3. 固定模型、输入和 greedy 参数，对比改动前后的 token 序列。映射到 Day 07 和 08 的数据结构，指出一个简化假设。

## 当天验收

- [ ] 提交源码 commit、最小 diff、GPU 运行命令与一段可关联请求的日志。
- [ ] 能够仅凭源码和日志，还原一轮从选中请求到产出 token 的调用顺序。

延伸阅读 · [Nano-vLLM](https://github.com/GeeeekExplorer/nano-vllm)
