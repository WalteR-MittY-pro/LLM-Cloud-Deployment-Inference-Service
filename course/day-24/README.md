# Day 24 · 用 Helm、持久化存储和 Gateway 发布模型

发布新模型时，客户端不应在权重尚未加载时接入，重建 Pod 也不应每次重新下载同一份权重。把这些行为写进部署配置。

**实验起点**　基于 Day 23 通过的 manifests、可用 StorageClass、已授权的 Gateway/Ingress 和 GPU 配额。

## 动手要求

1. 将镜像、模型 revision、GPU 数、TP、replicas、端口、PVC 和探针提取为 Helm values。渲染并核对 GPU 请求与实际并行方式。
2. 挂载 PVC，记录访问模式和跨节点限制。装载模型、更新 release、重建自己的 Pod 并回滚，观察缓存复用与 readiness。
3. 通过 Gateway 测鉴权、SSE、超时和取消。使用实验 Secret 引用凭据，并确认客户端断开后请求释放；记录限流设置与响应。

## 当天验收

- [ ] 交付 chart、可复现的 values、安装/回滚命令、权重复用证据及一次经过 Gateway 的真实流式调用。
- [ ] 用事件证明加载期间尚未接流量，验证无凭据请求被拒绝且日志未写出凭据。

延伸阅读 · [Helm 文档](https://helm.sh/docs/) · [持久卷](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) · [Gateway API](https://gateway-api.sigs.k8s.io/)
