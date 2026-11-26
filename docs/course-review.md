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

## 第一批验证实录

2026-11-26。从课程基线 ee9d381 增量实施；本次验证包含本机 macOS arm64 CPU 和 GitHub Actions Ubuntu x86_64 CPU。完整机器探测和请求日志留在 runs/，下表只列可复现命令与必要结果。

| 检查 | 实际结果 |
|---|---|
| 原仓库 `LAB_REFERENCE=1 python3 -m unittest discover -s tests -v`（Day 01 目录） | 5 项通过，退出 0 |
| 根目录 `make setup ENV=cpu && make check` | Ruff 与 22 项 CPU 测试通过，退出 0。涵盖官方数值对照、分块/交错缓存、多 EOS、预算、SSE 中断、读超时、HTTP 400 错误正文和失败重跑 |
| `uv lock --check --project environments/{cpu,pytorch,vllm}`（逐个运行） | 三套锁均退出 0。CPU 锁已在 macOS 与 Ubuntu 实际安装；另两套尚待 Linux NVIDIA 节点安装和验收 |
| `make lab DAY=02 IMPL=reference ARGS="--length 128 --layout strided"` | CPU 输入 [1,128,128]，contiguous=false。另跑 FP32、FP16、BF16 的数值检查，退出均为 0 |
| `make lab DAY=04 IMPL=reference DEVICE=cuda`（本机无 CUDA） | 预期失败。实验进程退出 1、make 退出 2；run.json 标 failed，保留异常，未生成 GPU 分数 |
| 原始 starter 与已完成的 starter | 原始 Day 02–05 分别在 TODO 处报 NotImplementedError；在干净临时 checkout 中将完成的练习置于 starter，Day 05 通过 starter → block → cache → runtime 的真实入口，退出 0 |
| Ubuntu 完整预训练 CPU 对照，commit efee10d | 同一模型及 tokenizer revision c1899de289a04d12100db370d81485cdf75e47ca，FP32、seed=7、单线程，prompt 为 `Give one use of a KV cache.`。Day 03 首 block 与完整 logits 最大绝对差均为 0；各层 K/V 通过。Day 04 缓存占用实测与预测均为 1,835,008 字节；Day 05 与官方 greedy 序列均为 `[3555,374,279,7428,315,264]`。三次运行均退出 0 |

第一次用完整权重执行时，某层 V 的一个元素出现 4.26e-5 的绝对偏差，超过当次允许误差。对齐 RoPE 逆频率、attention 缩放与 Q/K 归一化的运算顺序后，在相同输入与原容差下复测通过。这里的 0 只描述这一组输入与运行环境。[首次失败的日志](https://github.com/WalteR-MittY-pro/LLM-Inference-Lab/actions/runs/45793489721) · [修正后完整的 Linux CPU 记录](https://github.com/WalteR-MittY-pro/LLM-Inference-Lab/actions/runs/45794207796)

复跑真权重可在仓库根使用 `make lab DAY=03 IMPL=reference ARGS="--pretrained --warmup 0 --repeat 1"`，将 DAY 改为 04、05 即可复验缓存与 greedy。也可在 CPU course checks 的手动入口勾选 pretrained。日常 push/PR 只跑无需下载权重的测试。

RTX 4070 Ti SUPER、H200、真实 vLLM 服务流、CUDA Event 性能、双卡互连与 Kubernetes 部署均未在本批验收。API 回环实验验证网络协议；CPU 数值结果不能代替上述设备证据。

**本机离线复核。** 对下载的权重计算 SHA-256，首次校验发现断流后有缺失分片；补齐后与发布值 `f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b` 一致。模型配置、生成配置、tokenizer 文件也通过课程的指纹校验。于干净的 efee10d 工作树设置 HF_HUB_OFFLINE=1，使用 `--checkpoint runs/checkpoints/Qwen3-0.6B-c1899de --warmup 0 --repeat 1` 依次运行 Day 03、04、05，三个进程均退出 0。

| Day | 本机 Run ID | 实际观测 |
|---|---|---|
| 03 | 20261126T094441958662Z-050ce461dd | logits 形状 [1,8,151936]。首 block 与 logits 的最大绝对差都为 0；逐层 K/V 对照通过 |
| 04 | 20261126T094446347376Z-dd02d8f01e | 8 个输入 token，紧凑 KV 共 1,835,008 字节。增量与整段重算的末位置 logits 最大绝对差 4.05e-5，逐元素符合 `atol + rtol × |reference|`，两项容差均为 3e-5 |
| 05 | 20261126T094449283681Z-d929077912 | 6 个 greedy token 与官方实现及 Ubuntu 的本次运行一致。官方生成配置含采样参数；本实验显式关闭采样 |

本机快照与原始记录位于 Git 忽略的 runs/ 下。新机器用前述 `--pretrained` 命令拉取相同 revision。
