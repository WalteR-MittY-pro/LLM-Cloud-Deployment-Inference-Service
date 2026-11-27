# 从张量布局到可相信的 GPU 计时

同样是做投影，一次处理 128 个位置通常比逐个提交 128 次更能复用权重。先理解一次乘法实际读了哪些数据，再解释它会在哪里花时间。

~~~text
X[B,S,H] ── 合并前两轴 ──► [M,H]       M = B×S
                               × W[H,O]
                            [M,O] ──► Y[B,S,O]
地址(i,j,k) = 起始偏移 + i×stride₀ + j×stride₁ + k×stride₂ （以元素为单位）
~~~

连续的 [2,3,4] 通常有 stride [12,4,1]。交换最后两轴得到 [2,4,3] 和 [12,1,4]，存储本身没搬。view 合并轴要求相应 stride 可合并，reshape 必要时分配新存储，contiguous 显式产生连续表示。对照张量的 data_ptr 和 stride，再判断是否有复制。

**从小算式到性能预测。** [1,2] × [[2],[3]]=8。推广到 M 行、K 个输入、N 个输出，常用 GEMM 口径约为 2MKN FLOPs。一次理想搬运约为 b(MK+KN+MN) 字节，b 是每个元素字节数。M=1 时，权重读取占大头；M 增大时，同一个权重服务更多行。缓存层级、tile、重复读取与框架开销会改变真实流量，公式只用于实验前的预测。
解释：y = x₁ × w₁ + x₂ × w₂ + x₃ × w₃，假设 K = 3，3 次乘法、2 次加法。推广到 K 项，就是 K 次乘法加 K−1 次加法，一共 2K−1 次；对 M 个 token，每个要算 N 个输出，一共就是 M×N 个结果，M×N 个结果 × 每个结果约 2K 次运算 = 约 2MKN FLOPs

## 跟着数据走

1. 在 Python 构造 arange(24).reshape(2,3,4)，先写下元素 [1,2,3] 的偏移，再交换后两轴验证同一元素的新坐标。
2. 在 [starter/exercise.py](starter/exercise.py) 中实现 project，沿 H 收缩，保留 B/S。用手算和独立的 einsum 验证非连续输入。[参考实现](reference/exercise.py)供完成后对照。
3. 仓库根目录运行下面两组固定实验；把 length 依次改为 1 和 128，分别观察 GEMV 风格与 GEMM 风格的矩阵运算。CUDA 节点先执行 `make setup ENV=pytorch`，再给命令加 `ENV=pytorch DEVICE=cuda`，分别尝试三种 dtype。

~~~bash
make test DAY=02
make lab DAY=02 ARGS="--length 1 --dtype float32 --warmup 3 --repeat 20"
make lab DAY=02 ARGS="--length 128 --dtype float32 --warmup 3 --repeat 20"
make lab DAY=02 ARGS="--length 128 --layout strided --dtype float32 --warmup 3 --repeat 20"
~~~

后两条的 seed、数值和形状相同，只有存储布局变化。观察 requests.jsonl 的 input_shape、stride、contiguous；造出非连续输入的复制放在计时区间外。

timed 在 CPU 用单调时钟，在同一 CUDA 流分别记录开始/结束事件并等待结束事件。只围住 Python 调用可能只测到提交时间。GPU Event 时间不包括主机到设备搬运；当前输入事先留在设备上。报告 max_abs_error、dtype、设备、shape 和重复分布。低精度误差用 FP32 的同输入对照。

**源码映射。** 从 [PyTorch v2.8.0 Linear.forward](https://github.com/pytorch/pytorch/blob/ba56102387ef21a3b04b357e5b183d48f0afefc7/torch/nn/modules/linear.py) 找到 F.linear，核对权重存储为 [O,H]，与练习参数的 [H,O] 如何转换。下节在 q_proj、k_proj、v_proj 上沿用这一操作。

**定位与自测。** 若转置后 view 报错，先打印 stride，再预测哪种 reshape 会复制。若 GPU 时间接近零，核对是否记录了结束事件、是否预热。挑战：取两个元素数相同但布局不同的输入，给出何时发生复制的证据，分开计复制与乘法。
