# 团队共享 GPU 推理平台 · 十天实验课

**先打开 [第一课](course/01-stream.md)，完成其中的“实验一”。** 第一条请求走本机演示上游，约一分钟就能看到带时间戳的两个内容片段。Go 练习从 [Relay](internal/platform/stream.go) 开始；GPU 上的真实生成是第一天单独的过关项。

## 课程目标

作为内部平台工程师，用 Go、PostgreSQL、容器和 vLLM 向研发工具提供统一的流式推理 API。前三天完成两节点、双租户的纵向流程。第七天完成 Kubernetes 对照。最后三天把容器、宿主机、KVM 和 guest 的证据接入同一次排障。每日按验收推进，可在同一自然日连续完成多课。

| 天 | 课题 | 交付 |
|---|---|---|
| 1 | [一张卡与一条流](course/01-stream.md) | 直连与经网关的真实生成记录、流式测试 |
| 2 | [部署与 GPU 预留](course/02-07-platform.md#d2) | 两机器各一个副本、并发预留测试 |
| 3 | [租户服务上线](course/02-07-platform.md#d3) | Key、配额、账本、文档问答与百客户端基线 |
| 4 | [拆解推理耗时](course/02-07-platform.md#d4) | 区分 prefill、decode、队列与缓存影响 |
| 5 | [请求优化](course/02-07-platform.md#d5) | 固定卡数下的配额内达标率和达标吞吐 |
| 6 | [故障恢复](course/02-07-platform.md#d6) | 重复发布、节点失联、断流与重复记账回归 |
| 7 | [Kubernetes 接入](course/02-07-platform.md#d7) | 共享 API 在 Kubernetes 后端运行 |
| 8 | [容器与宿主机排障](course/08-10-systems.md#d8) | CPU 节流、OOM、端口和挂载的诊断记录 |
| 9 | [KVM 与 Firecracker](course/08-10-systems.md#d9) | 启动独立内核的 guest、观察进程和 I/O 边界 |
| 10 | [快照恢复与跨层盲诊](course/08-10-systems.md#d10) | 验证恢复后的业务状态，展示一次陌生故障的诊断和复测 |

## 项目入口

- [HTTP 与 worker 通信](internal/platform/http.go) 和 [进程入口](cmd/platform/main.go) 已接线。学习者实现 [流式转发](internal/platform/stream.go)、[控制面和鉴权记账](internal/platform/services.go)，再扩展管理 API。
- [数据库起始结构](db/001_init.sql)；[流式观察客户端](scripts/probe.py)、[请求轨迹生成](scripts/trace.py)、[负载回放](scripts/replay.py)、[结果统计](scripts/report.py)、[文档问答客户端](scripts/ask.py) 可直接使用。
- 两张独立 GPU、两个 Linux worker。单卡可容纳同一份模型；每个副本使用一张卡。实验私网内运行；跨主机流量使用可信实验网络或加密隧道。第九天另需可访问 KVM 的 Linux 节点，可与其中一台共用。GPU 推理放在宿主机或容器侧。
- 建议每轮保存 Git 版本或源码副本、模型版本、镜像 digest、GPU/驱动信息、请求轨迹、缓存状态、原始 JSONL 和故障时间线。把演示上游、真实 vLLM、两节点和虚拟机的结果分别标明。
- 从项目根运行 `./labgo test -race ./...` 检查骨架；`./labgo test -tags practice ./internal/platform -run TestDay1 -v` 验收第一课，初始应失败。Linux 需 Go 1.24+、Python 3、Docker；用 `./labgo build -o bin/platform ./cmd/platform` 编译本机程序。不要将 macOS 二进制直接拷到 Linux 运行。
