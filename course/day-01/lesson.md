# 从第一段响应定位推理链路

打开[部署与基础练习](README.md)前，想象有人反馈“页面已经连上，但文字很久才出来”。客户端何时看见文字？GPU 何时算出 token？这两个问题需要不同的证据。

~~~text
t0 发 POST → 服务端排队 → prefill → 采样 token → 解码为文本 → t1 收到首段非空正文
                                                后续若干 token → t2 收到 [DONE]
~~~

驱动和 runtime 让 GPU 能执行 PyTorch 运算；vLLM 加载权重后仍需把请求排进一次 forward。模型列表成功只能说明 HTTP 与模型注册路径可用。先探测 /v1/models，再发一次生成请求，就能缩小失败范围。仅拿型号的 0.6B 乘 2 字节会估出 1.2 GB。实际快照中 311 个张量共 751,632,384 个 BF16 元素，权重有效载荷为 1,503,264,768 字节。型号取整和嵌入层口径会影响估算；显存还要留给 KV、激活与运行时。

**手算。** 若 POST 在 0 ms，角色事件在 8 ms，正文“你好”在 55 ms，[DONE] 在 90 ms，则 first_text_ms=55、end_to_end_ms=90。即使“你好”刚好对应两个 token，也无法从这三个观测时刻算出 token 间隔。服务端计时需另取可关联的服务端证据。

## 引导与三个难度

1. **Level 1** 按 README 启动两种模型。先指出 curl 示例中的模型、输入、预算、结束条件，再在 starter/request_body.py 写出请求字典。切换模型后保留原请求内容。
2. **Level 2** 打开 [流解析骨架](starter/stream.py)，读一行字节，分别判断空行、角色事件、正文、服务端错误、[DONE] 和提前 EOF。先让模拟流测试通过。再实现 open_stream，把读超时传入 HTTP 调用；读取 HTTP 错误正文并保留状态码。先看 [client.py](client.py) 怎样关闭响应，再在回环服务上验证“已收到一半正文后断开”的结果。通过 `--level2` 让自己的解析器真正进入网络调用。
3. **Level 3** 用同一个已部署端点和足够长的固定 JSONL 负载，对比并发上限 1、4、8。把输入请求时间间距调到足以形成排队，三次用同一文件。先预热，分别观察客户端派发延迟、成功请求/秒、首段正文和错误率。有服务端 metrics 时再判断服务端是否排队。

从仓库根运行，API 客户端使用 CPU 环境，vLLM 进程在单独的 GPU 服务环境中：

~~~bash
make setup ENV=cpu
make test DAY=01
make test DAY=01 IMPL=reference
make lab DAY=01 ARGS="--level2 --warmup 1 --repeat 3 --concurrency 1"
~~~

默认的两条公开样例用于冒烟。对照实验应增大样本数，传 `--workload 路径`，并按实际启动配置传 `--model-revision`、`--tokenizer-revision`。每个 run 单独保存原始 SSE、失败行和报告。模拟流测试不占 GPU。真实模型验收需要两个型号各自的服务日志与成功调用。客户端的 `--timeout` 是单次网络读取超时；持续写入心跳的连接不会因此达到总时限。

**工业源码。** 从 HTTP handler 的 create_chat_completion 走到 OpenAIServingChat.create_chat_completion，再跟 chat_completion_stream_generator 看最后一个 [DONE] 如何发出，并对照自己的 read_chat_stream。[HTTP 路由](https://github.com/vllm-project/vllm/blob/62d4bc3c7e33b1b6c906e233e6af2d3506c482ca/vllm/entrypoints/openai/chat_completion/api_router.py#L59) · [SSE 生成函数](https://github.com/vllm-project/vllm/blob/62d4bc3c7e33b1b6c906e233e6af2d3506c482ca/vllm/entrypoints/openai/chat_completion/serving.py#L473)

**自测。** 只有 role 事件就断开时，status、first_text_ms、ttft_ms 应分别是什么？正文已经收到后断开呢？在 raw 日志里构造这两种情况并检查失败记录。
