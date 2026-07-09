# LLM Scheduling Capstone

FDU MSACS Capstone project (CSCI 6806 / INFO 4205, Summer 2026) on latency-aware
LLM serving. The current experiment compares the FCFS scheduler in vLLM with
the learning-to-rank (LTR) scheduler from
[vllm-ltr](https://github.com/hao-ai-lab/vllm-ltr).

The committed smoke test uses `facebook/opt-1.3b` to verify the complete
pipeline before running the larger Llama workload. It is a functional check,
not a statistically meaningful performance claim.

## Team

| Name | Student # | Role / main contribution |
|---|---|---|
| Yuze Gao | 2119104 | Core: LTR scheduler reproduction, OOD robustness study, mitigation design |
| Yuh Jen Sun | 2109902 | Cache-aware prefix-scoring probe (LMSYS trace) |
| Shun Huang | 2100618 | SLO-aware & Apt-Serve scheduling reproduction |
| Chenxi Li | 2133321 | Smoke-test reproduction & charts |
| Mengze Hu | 2135034 | PromptCache related-work review; KV-cache / batch-size measurement |

## Repository Layout

```text
.
├── scripts/                 # data, benchmark, sweep, and plotting helpers
├── results/                 # committed benchmark JSON files
├── figures/                 # generated plots
├── docs/                    # roadmap, papers, notes, and presentation material
├── report/                  # presentation artifacts
├── server_backup/           # GPU-server backup: 2026-06-21 aging-gate validation runs + logs
└── slo_reproduction/        # related-work probes: SLO-aware & Apt-Serve (simulation-level)
```

## Reference Environment

The smoke results in this repository were produced with:

- `vllm-ltr` commit `13bbf6ff`
- Python 3.11.8, using the system `pip` rather than Conda
- PyTorch `2.2.1+cu121`
- CUDA 12.1
- NVIDIA GeForce RTX 3090, 24 GB
- XFormers attention with `--enforce-eager`; FlashAttention was not installed

Model-selection decision: although the paper names Llama 3.1, the repository
traces and predictors are Llama-3-8B artifacts, and vLLM 0.4.1 with
Transformers 4.40.1 cannot parse the Llama 3.1 `rope_scaling` configuration.
This reproduction therefore uses `Meta-Llama-3-8B-Instruct` and will state the
deviation explicitly in the project defense.

The serving engine must be built on a CUDA Linux host. Plot generation can be
run separately on macOS or Linux.

## Reproduction

### 1. Build vllm-ltr

The working setup used Python 3.11.8 and the system `pip`. Check out the pinned
revision, install PyTorch for CUDA 12.1, build from source, and then pin the
legacy-compatible Transformers and FastAPI versions:

```bash
git clone https://github.com/hao-ai-lab/vllm-ltr.git
cd vllm-ltr
git checkout 13bbf6ff

python3.11 -m pip install \
  torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
pip install -e .
pip install transformers==4.40.1 fastapi==0.110.3
pip install numpy==1.26.4 fschat accelerate gcsfs scikit-learn scipy \
  matplotlib evaluate
```

Do not install `flash-attn` for this setup. The tested runtime uses XFormers
and the serving scripts pass `--enforce-eager`. The explicit dependency pins
are required because current `pip` resolution can select Transformers 5.x and
FastAPI 0.136, which are incompatible with the vLLM 0.4.1 code at this pinned
revision and cause build or runtime failures. A Conda environment with Python
3.10 remains an alternative, but it was not used for the committed smoke run.

Confirm the pinned environment:

```bash
git rev-parse --short=8 HEAD
python -c 'import fastapi, torch, transformers; print(torch.__version__, torch.version.cuda, transformers.__version__, fastapi.__version__)'
```

### 2. Download the trace and predictor

Run these commands from `vllm-ltr/benchmarks`:

```bash
huggingface-cli download LLM-ltr/Llama3-Trace \
  --local-dir ./Llama3-Trace --repo-type dataset
mv Llama3-Trace/*.jsonl .

mkdir -p MODEL/results
huggingface-cli download LLM-ltr/OPT-Predictors --local-dir MODEL/results
```

The smoke scripts expect the LMSYS trace
`lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl` and the
predictor configuration under `MODEL/results/`.

### 3. Run FCFS and LTR

Set `EXPERIMENT_ROOT` to a writable experiment workspace containing
`vllm-ltr/`. The scripts default to `/hy-tmp`, but the location is configurable:

```bash
export EXPERIMENT_ROOT=/path/to/experiment
export VLLM_LTR_DIR=/path/to/vllm-ltr
export RESULT_DIR="$PWD/results"

bash scripts/run_fcfs.sh
bash scripts/run_ltr.sh
```

The default smoke configuration is:

- model: `facebook/opt-1.3b`
- requests: 50
- request rate: 8
- generated output length: 128 tokens
- random seed: 0

Each script starts the serving process, waits for its health check, runs
`benchmark_serving_real.py`, and writes a JSON result to `RESULT_DIR`.

For the full 8B probe and rate sweep, use:

```bash
bash scripts/run_llama_probe.sh
bash scripts/run_rate_sweep.sh
```

### 4. Plot the comparison

From this repository root:

```bash
python scripts/plot_compare.py results/*.json
```

The plot includes request-latency CDF, mean latency, p99 latency, and normalized
latency in seconds per output token.

## Smoke Result

| Scheduler | Completed | Throughput (req/s) | Mean TTFT (ms) | Mean latency (s) | P99 latency (s) | Mean normalized latency (s/token) |
|-----------|----------:|-------------------:|---------------:|-----------------:|----------------:|----------------------------------:|
| FCFS | 50 | 4.5597 | 129.2 | 4.34 | 5.24 | 0.0377 |
| LTR | 50 | 4.7334 | 154.9 | 4.15 | 5.41 | 0.0394 |

![FCFS versus LTR smoke result](figures/fcfs_vs_ltr.png)

Both runs completed all 50 requests. In this small smoke test, LTR had slightly
lower mean request latency and slightly higher measured throughput, while FCFS
had lower mean TTFT, p99 request latency, and normalized latency. Larger,
repeated runs are required before drawing scheduling conclusions. The near tie
is expected: the predictor was trained to rank Llama-3-8B output lengths, but
its ranking on `facebook/opt-1.3b` is effectively noise (Kendall's Tau about
-0.09), so LTR behaves approximately like random scheduling in this smoke test.

## Honest Results Table (Single Source of Truth)

This is the authoritative table for the summary, midterm deck, and final
report.  All claims must be traceable to a committed result file.

### In-distribution (LMSYS trace, Meta-Llama-3-8B-Instruct)

| Rate (req/s) | FCFS mean TTFT | LTR mean TTFT | TTFT ratio | LTR tau |
|---:|---:|---:|---:|---:|
| 2  | 111 ms | 130 ms | 0.85× | −0.641 |
| 4  | 1,122 ms | 234 ms | **4.8×** | −0.642 |
| 8  | 16,362 ms | 2,026 ms | **8.1×** | −0.641 |
| 16 | 18,457 ms | 2,915 ms | **6.3×** | −0.642 |
| 32 | 21,215 ms | 6,095 ms | **3.5×** | −0.642 |

Peak in-distribution gain: **8.1× mean TTFT** at rate 8.

### Out-of-distribution (ShareGPT trace — predictor trained on LMSYS)

| Metric | FCFS | LTR | Verdict |
|:---|---:|---:|:---|
| Kendall tau | N/A | −0.420 (vs −0.642 in-dist) | **−34% ranking quality** |
| Mean TTFT (rate 4) | 40,892 ms | 23,810 ms | LTR 1.72× better mean TTFT ✓ |
| p99 latency (rate 4) | 151 s | 231 s | **LTR 1.53× worse p99** ✗ |
| Rate-8 stability | 500/500 complete | engine crash (seed 0) | **LTR crashes or yields no tail benefit** ✗ |

### OOD Breakdown Summary ("三连崩")

1. **Ranking quality collapses**: Kendall tau drops from −0.642 to −0.420 (−34%).
2. **Tail-latency inversion**: p99 worsens from 151 s (FCFS) to 231 s (LTR) — 53% worse.
3. **Seed-sensitive failure at rate 8**: mis-ranked preemption storm exhausts CPU swap and deterministically crashes the engine on seed 0 (and survives on some seeds but with **no tail benefit over FCFS**).

### Honest Contribution Statement

> We characterised the robustness boundary of internal-signal LLM scheduling:
> the LTR ranker achieves up to **8.1× mean TTFT in-distribution** but exhibits
> complete tail-latency inversion and engine failure **out-of-distribution**.
> On the OOD ShareGPT workload at rate 4, raw LTR improves *mean* TTFT by
> ~1.72×, **but this number is not deployable on its own**: at the same
> operating point it incurs a **1.53× p99 tail regression**, and at rate 8 the
> engine **crashes**. The only configuration that is actually deployable — no
> p99 regression and no crash — is the waiting-time aging gate, whose mean-TTFT
> gain shrinks to roughly **~1.2–1.3×** over FCFS. That mitigation has now been
> **validated on the RTX 3090** (2026-07-09, seeds 0–2): aging gate +
> preemption protection completes 500/500 at OOD rate 8 where raw LTR crashes,
> and at rate 4 beats FCFS on both mean and p99 TTFT (34.8 s / 87.7 s vs
> 40.4 s / 96.0 s). However, this safety comes at a cost: **on the in-distribution trace, the mean TTFT advantage drops from LTR's 2.03s to 13.07s** (compared to FCFS's 16.36s) — a tradeoff of in-distribution speed for out-of-distribution stability. We do **not** claim "8× everywhere," and we do **not** claim a
> free ~1.7× deployable gain.

