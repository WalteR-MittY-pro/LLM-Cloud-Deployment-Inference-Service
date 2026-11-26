# Day 23 · 让 Kubernetes 把 GPU 分给推理 Pod

节点能看到卡，不代表一个 Pod 已经申请并获得了卡。今天从节点资源一直追到容器中的第一次模型输出。

**实验起点**　`home-cluster` 的两台家庭 RTX Linux 节点。先核对已有 Device Plugin/Operator、runtimeClass 和实验 namespace；从 [Day 00 清单](../day-00/README.md)渲染单副本起步。

## 动手要求

1. 查看节点 capacity、allocatable、已申请量和 namespace 配额；记录实际扩展资源名、标签、taint 和可用区。
2. 先用单个 GPU 测试 Pod 验证设备可见，再用 Day 21 的推理镜像申请同一资源，设置加载与就绪探针。
3. 保留从调度、拉取、加载到 Ready 的事件；通过 Service 发出真实请求，核查模型 ID、回答和 Pod 所在节点。

## 当天验收

- [ ] 提交 GPU Pod/Deployment YAML、设备输出、事件及流式回答，解释可分配总量与当前空闲量的区别。
- [ ] 根据具体 FailedScheduling 事件区分资源、亲和性、配额问题；只有 CPU 集群时，本日 GPU 验收保持待测。

延伸阅读 · [Kubernetes GPU 调度](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/) · [GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/)
