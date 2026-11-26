# LLM Inference Lab

在 28 天里，从一次真实 GPU 模型调用开始，亲手实现推理循环、KV Cache、调度器与 GPU kernel，最后用两张卡对比面向 Agent 会话的路由策略。

**[开始第 1 天](course/day-01/README.md)** · **[查看 28 天课程目录](course/README.md)**

第 1 天包含从零部署指南、固定版本的服务配置、练习骨架、测试和独立参考实现。Day 02–28 已写好每天的实验要求、交付物和验收条件；后续实现随学习进度展开。

## 在 GPU 服务器开始

~~~bash
git clone https://github.com/WalteR-MittY-pro/LLM-Inference-Lab.git llm-inference-lab
cd llm-inference-lab/course/day-01
~~~

按[本课步骤](course/day-01/README.md)先部署 Qwen3-0.6B，再切换 Qwen3-4B。两个终端一个运行 vLLM，另一个使用你完成的 Python 客户端访问服务。只有 CPU 时可以先完成请求构造与测试。需要 GPU 的验收项以对应设备上的原始记录为准。
