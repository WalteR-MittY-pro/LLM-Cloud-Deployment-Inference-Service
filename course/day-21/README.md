# Day 21 · 把单卡推理服务装进容器

换一台服务器后，谁提供 GPU 驱动，谁提供运行库，模型权重又从哪里加载？从裸机记录出发，用一个可复建的容器回答。

**实验起点**　家庭 RTX 双机分别验证 Docker GPU 容器；主机级配置由所有者按 [Day 00](../day-00/README.md) 操作。复用 Day 01 的模型与客户端，记录实际卡型。

## 动手要求

1. 从固定版本的 GPU 镜像运行 nvidia-smi，核对容器可见设备与配额；记录宿主机驱动、镜像 tag/digest、容器内 PyTorch 和 vLLM。
2. 编写 Dockerfile 或固定镜像加启动配置，显式指定 GPU、模型缓存挂载、端口和共享内存。让权重保存在镜像外。
3. 从新容器分别请求 /v1/models、实际流式回答和 /metrics。复建容器，检查模型缓存是否复用，区分拉镜像、下载权重和加载时间。

## 当天验收

- [ ] 提交镜像 digest、启动配置、挂载关系和三个接口的真实记录，说明停止容器后哪些文件仍然存在。
- [ ] 与 Day 01 裸机基线比较就绪时间与稳态调用，在记录中注明冷/热缓存。

延伸阅读 · [vLLM 容器部署](https://docs.vllm.ai/en/stable/deployment/docker/) · [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/)
