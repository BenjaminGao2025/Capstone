# Number Verification Report (2026-07-21)

This report presents the empirical verification of experimental numbers against raw benchmark JSON artifacts, adhering strictly to the data hygiene rule (requiring 500/500 successful requests for statistical aggregation).

## 1. Four-Arm Ablation (LMSYS Trace, Request Rate 8)

Source JSONs under `results/llama3-8b/`:
- FCFS: `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-fcfs-20260611-104351.json`
- LTR-OPT: `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260611-104730.json`
- Ablation (our head): `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260613-021954-ablation-ourshead.json`
- V1 (Aging+Protect): `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-v1-val-seed0.json`

| Arm | Document Value | Recalculated Value | Matches |
|---|:---|:---|:---|
| FCFS Mean TTFT | 16.36 s | 16.36 s | Yes |
| LTR-OPT Mean TTFT | 2.03 s | 2.03 s | Yes |
| Ablation (our head) Mean TTFT | 1.84 s | 1.84 s | Yes |
| V1 (Aging+Protect) Mean TTFT | 13.07 s | 13.07 s | Yes |

## 2. Phase D Multi-Seed Table (OOD ShareGPT Trace, Seeds 0/1/2)

Source JSONs under `results/llama3-8b/p2/` (17 files):
- Data Hygiene: Runs completing <500 requests are classified as crashes and excluded from latency aggregation. For Rate 8 LTR, Seed 1 completed 500/500 while Seed 0/2 crashed.

| Metric | Document Value | Recalculated Value (Across-Seed) | Matches |
|---|:---|:---|:---|
| Rate 4 FCFS Mean TTFT | 40,438 ± 2,082 ms | 40,437.7 ± 2,081.8 ms | Yes |
| Rate 4 FCFS P99 TTFT | 95,977 ± 2,100 ms | 95,977.0 ± 2,099.8 ms | Yes |
| Rate 4 LTR Mean TTFT | 22,873 ± 1,228 ms | 22,873.3 ± 1,228.4 ms | Yes |
| Rate 4 LTR P99 TTFT | 148,592 ± 4,162 ms | 148,592.0 ± 4,162.1 ms | Yes |
| Rate 4 V1 Mean TTFT | 34,849 ± 3,172 ms | 34,849.4 ± 3,171.8 ms | Yes |
| Rate 4 V1 P99 TTFT | 87,653 ± 6,375 ms | 87,652.7 ± 6,375.1 ms | Yes |
| Rate 8 FCFS Mean TTFT | 67,579 ± 1,577 ms | 67,579.1 ± 1,577.2 ms | Yes |
| Rate 8 FCFS P99 TTFT | 153,551 ± 3,149 ms | 153,550.7 ± 3,149.3 ms | Yes |
| Rate 8 LTR Mean TTFT (Seed 1) | 36,863 ± 0 ms | 36,863.0 ± 0.0 ms | Yes |
| Rate 8 LTR P99 TTFT (Seed 1) | 158,825 ± 0 ms | 158,824.7 ± 0.0 ms | Yes |
| Rate 8 V1 Mean TTFT | 59,764 ± 1,165 ms | 59,764.4 ± 1,164.5 ms | Yes |
| Rate 8 V1 P99 TTFT | 148,386 ± 5,119 ms | 148,385.8 ± 5,119.0 ms | Yes |

## Conclusion

All numbers quoted in `docs/experiments/2026-06-21-aging-gate-validation.md` match the underlying raw benchmark JSON data exactly.
