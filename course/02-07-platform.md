# 从一张卡到一个可运维的平台

每日先画出一次请求或一次发布的时序，再打开代码。Go 的接线、协议客户端和数据表是起点。标作“你写”的逻辑及下面列出的集成实验由你完成。课内端点仅用于可信实验网络。

<a id="d2"></a>
## 第 2 天 · 两个节点如何避免分到同一张卡

**原理。** 数据库里的部署意图、worker 看到的容器、网关可以使用的副本，是三个不同事实。事务能把“挑一张卡”和“登记占用”作为一个提交完成；容器启动和权重加载发生在事务之外。worker 每次比较期望与实际，只推进一步，控制面重启后仍可继续。物理 GPU 用 node ID 和稳定设备 UUID 标识。

**先看数据。** 运行 docker run 前用 nvidia-smi -L 盘点两台机器；同一个 model revision、镜像 digest 和别名预置在两台机上。Docker API 留在本机，由 worker 访问。以下数据库只对本机发布端口；跨机 worker 连接控制面 HTTP，数据库地址提供给控制面和网关。

```bash
export POSTGRES_PASSWORD=$(openssl rand -hex 24)
docker run -d --name ti-pg -e POSTGRES_PASSWORD -e POSTGRES_DB=inference -p 127.0.0.1:15432:5432 postgres:16-alpine
docker exec ti-pg pg_isready -U postgres -d inference
docker exec -i ti-pg psql -v ON_ERROR_STOP=1 -U postgres -d inference < db/001_init.sql
export DATABASE_URL="postgres://postgres:$POSTGRES_PASSWORD@127.0.0.1:15432/inference?sslmode=disable"
export LAB_ADMIN_TOKEN=$(openssl rand -hex 32)
./labgo build -o bin/platform ./cmd/platform
./bin/platform -role control -listen 127.0.0.1:8090
```

数据库就绪之后再执行 SQL，一次即可。保留本实验的凭据供后续终端使用。做双节点实验时改为控制机私网地址，在 worker 设置同一个 LAB_ADMIN_TOKEN，启动 ./bin/platform -role worker -node node-a -control http://CONTROL_PRIVATE_IP:8090；另一台用 node-b。不同 CPU/OS 上分别编译。

**你写。** [services.go](../internal/platform/services.go) 的 Desired、Observe、Publish、Reconcile。先让空的 desired 列表也能触发心跳注册。用 PostgreSQL 约束保证一张卡至多被一个未释放的部署占用，再决定并发事务等待或冲突的行为。稳定 ID 标记容器，一个 worker tick 的超时不应终止已启动的容器；权重加载期间仍应持续上报 loading。先创建容器，后续 tick 再探测真实生成；通过后才写 ready。发布同 ID 不同参数应返回冲突。真实客户端需要超时和断开传播。

```bash
curl -sS -H "Authorization: Bearer $LAB_ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"id":"replica-a","model":"lab-model"}' http://127.0.0.1:8090/admin/deployments
```

