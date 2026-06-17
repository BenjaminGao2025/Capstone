from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path


DEFAULT_INPUT_BUCKETS = [128, 512, 1024]
DEFAULT_OUTPUT_BUCKETS = [64, 128, 256]
DEFAULT_BATCH_SIZES = [1, 2, 4]


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def make_prompt(tokenizer, target_tokens: int) -> tuple[str, int]:
    base = "The following is a short request for an LLM serving benchmark. "
    filler = "latency scheduling cache inference "
    prompt = base

    while len(tokenizer.encode(prompt)) < target_tokens:
        prompt += filler

    token_ids = tokenizer.encode(prompt)
    # Decode the prefix back to a prompt close to the requested bucket.
    prompt = tokenizer.decode(token_ids[:target_tokens])
    actual_tokens = len(tokenizer.encode(prompt))
    return prompt, actual_tokens


def run_profile(
    model: str,
    input_buckets: list[int],
    output_buckets: list[int],
    batch_sizes: list[int],
    repeats: int,
    output_path: Path,
) -> None:
    try:
        from vllm import LLM, SamplingParams
    except Exception as exc:
        raise SystemExit(
            "vLLM is not installed in this Python environment. "
            "Install/run this script inside your vLLM environment.\n"
            f"Original error: {type(exc).__name__}: {exc}"
        )

    llm = LLM(model=model)
    tokenizer = llm.get_tokenizer()

    rows: list[dict[str, object]] = []
    prompt_cache: dict[int, tuple[str, int]] = {}

    for input_bucket in input_buckets:
        prompt_cache[input_bucket] = make_prompt(tokenizer, input_bucket)

    # Warm-up: one tiny request to initialize model/runtime overhead.
    warmup_params = SamplingParams(max_tokens=8, temperature=0.0)
    llm.generate([prompt_cache[input_buckets[0]][0]], warmup_params)

    for input_bucket in input_buckets:
        prompt, actual_prompt_tokens = prompt_cache[input_bucket]

        for output_bucket in output_buckets:
            sampling_params = SamplingParams(max_tokens=output_bucket, temperature=0.0)

            for batch_size in batch_sizes:
                prompts = [prompt for _ in range(batch_size)]
                timings: list[float] = []

                for repeat in range(repeats):
                    start = time.perf_counter()
                    llm.generate(prompts, sampling_params)
                    total_time = time.perf_counter() - start
                    timings.append(total_time)

                    rows.append(
                        {
                            "model": model,
                            "input_bucket": input_bucket,
                            "output_bucket": output_bucket,
                            "batch_size": batch_size,
                            "repeat": repeat,
                            "actual_prompt_tokens": actual_prompt_tokens,
                            "requested_output_tokens": output_bucket,
                            "total_time_sec": f"{total_time:.6f}",
                            "time_per_request_sec": f"{total_time / batch_size:.6f}",
                            "cache_mode": "kv",
                        }
                    )

                print(
                    "profiled "
                    f"input={input_bucket}, output={output_bucket}, batch={batch_size}: "
                    f"median_total={statistics.median(timings):.4f}s"
                )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote profile to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect vLLM latency profile data.")
    parser.add_argument("--model", required=True, help="Hugging Face model name or local model path.")
    parser.add_argument("--input-buckets", default="128,512,1024", help="Comma-separated input token buckets.")
    parser.add_argument("--output-buckets", default="64,128,256", help="Comma-separated output token buckets.")
    parser.add_argument("--batch-sizes", default="1,2,4", help="Comma-separated batch sizes.")
    parser.add_argument("--repeats", type=int, default=3, help="Number of repeats for each configuration.")
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "vllm_latency_profile.csv"),
        help="Output CSV path.",
    )
    args = parser.parse_args()

    run_profile(
        model=args.model,
        input_buckets=parse_int_list(args.input_buckets),
        output_buckets=parse_int_list(args.output_buckets),
        batch_sizes=parse_int_list(args.batch_sizes),
        repeats=args.repeats,
        output_path=Path(args.output),
    )


if __name__ == "__main__":
    main()
