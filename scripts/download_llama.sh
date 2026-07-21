#!/bin/bash
# 下载 Meta-Llama-3-8B-Instruct 到 /hy-tmp(走 hf-mirror)
# 用法: HF_TOKEN=hf_xxx bash /hy-tmp/scripts/download_llama.sh
# token 仅经环境变量传入,绝不写入任何文件
set -e
source /hy-tmp/env.sh
# Use modelscope instead of HF to avoid gated token issues and speed up in China
python3 - <<'PY'
import os
from modelscope.hub.snapshot_download import snapshot_download
p = snapshot_download(
    "LLM-Research/Meta-Llama-3-8B-Instruct",
    local_dir="/hy-tmp/models/Meta-Llama-3-8B-Instruct",
    ignore_file_pattern=[r".*\.pth$"] # skip the 16GB original weights
)
print("downloaded to:", p)
PY
echo "=== 校验 ==="
ls -lh /hy-tmp/models/Meta-Llama-3-8B-Instruct/
du -sh /hy-tmp/models/Meta-Llama-3-8B-Instruct/ /hy-tmp/huggingface/
df -h /hy-tmp | tail -1
echo "DOWNLOAD_DONE(此后所有 serve/benchmark 都用本地路径,不再需要 token)"
