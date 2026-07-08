# Crash Artifacts from 6/21 Validation

The following JSON artifacts recorded ~0s latencies because the engine crashed and the benchmark harness erroneously flushed failed requests as 0 latency. These are kept for diagnostic purposes only.

- `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260621-091831-ood-sharegpt-aging-val.json`: [CRASH-ARTIFACT 15/500] (OOD r8 LTR)
- `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-20260621-092022-ood-sharegpt-aging-val.json`: [CRASH-ARTIFACT 15/500] (OOD r8 LTR+aging120s)
- preempt_sweep.log runs (Gate tuning Phase 1 without preemption protection, all CRASH-ARTIFACTs):
  - `vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-20260621-105324.json`: [CRASH-ARTIFACT 190/500]
  - `vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-20260621-111404.json`: [CRASH-ARTIFACT 130/500]
  - `vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-20260621-112004.json`: [CRASH-ARTIFACT 83/500]
  - `vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-aging-xxx-20260621-112243.json`: [CRASH-ARTIFACT 183/500]
