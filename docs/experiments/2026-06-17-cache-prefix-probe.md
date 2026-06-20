# Cache-Aware Scheduling Probe

Date: 2026-06-17

## Current Status

The cache-aware scheduling work is at the offline-probe stage. It does not
require a GPU and does not run the full vLLM serving engine. The committed
artifact is a reproducible method for testing whether shared-prefix reuse can
be added to the existing LTR scheduler signal:

```text
final_score = normalized_ltr_score + cache_weight * normalized_cache_bonus
```

This is intentionally a small, honest step before a large-model run. It checks
whether the cache signal exists in a trace, whether it changes request ranking,
and whether the resulting score table can be exported for the existing
`IPT_SCORE_FILE` path.

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

Second script:

```text
scripts/build_cache_aware_score_file.py
```

This script converts the same scoring idea into a prompt-to-score JSON file.
That file can be passed into the scheduler integration through the existing
`IPT_SCORE_FILE` route, so the offline method has a clear path into a later
serving experiment.

## Smoke Check

The repository includes a tiny hand-written demo trace and a tiny baseline LTR
score file:

```text
results/cache-prefix-probe-demo-trace.jsonl
results/cache-prefix-probe-demo-ltr.json
```

Run from this repository root:

```bash
python3 scripts/cache_prefix_probe.py \
  --trace results/cache-prefix-probe-demo-trace.jsonl \
  --result-json results/cache-prefix-probe-demo-ltr.json \
  --n 8 \
  --prefix-words 6 10 \
  --weights 0.1 0.5 1.0 \
  --out results/cache-prefix-probe-demo-output.json
```

Expected behavior:

- the script should load all 8 requests;
- the travel-agent and coding-tutor requests should be detected as repeated
  prefix groups;
- the output JSON should include `cache_only`, `base_ltr`, `combined`, and
  `best_combined_result` fields.

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

## Reproduction Notes

This method follows the same repository pattern as the larger Llama-3-8B
experiments:

- method documentation lives under `docs/experiments/`;
- runnable code lives under `scripts/`;
- committed smoke artifacts live under `results/`;
- large-model claims are separated from offline method checks.

For the full large-model experiment, a teammate with the CUDA vLLM-LTR
environment can run the probe against the real LMSYS or ShareGPT trace and then
use `scripts/build_cache_aware_score_file.py` to create the score table for a
serving run.

## Limitation

This probe does not prove end-to-end latency improvement yet. It only checks
whether the cache-aware idea is worth trying in the scheduler. A real serving
experiment would be the next step.

## Next Step

The next experimental step is to run one controlled serving comparison:

```text
FCFS vs original LTR vs cache-aware LTR
```

The minimum useful setting is one in-distribution LMSYS run at rate 8 with 500
requests, using the same environment as the formal Llama-3-8B reproduction.
If that run shows no latency improvement, the method should be reported as an
offline negative result rather than expanded into a larger sweep.
