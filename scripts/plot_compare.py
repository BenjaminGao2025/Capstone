#!/usr/bin/env python3
"""Compare FCFS vs LTR benchmark JSONs from vllm-ltr benchmark_serving_real.py.

Usage:
    python3 plot_compare.py results/*.json
    python3 plot_compare.py results/vllm-8.0qps-*-fcfs-*.json results/vllm-8.0qps-*-opt-xxx-*.json

Output:
    figures/fcfs_vs_ltr.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load(path):
    with open(path) as f:
        d = json.load(f)
    # per-request end-to-end latency = ttft + sum(inter-token latencies)
    lat = np.array([t + sum(itl) for t, itl in zip(d["ttfts"], d["itls"])])
    out_lens = np.array(d["output_lens"], dtype=float)
    norm = lat / np.maximum(out_lens, 1)  # s/token, paper's normalized latency
    sched = d.get("schedule_type") or ("ltr" if "opt" in Path(path).stem else "fcfs")
    label = "LTR" if str(sched).startswith("opt") else str(sched).upper()
    return {
        "label": label,
        "file": Path(path).name,
        "lat": lat,
        "norm": norm,
        "mean_ttft_ms": d["mean_ttft_ms"],
        "p99_ttft_ms": d["p99_ttft_ms"],
        "completed": d["completed"],
        "qps": d.get("request_rate", "?"),
    }


def main(paths):
    runs = [load(p) for p in paths]
    print(f"{'run':<10}{'file':<58}{'n':>5}{'mean lat(s)':>12}{'p99 lat(s)':>12}{'mean s/tok':>12}{'p99 s/tok':>12}")
    for r in runs:
        print(f"{r['label']:<10}{r['file']:<58}{r['completed']:>5}"
              f"{r['lat'].mean():>12.2f}{np.percentile(r['lat'], 99):>12.2f}"
              f"{r['norm'].mean():>12.4f}{np.percentile(r['norm'], 99):>12.4f}")

    fig, axes = plt.subplots(1, 4, figsize=(19, 4.5))
    labels = [r["label"] for r in runs]
    colors = ["#888888" if l == "FCFS" else "#2e7d32" for l in labels]

    for r, c in zip(runs, colors):  # CDF of per-request latency
        xs = np.sort(r["lat"])
        ys = np.arange(1, len(xs) + 1) / len(xs)
        axes[0].plot(xs, ys, label=r["label"], color=c, lw=2)
    axes[0].set_title("Request latency CDF")
    axes[0].set_xlabel("latency (s)")
    axes[0].set_ylabel("fraction of requests")
    axes[0].legend()

    axes[1].bar(labels, [r["lat"].mean() for r in runs], color=colors)
    axes[1].set_title("Mean request latency (s)")
    axes[2].bar(labels, [np.percentile(r["lat"], 99) for r in runs], color=colors)
    axes[2].set_title("P99 request latency (s)")
    axes[3].boxplot([r["norm"] for r in runs], tick_labels=labels, showfliers=False)
    axes[3].set_title("Normalized latency (s/token)")
    for ax in axes:
        ax.grid(axis="y", alpha=0.3)
    fig.suptitle(f"FCFS vs LTR — vllm-ltr in-distribution baseline (qps={runs[0]['qps']})")
    fig.tight_layout()
    out = Path("figures/fcfs_vs_ltr.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    print(f"\nsaved plot: {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