**过关。** 两张卡、三个同时到达的不同部署，只出现两个有效预留；重复提交同一 ID 只产生一个部署。保存 SQL 查询结果和两台机器 docker ps 的对应关系。从网关机器用 probe 分别直连两个私网端点验证。参考 [PostgreSQL 显式锁](https://www.postgresql.org/docs/current/explicit-locking.html)。

<a id="d3"></a>
## 第 3 天 · Key、配额、记账与真实应用

**原理。** 团队是配额主体，一个团队可以撤销单个应用的 Key。数据库保存配置和历史用量；一个网关实例可以先在内存里维护活跃配额。准入时只知道输入和声明的输出上限，结束时才能得到实际用量。先写出预扣、结算、失败和取消的规则。

**你写。** 增加管理端签发和撤销 Key 的入口（使用随机高熵密钥，只展示原文一次）。实现 Admit 和 Record。第一轮只做请求额度；第二轮加入输入/输出 token 预算，用同版 tokenizer 测输入，写明缓存 token 和输出预算如何计数。429 附重试提示，区分无就绪副本、超额和上游异常。补上拒绝请求的单独观测，避免鉴权前写错账。以网关生成的请求 ID 重试一次记账，查询账本应只有一条；缺少 usage 的中断请求保留 unknown。增加生成请求记录动作失败后的持久重试或可审计补偿。去掉 -dev-upstream 启动 gateway，使其真正走鉴权、路由和数据库。实验的独立数据库用户可在实现后按读写职责收紧权限。

**真实入口。** 使用 CJMP 已有 search_docs/read_section 检索一次实际问题，保留路径与小节；将结果原样作为 stdin 交给 scripts/ask.py。第一次用保存的检索结果复跑验证，随后从问答入口把实际检索输出接到同一调用。网关和客户端都有 request ID，检索耗时单独计量。模拟流量直接打网关。

```bash
LAB_KEY="$LAB_KEY_A" python3 scripts/ask.py '这个 API 在什么场景使用？' < work/cjmp-retrieval.txt
python3 scripts/trace.py burst --count 100 > work/burst.jsonl
python3 scripts/replay.py work/burst.jsonl > work/burst-results.jsonl
```

先 export LAB_KEY_A / LAB_KEY_B。固定轨迹限定输出上限，记录服务实际生成长度；需要严格等长时使用支持该设置的引擎后端并检查实际长度。压测客户端同时最多 100 个在途请求。第一轮标记缓存为冷或热并保持一致；保存失败请求，禁止只收成功记录。两个租户可代表同一应用的两个团队。**过关：** 撤销 A 的 Key，B 继续生成；SQL 统计能与客户端的 request ID 对上；报告首次 100 请求的成功数、限流数、超时与未完整结束数、每租户首 token 分布。不要将本课程的模拟客户端数写成实际用户数。

<a id="d4"></a>
## 第 4 天 · 拆开 prefill、decode、调度等待与 KV cache

**先预测。** 输入从 512 增至 2048 token，限制相同输出长度，主要增加哪段计算？单请求改成 16 个并发，后续输出速度和总 tokens/s 会同向变化吗？先写下预测。prefill 处理输入并建立 KV；decode 在生成循环里复用已有 KV。每轮组批决定哪些序列推进。长请求既可能增加首次计算，也可能使其他请求更久才能被调度。

**动手。** 用真实 tokenizer 构造匹配的输入长度，在同一台卡对比短/长输入、短/长输出和并发 1/4/16。先预热、固定模型/精度、记录实际输出长度和缓存命中。每组重复。采集客户端 JSONL、/metrics 原始数据、GPU 利用率及显存时间序列；若有 Nsight Systems，再为一组相同负载取时间线。按当前 vLLM 版本在 /metrics 核实 queue、prefill、decode、running/waiting 和 KV 使用指标，记录其统计层级。不同进程的墙钟先校准，单进程耗时用单调时钟。聚合直方图不能用作某个请求的精确耗时分解。

**过关。** 制作两行带原始数据的结论：一个输入长度导致的 TTFT 变化，一个并发导致的队列或生成速度变化。再固定公共前缀，比较冷、热缓存。解释客户端 TPOT 是后续可见正文耗时除以后续输出 token 数，不能单凭该数证明某个 GPU 算子慢。资料见 [vLLM 指标](https://docs.vllm.ai/en/stable/usage/metrics/) 和 [vLLM 压测口径](https://docs.vllm.ai/en/stable/benchmarking/cli/)。

<a id="d5"></a>
## 第 5 天 · 哪些优化让更多请求按时完成

**原理。** 先约定请求级 TTFT、TPOT 上限，以及配额内需要达到的比例；再压测。缓存状态、GPU 数量、模型、请求轨迹和硬件保持一致。两张卡始终运行两个副本，分别测两租户共享与各自独占。在相同服务目标下比较 goodput，并报告每个租户配额内达标的分子与分母。

**你写。** 先跑轮询基线，再只改一处，例如按估计队列负载选副本。验证是否因长输入聚集、瞬时读数滞后或前缀缓存失效而退化。再单独实验空闲容量出借和拥塞时先保护预算内请求。令牌预算是服务策略的一部分，记录请求级准入决策、超额借用和拒绝原因；独立按约定的初始桶容量、补充速率、到达时间和实际收费规则复核，不能用“最终被接收”反推配额内。

```bash
python3 scripts/trace.py steady --count 400 --rps 8 > work/steady.jsonl
python3 scripts/trace.py noisy --count 400 --rps 8 > work/noisy.jsonl
python3 scripts/replay.py work/noisy.jsonl > work/noisy-results.jsonl
python3 scripts/report.py --ttft-ms 1200 --tpot-ms 100 < work/noisy-results.jsonl
```

这里的阈值只是命令示例，替换成第 4 天预先确定的目标。生成器的 in_quota 默认 null，base/surge 描述施加的流量而非配额判定。基于已知预算独立标注原始轨迹，或在回放后按稳定序号及准入时刻核对后补标，再出正式达标率。若客户端 dispatch lag 持续增长，降低到达率或增加负载生成能力后重测；记录计划和实际到达率。脚本的 goodput 包含整个回放至最后完成的窗口，跨策略保持同一口径。短到只生成一个 token 的请求只判 TTFT；无实际输出计数的请求不能证明速度达标。

**过关。** 提交一张表：三种流量 × 两种路由；记录租户表现、好请求/秒、GPU 数量、失败与拒绝、缓存命中。给出一个优化生效的区间和一个没有收益或退化的区间。资料见 [vLLM goodput 指标](https://docs.vllm.ai/en/latest/cli/bench/serve/)。

<a id="d6"></a>
## 第 6 天 · 控制面恢复与半条流

**原理。** HTTP 超时无法证明远端没有创建容器，worker 失去联系也无法证明旧进程停了。响应头发出后，流中断仍可能留下 200 状态。把确证、未知和失败分别表示。

**你写。** 为控制面增加故障开关或调试断点，恰在 worker 启动成功而上报未完成时只停止自己的 control 进程。保留数据库，按原部署 ID 重发，记录节点的真实运行状态。让一个 worker 心跳过期，再在另一次实验中于固定测试请求收到第一段正文后停止该副本。为陈旧心跳、重复上报、断流、记账失败各加一个回归。推理流开始发正文后不可透明重试并拼接另一条生成结果。网关与管理进程分别重启，验证它们的故障影响范围；另测数据库依赖失效以明确剩余依赖。

**过关。** 展示操作时间线、原 request/deployment ID、旧实例数量、数据库行数、新请求路由和恢复耗时。恢复期间没有双重预留、重复收费或把半截答案算成成功；解释哪些检查来自真实节点。

<a id="d7"></a>
## 第 7 天 · 用同一个网关面对 Kubernetes

**原理。** 原先控制面选 node、worker 管本机容器；换成 Kubernetes 后，Deployment 管副本数，scheduler 选节点，kubelet 报告 Pod 状态。网关继续掌握租户和模型的服务语义。以相同的 HTTP 请求观察两种部署方法。

**动手。** 准备两个带 GPU 的可调度节点以及 NVIDIA device plugin，在两节点同一绝对路径放同一模型 revision。先释放课程自研后端占用的测试 GPU，再将 kube/inference.yaml.in 的镜像替换为第 1 天的 digest、路径替换为模型路径；kubectl config current-context 确认是实验集群。创建课程命名空间，在该命名空间 apply 生成的清单。用 kubectl get pods -o wide、describe pod、logs 对照两台宿主机显存；暂时制造资源不足，观察 Pending 原因。模板中的 /health 用于 Pod 探测；网关接流量前仍应做一次真实生成验证。

**你写。** 为管理服务增加 Kubernetes 后端，把发布命令变成创建或调整 Deployment；先以 Service 做连通测试，再通过 EndpointSlice 取得就绪副本，在网关可路由的集群网络内执行观测和逐副本路由。给读取 Pod/EndpointSlice、发布 Deployment 所需的最小命名空间权限。保持 model 名、租户 Key、请求与账本协议相同。kubectl port-forward service/lab-model 只用于连通性实验，不适合证明两个副本间的真实路由。

**过关。** 同一批流量在新后端完成；记录两个不同节点上的副本、Pod 替换时流量恢复的过程。能讲清 Kubernetes 调度的是 Pod，网关调度的是请求，vLLM 组批的是序列。参考 [Kubernetes GPU 调度](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/) 和 [Pod 生命周期](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)。
