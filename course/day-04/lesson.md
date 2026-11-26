# 给一个新 token 接上自己的历史

在第 101 步重算前 100 个位置，会重复执行它们的投影与层计算。KV 缓存保存每一层已经旋转的 K 和原始 V。只存必要的 KV heads，同时让新 query 看见属于自己的历史。

~~~text
一个请求，一层缓存
历史 K/V [B,Hkv,3,D] + 新 K/V [B,Hkv,2,D] → [B,Hkv,5,D]
                                  key 绝对位置   0 1 2 3 4
新 query 绝对位置 3                               ✓ ✓ ✓ ✓ ×
新 query 绝对位置 4                               ✓ ✓ ✓ ✓ ✓
~~~

若历史长度 P，本轮长度 T，打分矩阵是 [B,Hq,T,P+T]。新行 i 的可见条件为 j≤P+i；简单地在 T×(P+T) 矩阵的左上角套三角掩码会错位。位置编码也从 P 起算。Key 已旋转，拼接时不应再旋转历史。分组注意力只在计算时扩展头；把重复后的 heads 写入缓存会使显存随 Hq 而非 Hkv 增长。

**预测。** KV bytes=2×层数×B×Hkv×S×D×每元素字节。对 0.6B、28 层、8 个 KV heads、D=128、BF16，单请求每 token 为 112 KiB；1024 token 为 112 MiB。逐块比较前先写下理论值。torch 显存峰值还包括权重、张量和临时工作区；本教学实现每步 cat 还会复制历史，工业分页实现有不同开销。缓存把单步 attention 的历史读取保留下来，单个新 query 仍要与 S 个 key 做点积。

## 从 Day 03 扩展

1. 在 [starter/exercise.py](starter/exercise.py) 写 attend。每层输入和输出的 KV 都归调用者所有；切换请求时传入相应的 past。单测可先隔离此函数，完整实验会调用你 Day 03 的 block。
2. 按 [3,2,1] 切一段输入，分别对齐全部位置的 logits 和所有层缓存；再交错 A、B、A 检查状态隔离。自己写下第二段的正确可见矩阵，再跑测试。
3. 用相同模型、token 和 dtype，比较 prefill 后一 token 的增量时间与整段+一 token 重算时间。实验一次只换 length，同一组预热、重复与缓存初始状态。

~~~bash
make test DAY=04
for n in 128 512 1024 2048; do
  make lab DAY=04 ENV=pytorch DEVICE=cuda ARGS="--length $n --dtype bfloat16 --warmup 2 --repeat 5"
done
~~~

CPU 冒烟可用默认 ENV、DEVICE 和 length。上述长度扫描使用随机小模型；固定权重对照时通过 `--pretrained --prompt '…'` 输入文本，记录实际 token 数。requests.jsonl 同时给出 prefill_ms、elapsed_ms（增量）、recompute_ms、kv_tensor_bytes 和 predicted_kv_bytes；CUDA 分阶段记录相对各自开始时已分配量的额外峰值，单位为字节。预测偏差先查 dtype、层数、heads 和计数范围。

固定源码 · [Transformers DynamicCache 与逐层 update](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/cache_utils.py) · [Qwen3Attention 更新缓存的位置](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/models/qwen3/modeling_qwen3.py)

**自测与挑战。** 只测 T=1 会漏掉哪些未来信息泄漏？B 完成释放时，A 的哪组张量必须不变？挑战：给第二段最后一个 token 换值，逐行证明第一行输出不变。