### Diagnostic Figure

![OOD diagnostic: tau vs distribution and p99 inversion](figures/ood_tau_vs_shift.png)

See `scripts/ood_diagnostic.py` to reproduce.

### Mitigation: Waiting-Time Aging Gate (Simulation Study)

A naive score-percentile confidence gate provides **no improvement**: requests
mis-ranked as long are still served last even when the gate is applied, because
their low score is "confidently" wrong.

A **waiting-time aging gate** (escalate requests that have waited > W ×
mean_service_time to FCFS) breaks the starvation loop:

| W (× mean svc time) | OOD p99 ratio | OOD mean ratio | Verdict |
|---:|---:|---:|:---|
| 0 (FCFS) | 1.000× | 1.000× | baseline |
| 8 | **0.984×** | **0.937×** | Pareto-better than FCFS ✓ |
| 16 | 1.023× | 0.860× | slight p99 cost, big mean gain |
| ∞ (LTR) | 3.108× | 0.741× | maximum mean, severe p99 tail |

At W = 8, the aging gate achieves **both** lower mean and lower p99 than pure
FCFS on the OOD workload in this **single-load (ρ=0.97) simulation with
synthetic scores**.  This is an existence proof at one extreme load, not a
general or measured result.  See `scripts/confidence_gate_sim.py` for the
simulation; a load sweep and a real-vLLM implementation on the RTX 3090 remain
future work.

