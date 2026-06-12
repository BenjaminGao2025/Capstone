#!/bin/bash
# 迁移/清盘后的一键重建(在服务器上跑)
# 前置:已从 Mac rsync vllm-ltr 源码到 /hy-tmp/vllm-ltr、scripts 到 /hy-tmp/scripts
# 用法: bash /hy-tmp/scripts/rebuild_hytmp.sh
set -e

echo "=== 1. 目录与 env.sh ==="
mkdir -p /hy-tmp/tmp /hy-tmp/pip-cache /hy-tmp/huggingface /hy-tmp/results /hy-tmp/models
cat > /hy-tmp/env.sh << "EOF"
export TMPDIR=/hy-tmp/tmp
export PIP_CACHE_DIR=/hy-tmp/pip-cache
export HF_HOME=/hy-tmp/huggingface
export HF_ENDPOINT=https://hf-mirror.com
export TORCH_CUDA_ARCH_LIST=8.6
export PATH=/usr/local/cuda/bin:$PATH
export CUDA_HOME=/usr/local/cuda
EOF
grep -q "source /hy-tmp/env.sh" /root/.bashrc || sed -i "1i source /hy-tmp/env.sh" /root/.bashrc
source /hy-tmp/env.sh

echo "=== 2. 系统盘体检(钉死版本应随迁移保留) ==="
python3 - <<'PY'
import sys
try:
    import torch, transformers, numpy
    assert torch.__version__.startswith("2.2.1"), torch.__version__
    assert transformers.__version__ == "4.40.1", transformers.__version__
    print("PINNED_DEPS_OK", torch.__version__, transformers.__version__, numpy.__version__)
except Exception as e:
    print("PINNED_DEPS_BROKEN:", e)
    sys.exit(1)
PY

echo "=== 3. trace + 预测器下载(后台) ==="
B=/hy-tmp/vllm-ltr/benchmarks
DS=https://hf-mirror.com/datasets/LLM-ltr/Llama3-Trace/resolve/main
MD=https://hf-mirror.com/LLM-ltr/OPT-Predictors/resolve/main
(
cd $B
for f in \
  "lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl" \
  "lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c20000:30000-rFalse.jsonl" \
  "llama3-8b-sharegpt-test-t1-s0-8192.jsonl" \
  "llama3-8b-sharegpt-train-t1-s0-8192.jsonl" \
  "llama3-8b-alpaca-test-t1-s0-8192.jsonl" \
  "llama3-8b-alpaca-train-t1-s0-8192.jsonl"; do
  curl -sfL --retry 3 -o "$f" "$DS/$f" && echo "trace ok: $f"
done
for d in \
  opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 \
  opt-125m-llama3-8b-lmsys-class-trainbucket820-b32 \
  opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 \
  opt-125m-llama3-8b-sharegpt-class-trainbucket820-b32; do
  mkdir -p MODEL/results/$d/finetuned
  curl -sfL --retry 3 -o MODEL/results/$d/usage_config.json "$MD/$d/usage_config.json"
  curl -sfL --retry 3 -o MODEL/results/$d/finetuned/config.json "$MD/$d/finetuned/config.json"
  curl -sfL --retry 3 -o MODEL/results/$d/finetuned/model.safetensors "$MD/$d/finetuned/model.safetensors"
  echo "predictor ok: $d"
done
echo "ASSETS_DONE"
) > /hy-tmp/results/rebuild-assets.log 2>&1 &

echo "=== 4. vllm 重编译(后台,MAX_JOBS=8 实测安全) ==="
export MAX_JOBS=8
cd /hy-tmp/vllm-ltr
nohup pip install -e . --no-build-isolation > /hy-tmp/rebuild-build.log 2>&1 &
echo "BUILD_PID=$!"

echo "REBUILD_LAUNCHED — 看进度:"
echo "  tail -f /hy-tmp/rebuild-build.log      (编译,~40min)"
echo "  tail -f /hy-tmp/results/rebuild-assets.log  (下载)"
echo "Llama 权重另跑: HF_TOKEN=hf_xxx bash /hy-tmp/scripts/download_llama.sh"
