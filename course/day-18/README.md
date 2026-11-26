# Day 18 · 测量两张 H200 之间的 NCCL 通信

同一台机器里的两张 GPU 也可能通过不同链路通信。先把两卡间传送不同大小数据的代价测出来，明天才好解释张量并行。

**实验起点**　至少两张实际分配的 H200。首选同节点；若跨节点，登记网络接口、节点布局与实际传输路径。

## 动手要求

1. 记录 GPU 物理/逻辑 ID、nvidia-smi topo -m 和 rank 映射。画出真实连接并说明 DP、TP、PP、EP 各自在哪里交换数据。
2. 用 torch.distributed 写两个 rank 的 AllReduce。各 rank 给定不同的已知向量，在两个设备上验证求和结果与期望一致。
3. 用固定版本 nccl-tests 扫描消息大小，保存延迟、algbw、busbw；识别使用的传输。若有第三张卡，逐对比较而非直接扩至 TP3。

## 当天验收

- [ ] 交付拓扑图、rank 日志、正确性断言与真实双卡的通信曲线。
- [ ] 用一次小消息和一次大消息解释延迟/带宽主导区间；单卡权限时保留诊断并将双卡实测标为待做。

延伸阅读 · [NCCL collectives](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html) · [nccl-tests](https://github.com/NVIDIA/nccl-tests)
