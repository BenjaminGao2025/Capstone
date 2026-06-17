# SLO-Aware Scheduling Reproduction Starter

This folder contains a small reproduction scaffold for validating the main scheduling-level claim from:

> SLO-Aware Scheduling for Large Language Model Inferences

The goal is not to reproduce the full serving system yet. This first step uses our own synthetic workload trace to compare:

- `FCFS`: requests are served in arrival order.
- `SLO-aware`: ready requests are prioritized by urgency, using remaining SLO slack and estimated execution time.

## What It Produces

Running the script creates:

- `outputs/workload.csv`: generated request trace.
- `outputs/results.csv`: SLO attainment and average latency by request rate and policy.
- `outputs/slo_attainment.svg`: line chart for SLO attainment.
- `outputs/average_latency.svg`: line chart for average latency.

## Run

```powershell
python .\run_slo_reproduction.py
```

For the more paper-aligned simulated annealing version:

```powershell
python .\run_slo_sa_reproduction.py
```

This creates `outputs_sa/` with:

- `workload.csv`: generated workload trace.
- `served_requests.csv`: per-request serving outcome.
- `results_by_seed.csv`: aggregate metrics for each random seed.
- `results_summary.csv`: mean/std across five random seeds.
- `results.csv`: same content as `results_summary.csv` for convenience.
- `slo_attainment.svg`: FCFS vs simulated-annealing SLO-aware scheduling.
- `average_latency.svg`: average latency comparison.

## Method Scope

This is a simulation-level reproduction. It validates the scheduling trend before implementing the full paper system in vLLM.

The current SLO-aware policy is intentionally simple:

```text
priority = earliest deadline / least slack, with estimated service time considered
```

This can later be replaced by the paper's simulated annealing priority mapper.

`run_slo_sa_reproduction.py` adds that simulated annealing priority mapper. It still uses a synthetic latency predictor rather than a real vLLM profiler, so the current claim should be written as:

> simulation-level reproduction of the paper's scheduling effect.

## Apt-Serve Probe

To run the Apt-Serve-style hybrid cache and adaptive batch-composition probe:

```powershell
python .\run_aptserve_probe.py
```

This creates `outputs_aptserve/` with:

- `workload.csv`: generated workload trace.
- `served_requests.csv`: per-request serving outcome.
- `results_by_seed.csv`: aggregate metrics for each random seed.
- `results_summary.csv`: mean/std across five random seeds.
- `results.csv`: same content as `results_summary.csv` for convenience.
- `slo_attainment.svg`: FCFS with KV cache vs adaptive hybrid-cache scheduling.
- `average_batch_size.svg`: average admitted batch size under memory pressure.

This is also simulation-level. It does not implement Apt-Serve's vLLM changes or CUDA kernels. It tests the paper's core system intuition:

> KV-cache memory limits batch composition, while hybrid-cache-aware adaptive scheduling can admit better batches under memory pressure.
