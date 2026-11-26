# Day 22 · 用 Kubernetes 管理两个 CPU 服务副本

一个 Pod 退出后，哪个组件把副本数补回来？先用轻量 HTTP 服务观察控制器，不必为学习生命周期占住 GPU。

**实验起点**　家庭双机 K3s 的实验 namespace（`home-cluster`）。集群未就绪时先在本地 kind/Minikube CPU 集群练生命周期，实际双节点恢复另行验收。

## 动手要求

1. 声明两个返回实例标识的 HTTP 副本和 Service，配置 readiness probe，用 port-forward 请求并记录响应。
2. 删除自己实验中的一个 Pod，观察 Deployment、ReplicaSet、Pod 和 Service endpoints 的变化，记录恢复时间；滚动更新镜像并观察 ready 数。
3. 在实验 namespace 制造一个镜像标签错误或 readiness 配置错误。用 get events、describe 和 logs 定位原因并修复。

## 当天验收

- [ ] 交付 manifests、可见的实例标识、故障与恢复时间线；解释调度器、kubelet 和控制器各自的动作。
- [ ] 能够从事件区分 Pending、ImagePullBackOff 和应用启动后退出，并说明 readiness 对接流量的影响。

延伸阅读 · [Kubernetes 基础](https://kubernetes.io/docs/tutorials/kubernetes-basics/) · [kind](https://kind.sigs.k8s.io/)
