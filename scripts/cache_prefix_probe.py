#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
from collections import Counter


def clean_text(text):
    """Lowercase text and collapse repeated spaces."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_prefix(prompt, num_words):
    """Return the first num_words words of a prompt."""
    words = clean_text(prompt).split()
    return " ".join(words[:num_words])


def standardize(numbers):
    """Convert a list of numbers to z-scores so scales are comparable."""
    numbers = [float(x) for x in numbers]
    mean = sum(numbers) / len(numbers)
    variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
    std = math.sqrt(variance)

    if std == 0:
        return [0.0 for _ in numbers]

    return [(x - mean) / std for x in numbers]


def simple_rank(values):
    """Return simple ranks. Smallest value gets rank 0."""
    sorted_index = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0] * len(values)
    for rank, original_index in enumerate(sorted_index):
        ranks[original_index] = rank
    return ranks


def correlation(x_values, y_values):
    """Compute a simple Pearson correlation."""
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)

    numerator = 0.0
    x_denominator = 0.0
    y_denominator = 0.0

    for x, y in zip(x_values, y_values):
        numerator += (x - x_mean) * (y - y_mean)
        x_denominator += (x - x_mean) ** 2
        y_denominator += (y - y_mean) ** 2

    if x_denominator == 0 or y_denominator == 0:
        return None

    return numerator / math.sqrt(x_denominator * y_denominator)


def ranking_quality(scores, output_lengths):
    """Measure whether high scores tend to mean shorter outputs.

    Higher scheduling score means "run earlier". For shortest-job-first style
    scheduling, high scores should match short output lengths. So a negative
    rank correlation is good.
    """
    score_ranks = simple_rank(scores)
    length_ranks = simple_rank(output_lengths)
    rank_corr = correlation(score_ranks, length_ranks)

    if rank_corr is None:
        return {"rank_corr": None, "sjf_quality": None}

    return {
        "rank_corr": rank_corr,
        "sjf_quality": -rank_corr,
    }


def load_trace_with_vllm_sampler(trace_path, num_requests, tokenizer_path):
    """Try to load requests using the same sampler as vLLM-LTR."""
    try:
        from transformers import AutoTokenizer
        from benchmark_serving_real import sample_requests

        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        return sample_requests(trace_path, num_requests, False, -1, -1, tokenizer, "opt-xxx")
    except Exception:
        # If transformers, benchmark_serving_real, or the tokenizer path is not
        # available, we use the simple JSONL loader below.
        return None


def load_trace_simple(trace_path, num_requests):
    """Fallback JSONL loader if the vLLM-LTR sampler is not available."""
    requests = []

    with open(trace_path) as file:
        for line in file:
            if not line.strip():
                continue

            row = json.loads(line)
            prompt = (
                row.get("prompt")
                or row.get("input")
                or row.get("text")
                or row.get("conversation")
                or row.get("conversations")
            )
            if isinstance(prompt, list):
                prompt_parts = []
                for item in prompt:
                    if isinstance(item, dict):
                        prompt_parts.append(str(item.get("value") or item.get("content") or item))
                    else:
                        prompt_parts.append(str(item))
                prompt = " ".join(prompt_parts)
            output_length = (
                row.get("output_len")
                or row.get("output_length")
                or row.get("answer_len")
                or row.get("response_len")
                or row.get("completion_tokens")
            )

            if prompt is None or output_length is None:
                continue

            requests.append((str(prompt), int(output_length)))

            if len(requests) >= num_requests:
                break

    return requests


def load_requests(trace_path, num_requests, tokenizer_path):
    """Return two lists: prompts and true output lengths."""
    sampled_requests = load_trace_with_vllm_sampler(trace_path, num_requests, tokenizer_path)

    if sampled_requests is not None:
        prompts = [request[0] for request in sampled_requests]
        output_lengths = [float(request[2]) for request in sampled_requests]
        return prompts, output_lengths

    simple_requests = load_trace_simple(trace_path, num_requests)
    prompts = [request[0] for request in simple_requests]
    output_lengths = [float(request[1]) for request in simple_requests]
    return prompts, output_lengths


def load_ltr_scores(result_json_path, num_requests):
    """Load original LTR scores from an existing vLLM result JSON."""
    if result_json_path is None:
        return None, None

    with open(result_json_path) as file:
        result = json.load(file)

    if "pred_scores" in result and len(result["pred_scores"]) >= num_requests:
        return [float(x) for x in result["pred_scores"][:num_requests]], "pred_scores"

    if "aux_model_scores" in result and len(result["aux_model_scores"]) >= num_requests:
        return [float(x) for x in result["aux_model_scores"][:num_requests]], "aux_model_scores"

    raise ValueError("Could not find pred_scores or aux_model_scores in result JSON.")


def compute_cache_bonus(prompts, prefix_words):
    """Give a larger bonus when more requests share the same prefix."""
    prefixes = [get_prefix(prompt, prefix_words) for prompt in prompts]
    prefix_count = Counter(prefixes)

    group_sizes = []
    for prefix in prefixes:
        group_sizes.append(prefix_count[prefix])

    raw_bonus = []
    for group_size in group_sizes:
        # If group_size is 1, this request has no repeated prefix, so bonus is 0.
        # If group_size is larger, this request may have more cache reuse value.
        bonus = math.log1p(group_size - 1) * prefix_words
        raw_bonus.append(bonus)

    cache_info = {
        "prefix_words": prefix_words,
        "unique_prefixes": len(prefix_count),
        "reused_prefix_groups": sum(1 for count in prefix_count.values() if count > 1),
        "requests_with_reused_prefix": sum(1 for size in group_sizes if size > 1),
        "cache_hit_rate": sum(1 for size in group_sizes if size > 1) / len(prompts),
        "max_group_size": max(group_sizes),
    }

    return standardize(raw_bonus), cache_info


def run_experiment(args):
    prompts, output_lengths = load_requests(args.trace, args.n, args.tokenizer)
    num_requests = len(prompts)

    if num_requests == 0:
        raise SystemExit("No requests loaded. Please check the trace path.")

    ltr_scores, score_source = load_ltr_scores(args.result_json, num_requests)

    report = {
        "trace": args.trace,
        "result_json": args.result_json,
        "num_requests": num_requests,
        "score_source": score_source,
        "results": [],
    }

    best_result = None

    for prefix_words in args.prefix_words:
        cache_bonus, cache_info = compute_cache_bonus(prompts, prefix_words)
        cache_info["cache_only"] = ranking_quality(cache_bonus, output_lengths)

        if ltr_scores is not None:
            normalized_ltr_scores = standardize(ltr_scores)
            cache_info["base_ltr"] = ranking_quality(normalized_ltr_scores, output_lengths)
            cache_info["combined"] = []

            for cache_weight in args.weights:
                combined_scores = []
                for ltr_score, bonus in zip(normalized_ltr_scores, cache_bonus):
                    combined_scores.append(ltr_score + cache_weight * bonus)

                combined_quality = ranking_quality(combined_scores, output_lengths)
                combined_result = {
                    "cache_weight": cache_weight,
                    "rank_corr": combined_quality["rank_corr"],
                    "sjf_quality": combined_quality["sjf_quality"],
                }
                cache_info["combined"].append(combined_result)

                if combined_result["sjf_quality"] is not None:
                    if best_result is None or combined_result["sjf_quality"] > best_result["sjf_quality"]:
                        best_result = {
                            "prefix_words": prefix_words,
                            "cache_weight": cache_weight,
                            "rank_corr": combined_result["rank_corr"],
                            "sjf_quality": combined_result["sjf_quality"],
                        }

        report["results"].append(cache_info)

    if best_result is not None:
        report["best_combined_result"] = best_result

    if args.out:
        output_folder = os.path.dirname(args.out)
        if output_folder:
            os.makedirs(output_folder, exist_ok=True)
        with open(args.out, "w") as file:
            json.dump(report, file, indent=2)

    print(json.dumps(report, indent=2))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, help="Path to trace JSONL file.")
    parser.add_argument("--result-json", default=None, help="Existing vLLM result JSON with LTR scores.")
    parser.add_argument("--tokenizer", default="/hy-tmp/models/Meta-Llama-3-8B-Instruct")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--prefix-words", type=int, nargs="+", default=[16, 32, 64, 128])
    parser.add_argument("--weights", type=float, nargs="+", default=[0.05, 0.1, 0.2, 0.5, 1.0])
    parser.add_argument("--out", default=None, help="Optional output JSON path.")
    return parser.parse_args()


if __name__ == "__main__":
    run_experiment(parse_args())
