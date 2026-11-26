# Day 11 · 对照 SGLang 与 vLLM 的缓存管理

相同的长系统提示进入两个引擎时，它们怎么查找已缓存的前缀，又怎样决定淘汰什么？

**实验起点**　同一张 GPU，分别启动 vLLM 与 SGLang。复用 Day 10 的精确 token 前缀负载，固定模型 revision、精度和并发。

## 动手要求

1. 画出 radix tree 与分块前缀查找的小例子，标记请求分叉、复用和释放。沿各自固定版本的源码找到相应结构。
2. 分别跑无共享和高共享、冷与热缓存场景；保存启动参数、实际 attention backend、输入输出 token 数与原始延迟。
3. 用同一组统计规则比较 TTFT 与排队，标记 tokenizer 或模板差异，并复查是否真正输入了相同 token。

## 当天验收

- [ ] 提交可复跑的两组服务配置与负载、延迟表和一次命中路径的源码说明。
- [ ] 指出一项数据支持的差异与一项本实验无法单独归因的数据结构差异。

延伸阅读 · [SGLang 项目](https://github.com/sgl-project/sglang) · [SGLang 论文](https://arxiv.org/abs/2312.07104)
