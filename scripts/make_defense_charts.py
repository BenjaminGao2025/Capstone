#!/usr/bin/env python3
"""Generate midterm-defense charts from results/llama3-8b/*.json.

Outputs (figures/):
  fig_motivation.png      - tau collapse + tail-latency inversion + crash note
  fig_ttft_vs_rate.png    - mean TTFT & mean latency vs request rate (in-dist)
  fig_cdf_indist_r8.png   - per-request latency CDF, in-dist rate 8
  fig_cdf_ood_r4.png      - per-request latency CDF, OOD rate 4

Run from repo root:  python3 scripts/make_defense_charts.py
"""
import json
import os
import hashlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pathlib

# Find repo root to resolve relative paths
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST_PATH = os.path.join(REPO_ROOT, "results", "submission_manifest.json")
OUT = os.path.join(REPO_ROOT, "figures")
C_FCFS, C_LTR = "#777777", "#2e7d32"
RATES = [2, 4, 8, 16, 32]

with open(MANIFEST_PATH) as f:
    manifest = json.load(f)

def hash_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_experiment_data(exp_id):
    matching_exps = [e for e in manifest.get("experiments", []) if e.get("experiment_id") == exp_id]
    if len(matching_exps) == 0:
        raise RuntimeError(f"Missing experiment ID: {exp_id}")
    if len(matching_exps) > 1:
        raise RuntimeError(f"Duplicate experiment ID: {exp_id}")
        
    exp = matching_exps[0]
    
    if not exp.get("eligible_for_aggregation"):
        raise RuntimeError(f"Ineligible ID: {exp_id}")
        
    if exp.get("status") != "valid":
        raise RuntimeError(f"Status not valid for ID: {exp_id}")
        
    rel_path = exp.get("result_path")
    if not rel_path:
        raise RuntimeError(f"Missing result_path for ID: {exp_id}")
        
    # Check path containment
    p = pathlib.Path(REPO_ROOT) / rel_path
    try:
        resolved_p = p.resolve()
        resolved_root = pathlib.Path(REPO_ROOT).resolve()
    except Exception:
        raise RuntimeError(f"Path resolution error for ID: {exp_id}")
        
    if not resolved_p.is_relative_to(resolved_root):
        raise RuntimeError(f"Unsafe path traversal for ID: {exp_id}")
        
    path = os.path.join(REPO_ROOT, rel_path)
    if not os.path.exists(path):
        raise RuntimeError(f"Missing result file for ID: {exp_id}")
        
    # SHA verification
    actual_sha = hash_file(path)
    if actual_sha != exp.get("result_sha256"):
        raise RuntimeError(f"SHA mismatch for ID: {exp_id}")
        
    with open(path) as f:
        d = json.load(f)
        
    if not isinstance(d, dict):
        raise RuntimeError(f"Result JSON is not an object for ID: {exp_id}")
        
    # JSON metadata consistency check
    manifest_arm = exp.get("arm")
    json_sched = d.get("schedule_type", "")
    
    arm_matches = False
    manifest_sched = exp.get("scheduler_type")
    if manifest_sched and json_sched:
        arm_matches = (manifest_sched == json_sched)
    if not arm_matches and json_sched:
        if manifest_arm == "fcfs" and json_sched == "fcfs": arm_matches = True
        elif manifest_arm == "ltr" and json_sched.startswith("opt-") and not json_sched.startswith("opt-aging-"): arm_matches = True
        elif manifest_arm == "v1" and json_sched.startswith("opt-aging-"): arm_matches = True
        elif manifest_arm.startswith("opt-aging-") and json_sched.startswith("opt-aging-"): arm_matches = True
        elif manifest_arm.startswith("opt-") and not manifest_arm.startswith("opt-aging-") and json_sched.startswith("opt-") and not json_sched.startswith("opt-aging-"): arm_matches = True
        elif manifest_arm == json_sched: arm_matches = True
        
    if not arm_matches:
        raise RuntimeError(f"Wrong scheduler for ID: {exp_id}, JSON has {json_sched}, manifest arm is {manifest_arm}")
        
    if "request_rate" in d and abs(d["request_rate"] - exp.get("request_rate", -1)) > 1e-5:
        raise RuntimeError(f"request_rate mismatch for ID: {exp_id}")
        
    if d.get("completed") != exp.get("completed"):
        raise RuntimeError(f"completed count mismatch for ID: {exp_id}")
        
    if exp.get("eligible_for_aggregation") and d.get("completed") != exp.get("expected_num_prompts"):
        raise RuntimeError(f"completed != expected_num_prompts for ID: {exp_id}")
        
    if len(d.get("ttfts", [])) != d.get("completed", -1):
        raise RuntimeError(f"len(ttfts) mismatch for ID: {exp_id}")
        
    if len(d.get("itls", [])) != d.get("completed", -1):
        raise RuntimeError(f"len(itls) mismatch for ID: {exp_id}")
        
    lat = np.sort([t + sum(i) for t, i in zip(d["ttfts"], d["itls"])])
    return {
        "lat": lat,
        "mean_ttft": d["mean_ttft_ms"] / 1000,
        "mean_lat": float(lat.mean()),
        "p99_lat": float(np.percentile(lat, 99)),
        "tau": d.get("aux_kendall_tau"),
        "result_sha256": exp.get("result_sha256"),
    }


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
    fig.savefig(f"{OUT}/fig_motivation.png", dpi=180, metadata={'Date': None})
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
    fig.savefig(f"{OUT}/fig_ttft_vs_rate.png", dpi=180, metadata={'Date': None})
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
    fig.savefig(f"{OUT}/{fname}", dpi=180, metadata={'Date': None})
    print(f"saved {OUT}/{fname}")


