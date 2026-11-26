# Day 14 · 用时间线定位 Prefill 与 Decode 的瓶颈

同样一次生成，慢可能来自主机提交间隙、访存或矩阵运算。先让时间线显示 GPU 在什么时候做了什么。

**实验起点**　单 H200；复用 Day 05 能清楚切开 prefill/decode 的工作负载，固定 batch、prompt 与输出长度。

## 动手要求

1. 用 PyTorch Profiler 为两阶段加标签并导出 trace。各列 CUDA 耗时前五的算子，区分累计时间、单次时间和调用次数。
2. 用 Nsight Systems 对齐 CPU 提交与 GPU 执行，在具体区间标出一次空隙。可访问硬件计数器时，再用 Nsight Compute 检查一个 kernel。
3. 以 FLOPs/访存字节估算算术强度，结合 trace 提出一个瓶颈假设，只改变一个条件重测。计数器受限时保留已有时间线和限制。

## 当天验收

- [ ] 提交可打开的 trace、两个阶段的算子表、关键时间区间与对应运行命令。
- [ ] 用前后数据说明假设是否成立；将理论带宽、实测带宽和 GPU 活跃率分别标注。

延伸阅读 · [PyTorch Profiler](https://docs.pytorch.org/tutorials/recipes/recipes/profiler_recipe.html) · [Nsight Systems](https://docs.nvidia.com/nsight-systems/)
