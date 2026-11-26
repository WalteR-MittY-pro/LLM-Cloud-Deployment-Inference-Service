# Day 02 · 看懂张量的形状、布局和执行时间

模型里的线性层是矩阵乘法。同样的数值换一种内存布局，可能触发复制；计时位置不同，还可能只测到 CPU 提交指令的时间。

**实验起点**　沿用 Day 01 的 PyTorch 环境。固定随机种子，用 CPU 建立数值对照，在单张 GPU 测时间。

## 动手要求

1. 生成 [B,S,H] 输入和 [H,4H] 权重，手算一个小例子，再用 matmul 验证输出的形状和值。打印 transpose 前后的 shape、stride、is_contiguous。
2. 对转置结果依次尝试 view、reshape、contiguous，记录哪些操作共享存储、哪一步发生复制。比较单 token 与一批 token 的投影。
3. 在支持的 FP32、FP16、BF16 下预热并重复 GEMM/GEMV。GPU 用 CUDA Event 并等待结束；CPU 用单调时钟。

## 当天验收

- [ ] 提交张量程序和一张含形状、精度、设备、误差、中位耗时的表；为一种低精度给出容差。
- [ ] 用一个实测例子解释 stride 的含义，以及省略同步为何会得到不同的计时。

延伸阅读 · [PyTorch 张量视图](https://docs.pytorch.org/docs/stable/tensor_view.html)
