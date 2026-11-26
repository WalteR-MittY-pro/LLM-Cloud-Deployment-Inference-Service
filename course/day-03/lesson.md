# 一行 token ID 怎样变成下一个词的打分

若你只会调用 model.generate，缓存错位或权重加载错误通常都表现成“答非所问”。今天把一次 forward 拆到能找到第一个错误张量为止。只使用推理模式、等长无 padding 的稠密 Qwen3。

~~~text
token IDs [B,S] → embedding [B,S,H] → RMSNorm → Q proj → 按 head 做 q_norm → RoPE ─┐
                                             → K proj → 按 head 做 k_norm → RoPE ─┤ GQA
                                             → V proj ───────────────────────────┘
       x₁ = x + O(context) → RMSNorm → SiLU(gate) × up → down
       x₂ = x₁ + down → 下一层 → 最终 RMSNorm → LM head → logits [B,S,V]
~~~

**先分清三种宽度。** 固定 0.6B 配置 H=1024、16 个 Q heads、8 个 KV heads、D=128，所以 Q 投影为 2048、K/V 各为 1024。不能用 H/16 代替 head_dim。定义 Q[B,16,S,128] 与 K/V[B,8,S,128]，每两个相邻 Q heads 使用同一 KV head。把 contexts 拼回 [B,S,2048] 后 o_proj 才投回 1024 以便相加。

RMSNorm(x)=w·x/√(mean(x²)+ε)。残差支路的归一化沿 hidden 维；Qwen3 在 Q/K 投影后还有沿每个 head 的 D 维归一化，V 沿原投影进入 attention。RoPE 把通道配对旋转，角度取决于绝对位置；本模型将前后半维配对。Attention 每行按 softmax((QKᵀ)/√D + causal_mask)V 聚合历史。若某行能看到未来 token，训练语义和推理前缀已经不匹配。SwiGLU 的 gate 与 up 先扩维、逐元素相乘，再 down 回残差宽度。

**手算与走读。** 令 B=1,S=2，两行打分均为零。带因果掩码时第 1 行只取 v₁，第 2 行取 (v₁+v₂)/2。先复现这个例子，再跟 [model.py](../../src/mini_engine/model.py) 的 forward → decoder_block → attend：找到开始旋转的位置和第一个残差相加处。共享实现借官方模块持有权重，forward 由自己的算子执行。

## 一层、一整个模型、一次改错

在 [starter/exercise.py](starter/exercise.py) 写 decoder_block。复用传入的 attention，使 Day 04 可以替换缓存路径。先在随机小配置验证 shape；再用固定预训练权重，分别比较首 block、各层紧凑 K/V、最终 logits。正式 oracle 直接调用官方 forward，首 block 用 hook 拿取，避开最终归一化的位置差异。

~~~bash
make test DAY=03
make lab DAY=03 ARGS="--length 6 --repeat 3"
make lab DAY=03 IMPL=reference ARGS="--pretrained --warmup 0 --repeat 1"
~~~

最后一条首次需下载约 1.50 GB 权重，FP32 运行需额外内存；默认随机权重不需下载。报告记录最大绝对误差、形状、stride、dtype、atol/rtol。CPU FP32 对照 3e-5；改 BF16 时重新解释容差。看见广播维度正确仍有偏差时，从 q_norm/k_norm、RoPE 的通道配对、head 分组逐项排查。精确到逐位相等不适合作为跨后端浮点验收条件。

固定源码 · [模型配置](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/config.json) · [Transformers Qwen3Attention.forward、Qwen3DecoderLayer.forward 及 Qwen3ForCausalLM.forward](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/models/qwen3/modeling_qwen3.py)

**自测与挑战。** 为什么输入和输出 hidden 都是 1024，但 O 投影的输入有 2048 个通道？只改最后一个输入 token，预测哪些 logits 会变，再用测试验证。挑战：暂时跳过 q_norm，用同一个 seed 记录最早发生偏差的张量，恢复后重跑。
