# LLM Inference Lab

在 28 天里，从一次真实 GPU 模型调用开始，亲手实现推理循环、KV Cache、调度器与 GPU kernel，最后在家庭 RTX 与云端 H200 的 API 之间回放 Agent 会话，并比较路由策略。

**[Day 00 · Infrastructure Bootstrap](course/day-00/README.md)** · **[开始第 1 天](course/day-01/README.md)** · **[查看 28 天课程目录](course/README.md)**

Day 01–05 已提供教材、图示、练习、独立参考和测试。Day 03 的 Qwen3 forward 经 Day 04 接入 KV cache，Day 05 直接用于生成。Day 06–28 有逐日要求，后续按批次实施。见[课程审查与建设进度](docs/course-review.md)。

## 本地先跑通第一周

~~~bash
make doctor
make setup ENV=cpu
make check
make lab DAY=05 IMPL=reference ARGS="--length 8 --budget 4"
~~~

练习用 `make test DAY=03`；参考用 `make test DAY=03 IMPL=reference`。两者执行同一套测试。[环境选择](environments/README.md)与[实验协议](docs/experiment-protocol.md)说明如何在 GPU 上复现。

## 在 GPU 服务器开始

~~~bash
git clone https://github.com/WalteR-MittY-pro/LLM-Inference-Lab.git llm-inference-lab
cd llm-inference-lab/course/day-01
~~~

按[本课步骤](course/day-01/README.md)先部署 Qwen3-0.6B，再切换 Qwen3-4B。两个终端一个运行 vLLM，另一个使用你完成的 Python 客户端访问服务。只有 CPU 时可以先完成请求构造与测试。需要 GPU 的验收项以对应设备上的原始记录为准。
