# Prefill 一次，然后逐 token 解码

流式服务必须在算出第一个 token 时就交给调用者，也必须在 EOS 或预算耗尽时立即停止。今天把 Day 03 的 block、Day 04 的缓存与一个可验证的采样器拼成完整的单请求运行时。

~~~text
prompt IDs [1,S] ─prefill─► logits[:, -1] → 采样 → token ID → yield（主机可见）
                              ▲                              │
                              └── decode([token], past) ◄────┘
                                      EOS / 达到预算 → 返回
~~~

Logits 是未归一化的分数。greedy 直接取 argmax；温度 T>0 时先计算 softmax(logits/T)。top-k 保留最高 k 项，top-p 在按概率降序排列后保留使累计概率首次达到 p 的最小前缀，再归一化采样。以概率 [0.6,0.3,0.1]、p=0.8 为例，必须留下前两项；删除跨过阈值的第二项会改变分布。T=0 单独走 greedy，避免除零。固定 seed 用来复现实验，同一概率分布在不同后端仍可能采到不同 token。

**走读。** 手推 prompt [a,b]、预算 2。第一次 forward 输入 [a,b]，选出 c；第二次只输入 [c] 和 past。若 c 已是 EOS，只调用一次 forward。EOS 集合可能有多个元素，检查实际 generation_config。学习者实现 [sample、generate](starter/exercise.py)，分别用可控 logits、计数器和官方 greedy 序列验收。生成器 yield 的值包含触发停止的 EOS。

~~~bash
make test DAY=05
make lab DAY=05 ARGS="--length 16 --budget 6 --warmup 1 --repeat 3"
make lab DAY=05 IMPL=reference ARGS="--pretrained --prompt 'Name a planet.' --budget 6"
~~~

完整实验沿三天的同一实现分支逐层调用，Day 05 使用自己的 Day 03、04 成果。固定预训练对照使用官方 tokenizer 和同一组权重，greedy 路径每轮与 Transformers.generate(do_sample=False) 对照；随机采样检查候选集合、停止条件与同设备同 seed。记录输出文本、IDs 和 token_times_ms。预测总耗时近似为 prefill+采首 token+(N−1)×平均后续间隔；N=1 时 TPOT 无定义。Day 01 的 first_text_ms 还含 HTTP 与文本拼接，两者不能直接相减得出 GPU 时间。

固定源码 · [GenerationMixin.generate](https://github.com/huggingface/transformers/blob/8cb5963cc22174954e7dca2c0a3320b7dc2f4edc/src/transformers/generation/utils.py) · [固定模型的 EOS 配置](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/generation_config.json)

**故障、自测与挑战。** 第二步开始重复或跑偏，先比较两条路径第一个不同位置的 logits，并核对输入是否只含新增 token。预算为 0、首步 EOS、只输出 1 个 token，各应有几次 forward 和几个 ITL？挑战：用同一提示切换低/高温度，在固定设备上重复多轮，比较候选频率；分别说明数值正确性、随机波动和时间误差。
