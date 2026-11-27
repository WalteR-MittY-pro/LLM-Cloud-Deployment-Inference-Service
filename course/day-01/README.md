# Day 01 · 在自己的 GPU 上部署 Qwen

**[先读本课的原理、图示、走读与自测](lesson.md)** · [实验记录协议](../../docs/experiment-protocol.md)

今天你要让另一个终端里的程序向 GPU 发出一个问题，看到回答逐段出现。先用 Qwen3-0.6B 跑通链路，再用同一套配置切到 Qwen3-4B。最后你应该能判断一次失败发生在驱动、模型加载、服务就绪还是客户端。

## 一次请求经过哪里

假设同事在内网做了一个问答页面。页面只持有模型名和问题，权重常驻服务器显存。你今天分别扮演服务端和页面开发者，用两个终端观察这条路径。

~~~text
终端 B                                终端 A · vLLM                       NVIDIA GPU
用户问题 → build_request → HTTP POST → 对话模板、tokenizer → 调度、模型前向 → logits
看到逐段正文 ← read_chat_stream ← SSE ← 解码为文本 ← 采样、继续生成 ← 下一步前向
~~~

驱动让系统和程序访问设备。PyTorch 的 CUDA 构建提供张量运算，底层会使用 cuBLAS 等库。vLLM 加载 Safetensors 权重，安排请求何时执行。Tokenizer 把文字变成 token ID，再把生成的 ID 还原成文字。Hugging Face 模型仓库提供权重、配置和 tokenizer。CUDA Toolkit 提供 nvcc 等开发工具，第 13 天写 CUDA 时会用到。今天走预编译包安装路径。分别观察 nvidia-smi 里的驱动能力、torch.version.cuda 和 nvcc 的工具链版本，它们回答三个不同的问题。

## 1. 在获得 GPU 配额的 Linux 计算节点准备环境

以下步骤面向原生 Linux、Bash 和支持 BF16 的 NVIDIA GPU。两个终端要进入**同一台计算节点**，第二个终端通过回环地址访问服务。保留调度平台分配的 CUDA_VISIBLE_DEVICES。两个模型分别在同一张卡上顺序运行。

~~~bash
git clone https://github.com/WalteR-MittY-pro/LLM-Inference-Lab.git llm-inference-lab
cd llm-inference-lab/course/day-01
mkdir -p runs
SESSION=$(mktemp -d "$PWD/runs/session-1127")
printf '第二个终端设置 SESSION=%s\n' "$SESSION"
git rev-parse HEAD > "$SESSION"/course-commit.txt
nvidia-smi -L | tee "$SESSION"/gpu-list.txt
nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv | tee "$SESSION"/gpus.csv
nvidia-smi topo -m | tee "$SESSION"/topology.txt
~~~

记录分配到的型号、显存、整卡或 MIG、其他可用卡是否同机、节点间网络和模型缓存所在磁盘。双卡与 Kubernetes 权限留给后续课程，今天只需一张分配给你的卡。若 nvidia-smi 本身就失败，先确认当前是在作业的 GPU 节点。

服务器需要 Git、curl、uv、可访问的软件源和模型缓存。先运行 `uv --version`；没有 uv 时按[官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)安装到自己的用户目录。固定 0.6B 快照的 Safetensors 头部列出 751,632,384 个 BF16 元素，对应约 1.50 GB 权重；4B 按参数量粗估约 8 GB，预留包、内核、缓存和临时空间。需要换缓存磁盘时，在下载前将 HF_HOME 指向自己可写的目录。

~~~bash
make -C ../.. setup ENV=vllm
source ../../environments/vllm/.venv/bin/activate
vllm download-kernels
uv pip freeze > "$SESSION"/python-packages.txt
python - <<'PY' | tee "$SESSION"/torch.txt
import torch
print("PyTorch", torch.__version__, "CUDA build", torch.version.cuda)
assert torch.cuda.is_available(), "PyTorch 当前看不到 CUDA 设备"
print("GPU", torch.cuda.get_device_name(0), "capability", torch.cuda.get_device_capability(0))
print("CUDA tensor", (torch.ones(1, device="cuda") + 1).item())
PY
~~~

看见张量结果 2.0，说明这个 Python 环境已经能在 GPU 执行计算。environments/vllm/uv.lock 固定 Linux 服务依赖，serve.sh 固定两种模型及 tokenizer 的 revision。驱动与 wheel 不匹配时，带着驱动版本、torch.version.cuda 和报错核对安装矩阵；共享节点的驱动由平台管理。[vLLM 0.34.0 GPU 安装说明](https://docs.vllm.ai/en/v0.34.0/getting_started/installation/gpu/)

## 2. 用 curl 打通最短链路

终端 A 在本课目录运行以下命令，保持它在前台。第一次会下载模型。等待服务开始监听，再转到终端 B。

~~~bash
set -o pipefail
bash config/serve.sh 0.6B 2>&1 | tee "$SESSION"/server-0.6B.log
~~~

终端 B 从仓库根目录进入本课。先看服务列出的模型 ID，再看流式响应的原文。

~~~bash
cd course/day-01
source ../../environments/vllm/.venv/bin/activate
read -r -p '把终端 A 输出的 SESSION 绝对路径粘贴到这里: ' SESSION
set -o pipefail
curl -fsS http://127.0.0.1:8000/v1/models
curl -fsS -N http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"用一句话解释 KV Cache。"}],"max_tokens":128,"temperature":0,"stream":true,"chat_template_kwargs":{"enable_thinking":false}}' \
  | tee "$SESSION"/curl-0.6B.sse
