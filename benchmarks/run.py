import argparse
import json
from pathlib import Path

from .doctor import inspect
from .lessons import ROOT
from .records import attempt, report


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("doctor")
    show = commands.add_parser("report")
    show.add_argument("--run", type=Path, required=True)
    lab = commands.add_parser("lab")
    lab.add_argument("--day", choices=["01", "02", "03", "04", "05"], required=True)
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
        print(json.dumps(inspect(), ensure_ascii=False, indent=2))
        return
    if args.action == "report":
        report(args.run)
        print((args.run / "report.md").read_text())
        return
    with attempt(args.root, args.day, vars(args)) as (path, meta):
        if (
            min(args.repeat, args.threads, args.length, args.concurrency, args.timeout) <= 0
            or args.warmup < 0
            or args.budget < 0
        ):
            raise ValueError("检查 repeat、threads、length、concurrency、timeout、budget、warmup")
        if args.day == "01":
            from .api_lab import run
        else:
            from .model_lab import run
        run(args, path, meta)


if __name__ == "__main__":
    main()
