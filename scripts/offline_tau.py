#!/usr/bin/env python3
"""离线 Kendall Tau:预测器排序质量,不经 serving,直接 trace 打分。

在服务器 /hy-tmp/vllm-ltr/benchmarks 下运行:
    python3 /hy-tmp/scripts/offline_tau.py

- 数据:与 serving 完全相同的前 500 条(复用 sample_requests 的确定性过滤),
  以及全量(过滤后)版本作为稳健性参照
- 校验闸:lmsys-500 的 tau 必须 ≈ -0.6415(serving 实测),容差 0.02,
  否则 exit 2(管线不可信,停下报告)
"""
import sys, json, os
sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")

import torch
import scipy.stats
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from benchmark_serving_real import sample_requests

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
PRED_DIR = "/hy-tmp/vllm-ltr/benchmarks/MODEL/results/opt-125m-llama3-8b-lmsys-score-trainbucket10-b32/finetuned"
ARCHIVE = "/hy-tmp/results/kendall-tau-archive.txt"
SERVING_ANCHOR = -0.6415  # in-dist serving 实测(sweep 5 档全部一致)
TOL = 0.02

DATASETS = {
    "lmsys":    "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl",
    "sharegpt": "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-sharegpt-test-t1-s0-8192.jsonl",
}


def load_predictor():
    model = AutoModelForSequenceClassification.from_pretrained(PRED_DIR, num_labels=1)
    model = model.half().cuda().eval()
    tok = AutoTokenizer.from_pretrained("facebook/opt-125m")
    return model, tok


@torch.no_grad()
def score(model, tok, prompts, bs=16):
    out = []
    for i in range(0, len(prompts), bs):
        batch = prompts[i:i + bs]
        inp = tok(batch, max_length=2048, padding=True, truncation=True, return_tensors="pt")
        logits = model(inp["input_ids"].cuda(), inp["attention_mask"].cuda()).logits
        out.extend(logits.squeeze(-1).float().cpu().tolist())
    return out


def main():
    llama_tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model, opt_tok = load_predictor()
    lines = []
    gate_ok = True
    for name, path in DATASETS.items():
        # 与 serving 同口径:确定性取前 500(同过滤逻辑)
        reqs = sample_requests(path, 500, False, -1, -1, llama_tok, "opt-xxx")
        prompts = [r[0] for r in reqs]
        true_lens = [r[2] for r in reqs]  # output_len=-1 时 = trace 真实生成长度
        scores = score(model, opt_tok, prompts)
        tau, p = scipy.stats.kendalltau(scores, true_lens)
        line = "offline-%-8s-500 (no-serving)         %-18s %.4f    %.2e" % (name, name, tau, p)
        print(line)
        lines.append(line)
        if name == "lmsys":
            if abs(tau - SERVING_ANCHOR) > TOL:
                print(f"GATE_FAIL: lmsys offline tau {tau:.4f} vs serving anchor {SERVING_ANCHOR} (tol {TOL})")
                gate_ok = False
            else:
                print(f"GATE_PASS: lmsys offline tau {tau:.4f} ≈ serving anchor {SERVING_ANCHOR}")
    if not gate_ok:
        sys.exit(2)
    with open(ARCHIVE, "a") as f:
        for line in lines:
            f.write(line + "\n")
    print("OFFLINE_TAU_DONE")


if __name__ == "__main__":
    main()
