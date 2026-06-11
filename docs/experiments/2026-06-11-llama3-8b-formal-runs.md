# Llama-3-8B Formal Runs: Rate Sweep and OOD Evidence

Date: 2026-06-11

## Status

The formal `Meta-Llama-3-8B-Instruct` experiments are complete. The
in-distribution rate sweep reproduces the LTR scheduling advantage reported by
the base paper, and the out-of-distribution (OOD) runs provide three
independent pieces of evidence motivating direction A (predictor
generalization/robustness).

## Setup

- Model: `Meta-Llama-3-8B-Instruct` (FP16, local safetensors). The base paper
  cites Llama-3.1, but the public traces and OPT predictors released with
  vllm-ltr are all Llama-3-8B artifacts, so we match the artifacts and note
  the deviation.
- Hardware: single RTX 3090 (24 GB), container memory limit 23 GiB.
- Serving: vLLM 0.4.1 (vllm-ltr @ `13bbf6ff`), `--enable-chunked-prefill
  --enforce-eager --max-model-len 8192 --swap-space 4`, identical for both
  arms in every pair.
- Workload: 500 prompts per run, `seed=0`, true trace replay
  (`--output-len -1`).
- In-distribution: LMSYS test trace with the
  `opt-125m-llama3-8b-lmsys-score-trainbucket10-b32` predictor (matched).
- OOD: ShareGPT test trace with the same LMSYS-trained predictor
  (deliberate distribution mismatch).

## In-Distribution Rate Sweep (LMSYS)

| rate | arm | mean TTFT (s) | p99 TTFT (s) | mean lat (s) | p99 lat (s) | tau |
|------|------|------------:|------------:|------------:|------------:|------:|
| 2 | FCFS | 0.11 | 0.33 | 12.99 | 52.15 | – |
| 2 | LTR | 0.13 | 0.35 | 13.47 | 54.60 | -0.641 |
| 4 | FCFS | 1.12 | 7.53 | 29.06 | 105.87 | – |
| 4 | LTR | **0.23** | **0.50** | 27.93 | 109.22 | -0.642 |
| 8 | FCFS | 16.36 | 52.19 | 48.60 | 120.92 | – |
| 8 | LTR | **2.03** | 47.06 | **41.39** | 148.41 | -0.641 |
| 16 | FCFS | 18.46 | 80.53 | 59.96 | 137.35 | – |
| 16 | LTR | **2.92** | 52.18 | **46.29** | 147.07 | -0.642 |
| 32 | FCFS | 21.22 | 91.19 | 63.57 | 141.80 | – |
| 32 | LTR | **6.10** | 56.38 | **48.26** | 146.11 | -0.642 |

Reading: at light load (rate 2) the arms are equivalent — there is no queue to
reorder. From rate 4 upward LTR delivers a 3.5–8.1× mean TTFT advantage
(14.9× p99 TTFT at rate 4) and up to 1.32× mean latency, at the cost of a
slightly worse p99 latency (long requests are deprioritized — the expected
SJF tail trade-off). This reproduces the direction of the base paper's result.

## OOD Evidence (ShareGPT trace × LMSYS-trained predictor)

Three independent failure signals:

1. **Ranking quality collapses.** Kendall tau degrades from **-0.642**
   (in-distribution, stable across all five rates) to **-0.420** (OOD), a
   ~35% loss of ranking signal. Sign convention: the scheduler executes
   higher scores first (`scheduler.py:996`), so more-negative tau against
   true output length = effective SJF ordering; tau near 0 = no signal.
   Cross-validated two ways: serving-side measurement and an offline scoring
   pipeline agree to <0.002 on both datasets (offline lmsys -0.6402 vs
   serving -0.6415; offline sharegpt -0.4200 vs serving -0.4204).
2. **The latency advantage inverts in the tail (rate 4).** Mean TTFT
   advantage shrinks to 1.7×, while p99 TTFT becomes 1.6× *worse* than FCFS
   (151 s vs 96 s) and p99 latency 1.5× worse (231 s vs 150 s).

   | rate 4 OOD | mean TTFT (s) | p99 TTFT (s) | mean lat (s) | p99 lat (s) | tau |
   |------|------------:|------------:|------------:|------------:|------:|
   | FCFS | 40.89 | 96.26 | 78.53 | 150.16 | – |
   | LTR | 23.81 | **151.09** | 74.93 | **230.98** | -0.420 |

3. **At rate 8 the LTR arm crashes outright.** Mis-ranked long requests
   trigger a preemption storm; the fork hard-codes swap-mode preemption
   (`scheduler.py:1410/1434`, no CLI override), the 4 GB CPU swap pool is
   exhausted, and the engine aborts
   (`RuntimeError: Aborted due to the lack of CPU swap space`,
   `scheduler.py:1830`). FCFS completes 500/500 on the identical workload.
   Full artifacts are preserved in
   `results/llama3-8b/ood-rate8-crashed-evidence/` (paired FCFS JSON, the
   n=15 partial LTR JSON, gzipped server logs, error extract). Raising swap
   was not an option within the 23 GiB container limit (peak observed
   memory was already 20.93 GiB).

Together these upgrade the direction-A motivation from "performance
degradation under distribution shift" to "an availability risk": a mismatched
predictor does not just lose its advantage, it can take the service down.

## Data

- `results/llama3-8b/*.json` — per-run benchmark outputs with per-request
  arrays (`send_ts`, `latencies`, `first_token_ts`, `completion_ts`,
  `aux_kendall_tau`, …), enabling CDF/分布 plots without re-running.
- `results/llama3-8b/kendall-tau-archive.txt` — consolidated tau evidence
  chain with the sign convention documented in the header.
- `scripts/offline_tau.py` — offline predictor-quality pipeline (validated
  against serving measurements); future direction-A predictor iterations can
  be evaluated without GPU serving runs.

## Known Deviations and Notes

- Benchmark client patched: per-request timing arrays added to the result
  JSON, and a pre-existing array-misalignment bug fixed in the Kendall tau
  computation when requests fail (success-mask alignment in
  `benchmark_serving_real.py`).
- The crashed rate-8 OOD LTR run produced only 15/500 successful requests;
  its tau (n=15) is reported as invalid and excluded from analysis.
- p99 figures are computed from the per-request arrays
  (`ttft + sum(itl)`), consistent across arms.