def main():
    os.makedirs(OUT, exist_ok=True)
    
    sweep = {
        r: {
            "fcfs": get_experiment_data(f"sweep-r{r}-fcfs"),
            "ltr": get_experiment_data(f"sweep-r{r}-ltr")
        } for r in RATES
    }
    
    ood4f = get_experiment_data("ood-r4-fcfs")
    ood4l = get_experiment_data("ood-r4-ltr")

    fig_motivation(sweep[4]["fcfs"], sweep[4]["ltr"], ood4f, ood4l)
    fig_main(sweep)
    fig_cdf(sweep[8]["fcfs"], sweep[8]["ltr"],
            "Latency CDF — in-distribution (LMSYS, rate 8)", "fig_cdf_indist_r8.png")
    fig_cdf(ood4f, ood4l,
            "Latency CDF — OOD (ShareGPT trace × LMSYS predictor, rate 4)", "fig_cdf_ood_r4.png")
            
    figure_inputs = {
        "generator_version": "1.0.0",
        "fig_motivation": {
            "indist_r4_fcfs": {"exp_id": "sweep-r4-fcfs", "sha": sweep[4]["fcfs"]["result_sha256"], "p99_lat": sweep[4]["fcfs"]["p99_lat"]},
            "indist_r4_ltr": {"exp_id": "sweep-r4-ltr", "sha": sweep[4]["ltr"]["result_sha256"], "tau": sweep[4]["ltr"]["tau"], "p99_lat": sweep[4]["ltr"]["p99_lat"]},
            "ood_r4_fcfs": {"exp_id": "ood-r4-fcfs", "sha": ood4f["result_sha256"], "p99_lat": ood4f["p99_lat"]},
            "ood_r4_ltr": {"exp_id": "ood-r4-ltr", "sha": ood4l["result_sha256"], "tau": ood4l["tau"], "p99_lat": ood4l["p99_lat"]}
        },
        "fig_ttft_vs_rate": {
            str(r): {
                "fcfs": {"exp_id": f"sweep-r{r}-fcfs", "sha": sweep[r]["fcfs"]["result_sha256"], "mean_ttft": sweep[r]["fcfs"]["mean_ttft"], "mean_lat": sweep[r]["fcfs"]["mean_lat"]},
                "ltr": {"exp_id": f"sweep-r{r}-ltr", "sha": sweep[r]["ltr"]["result_sha256"], "mean_ttft": sweep[r]["ltr"]["mean_ttft"], "mean_lat": sweep[r]["ltr"]["mean_lat"]}
            } for r in RATES
        },
        "fig_cdf_indist_r8": {
            "fcfs": {"exp_id": "sweep-r8-fcfs", "sha": sweep[8]["fcfs"]["result_sha256"], "mean_lat": sweep[8]["fcfs"]["mean_lat"]},
            "ltr": {"exp_id": "sweep-r8-ltr", "sha": sweep[8]["ltr"]["result_sha256"], "mean_lat": sweep[8]["ltr"]["mean_lat"]}
        },
        "fig_cdf_ood_r4": {
            "fcfs": {"exp_id": "ood-r4-fcfs", "sha": ood4f["result_sha256"], "mean_lat": ood4f["mean_lat"]},
            "ltr": {"exp_id": "ood-r4-ltr", "sha": ood4l["result_sha256"], "mean_lat": ood4l["mean_lat"]}
        }
    }
    with open(os.path.join(OUT, "figure_inputs.json"), "w") as f:
        json.dump(figure_inputs, f, indent=2)
    print(f"saved {OUT}/figure_inputs.json")
    
    print("ALL_CHARTS_DONE")


if __name__ == "__main__":
    main()
