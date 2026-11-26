# 仓库审查与课程建设进度

审查起点是 ee9d381。检查了全部 28 份课程说明、根目录和课程索引、Day 01 的实际入口与测试，以及跨天引用。基线运行 Day 01 reference 的 5 个原有测试全部通过。原件中 Day 01 有完整部署链，Day 02–28 每天都提供任务和验收，公共模块、依赖锁、统一运行入口和 CI 尚未建立。

## 第一批变更和验收位置

| 编号 | 新增或改动的位置 | 核对办法 |
|---|---|---|
| T01 规范 | 根 AGENTS.md、docs/lesson-template.md、两级课程索引 | 依据十五项门槛审核任一课，逐项定位原理、实现与证据 |
| T02 教材 | course/day-01 至 day-05 的 README、lesson.md、starter、reference、tests | 先走一个手算例，再在 starter 做题，用同一测试对照 |
| T03 引擎 | src/mini_engine/model.py、runtime.py；benchmarks/lessons.py 和 model_lab.py | Day 03 block → Day 04 attention/cache → Day 05 generate；三个阶段共用同一组权重与 forward |
| T04 评测 | benchmarks/schemas、datasets、api_lab.py、metrics.py、numerical.py、performance.py | 同一 JSONL 复跑、记录部分失败，区分客户端正文与模型 token 计时，并对照理论与实际字节 |
| T05 环境与记录 | environments/{cpu,pytorch,vllm}、Makefile、doctor.py、records.py、run.py | 使用锁安装；同一目录连续做一次故障和一次成功，检查两个 Run ID、返回码与报告 |
| T06 测试 | tests/test_protocol.py、五天逐日测试、.github/workflows/cpu.yml | make check；数值 oracle 使用固定版本 HF，HTTP 使用可控回环服务；硬件层另行验收 |

保留了旧 Day 01 启动脚本、模型与 tokenizer revision、请求构造练习、SSE 客户端、原测试和 Day 06–28 的学习要求。原始部署讲解继续承担实机手册的职责。新增的三档练习与公共 harness 负责可重复验证。首批可验收范围是单机 CPU/单 GPU 前五天，集群与后续 serving 功能按批次增加。

## 后续批次与交付证据

| 日期 | 已有基础与仍缺的内容 | 任务及进入下一阶段的证据 |
|---|---|---|
| 06–12 引擎 | 已有调度、分页、前缀构造和控制变量的要求；当前主要为任务说明 | T07 先做 Nano-vLLM 再安排 vLLM 源码专题，届时同步目录/引用并固定 commit。Day 07、10 直接消费共享 schema；Day 08 实现随机分配回收、取消、OOM、共享写入和长跑不变量；Day 12 接开放到达与 SLO 的真实测量 |
| 13–17 GPU | 已有 kernel、profiler、归因与量化要求；尚无硬件报告 | T08 固定 4B 的 Ada/Hopper 对照与 HBM 带宽；先验数值，再测 BF16/受支持的 FP8；FA3/TMA/WGMMA 按实机后端选做 |
| 18–20 多卡 | 已要求 NCCL、32B TP1/TP2/双副本、等卡 P/D；拓扑与配额待实测 | T10 双卡先行；第三张分别作为第三副本或 1P2D/2P1D 扩展。T11 可选 MoE 设计路由分布与 All-to-All profiling，记录专家负载偏斜 |
| 21–27 云原生 | 已有 Docker、K8s、Helm、监控、Dynamo、llm-d 路线；尚无部署证据 | T09 在自己的服务中复现一次加载失败、一次 Pod Pending 和一次断连，交付有时间线的定位与恢复；分周提前准备 Docker/Compose、CPU K8s 与存储；主后端选一套实际部署 |
| 28 毕业实验 | 已规划 Day 07/10/12/19 数据沿用；当前两策略门槛不足以作研究结论 | T12 依次加入轮询、least-loaded、会话粘性、KV+load，做消融。跟踪真实 cache residency；先 replay，再验证独立 seed 的闭环任务，记录成功率、耗时和每成功任务成本；零成功时成本比率未定义 |
| 选修与呈现 | 可读的仓库教材已能使用 | T13 在有预算时只迁移一个云平台并核算清理成本。T14 待课程稳定后再做文档站 |

后续日期在本批保持原顺序。GPU 性能回归需同一卡型、配额、负载和稳定环境；共享卡测量只附上下文。L4 的 HTTP 回环只证明协议路径，真实模型 API、GPU 内核、双卡与集群各需其实际证据。
