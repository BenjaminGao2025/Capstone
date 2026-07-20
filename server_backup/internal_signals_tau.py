#!/usr/bin/env python3
"""Stage-1 signal screening for the model-internal length-prediction idea.

For the SAME 500 prompts used in serving runs (lmsys + sharegpt), run one
Llama-3-8B prefill each and extract zero-training internal signals:

  first_tok_entropy  - entropy of the next-token distribution at the last
                       prompt position (the "first generated token" entropy)
  mean_entropy       - mean per-position next-token entropy over the prompt
  entropy_std        - std of per-position entropy
  mean_nll           - mean negative log-likelihood of prompt tokens
                       (teacher forcing; ~ prompt perplexity)

Then Kendall tau of each signal vs true output length, in-dist vs OOD,
against the OPT-125M anchors (lmsys -0.642 / sharegpt -0.420).
Sign is reported raw; |tau| closer to 0.64 in-dist AND smaller in-dist→OOD
drop than OPT-125M = the idea survives stage 1.

Run on the 3090 (needs Llama weights local):
    cd /hy-tmp/vllm-ltr/benchmarks && python3 /hy-tmp/scripts/internal_signals_tau.py
"""
import json
import sys

sys.path.insert(0, "/hy-tmp/vllm-ltr/benchmarks")

import torch
import scipy.stats
from transformers import AutoModelForCausalLM, AutoTokenizer
from benchmark_serving_real import sample_requests

MODEL_DIR = "/hy-tmp/models/Meta-Llama-3-8B-Instruct"
OUT = "/hy-tmp/results/internal-signals-tau.json"
ARCHIVE = "/hy-tmp/results/kendall-tau-archive.txt"
DATASETS = {
    "lmsys":    "/hy-tmp/vllm-ltr/benchmarks/lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl",
    "sharegpt": "/hy-tmp/vllm-ltr/benchmarks/llama3-8b-sharegpt-test-t1-s0-8192.jsonl",
}
OPT_ANCHOR = {"lmsys": -0.642, "sharegpt": -0.420}
MAX_LEN = 2048  # same ceiling the OPT predictor sees — fair comparison


@torch.no_grad()
def signals_for(model, tok, prompt):
    ids = tok(prompt, return_tensors="pt", truncation=True, max_length=MAX_LEN).input_ids.cuda()
    logits = model(ids).logits.float()[0]            # [T, V]
    logp = torch.log_softmax(logits, dim=-1)         # [T, V]
    ent = -(logp.exp() * logp).sum(-1)               # [T] per-position next-token entropy
    # prompt-token NLL: position t predicts token t+1
    tgt = ids[0, 1:]
    nll = -logp[:-1].gather(1, tgt.unsqueeze(1)).squeeze(1)
    return {
        "first_tok_entropy": float(ent[-1]),
        "mean_entropy": float(ent.mean()),
        "entropy_std": float(ent.std()),
        "mean_nll": float(nll.mean()),
    }


def main():
    llama_tok = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_DIR, torch_dtype=torch.float16, device_map="cuda:0"
    ).eval()

    report = {}
    for name, path in DATASETS.items():
        reqs = sample_requests(path, 500, False, -1, -1, llama_tok, "opt-xxx")
        prompts = [r[0] for r in reqs]
        true_lens = [r[2] for r in reqs]
        rows = []
        for i, p in enumerate(prompts):
            rows.append(signals_for(model, llama_tok, p))
            if (i + 1) % 100 == 0:
                print(f"{name}: {i + 1}/500")
        taus = {}
        for k in rows[0]:
            tau, pv = scipy.stats.kendalltau([r[k] for r in rows], true_lens)
            taus[k] = {"tau": float(tau), "p": float(pv)}
        report[name] = taus
        print(f"== {name} (OPT-125M anchor tau = {OPT_ANCHOR[name]}) ==")
        for k, v in taus.items():
            print(f"   {k:<18} tau={v['tau']:+.4f}  p={v['p']:.2e}")

    json.dump(report, open(OUT, "w"), indent=2)
    with open(ARCHIVE, "a") as f:
        for name, taus in report.items():
            for k, v in taus.items():
                f.write(f"offline-internal-{k:<18} {name:<18} {v['tau']:+.4f}    {v['p']:.2e}\n")

    print("\n== verdict helper ==")
    for k in report["lmsys"]:
        t_in, t_ood = abs(report["lmsys"][k]["tau"]), abs(report["sharegpt"][k]["tau"])
        drop = (t_in - t_ood) / t_in * 100 if t_in > 0 else float("nan")
        opt_drop = (0.642 - 0.420) / 0.642 * 100
        print(f"   {k:<18} |tau| in={t_in:.3f} ood={t_ood:.3f} drop={drop:.0f}%  (OPT-125M: in=0.642 ood=0.420 drop={opt_drop:.0f}%)")
    print("SIGNALS_DONE ->", OUT)


if __name__ == "__main__":
    main()
