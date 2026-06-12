#!/usr/bin/env python3
"""P3-WP1: train the stage-2 winning head (last32/mlp) and export it for the engine.

Trains on cached lmsys_train features (Mac, CPU ok), checks multi-seed variance,
exports the best seed's weights + feature standardization to a single .pt file
that the vLLM worker will load.

Usage:  python3 scripts/egtp_export_head.py [features_dir] [out.pt]
"""
import sys

import numpy as np
import scipy.stats
import torch

FDIR = sys.argv[1] if len(sys.argv) > 1 else "/Users/benjamingao/20260609-capstone/features"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/Users/benjamingao/20260609-capstone/capstoneGitHub/results/llama3-8b/egtp_head_last32.pt"
VARIANT = "last32"
EVALS = ["lmsys_test", "sharegpt_test", "alpaca_test"]
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def load(split):
    z = np.load(f"{FDIR}/{split}.npz")
    return {k: z[k] for k in z.files}


def make_net(in_dim, hidden=256, seed=0):
    torch.manual_seed(seed)
    return torch.nn.Sequential(
        torch.nn.Linear(in_dim, hidden), torch.nn.ReLU(), torch.nn.Linear(hidden, 1)
    ).to(DEV)


def fit(net, X, y, epochs=60, lr=1e-3):
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
    dl = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(X, y), batch_size=256, shuffle=True)
    for _ in range(epochs):
        for xb, yb in dl:
            opt.zero_grad()
            torch.nn.functional.mse_loss(net(xb).squeeze(-1), yb).backward()
            opt.step()
    return net


def main():
    train = load("lmsys_train")
    evals = {e: load(e) for e in EVALS}
    Xtr = torch.tensor(train[VARIANT].astype(np.float32), device=DEV)
    ytr = torch.tensor(np.log(train["lens"].astype(np.float32)), device=DEV)
    mu, sd = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True) + 1e-6
    Xtr = (Xtr - mu) / sd

    results = []
    for seed in range(5):
        net = fit(make_net(Xtr.shape[1], seed=seed), Xtr, ytr)
        taus = {}
        for e in EVALS:
            Xe = (torch.tensor(evals[e][VARIANT].astype(np.float32), device=DEV) - mu) / sd
            with torch.no_grad():
                pred = net(Xe).squeeze(-1).cpu().numpy()
            taus[e] = abs(float(scipy.stats.kendalltau(pred, evals[e]["lens"])[0]))
        results.append((taus, net))
        print(f"seed {seed}: " + "  ".join(f"{e.split('_')[0]}={taus[e]:.3f}" for e in EVALS))

    arr = {e: [r[0][e] for r in results] for e in EVALS}
    print("\nvariance: " + "  ".join(
        f"{e.split('_')[0]} {np.mean(arr[e]):.3f}±{np.std(arr[e]):.3f}" for e in EVALS))

    best_i = int(np.argmax([r[0]["lmsys_test"] + r[0]["sharegpt_test"] for r in results]))
    taus, net = results[best_i]
    torch.save({
        "state_dict": {k: v.cpu() for k, v in net.state_dict().items()},
        "mu": mu.cpu(), "sd": sd.cpu(),
        "variant": VARIANT, "hidden": 256, "in_dim": Xtr.shape[1],
        "train": "lmsys_train(9760), log-length MSE, seed=" + str(best_i),
        "eval_taus": taus,
        "score_note": "higher head output = longer predicted output; scheduler wants shorter first -> use score = -head(h)",
    }, OUT)
    print(f"\nexported seed {best_i} -> {OUT}")
    print("EXPORT_DONE")


if __name__ == "__main__":
    main()
