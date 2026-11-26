# Day 15 · 用 Triton 融合算子并检验收益

一次加法、一次乘法和一次 ReLU 分开执行时，要把哪些中间结果写回显存？把它们放入一次 kernel 后，较小和较大的输入会有不同表现。

**实验起点**　复用 Day 13 的输入和 Day 14 的计时方法；跨 Ada/Hopper 对照时固定 shape、dtype 和 seed。

## 动手要求

1. 亲手写 Triton vector add、行 softmax 和分块矩阵乘。用 program_id 解释工作划分，并对尾块加 mask；阅读 RMSNorm 或 fused attention 的归约路径。
2. 写出 relu((a+b)*c) 的融合 kernel，用相同输入同 PyTorch 逐项比对，包含非整块尺寸和数值幅度较大的输入。
3. 预热后测多个规模的中位数、有效带宽和 kernel 启动次数。写出有效字节数的计算假设，用 profiler 核对中间结果的处理方式。

## 当天验收

- [ ] 交付三个基础练习与融合实现，提供 shape、精度、容差及最大误差。
- [ ] 给出基线/融合在多个规模和可用设备上的原始数据，解释一处收益变小或消失的条件。

延伸阅读 · [Triton 官方教程](https://triton-lang.org/main/getting-started/tutorials/)
