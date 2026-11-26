#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo '用法: bash config/serve.sh 0.6B|4B 或 bash config/serve.sh /主模型目录 [/DSpark草稿目录]' >&2
  exit 2
}

case "${1:-}" in
  0.6B|4B)
    [[ $# == 1 ]] || usage
    model="Qwen/Qwen3-$1"
    revision=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
      "$(dirname "$0")/revisions.json" "$model")
    options=(--dtype bfloat16 --revision "$revision" --tokenizer-revision "$revision")
    ;;
  /*)
    [[ $# -le 2 ]] || usage
    model=$1
    options=(--dtype auto --served-model-name day01-local)
    spec=$(python3 - "$@" <<'PYTHON'
import json
from pathlib import Path
import sys


def config(directory):
    path = Path(directory) / "config.json"
    if not path.is_absolute():
        raise SystemExit(f"请传入服务器上的绝对路径：{directory}")
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"无法读取模型配置 {path}：{error}")


target = config(sys.argv[1])
if any("dspark" in arch.lower() for arch in target.get("architectures", [])):
    raise SystemExit("第一个目录是 DSpark 草稿，请先传配套主模型，再传草稿目录。")
if len(sys.argv) == 3:
    draft = config(sys.argv[2])
    architectures = draft.get("architectures", [])
    if not (draft.get("model_type") == "qwen3" and
            any(a in ("DSparkDraftModel", "Qwen3DSparkModel") for a in architectures)):
        raise SystemExit("第二个目录需要是与主模型配套的 Qwen3 DSpark 草稿。")
    size = draft.get("block_size")
    if type(size) is not int or size < 1:
        raise SystemExit("草稿 config.json 缺少有效的 block_size。")
    print(json.dumps({"method": "dspark", "model": sys.argv[2], "num_speculative_tokens": size}))
PYTHON
)
    if [[ -n "$spec" ]]; then
      options+=(--speculative-config "$spec")
    fi
    ;;
  *) usage ;;
esac

exec vllm serve "$model" "${options[@]}" --max-model-len "${MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.85}" --max-num-seqs 16 \
  --host 127.0.0.1 --port "${PORT:-8000}"
