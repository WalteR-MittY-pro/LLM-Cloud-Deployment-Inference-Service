# Day 13 · 写下第一个 CUDA Kernel

CPU 提交一次 kernel 后，GPU 上哪个线程负责结果数组里的第 i 个元素？从可以手算的小数组练到跨 block 的矩阵。

**实验起点**　Linux CUDA 开发环境、nvcc 和一张分配给你的 GPU。记录设备型号、compute capability、Toolkit 和编译参数；安排 Ada/Hopper 对照。

## 动手要求

1. 从 grid、block、thread 索引写 vector add；取不能整除 block 大小的 N 并验证尾部边界。
2. 写矩阵转置和朴素矩阵乘，测试非方阵与不能整除 tile 的形状，逐项同 CPU 或 PyTorch 结果比较。
3. 改变访问方向与 block 形状，测预热后的 kernel 时间。用线程到地址的映射解释合并访存，并定位 Ada 与 Hopper 的设备差异。

## 当天验收

- [ ] 提交三个 CUDA kernel、编译运行命令和正确性记录，包含奇数尺寸。
- [ ] 画一个 warp 对应的相邻地址，列出实测时间；注明测试设备及数据是否包含主机传输。

延伸阅读 · [CUDA 编程指南](https://docs.nvidia.com/cuda/cuda-programming-guide/) · [Hopper 调优指南](https://docs.nvidia.com/cuda/hopper-tuning-guide/)
