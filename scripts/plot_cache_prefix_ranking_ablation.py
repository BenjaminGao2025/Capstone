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


def multiline_text(
    x: int,
    y: int,
    lines: list[str],
    size: int = 18,
    weight: int = 400,
    fill: str = "#152238",
    line_height: int = 24,
    anchor: str = "start",
) -> list[str]:
    return [
        text(x, y + i * line_height, line, size=size, weight=weight, fill=fill, anchor=anchor)
        for i, line in enumerate(lines)
    ]


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
    bg = "#f8fafc"
    ink = "#111827"
    muted = "#526174"
    blue = "#2563eb"
    teal = "#0f9f8f"
    orange = "#f59e0b"
    red = "#dc4a4a"
    grid = "#d8e1ee"
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
        text(72, 70, "Cache-Prefix Ranking Ablation", 34, 800, ink),
        text(72, 104, "One-figure summary for issue #19: prefix opportunity exists, but the cache bonus does not repair OOD ranking.", 17, 400, muted),
    ]

    # Main chart.
    out.append('<rect x="72" y="136" width="760" height="410" rx="10" fill="#ffffff" stroke="#cbd5e1"/>')
    out.append(text(104, 178, "Normalized evidence scale", 21, 800, ink))
    out.append(text(104, 204, "Horizontal bars keep all labels visible in README and mobile previews.", 14, 500, muted))

    axis_x, axis_y, axis_w = 332, 254, 420
    rows = [
        ("Prefix hit rate", hit_rate, teal, "LMSYS trace"),
        ("LTR tau", tau_lmsys, blue, "LMSYS"),
        ("LTR tau", tau_shifted, orange, "ShareGPT"),
        ("Base LTR", base, blue, "synthetic"),
        ("Best cache+LTR", best, teal, "no gain"),
        ("Cache weight 1.0", high_weight, red, "can hurt"),
    ]

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = axis_x + int(axis_w * tick)
        out.append(f'<line x1="{x}" y1="236" x2="{x}" y2="500" stroke="{grid}" stroke-width="1"/>')
        out.append(text(x, 522, f"{tick:.2f}", 12, 500, muted, "middle"))
    out.append(text(axis_x + axis_w / 2, 540, "value", 13, 600, muted, "middle"))

    for i, (label, value, color, note) in enumerate(rows):
        y = axis_y + i * 39
        bar_w = max(4, int(axis_w * value))
        out.append(text(104, y + 17, label, 15, 700, ink))
        out.append(text(254, y + 17, note, 12, 500, muted))
        out.append(f'<rect x="{axis_x}" y="{y}" width="{axis_w}" height="18" rx="9" fill="#edf2f7"/>')
        out.append(f'<rect x="{axis_x}" y="{y}" width="{bar_w}" height="18" rx="9" fill="{color}"/>')
        value_label = fmt_pct(value) if i == 0 else f"{value:.3f}"
        out.append(text(axis_x + bar_w + 12, y + 15, value_label, 14, 800, color))

    # Right-side findings panel.
    out.append('<rect x="872" y="136" width="336" height="410" rx="10" fill="#ffffff" stroke="#cbd5e1"/>')
    out.append(text(904, 178, "Key Findings", 22, 800, ink))

    findings = [
        (fmt_pct(hit_rate), "prefix reuse", [f'{lmsys["reused_requests"]}/500 requests reuse a prefix', f'largest shared group: {lmsys["largest_shared_group"]}']),
        (f'{rank["drop"]:.3f}', "tau drop", ["LTR ranking weakens under", "the shifted ShareGPT trace"]),
        (f'{best - base:+.3f}', "best cache delta", ["best tested cache bonus is", "neutral, not a ranking fix"]),
    ]
    for i, (big, label, lines) in enumerate(findings):
        y = 228 + i * 98
        out.append(text(904, y, big, 32, 800, [teal, orange, red][i]))
        out.append(text(1012, y - 4, label, 15, 800, ink))
        out.extend(multiline_text(1012, y + 18, lines, 13, 500, muted, 18))

    # Bottom conclusion strip.
    out.append('<rect x="72" y="582" width="1136" height="74" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>')
    out.append(text(104, 616, "Conclusion", 18, 800, "#1d4ed8"))
    out.extend(multiline_text(
        230,
        606,
        [
            "The cache-aware feature finds real shared-prefix opportunity, but adding the cache bonus is neutral at best for ranking.",
            "The method should be presented as a serving-level TTFT opportunity signal, not as a standalone OOD fix.",
        ],
        16,
        500,
        ink,
        24,
    ))

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
