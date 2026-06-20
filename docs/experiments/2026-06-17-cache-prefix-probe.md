# Yuhjen Cache-Aware Scheduling Probe

Date: 2026-06-17

## My Method Status

My contribution is a small cache-aware scheduling method that can be tested
without running the full large-model serving experiment. Instead of changing
vLLM first, I start with an offline probe: read a request trace, detect whether
multiple prompts share the same prefix, and turn that prefix reuse into an
extra scheduling score.

The method keeps the base LTR idea, but adds my own cache signal:

```text
final_score = normalized_ltr_score + cache_weight * normalized_cache_bonus
```

This is not a large-model result yet. It is a reproducible method prototype
that shows how my cache-aware idea can be measured first and then passed into a
future serving run through a score file.

## Goal

The goal is to connect my related-work direction on shared prefixes and KV
cache reuse to the team's scheduler experiment. The base LTR scheduler ranks
requests using predicted output length. My method asks a different question:

> If two or more requests share the same beginning context, should the scheduler
> give them a small priority bonus because they may create cache-reuse value?

Base paper signal:

- predicted output length / LTR score

My added signal:

- shared-prefix or cache-reuse opportunity

The high-level idea is still simple:

```text
final_score = LTR_score + cache_bonus
```

If a request is predicted to be short, the LTR score already helps it run
earlier. If the same request also shares a prefix with other requests, my
method adds a small cache bonus.

## Why This Is My Direction

This method comes from the related-work thread I worked on: shared prefixes are
important in LLM serving, especially for chatbots, RAG, agents, tool-use
prompts, and repeated system prompts.

- Hydragen shows that shared prefixes can affect inference efficiency.
- CacheGen and CachedAttention show that cache reuse and repeated context have
  real latency cost.
- vLLM-LTR focuses on scheduling by predicted output length, but does not
  directly use shared-prefix reuse as a scheduling feature.

My method turns that shared-prefix observation into a scheduler-level feature.
It is smaller than implementing a full cache system, but it is something I can
code, test, and hand to the teammate who has the large-model environment.

## What the Script Does

Script:

```text
scripts/cache_prefix_probe.py
```

The script:

1. Loads prompts from a trace file.
2. Normalizes each prompt and extracts the first N words as its prefix.
3. Counts how many requests share each prefix.
4. Gives a larger cache bonus to requests whose prefix appears more than once.
5. Optionally combines this cache bonus with the original LTR scores from an
   existing result JSON.
6. Reports rank-correlation and SJF-quality style diagnostics.

This is an offline probe. It does not change vLLM and does not require GPU.

Second script:

```text
scripts/build_cache_aware_score_file.py
```

This script converts my final score into a prompt-to-score JSON file. That file
can be passed into the existing scheduler integration through `IPT_SCORE_FILE`,
so the method has a concrete path from offline prototype to later GPU serving
experiment.

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

## What This Contributes

This contribution is different from the team's large reproduction run. It does
not claim that cache-aware scheduling is faster yet. What it contributes is:

- a concrete cache-aware scoring rule;
- a script that measures prefix reuse in a trace;
- a script that exports cache-aware scheduler scores;
- a no-GPU smoke test that other teammates can rerun;
- a clear next step for a teammate with the CUDA vLLM-LTR environment.

This lets me contribute code and methodology now, even before I can run the
large model myself.

## Limitation

This probe does not prove end-to-end latency improvement yet. It only checks
whether the cache-aware idea is measurable and easy to plug into the scheduler.
The cache bonus can also hurt if prefix reuse does not align with shorter
latency or better batching. A real serving experiment is required before making
any performance claim.

## Next Step

The next experimental step is to run one controlled serving comparison:

```text
FCFS vs original LTR vs cache-aware LTR
```

The minimum useful setting is one in-distribution LMSYS run at rate 8 with 500
requests, using the same environment as the formal Llama-3-8B reproduction.
If that run shows no latency improvement, the method should be reported as an
offline negative result rather than expanded into a larger sweep.