![Aging gate simulation](figures/confidence_gate_sim.png)

### Mitigation: Real-GPU Validation (2026-06-21)

The simulation prediction was validated on the RTX 3090 with the OOD ShareGPT
trace (seed 0, n=500, `SWAP_SPACE=4` — the original crash configuration):

| Rate | Arm | Completed | Mean TTFT | P99 TTFT |
|---:|:---|---:|---:|---:|
| 4 | FCFS | 500/500 | 49.6 s | 110.4 s |
| 4 | LTR | 500/500 | 24.3 s | 156.2 s |
| 4 | LTR+aging(120 s), no protect | 500/500 | 27.4 s | 120.3 s |
| 4 | **LTR+aging(60 s)+protect** | 500/500 | **37.1 s** | **98.0 s** |
| 8 | FCFS | 500/500 | 69.3 s | 158.9 s |
| 8 | LTR | **crash (15/500)** | — | — |
| 8 | LTR+aging(120 s), no protect | **crash (15/500)** | — | — |
| 8 | **LTR+aging(60 s)+protect** | 500/500 | **61.0 s** | **147.9 s** |

Two hardware-measured conclusions:

1. **Preemption protection (running requests pinned to priority tier −1) is
   the load-bearing component for survival** — the aging gate alone still
   crashes at rate 8.
