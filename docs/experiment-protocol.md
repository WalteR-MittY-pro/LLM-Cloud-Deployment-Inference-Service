# 一次实验如何留下可比较的证据

仓库根目录执行 `make setup ENV=cpu`、`make doctor`。统一入口采用 `make lab DAY=04 IMPL=reference DEVICE=cpu ARGS="--seed 7 --warmup 1 --repeat 3"`。输出的 RUN 路径是该次尝试的身份。用 `make report RUN=实际路径` 重算同一份原始记录。实现、seed、dtype、形状、模型与 tokenizer revision、工作负载以及可见设备都应与对照组一致。

| 每次运行的文件 | 怎么使用 |
|---|---|
| run.json | Run ID、UTC 起止时间、Git commit、环境、运行参数、模型来源与 revision、异常和退出码。随机模型由代码版本、seed 和配置定义 |
| requests.jsonl | 每次预热/稳态请求单独一行；算子实验记录形状和误差，生成实验记录真实 token ID 与观测时刻 |
| raw.log、stream-*.sse | 原始诊断与 HTTP 字节流。失败可保留已收到的正文；HTTP 服务所在硬件须用服务端证据补齐 |
| metrics.json、report.md | 从稳态原始行重算成功样本的分布，列明失败数、失败率和样本量。无样本的指标保留为空 |
| workload.jsonl | API 回放使用的脱敏输入快照，与 SHA-256 对照原始工作负载 |

**时间口径。** 首段文本从 POST 发出计到第一次非空正文。HTTP chunk 可含多个 token，首段耗时无法恢复精确 TTFT、ITL、TPOT。教学生成循环逐次取到可读的 token ID；令 tᵢ 为相对开始时刻，则 TTFT=t₁，ITLᵢ=tᵢ−tᵢ₋₁，TPOT=(tₙ−t₁)/(n−1)。n<2 时 TPOT 未定义。API 的端到端成功延迟到 [DONE]，客户端调度延迟从计划到达至实际派发，均不等于服务端排队。GPU kernel 计时用同一 CUDA stream 的事件，主机可见 token 计时含同步。独立重启的冷加载、编译、首轮预热和稳态应分别记录。

**统计。** 报告中位数与 nearest-rank p95/p99，并列样本数、极值和失败率；三次小样本的 p99 只能指示最慢一次。需要比较稳定性时重复启动整个 run，报告各 run 中位数的范围。吞吐按整个观测窗口内成功请求数/秒计算。Goodput 在预先选定的 TTFT、TPOT 阈值都可观测且满足时计数，除以同一窗口秒数。单 token 样本在这一双阈值协议中不计入，需另建单 token 口径。在线任务成功率留给实际任务判定。

**定量预测。** [性能模型](../benchmarks/performance.py)用十进制 byte/s。例如 32B 稠密参数以 BF16 理论占 64 GB；batch=1，每步恰读一次全部权重，以 4.8 TB/s 计算得到 13.33 ms/步，以 65% 有效带宽得到 20.51 ms/步（48.75 token/s）。这是忽略 KV、计算、采样、框架及通信的教学估算。算术强度 I=FLOP/bytes；Roofline 最短时间取 FLOP/峰值算力和 bytes/带宽两者最大值。一次传输可用启动延迟+字节数/带宽初估。和运行记录比较时先确认设备、精度、B、S 与缓存状态。

**共享格式。** [工作负载](../benchmarks/schemas/workload.json)、[观测](../benchmarks/schemas/observation.json)及[运行](../benchmarks/schemas/run.json)采用 JSON Schema。API 输入包括可重建的 prompt、session、到达时间和输出预算。使用 `--model-revision` 和 `--tokenizer-revision` 填入实际服务日志能证实的版本；未知值保留 null。重复测量保留 iteration。有限并发时已到达的请求可在客户端等待，工作线程的 dispatch_ms 可用于识别这一部分。工具等待、依赖闭环与四种路由基线在后续批次接入。

**权限和存储。** doctor 只探测当前账号可见设备、显存、拓扑、Docker 和 Kubernetes 权限；集群 RBAC 同意创建 Pod 仍需配额和设备。运行前记录节点独占状态，容器内可通过 LAB_IMAGE_DIGEST 登记实际镜像。runs/ 默认留在本地，发布证据前先去除请求正文、账号与私有节点信息。