~~~

在原始输出里找第一段非空的 choices[0].delta.content 和最后的 `data: [DONE]`。一个 SSE 事件可能只含角色，也可能携带一段正文；收到的文本分段数不能直接当成 token 数。

## 3. 亲手写请求体

打开 [starter/request_body.py](starter/request_body.py)，完成 build_request(model, prompt, max_tokens)。保留传入的模型名、原文和输出预算，生成上面 curl 示例的字典。若模型名或问题只有空白，或预算小于 1，抛出 ValueError。把 temperature 设为 0、关闭 Qwen3 thinking，两次请求就可以用相同的生成条件观察回答。

从本课目录运行。初始骨架会报 NotImplementedError，补完后五项测试都应通过。本机用 Python 3 即可先做这部分，客户端和测试只依赖标准库。

~~~bash
python -m unittest discover -s tests -p test_day01.py -v
python client.py --model Qwen/Qwen3-0.6B --record "$SESSION"/chat-0.6B.json
~~~

[client.py](client.py) 的 run 先用 /v1/models 检查服务实际加载的 ID，再向 /v1/chat/completions 提交你构造的请求。read_chat_stream 逐行读取 SSE，把正文立即打印出来；只在收到结束标志和非空正文后写入本次成功记录。first_text_ms 从发出 POST 前计到收到第一段正文，含本机 HTTP 和服务端开销；精确的逐 token 计时留给 Day 12。

做完再看[参考实现](reference/request_body.py)。用同一套测试及真实端点对照它：

~~~bash
LAB_REFERENCE=1 python -m unittest discover -s tests -v
python client.py --reference --model Qwen/Qwen3-0.6B --record "$SESSION"/reference-0.6B.json
~~~

## 4. 在同一张卡切换模型

终端 A 用 Ctrl-C 停止自己的 0.6B 服务，确认 GPU 显存释放，然后启动 4B。终端 B 等到模型列表出现新的 ID，用自己的练习实现提问。

~~~bash
# 终端 A
bash config/serve.sh 4B 2>&1 | tee "$SESSION"/server-4B.log
~~~

~~~bash
# 终端 B
curl -fsS http://127.0.0.1:8000/v1/models
python client.py --model Qwen/Qwen3-4B --record "$SESSION"/chat-4B.json
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv > "$SESSION"/after-4B.csv
~~~

如果 4B 报 KV 空间不足，先检查剩余显存，再尝试 `MAX_MODEL_LEN=2048 bash config/serve.sh 4B`。权重本身放不下时需要更大配额。服务列表有模型却返回 404 时，核对请求体里的模型 ID；连接被拒绝则看终端 A 的最后一段日志和端口。若端口已分配，可用 `PORT=8001` 启动，同步调整 curl 地址并给客户端传 `--base-url http://127.0.0.1:8001`。

## 当天验收

- [ ] 交付设备清单、拓扑、软件版本和仓库 commit；用一句话分别解释驱动、CUDA runtime、PyTorch 和 vLLM 的职责。
- [ ] 自己的实现通过测试。在同一张已分配 GPU 上先后启动两个模型，两份 chat JSON 中模型名不同，均有非空回答和 done=true，并能找到对应的服务日志。
- [ ] 在 curl 原始记录里指出首段正文和结束标志，解释为什么 /v1/models 成功后还要发一次实际生成请求。
- [ ] 在本次 SESSION 目录的 notes.md 记下设备、启动参数、一次遇到的问题及定位依据。单次计时用于验证调用；模型性能比较到 Day 12 再做预热和重复测量。结束后 Ctrl-C 释放服务。

手动部署记录按 SESSION 区分。正式测量从仓库根目录走 `make lab DAY=01`，自动保存每次尝试及失败。如果暂时只有 CPU，可以完成请求体和测试，把两个模型的 GPU 验收留空。

官方资料 · [vLLM Quickstart](https://docs.vllm.ai/en/v0.34.0/getting_started/quickstart/) · [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) · [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B)


## 学习结果：
1. 启动模型什么的都是脚本，vllm命令也很基础，主要是python里http请求发送逻辑：字典->json->encode为字节码->urlopen发送请求到url上
2. 然后就是vllm返回的时候，怎么判断连接还开着？那么当没超时且连接还开着，则可以持续接收，
如果遇到了EOF，那么报错返回，一般是回答中断；如果超时报超时错误、如果收到error，那么就直接报请求失败，error里有失败原因，这个时候收不收到[Done]已经无所谓了；最后如果没有超时，没有error，收到done，那么说明正常结束了