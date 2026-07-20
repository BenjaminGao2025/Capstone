#!/usr/bin/env python3
"""Generate a controlled offline sweep for the cache-prefix idea.

No model or serving engine is used. The sweep only measures how much
shared-prefix opportunity exists under different synthetic workload shapes.
"""

import argparse
import json
import os
from collections import Counter


PREFIX_WORDS = [2, 4, 6, 8, 10, 12]


def clean(text):
    return " ".join(text.lower().split())


def prefix_key(prompt, words):
    return " ".join(clean(prompt).split()[:words])


def cache_stats(prompts, words):
    prefixes = [prefix_key(prompt, words) for prompt in prompts]
    counts = Counter(prefixes)
    reused = sum(1 for prefix in prefixes if counts[prefix] > 1)
    groups = sum(1 for count in counts.values() if count > 1)
    return {
        "prefix_words": words,
        "unique_prefixes": len(counts),
        "reused_prefix_groups": groups,
        "requests_with_reused_prefix": reused,
        "cache_hit_rate": reused / len(prompts),
        "max_group_size": max(counts.values()),
    }


def build_workloads():
    agent_base = "agent system prompt tools calendar email files browser task"
    rag_base = "rag assistant policy document retrieval answer with citations"
    code_base = "coding assistant repository context unit tests explain bug"
    support_base = "support assistant customer ticket order refund shipping"

    shared_agent = []
    for base in [agent_base, rag_base, code_base, support_base]:
        for i in range(8):
            shared_agent.append(f"{base} user request variant {i} with short task details")

    mixed = []
    for base in [agent_base, rag_base, code_base, support_base]:
        for i in range(4):
            mixed.append(f"{base} user request variant {i} with short task details")
    for i in range(16):
        mixed.append(f"solo{i} independent topic {i * 7} wording {i * 13} no shared setup")

    random_like = []
    for i in range(32):
        random_like.append(
            f"random{i} topic {i * 11} wording {i * 17} context {i * 23} task {i * 29}"
        )

    return {
        "agent_shared_prefix": shared_agent,
        "mixed_prefix": mixed,
        "random_like": random_like,
    }


def render_svg(report):
    width = 980
    height = 520
    left = 90
    top = 86
    plot_width = 610
    plot_height = 285
    colors = {
        "agent_shared_prefix": "#2563eb",
        "mixed_prefix": "#16a34a",
        "random_like": "#dc2626",
    }
    labels = {
        "agent_shared_prefix": "agent-style shared prefixes",
        "mixed_prefix": "mixed workload",
        "random_like": "random-like prompts",
    }

    def x_for(index):
        return left + index * plot_width / (len(PREFIX_WORDS) - 1)

    def y_for(value):
        return top + (1.0 - value) * plot_height

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="90" y="38" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#111827">Cache-prefix opportunity by workload shape</text>',
        '<text x="90" y="62" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">Controlled synthetic sweep of shared-prefix opportunity for cache-aware scheduling.</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#9ca3af"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#9ca3af"/>',
    ]

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_for(tick)
        parts.append(f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">{tick:.2f}</text>')

    for i, words in enumerate(PREFIX_WORDS):
        x = x_for(i)
        parts.append(f'<text x="{x:.1f}" y="{top + plot_height + 27}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{words}</text>')

    for workload, rows in report["workloads"].items():
        points = []
        for i, row in enumerate(rows):
            points.append(f'{x_for(i):.1f},{y_for(row["cache_hit_rate"]):.1f}')
        parts.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{colors[workload]}" stroke-width="3"/>')
        for i, row in enumerate(rows):
            parts.append(f'<circle cx="{x_for(i):.1f}" cy="{y_for(row["cache_hit_rate"]):.1f}" r="5" fill="{colors[workload]}"/>')

    legend_x = 735
    legend_y = 105
    for i, workload in enumerate(["agent_shared_prefix", "mixed_prefix", "random_like"]):
        y = legend_y + i * 30
        parts.append(f'<rect x="{legend_x}" y="{y - 11}" width="14" height="14" fill="{colors[workload]}"/>')
        parts.append(f'<text x="{legend_x + 24}" y="{y}" font-family="Arial, sans-serif" font-size="13" fill="#374151">{labels[workload]}</text>')

    parts.extend([
        f'<text x="{left + plot_width / 2}" y="{height - 92}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#374151">prefix_words</text>',
        '<text x="90" y="450" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">Reading the chart</text>',
        '<text x="90" y="472" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">High cache_hit_rate means many requests share a prefix and the cache-aware scheduler has something to exploit.</text>',
        '<text x="90" y="492" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">Near-zero cache_hit_rate means the method should not claim an advantage; there is little shared-prefix structure.</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--svg-out", required=True)
    args = parser.parse_args()

    workloads = build_workloads()
    report = {"prefix_words": PREFIX_WORDS, "workloads": {}}
    for name, prompts in workloads.items():
        report["workloads"][name] = [cache_stats(prompts, words) for words in PREFIX_WORDS]

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
