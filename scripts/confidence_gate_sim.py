#!/usr/bin/env python3
"""OOD mitigation simulation: waiting-time aging gate.

Issue #20 acceptance criterion: at least one mitigation implemented + measured.

Background
----------
At rate-4 OOD (ShareGPT), the LTR ranker achieves |tau|=0.420 instead of the
in-dist 0.642.  The mis-ranked queue order inverts p99 (LTR 231s vs FCFS 151s
at rate 4), while still improving mean TTFT (LTR 23.8s vs FCFS 40.9s).

Why a score-percentile confidence gate does NOT help
-----------------------------------------------------
A naive gate that "only reorders requests in the top/bottom K% of scores" is
ineffective because mis-ranked SHORT requests are CONFIDENTLY predicted as long
(low score) and still get deprioritised.  Tested via simulation: all thresholds
0-45% give identical p99 to pure LTR.

Mitigation that DOES help: Waiting-Time Aging Gate
---------------------------------------------------
A request that has been waiting longer than W x mean_service_time is escalated
to FCFS (served next regardless of score).  This prevents indefinite starvation
of short requests that were mis-ranked as long.

  W = 0   : pure FCFS  (parity mean, parity p99)
  W small  : FCFS-like  (good p99, close-to-FCFS mean)
  W large  : LTR-like   (best mean, worst p99)
  W -> inf : pure LTR   (minimum mean, maximum p99)

The sweep over W shows the trade-off, with an operating point where the mean
latency benefit of LTR is largely preserved while the p99 tail is partially
recovered.

Output: figures/confidence_gate_sim.png

Run from repo root:
    python3 scripts/confidence_gate_sim.py
"""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.stats import kendalltau as _skt
    def _ktau(x, y):
        return float(_skt(x, y).statistic)
