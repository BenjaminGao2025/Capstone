#!/usr/bin/env python3
"""Stage-2 EGTP-lite: extract pooled hidden-state features from Llama-3-8B prefill.

Per prompt, one forward pass with output_hidden_states. Cached variants:
  ew16 / ew32   - entropy-weighted pooled hidden states, layer 16 / 32(last)
  mean16/mean32 - plain mean pooling (ablation: does entropy weighting matter?)
  last32        - last-token hidden state, layer 32 (ablation)

Datasets:
  train: lmsys TRAIN trace (c20000:30000) - same training distribution as the
         OPT-125M baseline predictor, for a fair generalization comparison
  eval:  lmsys / sharegpt / alpaca TEST, the exact same 500-prompt subsets used
         in all previous tau measurements (via sample_requests)

Output: /hy-tmp/features/{split}.npz  (fp16 features + true output lengths)

Run:  cd /hy-tmp/vllm-ltr/benchmarks && python3 /hy-tmp/scripts/egtp_extract_features.py
"""
import json
import os
import sys

sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from benchmark_serving_real import sample_requests

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
OUT_DIR = "/hy-tmp/features"
MAX_LEN = 2048
LAYERS = (16, 32)  # 32 = last (hidden_states[32]); Llama-3-8B has 32 blocks

EVAL = {
    "lmsys_test":    "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl",
    "sharegpt_test": "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-sharegpt-test-t1-s0-8192.jsonl",
    "alpaca_test":   "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-alpaca-test-t1-s0-8192.jsonl",
}
TRAIN_TRACE = "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c20000:30000-rFalse.jsonl"


def load_train(tok):
    """Train pairs with the same filter bounds sample_requests uses."""
    prompts, lens = [], []
    with open(TRAIN_TRACE) as f:
        rows = [json.loads(l) for l in f]
    p_ids = tok([r["prompt"] for r in rows]).input_ids
    c_ids = tok([r["generated"] for r in rows]).input_ids
    for r, pi, ci in zip(rows, p_ids, c_ids):
        pl, cl = len(pi), len(ci)
        if pl < 4 or cl < 4 or pl > 1024 or pl + cl > 20480:
            continue
        prompts.append(r["prompt"])
        lens.append(cl)
    return prompts, lens


@torch.no_grad()
def featurize(model, tok, prompt):
    ids = tok(prompt, return_tensors="pt", truncation=True, max_length=MAX_LEN).input_ids.cuda()
    out = model(ids, output_hidden_states=True)
    logp = torch.log_softmax(out.logits.float()[0], dim=-1)
    ent = -(logp.exp() * logp).sum(-1)                  # [T]
    w = (ent / ent.sum()).to(torch.float32)             # entropy weights
    feats = {}
    for L in LAYERS:
        h = out.hidden_states[L][0].float()             # [T, 4096]
        feats[f"ew{L}"] = (w.unsqueeze(1) * h).sum(0)
        feats[f"mean{L}"] = h.mean(0)
    feats["last32"] = out.hidden_states[LAYERS[-1]][0, -1].float()
    return {k: v.cpu().numpy().astype(np.float16) for k, v in feats.items()}


def run_split(model, tok, name, prompts, lens):
    keys = None
    rows = []
    for i, p in enumerate(prompts):
        f = featurize(model, tok, p)
        if keys is None:
            keys = sorted(f)
        rows.append([f[k] for k in keys])
        if (i + 1) % 250 == 0:
            print(f"{name}: {i + 1}/{len(prompts)}", flush=True)
    arrs = {k: np.stack([r[j] for r in rows]) for j, k in enumerate(keys)}
    arrs["lens"] = np.array(lens, dtype=np.int32)
    np.savez_compressed(os.path.join(OUT_DIR, f"{name}.npz"), **arrs)
    print(f"saved {name}.npz n={len(prompts)}", flush=True)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, torch_dtype=torch.float16, device_map="cuda:0"
    ).eval()

    for name, path in EVAL.items():
        reqs = sample_requests(path, 500, False, -1, -1, tok, "opt-xxx")
        run_split(model, tok, name, [r[0] for r in reqs], [r[2] for r in reqs])

    tp, tl = load_train(tok)
    print(f"train usable: {len(tp)}")
    run_split(model, tok, "lmsys_train", tp, tl)
    print("EXTRACT_DONE")


if __name__ == "__main__":
    main()
