#!/usr/bin/env python3
"""P3v2 Task-2 prep: precompute our head's scores for the eval prompts.

Produces {prompt: score} JSON per dataset so a FileAuxScorer can feed the
ORIGINAL opt scheduling policy (identical timing/sorting) with our head's
scores — clean head-vs-policy ablation. Score convention matches opt sort:
higher = predicted shorter (score = -head(h)).

Run on the server:
  cd /hy-tmp/vllm-ltr/benchmarks && python3 /hy-tmp/scripts/build_score_file.py
Needs: /hy-tmp/features/{lmsys_test,sharegpt_test}.npz (push from Mac),
       /hy-tmp/models/egtp_head_last32.pt, local Llama tokenizer.
"""
import json
import sys

sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")

import numpy as np
import torch
from transformers import AutoTokenizer
from benchmark_serving_real import sample_requests

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
HEAD = "/hy-tmp/models/egtp_head_last32.pt"
SETS = {
    "lmsys":    ("/hy-tmp/features/lmsys_test.npz",
                 "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl",
                 "/hy-tmp/models/ipt_scores_lmsys.json"),
    "sharegpt": ("/hy-tmp/features/sharegpt_test.npz",
                 "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-sharegpt-test-t1-s0-8192.jsonl",
                 "/hy-tmp/models/ipt_scores_sharegpt.json"),
}


def main():
    ckpt = torch.load(HEAD, map_location="cpu")
    net = torch.nn.Sequential(
        torch.nn.Linear(ckpt["in_dim"], ckpt["hidden"]), torch.nn.ReLU(),
        torch.nn.Linear(ckpt["hidden"], 1))
    net.load_state_dict(ckpt["state_dict"])
    net = net.float().eval()
    mu, sd = ckpt["mu"].float(), ckpt["sd"].float()
    tok = AutoTokenizer.from_pretrained(MODEL_DIR)

    for name, (npz_path, trace, out) in SETS.items():
        feats = torch.tensor(np.load(npz_path)["last32"].astype(np.float32))
        reqs = sample_requests(trace, 500, False, -1, -1, tok, "opt-xxx")
        prompts = [r[0] for r in reqs]
        assert len(prompts) == len(feats), (len(prompts), len(feats))
        with torch.no_grad():
            scores = (-net((feats - mu) / sd).squeeze(-1)).tolist()
        json.dump(dict(zip(prompts, scores)), open(out, "w"))
        print(f"{name}: {len(prompts)} scores -> {out}")
    print("SCORE_FILES_DONE")


if __name__ == "__main__":
    main()
