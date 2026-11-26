#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  0.6B)
    model=Qwen/Qwen3-0.6B
    revision=c1899de289a04d12100db370d81485cdf75e47ca
    ;;
  4B)
    model=Qwen/Qwen3-4B
    revision=1cfa9a7208912126459214e8b04321603b3df60c
    ;;
  *)
    echo '用法: bash config/serve.sh 0.6B|4B' >&2
    exit 2
    ;;
esac

exec vllm serve "$model" --revision "$revision" --tokenizer-revision "$revision" \
  --dtype bfloat16 --max-model-len "${MAX_MODEL_LEN:-4096}" \
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION:-0.85}" --max-num-seqs 16 \
  --host 127.0.0.1 --port "${PORT:-8000}"
