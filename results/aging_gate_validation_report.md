# Aging-Gate Mitigation Validation Report

## Environment & Configuration
- **Hardware**: RTX 3090 24GB (Note: This is a separate hardware run from the previously committed diagnostic numbers. FCFS p99=110s is the baseline for this specific run.)
- **vLLM Version**: 0.4.1 (pinned commit 13bbf6ff)
- **PyTorch**: 2.2.1+cu121
- **Trace**: ShareGPT (Out-of-Distribution, predictors trained on LMSYS)
- **Settings**: `SWAP_SPACE=4`, `AGING_GATE_S` Sweeps (30s, 60s, 120s)

## 1. Rate-4 Validation (The "Red Line" Checks)

The results at Request Rate = 4 perfectly align with the theoretical baseline and reproduce the OOD performance degradation of pure LTR. A sweep over `AGING_GATE_S` reveals that tighter thresholds (30s, 60s) successfully satisfy the strict FCFS baseline criterion.

| Scheduler | Mean TTFT (ms) | P99 TTFT (ms) | Notes |
| :--- | :--- | :--- | :--- |
| **FCFS** | 49,599 | **110,355** | Baseline |
| **LTR (opt)** | 24,254 | 156,161 | Mean TTFT improved (~2x), but P99 severely worsened (starvation). |
| **LTR+aging (120s)** | 27,354 | 120,292 | **FAIL!** P99 is 120.3s, which is **9% worse** than FCFS. |
| **LTR+aging (60s)** | 33,837 | **105,472** | **PASS!** P99 <= FCFS, and Mean TTFT is 1.46x faster than FCFS. |
| **LTR+aging (30s)** | 40,561 | **101,199** | **PASS!** P99 <= FCFS, and Mean TTFT is 1.22x faster than FCFS. |

*Note: Tighter thresholds effectively suppress the P99 tail below the FCFS baseline while still providing significant mean TTFT speedups (1.2x - 1.4x).*

## 2. Rate-8 Stress Test (Preemption Churn / Swap Exhaustion)

At Request Rate = 8, the system is subjected to extreme load, highlighting the swap exhaustion vulnerability when shorter requests continuously preempt running ones.

- **FCFS**: **Completed successfully.** (Mean TTFT = ~69s, P99 TTFT = ~158s). Pure FCFS has no preemption, hence no swap churn.
- **LTR (opt)**: **Crashed as expected.** The engine aborted due to `RuntimeError: Aborted due to the lack of CPU swap space`.
- **LTR+aging (30s, 60s, 120s)**: **Crashed.** The engine aborted with the exact same CPU swap space exhaustion error across all tested thresholds.

### Structural Vulnerability Analysis
Even at the tightest passing threshold (`AGING_GATE_S=30s`), LTR+aging still crashes at Rate-8. This confirms a **structural limitation**: the current aging gate only reorders the *waiting queue*. The Rate-8 crash is driven by *preemption churn* (new short requests constantly preempting already running requests and forcing them into swap). Since the gate does not explicitly prevent new arrivals from preempting running requests, sorting the wait-queue is structurally unable to prevent swap exhaustion at extreme loads.

## Final Verdict
**FAIL / Partial Mitigation.** 
The aging gate succeeds at mitigating tail latency under moderate OOD overload (Rate 4) if the threshold is carefully tuned (e.g., 30s or 60s). However, it structurally fails to prevent swap exhaustion under extreme overload (Rate 8) because it does not govern the running-request preemption dynamics.
