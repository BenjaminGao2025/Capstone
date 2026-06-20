#!/usr/bin/env python3
"""Build the cache-prefix ranking ablation summary figure."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def rect_bar(x: int, y: int, width: int, height: int, fill: str) -> str:
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="6" fill="{fill}"/>'


def text(x: int, y: int, value: str, size: int = 18, weight: int = 400, fill: str = "#152238", anchor: str = "start") -> str:
    safe = (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        f'<text x="{x}" y="{y}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{safe}</text>'
    )


def make_summary(lmsys: dict, tau: dict, synthetic: dict) -> dict:
    best_lmsys = next(row for row in lmsys["rows"] if row["prefix_words"] == lmsys["best_prefix_words"])
    tau_lmsys = abs(tau["lmsys-score"]["lmsys"]["tau"])
    tau_sharegpt = abs(tau["lmsys-score"]["sharegpt"]["tau"])

    synthetic_rows = synthetic["results"]
    base_quality = synthetic_rows[0]["base_ltr"]["sjf_quality"]
    best_combined = synthetic["best_combined_result"]["sjf_quality"]
    high_weight_candidates = [
        combined["sjf_quality"]
        for row in synthetic_rows
        for combined in row["combined"]
        if combined["cache_weight"] == 1.0 and row["cache_hit_rate"] > 0
    ]
    high_weight_quality = min(high_weight_candidates) if high_weight_candidates else None

    return {
        "source": "committed_cache_prefix_ranking_ablation",
        "source_files": [
            "results/cache-prefix-lmsys-offline-summary.json",
            "results/llama3-8b/cross-tau-matrix.json",
            "results/cache-prefix-probe-synthetic-output.json",
        ],
        "lmsys_prefix_probe": {
            "prefix_words": best_lmsys["prefix_words"],
            "cache_hit_rate": best_lmsys["cache_hit_rate"],
            "reused_requests": best_lmsys["reused_requests"],
            "reused_prefix_groups": best_lmsys["reused_prefix_groups"],
            "largest_shared_group": best_lmsys["largest_shared_group"],
        },
        "cross_trace_ranking_quality": {
            "metric": "absolute Kendall tau for lmsys-score",
            "in_distribution_lmsys": tau_lmsys,
            "shifted_sharegpt": tau_sharegpt,
            "drop": tau_lmsys - tau_sharegpt,
        },
        "synthetic_cache_bonus_effect": {
            "metric": "SJF-quality rank diagnostic",
            "base_ltr": base_quality,
            "best_combined": best_combined,
            "best_delta": best_combined - base_quality,
            "weight_1_min_quality_when_cache_present": high_weight_quality,
        },
        "conclusion": "The cache-prefix signal finds reuse opportunity, but the committed ablation does not show a ranking-quality gain from adding the cache bonus; the OOD ranking drop remains.",
    }


def make_svg(summary: dict) -> str:
    width, height = 1280, 720
    bg = "#f7f9fc"
    ink = "#162033"
    muted = "#516173"
    blue = "#2f63e6"
    teal = "#18a999"
    orange = "#f59e0b"
    red = "#d94f4f"
    grid = "#dbe3ef"
    card = "#ffffff"

    lmsys = summary["lmsys_prefix_probe"]
    rank = summary["cross_trace_ranking_quality"]
    synth = summary["synthetic_cache_bonus_effect"]

    hit_rate = lmsys["cache_hit_rate"]
    tau_lmsys = rank["in_distribution_lmsys"]
    tau_shifted = rank["shifted_sharegpt"]
    base = synth["base_ltr"]
    best = synth["best_combined"]
    high_weight = synth["weight_1_min_quality_when_cache_present"]

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Cache-prefix ranking ablation">',
        f'<rect width="{width}" height="{height}" fill="{bg}"/>',
        text(80, 76, "Cache-Prefix Ranking Ablation", 34, 800, ink),
        text(80, 112, "Committed evidence: reusable LMSYS prefixes exist, but cache bonus is neutral or harmful for ranking quality.", 18, 400, muted),
    ]

    # Three report cards.
    cards = [
        (80, 150, 350, 360, "1  Trace opportunity", "RunPod LMSYS prefix probe"),
        (465, 150, 350, 360, "2  OOD ranking quality", "Kendall tau, lmsys-score"),
        (850, 150, 350, 360, "3  Cache-bonus effect", "Synthetic score ablation"),
    ]
    for x, y, w, h, title, subtitle in cards:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{card}" stroke="#ccd7e8"/>')
        out.append(text(x + 28, y + 45, title, 22, 800, ink))
        out.append(text(x + 28, y + 76, subtitle, 15, 500, muted))

    # Card 1: real trace prefix opportunity.
    bar_x, base_y, max_h = 170, 430, 210
    bar_h = int(max_h * hit_rate / 0.2)
    out.append(f'<line x1="125" y1="{base_y}" x2="385" y2="{base_y}" stroke="{grid}" stroke-width="2"/>')
    out.append(rect_bar(bar_x, base_y - bar_h, 92, bar_h, teal))
    out.append(text(bar_x + 46, base_y - bar_h - 18, fmt_pct(hit_rate), 24, 800, teal, "middle"))
    out.append(text(bar_x + 46, base_y + 32, "hit rate", 16, 600, muted, "middle"))
    out.append(text(118, 485, f'{lmsys["reused_requests"]} reused requests / 500', 17, 700, ink))
    out.append(text(118, 512, f'{lmsys["reused_prefix_groups"]} groups; largest group {lmsys["largest_shared_group"]}', 15, 500, muted))

    # Card 2: in-distribution vs shifted tau.
    chart_x, chart_y, chart_w, chart_h = 525, 242, 220, 190
    out.append(f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{grid}" stroke-width="2"/>')
    for i, (label, value, color) in enumerate([("LMSYS", tau_lmsys, blue), ("ShareGPT", tau_shifted, orange)]):
        h = int(chart_h * value / 0.75)
        x = chart_x + 26 + i * 100
        out.append(rect_bar(x, chart_y + chart_h - h, 64, h, color))
        out.append(text(x + 32, chart_y + chart_h - h - 14, f"{value:.3f}", 19, 800, color, "middle"))
        out.append(text(x + 32, chart_y + chart_h + 30, label, 15, 600, muted, "middle"))
    out.append(text(502, 485, f'Drop: {rank["drop"]:.3f} absolute tau', 17, 700, ink))
    out.append(text(502, 512, "Shifted trace remains harder for LTR.", 15, 500, muted))

    # Card 3: cache-bonus effect.
    effect_x, effect_y, effect_w, effect_h = 892, 242, 260, 190
    out.append(f'<line x1="{effect_x}" y1="{effect_y + effect_h}" x2="{effect_x + effect_w}" y2="{effect_y + effect_h}" stroke="{grid}" stroke-width="2"/>')
    bars = [("base", base, blue), ("best", best, teal), ("w=1.0", high_weight, red)]
    for i, (label, value, color) in enumerate(bars):
        h = int(effect_h * value / 1.05)
        x = effect_x + 20 + i * 82
        out.append(rect_bar(x, effect_y + effect_h - h, 55, h, color))
        out.append(text(x + 28, effect_y + effect_h - h - 14, f"{value:.3f}", 18, 800, color, "middle"))
        out.append(text(x + 28, effect_y + effect_h + 30, label, 15, 600, muted, "middle"))
    delta = best - base
    out.append(text(888, 485, f'Best delta vs base: {delta:+.3f}', 17, 700, ink))
    out.append(text(888, 512, "Large cache weight can hurt ranking.", 15, 500, muted))

    # Conclusion strip.
    out.append('<rect x="80" y="560" width="1120" height="92" rx="14" fill="#edf4ff" stroke="#b9d0ff"/>')
    out.append(text(110, 596, "Conclusion", 20, 800, "#193a8a"))
    out.append(text(110, 626, "Cache-prefix reuse is a real workload signal, but final_score = z_ltr + cache_weight * z_cache_bonus does not fix OOD ranking.", 18, 500, ink))
    out.append(text(110, 650, "Use it as a prefill / TTFT opportunity signal until serving-level validation shows an end-to-end latency win.", 16, 500, muted))

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lmsys-summary", type=Path, default=Path("results/cache-prefix-lmsys-offline-summary.json"))
    parser.add_argument("--cross-tau", type=Path, default=Path("results/llama3-8b/cross-tau-matrix.json"))
    parser.add_argument("--synthetic", type=Path, default=Path("results/cache-prefix-probe-synthetic-output.json"))
    parser.add_argument("--summary-out", type=Path, default=Path("results/cache-prefix-ranking-ablation-summary.json"))
    parser.add_argument("--svg-out", type=Path, default=Path("figures/cache_prefix_ranking_ablation.svg"))
    args = parser.parse_args()

    summary = make_summary(
        load_json(args.lmsys_summary),
        load_json(args.cross_tau),
        load_json(args.synthetic),
    )
    args.summary_out.parent.mkdir(parents=True, exist_ok=True)
    args.summary_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    args.svg_out.parent.mkdir(parents=True, exist_ok=True)
    args.svg_out.write_text(make_svg(summary), encoding="utf-8")
    print(f"wrote: {args.summary_out}")
    print(f"wrote: {args.svg_out}")


if __name__ == "__main__":
    main()
