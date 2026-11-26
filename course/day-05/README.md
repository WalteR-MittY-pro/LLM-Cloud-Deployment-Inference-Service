# Day 05 · 写出从提示词到流式输出的生成循环

**[先读本课的原理、图示、走读与自测](lesson.md)** · [实验记录协议](../../docs/experiment-protocol.md)

把前四天串成第一个里程碑。服务接到一段文本后，先处理整个 prompt，然后每次只决定一个新 token。

**实验起点**　用预训练小模型、tokenizer 和单张 GPU；复用 Day 04 的正确性测试。

## 动手要求

1. 自己驱动 forward，不调用 generate。先做 greedy，区分首次 prefill 和每步 decode，逐步产出生成 token。
2. 加入 temperature、top-k、top-p、EOS 和最大输出长度。用可控 logits 测 EOS 在第一步出现、输出仅一个 token、达到长度上限三种边界。
3. 用同一提示词跑预训练模型，记录提交、首 token 和末 token 的时刻。只在至少两个输出 token 时计算 TPOT。

## 当天验收

- [ ] 提交 mini_inference.py、测试和一次真实 GPU 生成记录；greedy token 序列能与相同参数下的库实现对照。
- [ ] 从 tokenizer 到首 token 逐步讲出调用顺序，再用 Day 04 的实验证明下一步如何利用缓存。

延伸阅读 · [Transformers 生成接口](https://huggingface.co/docs/transformers/main/en/main_classes/text_generation)
