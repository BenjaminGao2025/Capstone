# Cache-Aware Scheduling Probe

Date: 2026-06-17

## Goal

This is a lightweight experiment inspired by CacheGen and CachedAttention. The
goal is not to implement those systems directly. Instead, we test whether a
simple cache-related signal can be added to the base paper's LTR scheduler.

Base paper signal:

- predicted output length / LTR score

Proposed extra signal:

- shared-prefix or cache-reuse opportunity

The high-level idea is:

```text
final_score = LTR_score + cache_bonus
```

If a request is predicted to be short, it already receives a high LTR priority.
If it also shares a prefix with other requests, we add a small cache bonus.

## Why This Relates to CacheGen and CachedAttention

- CacheGen shows that even reused KV cache can be expensive to load.
- CachedAttention shows that recomputing old context in multi-turn chat is
  wasteful.
- Both papers suggest that latency is not only about request ordering or output
  length. Cache reuse and repeated context also matter.

This probe turns that related-work idea into a scheduler-level feature.

## What the Script Does

Script:

```text
scripts/cache_prefix_probe.py
```

The script:

1. Loads the same trace prompts used by the vLLM-LTR experiments.
2. Groups requests by normalized prompt prefix.
3. Computes a cache bonus for prefixes that appear more than once.
4. Optionally combines this cache bonus with the original LTR scores from an
   existing result JSON.
5. Reports rank-correlation and SJF-quality style diagnostics.

This is an offline probe. It does not change vLLM and does not require GPU.

## Example Commands

In-distribution LMSYS:

```bash
cd /hy-tmp/vllm-ltr/benchmarks
python3 /hy-tmp/scripts/cache_prefix_probe.py \
  --trace lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl \
  --result-json /hy-tmp/results/llama3-8b/vllm-8.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260611-104730.json \
  --out /hy-tmp/results/cache-prefix-probe-lmsys.json
```

OOD ShareGPT:

```bash
cd /hy-tmp/vllm-ltr/benchmarks
python3 /hy-tmp/scripts/cache_prefix_probe.py \
  --trace llama3-8b-sharegpt-test-t1-s0-8192.jsonl \
  --result-json /hy-tmp/results/llama3-8b/vllm-4.0qps-cv1.0-Meta-Llama-3-8B-Instruct-opt-xxx-20260611-113821-ood-sharegpt.json \
  --out /hy-tmp/results/cache-prefix-probe-sharegpt.json
```

## How to Read the Result

Important fields:

- `requests_with_reused_prefix`: how many requests share a prefix with another
  request.
- `cache_only`: whether the cache signal alone correlates with true output
  length.
- `base_ltr`: original LTR ranking quality.
- `combined`: LTR score plus cache bonus.
- `best_combined_by_sjf_quality`: best tested cache weight.

The signal is promising if:

- the combined score improves over `base_ltr`, especially on OOD data, or
- it does not improve rank correlation but shows many reused-prefix opportunities,
  which means it may still be useful for TTFT/prefill latency in a real serving
  experiment.

## Limitation

This probe does not prove end-to-end latency improvement yet. It only checks
whether the cache-aware idea is worth trying in the scheduler. A real serving
experiment would be the next step.