except ImportError:
    def _ktau(x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        n = len(x)
        rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
        conc = sum(
            np.sign(rx[i] - rx[i+1:]) @ np.sign(ry[i] - ry[i+1:])
            for i in range(n - 1)
        )
        return float(conc / (n * (n - 1) / 2))

RES        = "results/llama3-8b"
OUT        = "figures"
OOD_TAU    = -0.420
INDIST_TAU = -0.640
TARGET_RHO = 0.97     # high utilisation so queue builds up and aging matters
SEED       = 42
N_TRIALS   = 12
# W values: multiples of mean_service_time before aging kicks in
# W=0 → pure FCFS; W=inf → pure LTR; sweep log-spaced + inf endpoint
W_VALUES   = [0, 1, 2, 4, 8, 16, 32, 64, 128, 999999]  # 999999 ≈ infinity
W_LABELS   = ["0\n(FCFS)", "1", "2", "4", "8", "16", "32", "64", "128", "∞\n(LTR)"]


def load_output_lens():
    paths = glob.glob(os.path.join(
        RES,
        "vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-fcfs-20260611-113110*ood-sharegpt.json",
    ))
    assert paths, "FCFS OOD sharegpt result not found"
    return np.array(json.load(open(paths[0]))["output_lens"])


def calibrate_noise(true_ranks, output_lens, target_tau, seed):
    n = len(output_lens)
    lo, hi = 0.0, float(n * 4)
    for _ in range(50):
        mid = (lo + hi) / 2.0
        rng = np.random.RandomState(seed)
        scores = -true_ranks + rng.randn(n) * mid
        tau = _ktau(scores, output_lens)
        if tau < target_tau:
            lo = mid
        else:
            hi = mid
    rng = np.random.RandomState(seed)
    return -true_ranks + rng.randn(n) * ((lo + hi) / 2.0)


def simulate_aging(output_lens, scores, arrivals, W_factor, mean_svc, decode_rate):
    """Single-server priority queue with waiting-time aging gate.

    W_factor : float
        Age threshold in units of mean_service_time.  A request waiting
        longer than W_factor * mean_svc gets escalated to FCFS.
        W_factor=0  → pure FCFS.
        W_factor=999999 → pure LTR (no aging).
    """
    n = len(output_lens)
    age_threshold = W_factor * mean_svc
    queue = []
    time = 0.0
    idx = 0
    finish_times = np.empty(n)

    while idx < n or queue:
        # Add all requests that have arrived by current time (before idle-advance)
        while idx < n and arrivals[idx] <= time:
            queue.append(idx)
            idx += 1

        if not queue:
            time = float(arrivals[idx])
            queue.append(idx)
            idx += 1
            while idx < n and arrivals[idx] <= time:
                queue.append(idx)
                idx += 1

        # Aging gate: any request waiting > age_threshold gets FCFS priority
        aged = [r for r in queue if (time - arrivals[r]) >= age_threshold]
        if aged or W_factor == 0:
            # Serve oldest-waiting (FCFS for aged or if W=0)
            chosen = min(queue if W_factor == 0 else aged, key=lambda r: arrivals[r])
        else:
            # LTR: serve highest score among non-aged
            chosen = max(queue, key=lambda r: scores[r])
        queue.remove(chosen)

        time += float(output_lens[chosen]) * decode_rate
        finish_times[chosen] = time

    return finish_times - arrivals


def run_one_trial(output_lens, true_ranks, target_tau, decode_rate, mean_svc, seed):
    n = len(output_lens)
    rng = np.random.RandomState(seed)
    rate = TARGET_RHO / mean_svc
    arrivals = np.cumsum(rng.exponential(1.0 / rate, n))

    scores = calibrate_noise(true_ranks, output_lens, target_tau, seed)
    actual_tau = _ktau(scores, output_lens)

    # FCFS baseline (W=0)
    lats_fcfs = simulate_aging(output_lens, scores, arrivals, 0, mean_svc, decode_rate)
    fcfs_p99  = float(np.percentile(lats_fcfs, 99))
    fcfs_mean = float(np.mean(lats_fcfs))

    out = {}
    for W in W_VALUES:
        lats = simulate_aging(output_lens, scores, arrivals, W, mean_svc, decode_rate)
        out[W] = {
            "p99_ratio":  float(np.percentile(lats, 99)) / fcfs_p99,
            "mean_ratio": float(np.mean(lats)) / fcfs_mean,
        }
    return out, actual_tau


def main():
    os.makedirs(OUT, exist_ok=True)
    output_lens = load_output_lens()
    n = len(output_lens)
    true_ranks = np.argsort(np.argsort(output_lens)).astype(float)

    decode_rate = TARGET_RHO / (4.0 * float(np.mean(output_lens)))
    mean_svc    = float(np.mean(output_lens)) * decode_rate
    print(f"n={n}, mean_output={output_lens.mean():.0f}, "
          f"decode_rate={decode_rate:.5f} s/token, mean_svc={mean_svc:.3f}s, ρ={TARGET_RHO}")

    ood_p99  = {W: [] for W in W_VALUES}
    ood_mean = {W: [] for W in W_VALUES}
    ind_p99  = {W: [] for W in W_VALUES}
    ind_mean = {W: [] for W in W_VALUES}
    tau_ood_checks, tau_ind_checks = [], []

    for trial in range(N_TRIALS):
        r_ood, t_ood = run_one_trial(output_lens, true_ranks, OOD_TAU,
                                     decode_rate, mean_svc, SEED + trial)
        r_ind, t_ind = run_one_trial(output_lens, true_ranks, INDIST_TAU,
                                     decode_rate, mean_svc, SEED + trial + 1000)
        tau_ood_checks.append(t_ood)
        tau_ind_checks.append(t_ind)
        for W in W_VALUES:
            ood_p99[W].append(r_ood[W]["p99_ratio"])
            ood_mean[W].append(r_ood[W]["mean_ratio"])
            ind_p99[W].append(r_ind[W]["p99_ratio"])
            ind_mean[W].append(r_ind[W]["mean_ratio"])
        print(f"  trial {trial+1}/{N_TRIALS}: ood_tau={t_ood:.3f}  ind_tau={t_ind:.3f}",
              flush=True)

    mean_ood = float(np.mean(tau_ood_checks))
    mean_ind = float(np.mean(tau_ind_checks))

    ood_p99_m  = [float(np.mean(ood_p99[W]))  for W in W_VALUES]
    ood_mean_m = [float(np.mean(ood_mean[W])) for W in W_VALUES]
    ind_p99_m  = [float(np.mean(ind_p99[W]))  for W in W_VALUES]
    ind_mean_m = [float(np.mean(ind_mean[W])) for W in W_VALUES]

    print(f"\nMean tau: OOD={mean_ood:.3f}  in-dist={mean_ind:.3f}")
    print(f"\n{'W':>8} | OOD p99 | OOD mean | InDist p99 | InDist mean")
    for i, (W, wl) in enumerate(zip(W_VALUES, W_LABELS)):
        print(f"  {wl.replace(chr(10), ' '):>8} | {ood_p99_m[i]:.3f}x  | {ood_mean_m[i]:.3f}x"
              f"  | {ind_p99_m[i]:.3f}x    | {ind_mean_m[i]:.3f}x")

    # ── Figure ────────────────────────────────────────────────────────────────
    C_OOD  = "#c62828"
    C_IND  = "#2e7d32"
    xs = list(range(len(W_VALUES)))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))

    # Left: p99 ratio
    ax = axes[0]
    ax.plot(xs, ood_p99_m, "o-",  color=C_OOD, lw=2.2,
            label=f"OOD (τ={mean_ood:.3f})")
    ax.plot(xs, ind_p99_m, "s--", color=C_IND, lw=2.2,
            label=f"In-dist (τ={mean_ind:.3f})")
    ax.axhline(1.0, color="black", lw=1, ls=":")
    ax.text(xs[-1] - 0.1, 1.04, "FCFS parity", fontsize=8.5, ha="right")
    ax.set_xticks(xs)
    ax.set_xticklabels(W_LABELS, fontsize=8)
    ax.set_xlabel("Age threshold W  (× mean_service_time)\nW=0 → pure FCFS;  W=∞ → pure LTR")
    ax.set_ylabel("p99 latency ratio  (policy / FCFS)")
    ax.set_title("(a) p99 latency ratio vs age threshold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    # Right: mean ratio
    ax = axes[1]
    ax.plot(xs, ood_mean_m, "o-",  color=C_OOD, lw=2.2,
            label=f"OOD (τ={mean_ood:.3f})")
    ax.plot(xs, ind_mean_m, "s--", color=C_IND, lw=2.2,
            label=f"In-dist (τ={mean_ind:.3f})")
    ax.axhline(1.0, color="black", lw=1, ls=":")
    ax.text(xs[-1] - 0.1, 1.015, "FCFS parity", fontsize=8.5, ha="right")
    ax.set_xticks(xs)
    ax.set_xticklabels(W_LABELS, fontsize=8)
    ax.set_xlabel("Age threshold W  (× mean_service_time)\nW=0 → pure FCFS;  W=∞ → pure LTR")
    ax.set_ylabel("mean latency ratio  (policy / FCFS)")
    ax.set_title("(b) Mean latency ratio vs age threshold")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    note = (
        f"Single-server queue, ρ={TARGET_RHO}, actual output_lens from committed FCFS OOD serving run.\n"
        f"Synthetic scores calibrated to target τ via binary search.  Avg over {N_TRIALS} Poisson-arrival trials.\n"
        f"A score-percentile gate (not shown) provides NO benefit — all thresholds give identical p99 to pure LTR.\n"
        f"Waiting-time aging restores p99 towards FCFS while preserving part of LTR's mean latency advantage."
    )
    fig.text(0.5, 0.01, note, ha="center", fontsize=7.5, color="#555",
             bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.75))

    fig.suptitle("Waiting-Time Aging Gate — OOD Mitigation Simulation Study",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.12, 1, 1])
    out_path = os.path.join(OUT, "confidence_gate_sim.png")
    fig.savefig(out_path, dpi=180)
    print(f"\nsaved  {out_path}")

    # Find good operating point: lowest p99 while mean < 0.90
    candidates = [(i, ood_p99_m[i], ood_mean_m[i]) for i in range(len(W_VALUES))
                  if ood_mean_m[i] < 0.90]
    if candidates:
        best = min(candidates, key=lambda t: t[1])
        print(f"\nBest OOD operating point: W={W_LABELS[best[0]]} → "
              f"p99={best[1]:.3f}x, mean={best[2]:.3f}x vs FCFS")
    print(f"Pure LTR OOD:  p99={ood_p99_m[-1]:.3f}x  mean={ood_mean_m[-1]:.3f}x")
    print(f"Pure FCFS OOD: p99={ood_p99_m[0]:.3f}x  mean={ood_mean_m[0]:.3f}x")


if __name__ == "__main__":
    main()
