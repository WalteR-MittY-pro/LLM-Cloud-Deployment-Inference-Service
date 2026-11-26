# LLM Inference Lab 课程建设约定

每次改课前检查 HEAD、工作区、当日入口、相邻课程的输入输出和已有测试。保留有教学价值的实现与历史数据。

- 新课从 [课程模板](docs/lesson-template.md) 开始。讲清同一个工程问题的动机、图示、推导、手算、实现、源码和验收。核心机制留在 starter；reference 走同一入口与契约。
- 教学代码沿 Day 03 → 04 → 05 复用。已有工业引擎通过 API 独立运行。共享逻辑只保留一份，先有实际调用者再抽取。
- 新增行为附独立判据。数值对照记录模型和 tokenizer revision、Transformers commit、dtype 和容差。使用 make check 运行 CPU 检查；未实现的 starter 可以按设计失败。
- 实验走 make lab，保留独立 Run ID、失败及部分观测。严分理论、模拟、CPU、真实 GPU 和真正的在线 Agent。用实测设备与样本做性能判断。
- GPU/CUDA/K8s 按实际授权探测。不得修改共享机器驱动、申请未分配卡或更改集群组件来让课程通过。
- 后续批次从[验收清单](docs/course-review.md)选任务；更新交叉引用、原始证据和未测项。
