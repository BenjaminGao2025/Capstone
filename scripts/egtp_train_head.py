#!/usr/bin/env python3
"""Stage-2 EGTP-lite: train a small head on cached features, judge vs OPT-125M.

Train on lmsys_train features only (same distribution as the OPT baseline),
target log(output_len). Heads: closed-form ridge regression + a tiny MLP.
Eval: Kendall tau on lmsys/sharegpt/alpaca test (the same 500-prompt subsets).

Gate (printed as VERDICT):
  PASS      in-dist |tau| >= 0.60 AND sharegpt |tau| > 0.42
  IN-FAIL   in-dist < 0.60                  -> idea dies cheaply
  OOD-FAIL  in-dist ok but sharegpt <= 0.42 -> "internal = robust" falsified

Runs on CPU or GPU:  python3 egtp_train_head.py [features_dir]
"""
import sys

import numpy as np
import torch
import scipy.stats

FDIR = sys.argv[1] if len(sys.argv) > 1 else "/hy-tmp/features"
VARIANTS = ["ew16", "ew32", "mean16", "mean32", "last32"]
EVALS = ["lmsys_test", "sharegpt_test", "alpaca_test"]
OPT_ANCHOR = {"lmsys_test": 0.640, "sharegpt_test": 0.420, "alpaca_test": 0.579}
DEV = "cuda" if torch.cuda.is_available() else "cpu"


def load(split):
    z = np.load(f"{FDIR}/{split}.npz")
    return {k: z[k] for k in z.files}


def ridge(X, y, lam=10.0):
    Xb = torch.cat([X, torch.ones(len(X), 1, device=DEV)], 1)
    A = Xb.T @ Xb + lam * torch.eye(Xb.shape[1], device=DEV)
    return torch.linalg.solve(A, Xb.T @ y)


def mlp_fit(X, y, hidden=256, epochs=60, lr=1e-3):
    torch.manual_seed(0)
    net = torch.nn.Sequential(
        torch.nn.Linear(X.shape[1], hidden), torch.nn.ReLU(),
        torch.nn.Linear(hidden, 1),
    ).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=1e-4)
    ds = torch.utils.data.TensorDataset(X, y)
    dl = torch.utils.data.DataLoader(ds, batch_size=256, shuffle=True)
    for _ in range(epochs):
        for xb, yb in dl:
            opt.zero_grad()
            loss = torch.nn.functional.mse_loss(net(xb).squeeze(-1), yb)
            loss.backward()
            opt.step()
    return net


def main():
    train = load("lmsys_train")
    evals = {e: load(e) for e in EVALS}
    ytr = torch.tensor(np.log(train["lens"].astype(np.float32)), device=DEV)

    print(f"train n={len(ytr)} on {DEV}")
    best = None
    for v in VARIANTS:
        Xtr = torch.tensor(train[v].astype(np.float32), device=DEV)
        mu, sd = Xtr.mean(0, keepdim=True), Xtr.std(0, keepdim=True) + 1e-6
        Xtr = (Xtr - mu) / sd

        w = ridge(Xtr, ytr)
        net = mlp_fit(Xtr, ytr)

        for head, predict in [
            ("ridge", lambda X: (torch.cat([X, torch.ones(len(X), 1, device=DEV)], 1) @ w)),
            ("mlp",   lambda X: net(X).squeeze(-1)),
        ]:
            taus = {}
            for e in EVALS:
                Xe = torch.tensor(evals[e][v].astype(np.float32), device=DEV)
                Xe = (Xe - mu) / sd
                with torch.no_grad():
                    pred = predict(Xe).cpu().numpy()
                tau, p = scipy.stats.kendalltau(pred, evals[e]["lens"])
                taus[e] = abs(float(tau))
            line = f"{v:<7} {head:<6}" + "".join(f"  {e.split('_')[0]}={taus[e]:.3f}" for e in EVALS)
            print(line)
            score = (taus["lmsys_test"], taus["sharegpt_test"])
            if best is None or score > best[0]:
                best = (score, v, head, taus)

    (ind, ood), v, head, taus = best
    print(f"\nBEST: {v}/{head}  in-dist={ind:.3f} (OPT 0.640)  sharegpt={ood:.3f} (OPT 0.420)  alpaca={taus['alpaca_test']:.3f} (OPT 0.579)")
    if ind >= 0.60 and ood > 0.42:
        print("VERDICT: PASS — internal representations match in-dist and beat OPT OOD; stage 3 justified")
    elif ind < 0.60:
        print("VERDICT: IN-FAIL — cannot match OPT in-distribution; idea dies cheaply")
    else:
        print("VERDICT: OOD-FAIL — in-dist ok but no robustness gain; hypothesis falsified")
    print("HEAD_DONE")


if __name__ == "__main__":
    main()
