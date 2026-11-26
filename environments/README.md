# 同一门课的三套隔离环境

在仓库根运行 `make setup ENV=cpu`，然后 `make doctor`。三个目录各自拥有 pyproject.toml、uv.lock 和本地 .venv。make setup 使用 uv sync --locked；依赖解析与目标机器上的设备验证分别进行。使用 Python 3.12、uv 0.11.8，安装前确认软件源可达、磁盘有空间。

| ENV | 支持目标 | 安装后的用途 |
|---|---|---|
| cpu | macOS arm64 或 Linux x86_64 | PyTorch 2.8.0、Transformers 4.57.1；CPU 对照、所有测试及 Day 01 客户端。Linux 指向 PyTorch 官方 CPU wheel |
| pytorch | Linux x86_64，已分配的兼容 NVIDIA GPU | 同一教学代码、同版本框架，PyTorch cu128 wheel；Day 02–05 CUDA 正确性和性能实验 |
| vllm | Linux x86_64、兼容 CUDA 13 的驱动 | vLLM 0.34.0 独立服务、PyTorch 2.14.0；从 Day 01 的 serve.sh 启动两种模型 |

**GPU 节点操作。** 先在拿到配额的作业内运行 doctor，确认驱动、可见设备和剩余显存。Day 01 运行 `make setup ENV=vllm` 后激活 environments/vllm/.venv，再下载该版本的 kernels。客户端可从 CPU 环境访问同一节点的回环地址。Day 02–05 CUDA 实验改用 `make setup ENV=pytorch` 和 `make lab DAY=04 ENV=pytorch DEVICE=cuda`。安装 PyTorch wheel 不会安装或升级宿主机驱动。现有集群的驱动不满足时，在获准的兼容节点或与管理员确认过的镜像中运行，再记录镜像 digest。

**固定依据。** vLLM 源码 release 的 cuda.txt 指定 torch、torchaudio、torchvision 的组合；Dockerfile 的默认 CUDA 为 13.0.3。vllm 锁使用 PyPI 的 release 分发，含 CUDA runtime 13.0.96。手动维护的旧 config/requirements.txt 仅用作直接依赖入口；课程验收使用完整锁。硬件不同的实验不用同一份 pip freeze 混装。SGLang、Nano-vLLM 和容器镜像随对应课程引入后再锁定。

[固定版 vLLM 依赖](https://github.com/vllm-project/vllm/blob/62d4bc3c7e33b1b6c906e233e6af2d3506c482ca/requirements/cuda.txt) · [固定版容器工具链](https://github.com/vllm-project/vllm/blob/62d4bc3c7e33b1b6c906e233e6af2d3506c482ca/docker/Dockerfile) · [教学模型源码](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/models/qwen3/modeling_qwen3.py)

## ENV 选择软件，PROFILE 描述实验地点

六个 [profile](lab-topology/profiles) 描述预期硬件、网络与权限，实际能力在对应主机运行后才有证据。每个 profile 可分别使用 cpu 客户端、pytorch 教学环境或 vllm 服务环境。原来的 make 命令可以继续使用；省略 PROFILE 时记录为未指定。

~~~bash
make setup ENV=cpu PROFILE=home-4070
make doctor ENV=cpu PROFILE=home-4070 ARGS="--torch"
make lab DAY=00 ENV=cpu PROFILE=home-4070
make report RUN=实际运行目录 PROFILE=home-4070
~~~

setup 在当前目录安装所选依赖锁；PROFILE 只做名称校验。doctor、lab 都在执行命令的机器上运行。report 从指定 Run ID 读取原记录，可核对 profile。选云端容器时沿用平台分配的可见设备；家庭集群的只读探测需要显式的 context。[Day 00 操作步骤](../course/day-00/README.md)
