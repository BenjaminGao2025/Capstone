#!/usr/bin/env python3
"""v3 gate 1: do prefix-probe features rank output lengths well enough?

For each k in {128,256,512} and feature in {last32, mean16}: train the
P2-identical head (4096->256->1 MLP, log-length MSE) on lmsys_train_k{K},
evaluate |Kendall tau| on lmsys/sharegpt/alpaca test_k{K}, 5 seeds each.

Anchors: full-prompt head (P2 multi-seed mean) and OPT-125M baseline.
PASS criterion (fixed in advance): k=256 last32 must be within 0.05 of the
full-prompt head on lmsys AND >= OPT-125M on sharegpt.

Usage: python3 prefix_gate1.py [features_prefix_dir]   (CPU/GPU both fine)
"""
import sys

import numpy as np
import scipy.stats
import torch

FDIR = sys.argv[1] if len(sys.argv) > 1 else "/hy-tmp/features_prefix"
KS = (128, 256, 512)
VARIANTS = ("last32", "mean16")
EVALS = ("lmsys_test", "sharegpt_test", "alpaca_test")
FULL_ANCHOR = {"lmsys_test": 0.712, "sharegpt_test": 0.445, "alpaca_test": 0.686}
OPT_ANCHOR = {"lmsys_test": 0.640, "sharegpt_test": 0.420, "alpaca_test": 0.579}
DEV = "cuda" if torch.cuda.is_available() else "cpu"
SEEDS = 5


def load(name):
    z = np.load(f"{FDIR}/{name}.npz")
    return {k: z[k] for k in z.files}


def fit(X, y, seed):
    torch.manual_seed(seed)
    net = torch.nn.Sequential(
        torch.nn.Linear(X.shape[1], 256), torch.nn.ReLU(), torch.nn.Linear(256, 1)
    ).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    dl = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X, y), batch_size=256, shuffle=True)
    for _ in range(60):
        for xb, yb in dl:
            opt.zero_grad()
            torch.nn.functional.mse_loss(net(xb).squeeze(-1), yb).backward()
            opt.step()
    return net


def main():
    print(f"gate1 on {FDIR} ({DEV})")
    results = {}
    for k in KS:
        train = load(f"lmsys_train_k{k}")
        tests = {e: load(f"{e}_k{k}") for e in EVALS}
        ytr = torch.tensor(np.log(train["lens"].astype(np.float32)), device=DEV)
        for v in VARIANTS:
            Xtr = torch.tensor(train[v].astype(np.float32), device=DEV)
            mu, sd = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True) + 1e-6
            Xtr = (Xtr - mu) / sd
            taus = {e: [] for e in EVALS}
            for s in range(SEEDS):
                net = fit(Xtr, ytr, s)
                for e in EVALS:
                    Xe = (torch.tensor(tests[e][v].astype(np.float32), device=DEV) - mu) / sd
                    with torch.no_grad():
                        pred = net(Xe).squeeze(-1).cpu().numpy()
                    taus[e].append(abs(float(scipy.stats.kendalltau(pred, tests[e]["lens"])[0])))
            stat = {e: (float(np.mean(taus[e])), float(np.std(taus[e]))) for e in EVALS}
            results[(k, v)] = stat
            print(f"k={k:<4}{v:<8}" + "".join(
                f"  {e.split('_')[0]}={stat[e][0]:.3f}±{stat[e][1]:.3f}" for e in EVALS), flush=True)

    print("\nanchors: full-prompt " + " ".join(f"{e.split('_')[0]}={FULL_ANCHOR[e]}" for e in EVALS))
    print("         OPT-125M    " + " ".join(f"{e.split('_')[0]}={OPT_ANCHOR[e]}" for e in EVALS))
    m = results[(256, "last32")]
    in_ok = m["lmsys_test"][0] >= FULL_ANCHOR["lmsys_test"] - 0.05
    ood_ok = m["sharegpt_test"][0] >= OPT_ANCHOR["sharegpt_test"]
    print(f"\nk=256 last32: lmsys {m['lmsys_test'][0]:.3f} (need >= {FULL_ANCHOR['lmsys_test']-0.05:.3f}: {'ok' if in_ok else 'FAIL'}), "
          f"sharegpt {m['sharegpt_test'][0]:.3f} (need >= {OPT_ANCHOR['sharegpt_test']:.3f}: {'ok' if ood_ok else 'FAIL'})")
    print("GATE1_VERDICT:", "PASS" if (in_ok and ood_ok) else "FAIL")
    print("GATE1_DONE")


if __name__ == "__main__":
    main()
