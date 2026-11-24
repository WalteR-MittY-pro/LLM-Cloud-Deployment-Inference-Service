# 第一课 · 请求什么时候才算开始回答？

目标是区分四个时刻：客户端发送请求、收到响应头、收到首个非空正文、收到流结束标记。假如上游 150 ms 时就生成第一个字，网关却等完整回答再一次性发出，内容和 HTTP 状态都正确，用户仍然觉得卡。先亲眼看到这个现象，再写代码。

## 实验一 · 先用协议演示上游

在项目根目录打开终端 A：

```bash
./labgo run ./cmd/platform -role demo -listen 127.0.0.1:8001
```

终端 B：

```bash
python3 scripts/probe.py
```

预期约 150 ms 看到“云”，约 300 ms 看到“服务”，最后一行有 `complete: true` 对应的 JSON 信息。启动抖动会改变具体数值。演示的 token 数是固定值，仅用来验证协议。直看线路上的原始数据：

```bash
curl -sSN http://127.0.0.1:8001/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"lab-model","stream":true,"messages":[{"role":"user","content":"你好"}]}'
```

观察第一帧的 role、两帧正文、usage 和 [DONE]。SSE 用空行分隔事件，TCP 读到的一块数据可能是半帧或多帧。流里的一个片段也可能包含多个 token。先自己回答：若把 role 帧当作首 token，你会把哪段等待漏掉？

## 实验二 · 让网关逐帧转发

打开终端 C：

```bash
./labgo run ./cmd/platform -role gateway -listen 127.0.0.1:8080 -dev-upstream http://127.0.0.1:8001
```

`python3 scripts/probe.py --url http://127.0.0.1:8080` 起初返回 501，代表进入了留白函数。只编辑 [stream.go](../internal/platform/stream.go) 中的 Relay。输入是上游 SSE，输出是可刷新的 HTTP 响应。保留事件内容和边界，记录首个非空正文、usage 和结束标记。上游提前断流要能向调用者报告，记录已经收到的部分。可查 Go 的 bufio.Reader、net/http.ResponseController 和 io.Reader。不要把整个响应读到内存再发。

```bash
./labgo test -tags practice ./internal/platform -run TestDay1 -v
```

测试分别覆盖完整流、只有 role 就断开、下游必须在上游结束前收到正文。改完重启网关，再对比直连与经网关的两次 probe；记录终端中两条正文出现的时间。请求开始传数据后，服务器无法改写已经发出的 200，客户端必须辨认完整结束。资料见 [Go HTTP](https://pkg.go.dev/net/http)。

## 实验三 · 先学会挂载、端口和日志

在 Linux 或 Docker Desktop 的项目目录中，用课程专用容器名。宿主机文件通过只读挂载出现在容器 /www；127.0.0.1:18080 是宿主机入口，8080 是容器内端口。

```bash
mkdir -p work/site
echo 'ready from mounted file' > work/site/index.html
docker run -d --name ti-web -p 127.0.0.1:18080:8080 --mount "type=bind,src=$PWD/work/site,dst=/www,readonly" busybox:1.36.1 httpd -f -p 8080 -h /www
curl -fsS http://127.0.0.1:18080
docker port ti-web
docker inspect ti-web --format '{{json .Mounts}}'
docker exec ti-web cat /www/index.html
```

重复创建一个名为 ti-unpublished 的容器，省略 -p。用 docker exec 在里面 wget -qO- http://127.0.0.1:8080，再用 docker port 检查。然后单独制造启动错误：

```bash
docker run --name ti-bad busybox:1.36.1 sh -c 'cat /missing/config || exit 1'
docker ps -a --filter name=ti-bad
docker logs ti-bad
docker inspect ti-bad --format '{{.State.Status}} exit={{.State.ExitCode}}'
```

验收：解释“端口没有发布”和“容器已退出”为什么都能让宿主机连接失败，写出区分二者的第一条检查。完成后只清理自己创建的实例，例如 docker rm -f ti-web ti-bad；ti-unpublished 如已创建也单独删除。

## 实验四 · 换成真实模型

在有 NVIDIA GPU 和容器运行时的 Linux 上操作。课程默认使用一份本地、单卡可容纳、带聊天模板的指令模型，例如 Qwen2.5-1.5B-Instruct。将 MODEL_DIR 指向包含 config.json、tokenizer 和权重的实际目录。先检查 nvidia-smi，选择与驱动兼容的 vLLM 镜像版本并固定 digest；已有可运行服务器可直接使用其 URL 和模型别名。

```bash
export MODEL_DIR=/absolute/path/to/local-model
export VLLM_IMAGE=vllm/vllm-openai:YOUR_VERIFIED_TAG
docker pull "$VLLM_IMAGE"
VLLM_PIN=$(docker image inspect --format '{{index .RepoDigests 0}}' "$VLLM_IMAGE")
docker run -d --name ti-model --gpus device=0 --shm-size 2g \
  -p 127.0.0.1:8000:8000 --mount "type=bind,src=$MODEL_DIR,dst=/models/current,readonly" \
  "$VLLM_PIN" --model /models/current --served-model-name lab-model --max-model-len 4096
docker logs --tail 40 ti-model
curl -fsS http://127.0.0.1:8000/v1/models
python3 scripts/probe.py --url http://127.0.0.1:8000
```

权重加载期间反复观察日志，再试最后两个命令。用相同模型别名重启网关，把 -dev-upstream 改为 http://127.0.0.1:8000；如果网关在另一台机器，使用实验私网或 SSH 转发。记录镜像 digest、模型 revision、GPU 型号、第一条冷请求和预热后的十个样本。

**过关**：三个练习测试通过；用同一个问题分别直连真实 vLLM 和经过网关完成流式生成；能从日志、客户端时间戳判断一次人为制造的失败发生在哪一层。资料见 [vLLM 官方容器指南](https://docs.vllm.ai/en/stable/deployment/docker/)。
