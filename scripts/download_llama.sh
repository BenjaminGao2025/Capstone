#!/bin/bash
# 下载 Meta-Llama-3-8B-Instruct 到 /hy-tmp(走 hf-mirror)
# 用法: HF_TOKEN=hf_xxx bash /hy-tmp/scripts/download_llama.sh
# token 仅经环境变量传入,绝不写入任何文件
set -e
source /hy-tmp/env.sh
: "${HF_TOKEN:?需要 HF_TOKEN 环境变量(Read-only token,用完即可在 HF 后台撤销)}"

python3 - <<'PY'
import os
from huggingface_hub import snapshot_download
p = snapshot_download(
    "meta-llama/Meta-Llama-3-8B-Instruct",
    local_dir="/hy-tmp/models/Meta-Llama-3-8B-Instruct",
    token=os.environ["HF_TOKEN"],
    # 只要 safetensors + 配置/tokenizer,跳过 original/ 下 16GB 的 .pth
    allow_patterns=["*.safetensors", "*.safetensors.index.json", "config.json",
                    "generation_config.json", "tokenizer*", "special_tokens_map.json"],
)
print("downloaded to:", p)
PY
echo "=== 校验 ==="
ls -lh /hy-tmp/models/Meta-Llama-3-8B-Instruct/
du -sh /hy-tmp/models/Meta-Llama-3-8B-Instruct/ /hy-tmp/huggingface/
df -h /hy-tmp | tail -1
echo "DOWNLOAD_DONE(此后所有 serve/benchmark 都用本地路径,不再需要 token)"
