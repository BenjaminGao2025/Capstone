#!/usr/bin/env python3
"""Build a prompt -> score file for the cache-aware scheduling idea.

This script is intentionally simple. It combines the existing LTR score with
a shared-prefix cache bonus:

    final_score = LTR_score + cache_weight * cache_bonus

The output JSON can be used by the existing FileAuxScorer path through
IPT_SCORE_FILE.
"""

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


def get_prefix(text, prefix_words):
    words = clean_text(text).split()
    return " ".join(words[:prefix_words])


def zscore(values):
    values = [float(value) for value in values]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    std = math.sqrt(variance)

    if std == 0:
        return [0.0 for _ in values]

    return [(value - mean) / std for value in values]


def load_prompts(trace_path, num_requests):
    prompts = []

    with open(trace_path) as file:
        for line in file:
            row = json.loads(line)
            prompt = row.get("prompt")

            if prompt is None:
                continue

            prompts.append(prompt)

            if len(prompts) >= num_requests:
                break

    return prompts


def load_ltr_scores(result_path, num_requests):
    with open(result_path) as file:
        result = json.load(file)

    for key in ["pred_scores", "aux_model_scores"]:
        if key not in result or len(result[key]) < num_requests:
            continue

        scores = result[key][:num_requests]
        if all(score is not None for score in scores):
            return [float(score) for score in scores], key

    raise ValueError("No usable pred_scores or aux_model_scores found.")


def build_score_file(args):
    prompts = load_prompts(args.trace, args.num_requests)
    if not prompts:
        raise SystemExit("No prompts loaded. Check --trace.")

    ltr_scores, score_source = load_ltr_scores(args.result_json, len(prompts))
    ltr_scores = zscore(ltr_scores)

    prefixes = [get_prefix(prompt, args.prefix_words) for prompt in prompts]
    prefix_counts = Counter(prefixes)

    raw_cache_bonus = []
    for prefix in prefixes:
        group_size = prefix_counts[prefix]
        bonus = math.log1p(group_size - 1) * args.prefix_words
        raw_cache_bonus.append(bonus)

    cache_bonus = zscore(raw_cache_bonus)

    final_scores = []
    for ltr_score, bonus in zip(ltr_scores, cache_bonus):
        final_scores.append(ltr_score + args.cache_weight * bonus)

    score_table = dict(zip(prompts, final_scores))

    output_dir = os.path.dirname(args.out)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.out, "w") as file:
        json.dump(score_table, file)

    hit_count = sum(1 for prefix in prefixes if prefix_counts[prefix] > 1)

    print("wrote:", args.out)
    print("num_scores:", len(score_table))
    print("score_source:", score_source)
    print("prefix_words:", args.prefix_words)
    print("cache_weight:", args.cache_weight)
    print("cache_hit_rate:", hit_count / len(prompts))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--result-json", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--num-requests", type=int, default=500)
    parser.add_argument("--prefix-words", type=int, default=16)
    parser.add_argument("--cache-weight", type=float, default=1.0)
    return parser.parse_args()


if __name__ == "__main__":
    build_score_file(parse_args())
