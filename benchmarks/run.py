import argparse
import json
from pathlib import Path

from .doctor import inspect
from .lessons import ROOT
from .records import attempt, report
from .profiles import ENVS, PROFILES


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--profile", choices=PROFILES)
    doctor.add_argument("--env", choices=ENVS)
    doctor.add_argument("--allocated-gpus", type=int)
    doctor.add_argument("--kube-context")
    doctor.add_argument("--torch", action="store_true", default=None)
    doctor.add_argument("--output", type=Path)
    show = commands.add_parser("report")
    show.add_argument("--run", type=Path, required=True)
    show.add_argument("--profile", choices=PROFILES)
    lab = commands.add_parser("lab")
    lab.add_argument("--day", choices=["00", "01", "02", "03", "04", "05", "19", "28"], required=True)
    lab.add_argument("--profile", choices=PROFILES)
    lab.add_argument("--env", choices=ENVS)
    lab.add_argument("--kube-context")
    lab.add_argument("--smoke", choices=["inventory", "cuda", "nccl"], default="inventory")
    lab.add_argument(
        "--gpus", "--allocated-gpus", type=int, help="操作人明确确认已分配给同一容器的 NCCL 卡数"
    )
    lab.add_argument("--home-port", type=int, default=8000)
    lab.add_argument("--cloud-port", type=int, default=18000)
    lab.add_argument("--route", choices=["home", "cloud", "round-robin"], default="round-robin")
    lab.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    lab.add_argument("--impl", choices=["starter", "reference"], default="starter")
    lab.add_argument("--root", default=str(ROOT / "runs"))
    lab.add_argument("--seed", type=int, default=7)
    lab.add_argument("--threads", type=int, default=1)
    lab.add_argument("--warmup", type=int, default=1)
    lab.add_argument("--repeat", type=int, default=3)
    lab.add_argument("--layout", choices=["contiguous", "strided"], default="contiguous")
    lab.add_argument("--length", type=int, default=16)
    lab.add_argument("--budget", type=int, default=6)
    lab.add_argument("--dtype", choices=["float32", "float16", "bfloat16"], default="float32")
    lab.add_argument("--prompt", default="Give one use of a KV cache.")
    weights = lab.add_mutually_exclusive_group()
    weights.add_argument("--pretrained", action="store_true")
    weights.add_argument("--checkpoint", help="本地 Qwen3-0.6B 快照目录")
    lab.add_argument("--temperature", type=float, default=0)
    lab.add_argument("--top-k", type=int, default=0)
    lab.add_argument("--top-p", type=float, default=1)
    lab.add_argument("--model", default="Qwen/Qwen3-0.6B")
    lab.add_argument("--model-revision")
    lab.add_argument("--tokenizer-revision")
    lab.add_argument("--base-url", default="http://127.0.0.1:8000")
    lab.add_argument("--timeout", type=float, default=30)
    lab.add_argument("--workload", default=str(ROOT / "benchmarks/datasets/first-chat.jsonl"))
    lab.add_argument("--concurrency", type=int, default=1)
    lab.add_argument("--level2", action="store_true")
    args = parser.parse_args()
    if args.action == "doctor":
        if args.kube_context and args.profile not in ("home-cluster", "hybrid"):
            parser.error("--kube-context requires home-cluster or hybrid")
        observation = inspect(args.profile, args.kube_context, args.torch or args.profile is None)
        if args.allocated_gpus is not None and args.allocated_gpus < 0:
            parser.error("--allocated-gpus must be nonnegative")
        observation["declared_allocated_gpu_count"] = args.allocated_gpus
        observation["env"] = args.env
        rendered = json.dumps(observation, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as out:
                out.write(rendered)
        else:
            print(rendered, end="")
        return
    if args.action == "report":
        if args.profile and json.loads((args.run / "run.json").read_text()).get("profile") != args.profile:
            parser.error("run was recorded with a different profile")
        report(args.run)
        print((args.run / "report.md").read_text())
        return
    if args.day == "00" and args.smoke != "inventory":
        args.device = "cuda"
    config = vars(args).copy()
    config["kube_context"] = "explicit" if args.kube_context else None
    with attempt(args.root, args.day, config, kube_context=args.kube_context) as (path, meta):
        if (
            min(args.repeat, args.threads, args.length, args.concurrency, args.timeout) <= 0
            or args.warmup < 0
            or args.budget < 0
        ):
            raise ValueError("检查 repeat、threads、length、concurrency、timeout、budget、warmup")
        if args.gpus is not None and args.gpus < 0:
            raise ValueError("Allocated GPU count must be nonnegative")
        if args.day != "00" and args.smoke != "inventory":
            raise ValueError("CUDA/NCCL bootstrap checks are available on Day 00")
        if args.day == "19" and args.profile != "cloud-h200-multi":
            raise ValueError("Day 19 replays an already provisioned cloud-h200-multi API")
        if args.day == "28" and args.profile != "hybrid":
            raise ValueError("Day 28 API routing requires PROFILE=hybrid")
        if args.day == "00":
            from .bootstrap import run
        elif args.day in ("01", "19", "28"):
            from .api_lab import run
        else:
            from .model_lab import run
        run(args, path, meta)


if __name__ == "__main__":
    main()
