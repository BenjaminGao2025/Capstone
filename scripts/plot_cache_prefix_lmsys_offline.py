#!/usr/bin/env python3
"""Render the LMSYS offline cache-prefix probe as SVG."""

import argparse
import json
import os


def bar_group(x, y_base, width, height, value, max_value, color, label, value_label):
    bar_h = 0 if max_value == 0 else height * value / max_value
    y = y_base - bar_h
    return [
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width}" height="{bar_h:.1f}" rx="8" fill="{color}"/>',
        f'<text x="{x + width / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#e5e7eb">{value_label}</text>',
        f'<text x="{x + width / 2:.1f}" y="{y_base + 24:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#94a3b8">{label}</text>',
    ]


def render_svg(report):
    rows = report["rows"]
    width = 1100
    height = 620
    panel_y = 170
    panel_h = 270
    y_base = panel_y + 205
    bar_h = 150
    colors = {
        "hit": "#ec4899",
        "reuse": "#60a5fa",
        "quality": "#2dd4bf",
        "accent": "#fde68a",
    }

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0b1020"/>',
        '<pattern id="grid" width="80" height="80" patternUnits="userSpaceOnUse">',
        '<path d="M 80 0 L 0 0 0 80" fill="none" stroke="#1f2a44" stroke-width="1"/>',
        '</pattern>',
        '<rect width="100%" height="100%" fill="url(#grid)" opacity="0.55"/>',
        '<text x="70" y="54" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#22d3ee">LMSYS TRACE · OFFLINE PREFIX PROBE</text>',
        '<text x="70" y="105" font-family="Arial, sans-serif" font-size="34" font-weight="800" fill="#f8fafc">Shared-prefix signal in 500 LMSYS requests</text>',
        '<text x="70" y="137" font-family="Arial, sans-serif" font-size="16" fill="#cbd5e1">Prefix length 16 gives the strongest cache-only signal in this probe.</text>',
        f'<rect x="60" y="{panel_y}" width="980" height="{panel_h}" rx="14" fill="#111827" stroke="#263449"/>',
    ]

    group_specs = [
        ("Cache hit rate", "hit", "cache_hit_rate", max(row["cache_hit_rate"] for row in rows), lambda v: f"{v * 100:.1f}%"),
        ("Reused requests", "reuse", "reused_requests", max(row["reused_requests"] for row in rows), lambda v: f"{int(v)}"),
        ("Cache-only quality", "quality", "cache_only_quality", max(row["cache_only_quality"] for row in rows), lambda v: f"{v:.3f}"),
    ]
    group_x = [110, 420, 730]
    bar_w = 52
    gap = 18

    for gx, (title, color_key, field, max_value, formatter) in zip(group_x, group_specs):
        parts.append(f'<text x="{gx}" y="{panel_y + 55}" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#f8fafc">{title}</text>')
        for i, row in enumerate(rows):
            x = gx + i * (bar_w + gap)
            parts.extend(
                bar_group(
                    x,
                    y_base,
                    bar_w,
                    bar_h,
                    row[field],
                    max_value,
                    colors[color_key],
                    str(row["prefix_words"]),
                    formatter(row[field]),
                )
            )

    parts.extend([
        '<rect x="90" y="480" width="920" height="78" rx="12" fill="#111827" stroke="#263449"/>',
        '<line x1="110" y1="500" x2="990" y2="500" stroke="#ec4899" stroke-width="2"/>',
        '<text x="110" y="530" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#f8fafc">Interpretation</text>',
        '<text x="110" y="554" font-family="Arial, sans-serif" font-size="15" fill="#cbd5e1">Shared-prefix reuse exists in the workload: prefix_words=16 finds 73 reused requests, a 14.6% hit rate, and the highest cache-only quality.</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.input) as file:
        report = json.load(file)

    folder = os.path.dirname(args.out)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(args.out, "w") as file:
        file.write(render_svg(report))

    print("wrote:", args.out)


if __name__ == "__main__":
    main()
