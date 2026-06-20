#!/usr/bin/env python3
"""Summarize shared-prefix reuse for an LMSYS-style JSONL trace."""

import argparse
import json
import math
import os
import re
from collections import Counter


def clean_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_prompt(row):
    prompt = (
        row.get("prompt")
        or row.get("input")
        or row.get("text")
        or row.get("conversation")
        or row.get("conversations")
    )

    if isinstance(prompt, list):
        parts = []
        for item in prompt:
            if isinstance(item, dict):
                parts.append(str(item.get("value") or item.get("content") or item))
            else:
                parts.append(str(item))
        prompt = " ".join(parts)

    return None if prompt is None else str(prompt)


def extract_output_length(row):
    output_length = (
        row.get("output_len")
        or row.get("output_length")
        or row.get("answer_len")
        or row.get("response_len")
        or row.get("completion_tokens")
    )
    return None if output_length is None else int(output_length)


def load_requests(trace_path, limit):
    requests = []
    with open(trace_path) as file:
        for line in file:
            if not line.strip():
                continue
            row = json.loads(line)
            prompt = extract_prompt(row)
            output_length = extract_output_length(row)
            if prompt is None:
                continue
            requests.append((prompt, output_length))
            if len(requests) >= limit:
                break
    return requests


def prefix_for(prompt, prefix_words):
    return " ".join(clean_text(prompt).split()[:prefix_words])


def standardize(numbers):
    if not numbers:
        return []
    numbers = [float(x) for x in numbers]
    mean = sum(numbers) / len(numbers)
    variance = sum((x - mean) ** 2 for x in numbers) / len(numbers)
    std = math.sqrt(variance)
    if std == 0:
        return [0.0 for _ in numbers]
    return [(x - mean) / std for x in numbers]


def simple_rank(values):
    sorted_index = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0] * len(values)
    for rank, original_index in enumerate(sorted_index):
        ranks[original_index] = rank
    return ranks


def correlation(x_values, y_values):
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
    if not scores or not output_lengths or len(scores) != len(output_lengths):
        return None
    if min(scores) == max(scores):
        return None
    score_ranks = simple_rank(scores)
    length_ranks = simple_rank(output_lengths)
    rank_corr = correlation(score_ranks, length_ranks)
    if rank_corr is None:
        return None
    return -rank_corr


def summarize(prompts, output_lengths, prefix_words):
    prefixes = [prefix_for(prompt, prefix_words) for prompt in prompts]
    counts = Counter(prefixes)
    group_sizes = [counts[prefix] for prefix in prefixes]
    raw_bonus = [math.log1p(group_size - 1) * prefix_words for group_size in group_sizes]
    complete_output_lengths = all(output_length is not None for output_length in output_lengths)
    cache_only_quality = None
    if complete_output_lengths:
        cache_only_quality = ranking_quality(standardize(raw_bonus), output_lengths)
    reused_requests = sum(1 for size in group_sizes if size > 1)
    max_group_size = max(group_sizes) if group_sizes else 0
    cache_hit_rate = reused_requests / len(prompts) if prompts else 0.0

    return {
        "prefix_words": prefix_words,
        "cache_hit_rate": round(cache_hit_rate, 4),
        "reused_requests": reused_requests,
        "reused_prefix_groups": sum(1 for count in counts.values() if count > 1),
        "largest_shared_group": max_group_size,
        "cache_only_quality": None if cache_only_quality is None else round(cache_only_quality, 3),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True, help="Path to the LMSYS JSONL trace.")
    parser.add_argument("--out", required=True, help="Summary JSON output path.")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--prefix-words", type=int, nargs="+", default=[16, 32, 64, 128])
    args = parser.parse_args()

    requests = load_requests(args.trace, args.limit)
    prompts = [request[0] for request in requests]
    output_lengths = [request[1] for request in requests]
    rows = [summarize(prompts, output_lengths, prefix_words) for prefix_words in args.prefix_words]
    best = max(rows, key=lambda row: row["cache_hit_rate"]) if rows else {}

    report = {
        "source": "local_offline_lmsys_trace_probe",
        "provenance": {
            "artifact_type": "trace_level_summary",
            "trace_path": args.trace,
            "trace_window": f"first {len(prompts)} LMSYS requests",
            "analysis": "shared-prefix reuse sweep",
            "script": "scripts/summarize_lmsys_prefix_reuse.py",
            "prefix_words": args.prefix_words,
        },
        "workload": f"first {len(prompts)} LMSYS requests",
        "method": "offline shared-prefix probe",
        "rows": rows,
        "best_prefix_words": best.get("prefix_words"),
        "best_cache_hit_rate": best.get("cache_hit_rate"),
        "best_reused_requests": best.get("reused_requests"),
        "largest_shared_group": best.get("largest_shared_group"),
        "best_cache_only_quality": best.get("cache_only_quality"),
        "interpretation": "Shared-prefix reuse is present when multiple requests share the same cleaned word prefix.",
    }

    output_folder = os.path.dirname(args.out)
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
    with open(args.out, "w") as file:
        json.dump(report, file, indent=2)
        file.write("\n")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
