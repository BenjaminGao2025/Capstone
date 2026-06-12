#!/usr/bin/env python3
"""Generate midterm-defense charts from results/llama3-8b/*.json.

Outputs (figures/):
  fig_motivation.png      - tau collapse + tail-latency inversion + crash note
  fig_ttft_vs_rate.png    - mean TTFT & mean latency vs request rate (in-dist)
  fig_cdf_indist_r8.png   - per-request latency CDF, in-dist rate 8
  fig_cdf_ood_r4.png      - per-request latency CDF, OOD rate 4

Run from repo root:  python3 scripts/make_defense_charts.py
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
C_FCFS, C_LTR = "#777777", "#2e7d32"
RATES = [2, 4, 8, 16, 32]


def load(pattern):
    paths = [p for p in glob.glob(os.path.join(RES, pattern)) if "crashed" not in p]
    assert len(paths) == 1, f"{pattern} -> {paths}"
    d = json.load(open(paths[0]))
    lat = np.sort([t + sum(i) for t, i in zip(d["ttfts"], d["itls"])])
    return {
        "lat": lat,
        "mean_ttft": d["mean_ttft_ms"] / 1000,
        "mean_lat": float(lat.mean()),
        "p99_lat": float(np.percentile(lat, 99)),
        "tau": d.get("aux_kendall_tau"),
    }


def indist(rate, arm):
    # sweep files only (exclude the rate-8 probe runs by timestamp prefix 10*)
    pat = f"vllm-{rate}.0qps-*-{arm}-20260611-1[01]*.json" if arm != "tpt-class10-xxx" \
        else f"vllm-{rate}.0qps-*-{arm}-*.json"
    paths = [p for p in glob.glob(os.path.join(RES, pat)) if "ood" not in p]
    assert len(paths) == 1, f"{pat} -> {paths}"
    return load(os.path.basename(paths[0]))


def ood(rate, arm):
    return load(f"vllm-{rate}.0qps-*-{arm}-*-ood-sharegpt.json")


def fig_motivation(ind4f, ind4l, ood4f, ood4l):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))

    ax = axes[0]
    taus = [-ind4l["tau"], -ood4l["tau"]]
    bars = ax.bar(["In-distribution\n(LMSYS)", "OOD\n(ShareGPT)"], taus,
                  color=[C_LTR, "#c62828"], width=0.55)
    for b, v in zip(bars, taus):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.012, f"{v:.3f}",
                ha="center", fontsize=12, fontweight="bold")
    ax.set_ylabel("Prediction ranking quality\n(-Kendall's τ, higher is better)")
    ax.set_ylim(0, 0.75)
    ax.set_title("(a) Predictor quality collapses off-distribution")
    ax.grid(axis="y", alpha=0.3)

    ax = axes[1]
    ratios = [ind4l["p99_lat"] / ind4f["p99_lat"], ood4l["p99_lat"] / ood4f["p99_lat"]]
    bars = ax.bar(["In-distribution\n(rate 4)", "OOD\n(rate 4)"], ratios,
                  color=[C_LTR, "#c62828"], width=0.55)
    for b, v in zip(bars, ratios):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}x",
                ha="center", fontsize=12, fontweight="bold")
    ax.axhline(1.0, color="black", lw=1, ls="--")
    ax.text(0.98, 1.03, "parity vs FCFS", fontsize=9, ha="right",
            transform=ax.get_yaxis_transform())
    ax.set_ylabel("p99 latency ratio  (LTR / FCFS)")
    ax.set_ylim(0, 1.85)
    ax.set_title("(b) Tail-latency advantage inverts")
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Why predictor generalization matters (direction A motivation)",
                 fontsize=13, fontweight="bold")
    fig.text(0.5, 0.015,
             "At rate 8 OOD the mis-ranked preemption storm exhausts CPU swap and the LTR engine crashes "
             "(FCFS completes 500/500 on the identical workload).",
             ha="center", fontsize=9.5, style="italic", color="#c62828")
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(f"{OUT}/fig_motivation.png", dpi=180)
    print(f"saved {OUT}/fig_motivation.png")


def fig_main(sweep):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, key, label in [(axes[0], "mean_ttft", "Mean TTFT (s)"),
                           (axes[1], "mean_lat", "Mean request latency (s)")]:
        ax.plot(RATES, [sweep[r]["fcfs"][key] for r in RATES], "o-", color=C_FCFS, label="FCFS", lw=2)
        if "cls" in sweep[RATES[0]]:
            ax.plot(RATES, [sweep[r]["cls"][key] for r in RATES], "^-", color="#F9A825",
                    label="Classification (τ -0.30)", lw=2)
        ax.plot(RATES, [sweep[r]["ltr"][key] for r in RATES], "s-", color=C_LTR, label="LTR (τ -0.64)", lw=2)
        ax.set_xlabel("Request rate (req/s)")
        ax.set_ylabel(label)
        ax.set_xscale("log", base=2)
        ax.set_xticks(RATES)
        ax.set_xticklabels(RATES)
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_yscale("log")
    best = max(sweep[r]["fcfs"]["mean_ttft"] / sweep[r]["ltr"]["mean_ttft"] for r in RATES)
    axes[0].set_title(f"up to {best:.1f}x mean-TTFT advantage")
    axes[1].set_title("Llama-3-8B-Instruct, LMSYS trace, 500 prompts")
    fig.suptitle("In-distribution reproduction: LTR vs FCFS", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig_ttft_vs_rate.png", dpi=180)
    print(f"saved {OUT}/fig_ttft_vs_rate.png")


def fig_cdf(f, l, title, fname):
    fig, ax = plt.subplots(figsize=(6.2, 4.4))
    for r, c, lab in [(f, C_FCFS, "FCFS"), (l, C_LTR, "LTR")]:
        ys = np.arange(1, len(r["lat"]) + 1) / len(r["lat"])
        ax.plot(r["lat"], ys, color=c, lw=2, label=lab)
    ax.set_xlabel("Per-request end-to-end latency (s)")
    ax.set_ylabel("Fraction of requests")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{OUT}/{fname}", dpi=180)
    print(f"saved {OUT}/{fname}")


def main():
    os.makedirs(OUT, exist_ok=True)
    sweep = {r: {"fcfs": indist(r, "fcfs"), "ltr": indist(r, "opt-xxx")} for r in RATES}
    try:
        for r in RATES:
            sweep[r]["cls"] = indist(r, "tpt-class10-xxx")
    except AssertionError:
        pass  # class arm not run yet — fall back to two lines
    ood4f, ood4l = ood(4, "fcfs"), ood(4, "opt-xxx")

    fig_motivation(sweep[4]["fcfs"], sweep[4]["ltr"], ood4f, ood4l)
    fig_main(sweep)
    fig_cdf(sweep[8]["fcfs"], sweep[8]["ltr"],
            "Latency CDF — in-distribution (LMSYS, rate 8)", "fig_cdf_indist_r8.png")
    fig_cdf(ood4f, ood4l,
            "Latency CDF — OOD (ShareGPT trace × LMSYS predictor, rate 4)", "fig_cdf_ood_r4.png")
    print("ALL_CHARTS_DONE")


if __name__ == "__main__":
    main()
