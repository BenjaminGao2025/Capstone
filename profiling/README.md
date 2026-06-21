# vLLM Latency Profiling

This folder is for collecting real latency measurements that can replace the synthetic latency model in the reproduction scripts.

## Current Purpose

Run a small grid of vLLM requests and export:

```text
vllm_latency_profile.csv
```

Each row records measured latency for a specific:

- input token bucket
- output token bucket
- batch size
- repeat number

## Run

Example:

```powershell
cd "G:\Documents\6806 Capstone\profiling"
python .\run_vllm_profile.py --model meta-llama/Meta-Llama-3-8B-Instruct
```

For a smaller local test model:

```powershell
python .\run_vllm_profile.py --model facebook/opt-125m
```

## Output Columns

- `model`
- `input_bucket`
- `output_bucket`
- `batch_size`
- `repeat`
- `actual_prompt_tokens`
- `requested_output_tokens`
- `total_time_sec`
- `time_per_request_sec`
- `cache_mode`

## Notes

This script requires vLLM to be installed in the Python environment where it is run.

The current Codex environment does not have vLLM installed, so this script is prepared for your local vLLM environment.
