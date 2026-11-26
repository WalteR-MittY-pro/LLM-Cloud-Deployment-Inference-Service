#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  0.6B|4B) model="Qwen/Qwen3-$1" ;;
  *) echo '用法: bash config/serve.sh 0.6B|4B' >&2; exit 2 ;;
esac
config_dir=$(dirname "$0")
revision=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
  "$config_dir/revisions.json" "$model")

exec vllm serve "$model" --revision "$revision" --tokenizer-revision "$revision" \
  --dtype bfloat16 --max-model-len "${MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.85}" --max-num-seqs 16 \
  --host 127.0.0.1 --port "${PORT:-8000}"
