# 容器、虚拟机与跨层排障

继续使用同一套推理服务。第八天以客户端和 worker 容器为观测对象；第九天在有 /dev/kvm 的 Linux 机器启动另一个小型 guest；第十天从 guest 发起推理请求，模型仍运行在原 GPU worker。做快照的对象是这台 CPU microVM。所有故障注入只操作自己创建的课程进程、容器或虚拟机。

<a id="d8"></a>
## 第 8 天 · 把一个容器故障追到 Linux

**要回答的问题。** GPU 还有余量，客户却说接口慢。是容器拿不到 CPU、内存触顶，还是端口、文件或名称解析有错？把实例 ID、宿主 PID、cgroup、网络 namespace 和应用 request ID 连在一起，形成一条可检查的证据链。

**第一站：一个进程，两种视角。** 在原生 Linux 的实验节点跑下面命令。宿主 shell 需要有权读取该 PID 的 /proc，进入 namespace 需要相应权限。Docker Desktop 上的宿主 PID 属于其 Linux VM。

```bash
docker run -d --name ti-cpu --cpus .25 busybox:1.36.1 sh -c 'while :; do :; done'
PID=$(docker inspect -f '{{.State.Pid}}' ti-cpu)
ps -p "$PID" -o pid,comm,cmd
readlink "/proc/$PID/ns/net"
cat "/proc/$PID/cgroup"
docker exec ti-cpu sh -c 'cat /sys/fs/cgroup/cpu.max; cat /sys/fs/cgroup/cpu.stat'
sleep 2
docker exec ti-cpu cat /sys/fs/cgroup/cpu.stat
docker stop ti-cpu
docker rm ti-cpu
```

这是 cgroup v2 实验。先用 stat -fc %T /sys/fs/cgroup 核对 cgroup2fs。比较两个时刻的 nr_throttled 和 throttled_usec 增量。重复运行时改 CPU 配额，使现象发生变化。把探针迁移到负载发生器或网关，再观察客户端 dispatch lag、网关耗时和 GPU 压力，区分“发不出足量请求”和“模型处理不过来”。

**第二站：为什么进程突然没了。** 在独立的一次性课程容器做有上限的小内存试验，保留退出信息。

```bash
docker run --name ti-mem --memory 64m --memory-swap 64m python:3.12-alpine python -c 'x=bytearray(96*1024*1024); print(len(x))'
docker inspect ti-mem --format 'exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{.State.Error}}'
docker logs ti-mem
docker rm ti-mem
```

记录实际结果，操作系统可能杀进程或分配失败。单个 137 退出码只表明 SIGKILL 的常见编码，结合 OOMKilled、memory.events 或 kernel 日志确认原因。对照 vLLM 的 CUDA out of memory 错误、CPU RAM 和 GPU 显存来源，说明为什么两种 OOM 的处置不同。

**第三站：连接失败。** 重用第一课的小 HTTP 容器，在容器内访问服务、在宿主机访问发布端口、从网关所在网络访问 worker。依次查容器监听地址（ss 或 netstat）、docker port、网关内 DNS、TCP、HTTP 状态。再分别使模型挂载路径错误、上游 URL 指向未监听的端口。使用 docker inspect 的 Mounts、docker logs、curl -v 记录每一层最早的异常。