2. At rate 4 the combined policy is **Pareto-better than FCFS on the OOD
   trace** (lower mean *and* lower p99), matching the simulation's W=8
   prediction. The deployable mean gain is ~1.2–1.3×, not raw LTR's 1.7×.

Single seed; multi-seed repetition is future work. Full write-up:
[aging-gate GPU validation report](docs/experiments/2026-06-21-aging-gate-validation.md).
Raw JSONs and logs: `server_backup/results/`.

## Current Status

The formal `Meta-Llama-3-8B-Instruct` reproduction is complete: the
in-distribution rate sweep (2–32 req/s) reproduces the LTR advantage (up to
8.1× mean TTFT), and the out-of-distribution evidence is in hand — ranking
quality drops (tau -0.642 → -0.420), the tail-latency advantage inverts, and
at rate 8 the mis-ranked LTR arm exhausts swap and crashes the engine. See the
[formal run report](docs/experiments/2026-06-11-llama3-8b-formal-runs.md) and
the earlier
[reproduction milestone report](docs/experiments/2026-06-10-vllm-ltr-reproduction.md).
The aging-gate mitigation has been validated on hardware: with preemption
protection enabled, all OOD runs complete at rates 4 and 8, and the rate-4
configuration beats FCFS on both mean and p99 TTFT
([validation report](docs/experiments/2026-06-21-aging-gate-validation.md)).

## Cache-Aware Prefix Analysis

This branch adds a trace-level analysis for cache-aware prefix scoring. The
method measures how often requests reuse the same prompt prefix and converts
that signal into a cache-aware scheduling score.

The main evaluation figure consolidates the cache-prefix result into one
readable ablation: measured prefix opportunity, in-distribution versus shifted
ranking quality, and the effect of adding the cache bonus to LTR. Supporting
LMSYS, ratio-sweep, and workload-shape plots are kept in the detailed report
rather than repeated on the repository front page.

![Cache-prefix ranking ablation](figures/cache_prefix_ranking_ablation.svg)

Conclusion: the cache-prefix probe finds real shared-prefix opportunity in the
LMSYS trace, but adding the cache bonus does not improve the committed offline
ranking diagnostic. The base LTR ranking signal still drops on the shifted
ShareGPT trace, and the synthetic cache-weight sweep shows that large cache
weights can make ranking quality worse. This method is therefore best framed as
a prefill/TTFT opportunity signal that needs serving-level validation, not as a
standalone fix for OOD ranking.

| Offline check | Main measurement | Takeaway |
|---|---:|---|
| LMSYS trace probe | 14.6% hit rate at `prefix_words=16` | Shared-prefix reuse exists in the trace. |
| Shared-prefix ratio sweep | `cache_hit_rate` 0.00 → 1.00 | The signal scales with controlled prefix reuse. |
| Workload-shape sweep | high / medium / zero reuse | The method distinguishes agent-like traffic from random-like traffic. |
| Ranking ablation | 0.640 → 0.420 absolute tau; best cache delta +0.000 | The cache bonus is a prefill/TTFT opportunity signal, not an OOD ranking fix. |

Details and reproduction commands are in the
[cache-aware prefix-scoring report](docs/experiments/2026-06-17-cache-prefix-probe.md).

## Project Documents

- [vLLM-LTR reproduction milestone](docs/experiments/2026-06-10-vllm-ltr-reproduction.md)
- [Aging-gate GPU validation (2026-06-21)](docs/experiments/2026-06-21-aging-gate-validation.md)
- [Smoke test report](docs/smoke-test-report.md)
- [Roadmap](docs/roadmap-v0.1.md)
- [Related-work summaries](docs/related-work/)
- [Presentation material](docs/presentation/)
