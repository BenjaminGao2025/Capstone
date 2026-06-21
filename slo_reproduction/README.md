# SLO-Aware and Apt-Serve Scheduling Probes

This folder contains paper-inspired probes for two related scheduling papers:

- `SLO-Aware Scheduling for Large Language Model Inferences`
- `Apt-Serve: Adaptive Request Scheduling on Hybrid Cache for Scalable LLM Inference Serving`

These scripts are not full vLLM implementations of the original systems. They
are simulation-level and trace-driven checks used to decide which scheduling
signals are useful to combine with the base LTR scheduler.

## Result Sets

There are four result sets in this folder. They should be interpreted
separately.

| Path | Scope | Main supported conclusion |
|------|-------|---------------------------|
| `outputs/` | early synthetic SLO-aware probe | SLO-aware priority improves SLO attainment, but average latency is not consistently lower under high load |
| `outputs_sa/` | simulated-annealing SLO-aware probe over five seeds | more paper-aligned SLO-aware scheduling simulation; still synthetic |
| `outputs_aptserve/` | synthetic Apt-Serve-style hybrid-cache probe over five seeds | adaptive hybrid scheduling lowers mean latency in this simulation, but high-load variance is large |
| `related_bigmodel_results/` | supplementary Llama-3-8B trace-driven probe | later trace-derived check showing latency-reduction potential under a different workload setting |

The early synthetic CSVs and the later trace-driven CSV use different request
rates and workload assumptions. Do not compare their numbers as if they came
from one experiment.

## Run Synthetic SLO-Aware Probe

```powershell
python .\run_slo_reproduction.py
```

This creates `outputs/`:

- `workload.csv`: generated request trace.
- `results.csv`: SLO attainment and average latency by request rate and policy.
- `slo_attainment.svg`: SLO attainment chart.
- `average_latency.svg`: average latency chart.

The strongest conclusion from this early probe is improved SLO attainment, not
stable average-latency reduction.

## Run Simulated-Annealing SLO-Aware Probe

```powershell
python .\run_slo_sa_reproduction.py
```

This creates `outputs_sa/`:

- `workload.csv`: generated workload trace.
- `served_requests.csv`: per-request serving outcome.
- `results_by_seed.csv`: aggregate metrics for each random seed.
- `results_summary.csv`: mean/std across five random seeds.
- `results.csv`: same content as `results_summary.csv` for convenience.
- `slo_attainment.svg`: FCFS vs simulated-annealing SLO-aware scheduling.
- `average_latency.svg`: average latency comparison.

This version is closer to the SLO-aware paper's priority-mapping idea, but it
still uses a synthetic latency model rather than a real vLLM serving loop.

## Run Apt-Serve Probe

```powershell
python .\run_aptserve_probe.py
```

This creates `outputs_aptserve/`:

- `workload.csv`: generated workload trace.
- `served_requests.csv`: per-request serving outcome.
- `results_by_seed.csv`: aggregate metrics for each random seed.
- `results_summary.csv`: mean/std across five random seeds.
- `results.csv`: same content as `results_summary.csv` for convenience.
- `slo_attainment.svg`: FCFS with KV cache vs adaptive hybrid-cache scheduling.
- `average_batch_size.svg`: average admitted batch size under memory pressure.

This is also simulation-level. It does not implement Apt-Serve's vLLM runtime
changes or CUDA kernels. It tests the paper's core intuition that KV-cache
memory pressure affects batch composition and latency.

## Supplementary Trace-Driven Probe

`related_bigmodel_results/summary.csv` contains a later Llama-3-8B
trace-driven probe. It is kept as supplementary evidence because it uses a
different trace-derived workload setting from the early synthetic CSVs.

**Probe warning:** these trace-driven numbers still use a synthetic latency
model. They are not real vLLM hardware measurements and should not be presented
as a full reproduction of SLO-Aware Scheduling or Apt-Serve.

The trace-driven result can be cited as latency-reduction potential, but it
should not be described as a full reproduction of SLO-Aware Scheduling or
Apt-Serve.