**你做的交付。** 三张故障卡，每张只写症状、第一条区分性检查、反例、修复、同负载复测。最少覆盖一项资源限制、一项网络/挂载和一项能排除 GPU 的检查。参考 [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)、[Linux namespaces](https://man7.org/linux/man-pages/man7/namespaces.7.html)、[Docker 资源约束](https://docs.docker.com/engine/containers/resource_constraints/)。

<a id="d9"></a>
## 第 9 天 · CPU microVM 如何在 Linux 上真正跑起来

**先建立模型。** 宿主 Linux 的 KVM 接口让 VMM 创建 VM、登记 guest 内存和创建 vCPU；Firecracker 是宿主用户态进程，负责配置和设备模型。guest Linux 有自己的内核，guest 进程的系统调用进入 guest 内核。许多指令直接在硬件虚拟化模式下执行，涉及特定设备或事件时才需要退出到宿主处理。virtio 约定 guest 驱动和后端怎样传递 I/O，CPU 的地址转换还要把 guest 物理地址映射到宿主物理内存。学习时先跟踪一条读文件/设备路径，再看 CPU 细节。

**检查实际的 KVM 能力。** 在原生或支持嵌套虚拟化的 Linux 节点上执行：

```bash
uname -m
ls -l /dev/kvm
python3 - <<'PY'
import os, fcntl
fd=os.open("/dev/kvm",os.O_RDWR)
try:
    print("KVM API version:",fcntl.ioctl(fd,0xAE00,0))
finally:
    os.close(fd)
PY
```

0xAE00 是 KVM_GET_API_VERSION，现代 Linux ABI 预期为 12。保留错误原文以区别缺少设备、权限不足和无法使用嵌套虚拟化。能打开 KVM 只是第一步；真正的通过条件是启动 guest 并运行程序。[KVM API](https://docs.kernel.org/virt/kvm/api.html)

**启动与观测。** 跟随 [Firecracker 官方 Getting Started](https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md)，固定同一 release 的 VMM、兼容的 guest kernel/rootfs，核对 x86_64 或 aarch64。使用一个课程专用工作目录、Unix API socket 和可写 rootfs 副本。配置 boot-source、根盘、vCPU 和内存后执行 InstanceStart。启动阶段留存 VMM PID、API 调用状态、串口日志和 guest 内 first-command 的时间。第二次运行区分文件缓存状态。

**三个观察点。**

1. 分别记录宿主、容器、guest 的 uname、/proc/sys/kernel/random/boot_id 和 /proc/1/cmdline。结合实际 namespace 与 VMM PID 解释证据；单独一个内核版本号不能证明隔离。
2. 宿主用 ps -T -p VMM_PID 和 /proc/VMM_PID/status 看 VMM 线程与内存，guest 中看 /proc/cpuinfo 与 /proc/meminfo。给 guest 改 vCPU 数或内存再复测。说明 vCPU 数、宿主 CPU 配额和物理核数量的区别。
3. 依官方网络示例配置课程专用 TAP 和唯一测试地址。用 guest 的只读健康请求访问实验私网中一个可达的服务，然后从 guest 请求推理网关；网关仅向实验网开放并执行租户鉴权。确认应用层返回内容，分别记录 host→网关和 guest→网关的时间。无需把 GPU 传给 guest。

**你做的交付。** 画一张从 guest 程序到 virtio 网卡、TAP、网关、vLLM、GPU 的路径图。在图上标出 guest 系统调用的处理者、GPU 调用的发起者，以及每段可查的日志或指标。以“收到首个业务成功响应”为共同终点比较容器与 microVM 启动；另报镜像/内核/rootfs 是否已在本地、准备时间、后台进程就绪时间。此次测量只是你选定环境的结果。

<a id="d10"></a>
## 第 10 天 · 快照、恢复和陌生故障

**快照是不是磁盘拷贝？** 先在 guest 的 tmpfs（例如 /dev/shm，先用 mount 确认文件系统类型）写一个随机标记，启动一个短小计数进程，在 tmpfs 文件写下当前值。记下 guest 的 boot_id、计数器和时刻。在宿主通过 Firecracker API 暂停并创建完整快照，保存 VM 状态、内存文件以及一致的课程磁盘副本。按该 release 的 [快照说明](https://github.com/firecracker-microvm/firecracker/blob/main/docs/snapshotting/snapshot-support.md) 在兼容宿主和 CPU 配置下恢复。先停止原 VM，避免相同磁盘或网络身份并发使用。重新创建需要的宿主设备和 TAP，恢复后再发一条新的 HTTP 请求。

**过关 1。** 证明 tmpfs 标记与计数进程跨恢复保留；从相同磁盘冷启动作为对照。记录冷启和恢复到第一条有效 HTTP 响应的时间。解释磁盘内容、guest 内存、宿主外部服务及原 TCP 连接分别由谁恢复。应用必须容许连接重建。记录快照大小和宿主 page cache 状态。

**过关 2：跨层盲诊。** 请同伴只告诉你用户症状，或把三种预设场景的运行顺序打乱，事后核对注入配置。候选故障：网关 CPU 配额过低、一个副本从就绪池中退出、guest 到网关使用了错误端口。另用健康服务加长输入构造“无故障但首 token 更慢”的对照。一次只改变一项，保留正常租户流量，并预留可返回的基线版本。

1. 客户端先看 request ID、连接错误、首正文时间、有没有 [DONE]。连接没建立时本来就拿不到网关 ID。
2. 有 ID 时查网关准入和路由、数据库账本，再看 vLLM 等待队列、prefill/decode 与显存。没有 ID 时先检查 guest IP/路由、TAP、DNS、宿主监听和网关日志。
3. 给出两个不同层的候选原因，为每个写一条能区分它们的检查。找到根因后只改一项并重放原轨迹。对比配额内达标率、goodput、异常数和 p95 TTFT；保留事实推翻原判断的例子。

**最终演示。** 让一个真实 CJMP 文档问题经过网关，随后施加可重复突发，从 guest 客户端展示异常和恢复。展示两台 GPU 节点的发布状态、一份数据库账单、一个已测得的优化和一条未知故障的诊断链。列出设备/样本/版本和可推广范围。十天完成意味着你能独立搭建这个系统，并能解释、定位和复测这些已覆盖的故障。

## 第 8～10 天的进阶独立课

这三门安排在相应日的主实验之后。每门先完成一个最小对照，记录实测结果；需要更深的源码或硬件优化时，再从结果继续追。

| 排课 | 独立实验 | 产出 |
|---|---|---|
| 第 8 天 | 同一个可用模型对比 vLLM/SGLang 的前缀缓存，另测 BF16 与受支持的 FP8 KV 配置 | 同图记录输入长度、实际命中、显存、输出质量抽查、TTFT 和有效吞吐 |
| 第 9 天 | 在云上另一台 GPU 节点测单卡与双卡 TP；用时间线识别 NCCL collective，和双副本吞吐分开测 | 同一模型不同并行方式的时延、卡数和成本；解释通信发生位置 |
| 第 10 天 | 从一次真实 trace 选一个算子，用 Triton 或 PyTorch 做最小对照与正确性检查 | 一张输入形状、数值误差、kernel 时间和端到端占比表；估算加速能影响多少用户延迟 |

已有时间线先确定是否存在对应热点。算子本身很快、TP 通信开销抵消计算收益，也是有效的实验结论。使用 [SGLang 文档](https://docs.sglang.ai/)、[NCCL Tests](https://github.com/NVIDIA/nccl-tests) 和 [Triton 教程](https://triton-lang.org/main/getting-started/tutorials/index.html) 获取与实机版本匹配的入口；第十天至少对一项代表性形状先测 PyTorch 正确性与耗时，再与一个 Triton 实现对照。GPU 直通、从零实现 VMM、跨机活迁移属于更深的后续方向。
