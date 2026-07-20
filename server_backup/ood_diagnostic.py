#!/usr/bin/env python3
"""OOD diagnostic figure: ranking quality (|tau|) vs test distribution.

Issue #20 acceptance criterion: diagnostic figure committed under figures/.

What it shows:
  Left panel  – |tau| for OPT predictor (lmsys-trained) and EGTP head across
                three test distributions, ordered by observed degradation.
  Right panel – Concrete consequence at serving time: p99 latency ratio
                (LTR / FCFS) at rate-4, in-dist vs OOD ShareGPT.

Data sources (all committed to the repo):
  results/llama3-8b/cross-tau-matrix.json  – offline scoring tau
  results/llama3-8b/egtp-stage2-verdict.txt (hardcoded from known values)
  results/llama3-8b/*.json                 – per-request serving latencies

Run from repo root:
    python3 scripts/ood_diagnostic.py
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RES = "results/llama3-8b"
OUT = "figures"

# ── Tau data ──────────────────────────────────────────────────────────────────
# OPT predictor (lmsys-trained) from cross-tau-matrix.json
TAU_OPT = {
    "LMSYS\n(in-dist)":  0.6402,
    "Alpaca\n(OOD)":     0.5790,
    "ShareGPT\n(OOD)":  0.4200,
}

# EGTP head (last32/mlp, lmsys-trained) from egtp-stage2-verdict.txt
TAU_EGTP = {
    "LMSYS\n(in-dist)":  0.713,
    "Alpaca\n(OOD)":     0.674,
    "ShareGPT\n(OOD)":  0.428,
}

DATASETS = list(TAU_OPT.keys())


def load_latencies(pattern):
    paths = [p for p in glob.glob(os.path.join(RES, pattern)) if "crashed" not in p]
    assert len(paths) == 1, f"Expected 1 file, got {paths}"
    d = json.load(open(paths[0]))
    lats = np.array([t + sum(itl) for t, itl in zip(d["ttfts"], d["itls"])])
    return lats


def p99(arr):
    return float(np.percentile(arr, 99))


def main():
    os.makedirs(OUT, exist_ok=True)

    # ── Serving latency data ─────────────────────────────────────────────────
    fcfs_ind = load_latencies(
        "vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-fcfs-20260611-103*.json"
    )
    ltr_ind = load_latencies(
        "vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260611-104011*.json"
    )
    fcfs_ood = load_latencies(
        "vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-fcfs-20260611-113110*ood-sharegpt.json"
    )
    ltr_ood = load_latencies(
        "vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260611-113821*ood-sharegpt.json"
    )

    p99_ratio_ind = p99(ltr_ind) / p99(fcfs_ind)   # expect ~1.03
    p99_ratio_ood = p99(ltr_ood) / p99(fcfs_ood)   # expect ~1.53

    # ── Figure ───────────────────────────────────────────────────────────────
    C_OPT  = "#2e7d32"
    C_EGTP = "#1565c0"
    C_GOOD = "#2e7d32"
    C_BAD  = "#c62828"
    WIDTH  = 0.35

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    # Left: |tau| grouped bar chart
    ax = axes[0]
    x = np.arange(len(DATASETS))
    b1 = ax.bar(x - WIDTH / 2, [TAU_OPT[d]  for d in DATASETS], WIDTH,
                label="OPT predictor (lmsys-trained)", color=C_OPT,  alpha=0.85)
    b2 = ax.bar(x + WIDTH / 2, [TAU_EGTP[d] for d in DATASETS], WIDTH,
                label="EGTP head (last32/mlp, lmsys-trained)", color=C_EGTP, alpha=0.85)

    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.012,
                    f"{h:.3f}", ha="center", va="bottom", fontsize=9)

    # Annotate the in-dist→ShareGPT drop for OPT predictor
    ax.annotate("", xy=(2 - WIDTH / 2, TAU_OPT["ShareGPT\n(OOD)"]),
                xytext=(0 - WIDTH / 2, TAU_OPT["LMSYS\n(in-dist)"]),
                arrowprops=dict(arrowstyle="->", color=C_BAD, lw=1.5))
    drop_pct = (TAU_OPT["LMSYS\n(in-dist)"] - TAU_OPT["ShareGPT\n(OOD)"]) / TAU_OPT["LMSYS\n(in-dist)"] * 100
    ax.text(1.0, 0.46, f"−{drop_pct:.0f}% quality\n(OPT, lmsys→ShareGPT)",
            fontsize=8.5, color=C_BAD, ha="center")

    ax.set_xticks(x)
    ax.set_xticklabels(DATASETS, fontsize=9.5)
    ax.set_ylabel("|Kendall's τ|  (ranking quality, higher is better)")
    ax.set_ylim(0, 0.82)
    ax.set_title("(a) Ranking quality collapses off-distribution")
    ax.legend(fontsize=8.5, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # Right: p99 latency ratio at rate 4
    ax = axes[1]
    labels = ["In-dist\n(LMSYS, rate 4)", "OOD\n(ShareGPT, rate 4)"]
    ratios = [p99_ratio_ind, p99_ratio_ood]
    colors = [C_GOOD if r <= 1.0 else C_BAD for r in ratios]
    bars = ax.bar(labels, ratios, color=colors, width=0.5, alpha=0.85)
    for bar, v in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.025,
                f"{v:.2f}×", ha="center", fontsize=12, fontweight="bold")
    ax.axhline(1.0, color="black", lw=1.2, ls="--")
    ax.text(0.98, 1.03, "parity", fontsize=9, ha="right",
            transform=ax.get_yaxis_transform(), color="black")
    ax.set_ylabel("p99 latency ratio  (LTR / FCFS)\n<1 = LTR wins  |  >1 = LTR loses")
    ax.set_ylim(0, 1.85)
    ax.set_title("(b) Tail-latency advantage inverts OOD")
    ax.grid(axis="y", alpha=0.3)
    note = (f"In-dist: p99 LTR={p99(ltr_ind):.1f}s vs FCFS={p99(fcfs_ind):.1f}s\n"
            f"OOD:      p99 LTR={p99(ltr_ood):.1f}s vs FCFS={p99(fcfs_ood):.1f}s\n"
            f"Rate-8 OOD: LTR engine crashes (FCFS completes 500/500)")
    ax.text(0.01, 0.01, note, transform=ax.transAxes, fontsize=7.5,
            verticalalignment="bottom", color="#555555",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

    fig.suptitle("OOD Diagnostic: Why the Learned Ranker Breaks Down",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    out_path = os.path.join(OUT, "ood_tau_vs_shift.png")
    fig.savefig(out_path, dpi=180)
    print(f"saved  {out_path}")
    print(f"\nKey numbers for honest 口径 table:")
    k_ind = "LMSYS\n(in-dist)"
    k_ood = "ShareGPT\n(OOD)"
    print(f"  In-dist tau  : OPT {TAU_OPT[k_ind]:.3f}  EGTP {TAU_EGTP[k_ind]:.3f}")
    print(f"  OOD-sharegpt : OPT {TAU_OPT[k_ood]:.3f}  EGTP {TAU_EGTP[k_ood]:.3f}")
    print(f"  p99 ratio in-dist r4 : {p99_ratio_ind:.3f}x (LTR/FCFS, <1 is good)")
    print(f"  p99 ratio OOD r4     : {p99_ratio_ood:.3f}x (LTR/FCFS, >1 is bad)")


if __name__ == "__main__":
    main()
