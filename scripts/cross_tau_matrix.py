#!/usr/bin/env python3
"""Cross-distribution tau matrix: 2 score-predictors x 3 traces (lmsys/sharegpt/alpaca).

Answers direction A's first question: does "just train on the target
distribution" fix OOD, and what does the generalization landscape look like?

Run on the 3090 (predictor scoring on GPU, minutes):
    cd /hy-tmp/vllm-ltr/benchmarks && python3 /hy-tmp/scripts/cross_tau_matrix.py
"""
import json
import sys

sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")

import torch
import scipy.stats
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from benchmark_serving_real import sample_requests

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
BASE = "/hy-tmp/vllm-ltr/benchmarks/MODEL/results"
PREDICTORS = {
    "lmsys-score":    f"{BASE}/opt-125m-llama3-8b-lmsys-score-trainbucket10-b32/finetuned",
    "sharegpt-score": f"{BASE}/opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32/finetuned",
}
TRACES = {
    "lmsys":    "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl",
    "sharegpt": "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-sharegpt-test-t1-s0-8192.jsonl",
    "alpaca":   "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-alpaca-test-t1-s0-8192.jsonl",
}
OUT = "/hy-tmp/results/cross-tau-matrix.json"
ARCHIVE = "/hy-tmp/results/kendall-tau-archive.txt"


@torch.no_grad()
def score_all(pred_dir, prompts, bs=16):
    model = AutoModelForSequenceClassification.from_pretrained(pred_dir, num_labels=1).half().cuda().eval()
    tok = AutoTokenizer.from_pretrained("facebook/opt-125m")
    out = []
    for i in range(0, len(prompts), bs):
        inp = tok(prompts[i:i + bs], max_length=2048, padding=True, truncation=True, return_tensors="pt")
        out.extend(model(inp["input_ids"].cuda(), inp["attention_mask"].cuda()).logits.squeeze(-1).float().cpu().tolist())
    del model
    torch.cuda.empty_cache()
    return out


def main():
    llama_tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    data = {}
    for tname, tpath in TRACES.items():
        reqs = sample_requests(tpath, 500, False, -1, -1, llama_tok, "opt-xxx")
        data[tname] = ([r[0] for r in reqs], [r[2] for r in reqs])
        print(f"loaded {tname}: 500 prompts")

    matrix = {}
    for pname, pdir in PREDICTORS.items():
        matrix[pname] = {}
        for tname, (prompts, lens) in data.items():
            tau, pv = scipy.stats.kendalltau(score_all(pdir, prompts), lens)
            matrix[pname][tname] = {"tau": float(tau), "p": float(pv)}
            print(f"{pname:<16} x {tname:<9} tau={tau:+.4f} p={pv:.2e}")

    json.dump(matrix, open(OUT, "w"), indent=2)
    with open(ARCHIVE, "a") as f:
        for pname, row in matrix.items():
            for tname, v in row.items():
                f.write(f"matrix-{pname:<16} {tname:<18} {v['tau']:+.4f}    {v['p']:.2e}\n")

    print("\n=== matrix (|tau|, rows=predictor, cols=trace) ===")
    cols = list(TRACES)
    print(" " * 18 + "".join(f"{c:>11}" for c in cols))
    for pname, row in matrix.items():
        print(f"{pname:<18}" + "".join(f"{abs(row[c]['tau']):>11.3f}" for c in cols))
    print("MATRIX_DONE ->", OUT)


if __name__ == "__main__":
    main()
