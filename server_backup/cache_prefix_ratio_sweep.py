#!/usr/bin/env python3
"""Measure cache-prefix opportunity as the shared-prefix ratio changes.

The sweep constructs controlled traces with the same number of requests but
different fractions of shared setup prompts. It is meant to answer a narrow
method question: how much reusable-prefix structure is visible to the
cache-aware scoring rule?
"""

import argparse
import json
import os
from collections import Counter


RATIOS = [0.0, 0.25, 0.50, 0.75, 1.0]
PREFIX_WORDS = 6
TOTAL_REQUESTS = 40
GROUP_SIZE = 5


def clean(text):
    return " ".join(text.lower().split())


def prefix_key(prompt, words=PREFIX_WORDS):
    return " ".join(clean(prompt).split()[:words])


def build_prompts(shared_ratio):
    shared_requests = int(TOTAL_REQUESTS * shared_ratio)
    shared_requests = shared_requests - (shared_requests % GROUP_SIZE)
    unique_requests = TOTAL_REQUESTS - shared_requests

    prompts = []
    for group in range(shared_requests // GROUP_SIZE):
        base = f"agent workflow shared setup group {group} tool catalog policy context"
        for item in range(GROUP_SIZE):
            prompts.append(f"{base} user task variant {item} specific question {group}-{item}")

    for item in range(unique_requests):
        prompts.append(
            f"solo{item} independent request topic {item * 7} wording {item * 11} context {item * 13}"
        )

    return prompts


def stats_for(prompts):
    prefixes = [prefix_key(prompt) for prompt in prompts]
    counts = Counter(prefixes)
    reused_requests = sum(1 for prefix in prefixes if counts[prefix] > 1)
    reused_groups = sum(1 for count in counts.values() if count > 1)
    return {
        "total_requests": len(prompts),
        "prefix_words": PREFIX_WORDS,
        "unique_prefixes": len(counts),
        "reused_prefix_groups": reused_groups,
        "requests_with_reused_prefix": reused_requests,
        "cache_hit_rate": reused_requests / len(prompts),
        "max_group_size": max(counts.values()),
    }


def render_svg(report):
    width = 980
    height = 500
    left = 92
    top = 78
    plot_width = 610
    plot_height = 270
    rows = report["rows"]

    def x_for(index):
        if len(rows) == 1:
            return left + plot_width / 2
        return left + index * plot_width / (len(rows) - 1)

    def y_for(value):
        return top + (1 - value) * plot_height

    points = " ".join(
        f"{x_for(i):.1f},{y_for(row['cache_hit_rate']):.1f}" for i, row in enumerate(rows)
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="92" y="36" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">Shared-prefix ratio sweep</text>',
        '<text x="92" y="59" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">Controlled trace-level analysis of cache-aware scheduling opportunity.</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#9ca3af"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#9ca3af"/>',
    ]

    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = y_for(tick)
        parts.append(f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">{tick:.2f}</text>')

    parts.append(f'<polyline points="{points}" fill="none" stroke="#7c3aed" stroke-width="4"/>')

    for i, row in enumerate(rows):
        x = x_for(i)
        y = y_for(row["cache_hit_rate"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#7c3aed"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_height + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{int(row["shared_ratio"] * 100)}%</text>')
        parts.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#4c1d95">{row["cache_hit_rate"]:.2f}</text>')

    parts.extend([
        f'<text x="{left + plot_width / 2}" y="{height - 92}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#374151">target shared-prefix ratio</text>',
        '<text x="740" y="115" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">Measured fields</text>',
        '<text x="740" y="140" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">cache_hit_rate</text>',
        '<text x="740" y="160" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">reused_prefix_groups</text>',
        '<text x="740" y="180" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">max_group_size</text>',
        '<text x="92" y="444" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">As the controlled workload contains more shared setup prompts, the cache-aware signal observes more reusable-prefix opportunity.</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--svg-out", required=True)
    args = parser.parse_args()

    rows = []
    for ratio in RATIOS:
        prompts = build_prompts(ratio)
        row = stats_for(prompts)
        row["shared_ratio"] = ratio
        rows.append(row)

    report = {
        "total_requests": TOTAL_REQUESTS,
        "prefix_words": PREFIX_WORDS,
        "group_size": GROUP_SIZE,
        "rows": rows,
    }

    for path in [args.json_out, args.svg_out]:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    with open(args.json_out, "w") as file:
        json.dump(report, file, indent=2)
    with open(args.svg_out, "w") as file:
        file.write(render_svg(report))

    print("wrote:", args.json_out)
    print("wrote:", args.svg_out)


if __name__ == "__main__":
    main()
