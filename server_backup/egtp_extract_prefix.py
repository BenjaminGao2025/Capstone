#!/usr/bin/env python3
"""v3 gate-1 raw material: PREFIX-PROBE truncated-feature extraction (no training).

For k in {128, 256, 512}: run Llama-3-8B prefill on the FIRST k tokens of each
prompt only, and cache per prompt:
  last32  - hidden state at the last kept position, layer 32 (P2's winning config)
  mean16  - mean-pooled layer-16 hidden states over kept positions (ablation spare)
Plus metadata: true output length (label), real full-prompt token length, and a
truncated flag (False = prompt was shorter than k, full prompt used).

Splits mirror P2 exactly: lmsys_train (filtered) + lmsys/sharegpt/alpaca test
(the same 500-prompt subsets via sample_requests).

Output: /hy-tmp/features_prefix/{split}_k{K}.npz
Offline head training / tau validation on these files is TEAMMATE work — this
script deliberately stops at extraction.

Run:  cd /hy-tmp/vllm-ltr/benchmarks && python3 /hy-tmp/scripts/egtp_extract_prefix.py
"""
import os
import sys

sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")
sys.path.insert(0, "/hy-tmp/scripts")

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from benchmark_serving_real import sample_requests
from egtp_extract_features import load_train, EVAL

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
OUT_DIR = "/hy-tmp/features_prefix"
KS = (128, 256, 512)


@torch.no_grad()
def featurize_prefix(model, tok, prompt, k):
    full_ids = tok(prompt, return_tensors="pt", truncation=True, max_length=8192).input_ids
    real_len = full_ids.shape[1]
    ids = full_ids[:, :k].cuda()
    out = model(ids, output_hidden_states=True)
    h16 = out.hidden_states[16][0].float()
    h32 = out.hidden_states[32][0].float()
    return (
        h32[-1].cpu().numpy().astype(np.float16),       # last32 at position min(k, real_len)-1
        h16.mean(0).cpu().numpy().astype(np.float16),   # mean16 over kept positions
        real_len,
        real_len > k,
    )


def run_split(model, tok, name, prompts, lens, k):
    last32, mean16, plens, trunc = [], [], [], []
    for i, p in enumerate(prompts):
        a, b, rl, tr = featurize_prefix(model, tok, p, k)
        last32.append(a); mean16.append(b); plens.append(rl); trunc.append(tr)
        if (i + 1) % 1000 == 0:
            print(f"{name} k={k}: {i + 1}/{len(prompts)}", flush=True)
    path = os.path.join(OUT_DIR, f"{name}_k{k}.npz")
    np.savez_compressed(
        path,
        last32=np.stack(last32), mean16=np.stack(mean16),
        lens=np.array(lens, dtype=np.int32),
        prompt_lens=np.array(plens, dtype=np.int32),
        truncated=np.array(trunc, dtype=bool),
    )
    n_tr = int(np.sum(trunc))
    print(f"saved {path} n={len(prompts)} truncated_at_k={n_tr}", flush=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, torch_dtype=torch.float16, device_map="cuda:0"
    ).eval()

    splits = {}
    for name, path in EVAL.items():
        reqs = sample_requests(path, 500, False, -1, -1, tok, "opt-xxx")
        splits[name] = ([r[0] for r in reqs], [r[2] for r in reqs])
    tp, tl = load_train(tok)
    splits["lmsys_train"] = (tp, tl)
    print(f"splits: " + ", ".join(f"{k}={len(v[0])}" for k, v in splits.items()))

    for k in KS:
        for name, (prompts, lens) in splits.items():
            run_split(model, tok, name, prompts, lens, k)
    print("PREFIX_EXTRACT_DONE")


if __name__ == "__main__":
    main()
