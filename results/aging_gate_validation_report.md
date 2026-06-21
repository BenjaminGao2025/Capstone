# Aging-Gate Mitigation Validation Report

## Environment & Configuration
- **Hardware**: RTX 3090 24GB (Note: This is a separate hardware run from the previously committed diagnostic numbers. FCFS p99=110s is the baseline for this specific run.)
- **vLLM Version**: 0.4.1 (pinned commit 13bbf6ff)
- **PyTorch**: 2.2.1+cu121
- **Trace**: ShareGPT (Out-of-Distribution, predictors trained on LMSYS)
- **Settings**: `SWAP_SPACE=4`, `AGING_GATE_S=120`

## 1. Rate-4 Validation (The "Red Line" Checks)

The results at Request Rate = 4 perfectly align with the theoretical baseline and reproduce the OOD performance degradation of pure LTR. However, the aging gate at 120s fails to meet the strict FCFS baseline criterion.

| Scheduler | Mean TTFT (ms) | P99 TTFT (ms) | Notes |
| :--- | :--- | :--- | :--- |
| **FCFS** | 49,599 | **110,355** | Baseline |
| **LTR (opt)** | 24,254 | 156,161 | Mean TTFT improved (~2x), but P99 severely worsened (starvation). |
| **LTR+aging (120s)** | 27,354 | **120,292** | **FAIL!** P99 is 120.3s, which is **9% worse** than FCFS (110.4s). |

*Note: While LTR+aging recovers most of the LTR-induced P99 regression (156s -> 120s), it does not reach the required FCFS baseline (<= 110s).*

## 2. Rate-8 Stress Test (Preemption Churn / Swap Exhaustion)

At Request Rate = 8, the system is subjected to extreme load, highlighting the swap exhaustion vulnerability when shorter requests continuously preempt running ones.

- **FCFS**: **Completed successfully.** (Mean TTFT = ~69s, P99 TTFT = ~158s). Pure FCFS has no preemption, hence no swap churn.
- **LTR (opt)**: **Crashed as expected.** The engine aborted due to `RuntimeError: Aborted due to the lack of CPU swap space`.
- **LTR+aging (120s)**: **Crashed.** The engine also aborted with the exact same CPU swap space exhaustion error.

### Structural Vulnerability Analysis
The `AGING_GATE_S=120` threshold is too loose for Rate=8. However, there is a **structural limitation**: the current aging gate only reorders the *waiting queue*. The Rate-8 crash is driven by *preemption churn* (new short requests constantly preempting already running requests and forcing them into swap). Since the gate does not explicitly prevent new arrivals from preempting running requests, modifying the wait-queue sorting may be structurally unable to prevent swap exhaustion at extreme loads.

## Final Verdict
**FAIL (Partial Mitigation).** 
The aging gate at 120s is ineffective against the predefined strict red lines:
1. FAILS criterion (a): P99 (120.3s) is worse than FCFS (110.4s).
2. FAILS criterion (b): Does not survive the Rate-8 stress test.

*Next Steps:* Perform a threshold sweep (`AGING_GATE_S` = 30s, 60s) at Rate-4 to see if a tighter gate can satisfy the FCFS P99 red line without destroying the mean TTFT. If successful, test survival at Rate-8. If all fail, the hypothesis is negative (pure waiting-queue sorting is insufficient to cure OOD starvation/churn).
