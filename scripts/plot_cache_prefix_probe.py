#!/usr/bin/env python3
"""Render a small SVG chart for cache-prefix probe output.

This uses only the Python standard library so the figure can be regenerated on
a laptop without installing matplotlib.
"""

import argparse
import json
import os


def x_for(index, count, left, width):
    if count <= 1:
        return left + width / 2
    return left + index * width / (count - 1)


def y_for(value, min_value, max_value, top, height):
    if max_value == min_value:
        return top + height / 2
    return top + (max_value - value) * height / (max_value - min_value)


def polyline(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render_svg(report):
    rows = report["results"]
    prefix_words = [row["prefix_words"] for row in rows]
    hit_rates = [row["cache_hit_rate"] for row in rows]

    best_quality = []
    for row in rows:
        combined = row.get("combined") or []
        values = [item["sjf_quality"] for item in combined if item["sjf_quality"] is not None]
        best_quality.append(max(values) if values else None)

    valid_quality = [value for value in best_quality if value is not None]
    quality_min = min(valid_quality + [0.0])
    quality_max = max(valid_quality + [1.0])

    width = 900
    height = 430
    left = 90
    top = 70
    plot_width = 700
    plot_height = 250
    count = len(rows)

    hit_points = []
    quality_points = []
    for i, value in enumerate(hit_rates):
        x = x_for(i, count, left, plot_width)
        hit_points.append((x, y_for(value, 0.0, 1.0, top, plot_height)))
    for i, value in enumerate(best_quality):
        if value is None:
            continue
        x = x_for(i, count, left, plot_width)
        quality_points.append((x, y_for(value, quality_min, quality_max, top, plot_height)))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="90" y="34" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">Synthetic offline cache-prefix sanity check</text>',
        '<text x="90" y="56" font-family="Arial, sans-serif" font-size="13" fill="#4b5563">No large model or vLLM server is used; this only visualizes the prefix-scoring calculation.</text>',
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" y2="{top + plot_height}" stroke="#9ca3af" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#9ca3af" stroke-width="1"/>',
    ]

    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_for(tick, 0.0, 1.0, top, plot_height)
        parts.append(f'<line x1="{left - 5}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">{tick:.2f}</text>')

    parts.append(f'<polyline points="{polyline(hit_points)}" fill="none" stroke="#2563eb" stroke-width="3"/>')
    parts.append(f'<polyline points="{polyline(quality_points)}" fill="none" stroke="#dc2626" stroke-width="3"/>')

    for i, word_count in enumerate(prefix_words):
        x = x_for(i, count, left, plot_width)
        parts.append(f'<circle cx="{x:.1f}" cy="{hit_points[i][1]:.1f}" r="5" fill="#2563eb"/>')
        if i < len(quality_points):
            parts.append(f'<circle cx="{quality_points[i][0]:.1f}" cy="{quality_points[i][1]:.1f}" r="5" fill="#dc2626"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_height + 26}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{word_count}</text>')

    parts.extend([
        f'<text x="{left + plot_width / 2}" y="{height - 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#374151">prefix_words</text>',
        '<rect x="585" y="84" width="12" height="12" fill="#2563eb"/>',
        '<text x="604" y="95" font-family="Arial, sans-serif" font-size="13" fill="#374151">cache_hit_rate</text>',
        '<rect x="585" y="106" width="12" height="12" fill="#dc2626"/>',
        '<text x="604" y="117" font-family="Arial, sans-serif" font-size="13" fill="#374151">best combined sjf_quality</text>',
        '<text x="90" y="390" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">Interpretation: this chart checks whether repeated-prefix structure exists and whether adding the cache bonus changes ranking diagnostics.</text>',
        "</svg>",
    ])
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="cache_prefix_probe.py output JSON")
    parser.add_argument("--out", required=True, help="SVG output path")
    args = parser.parse_args()

    with open(args.input) as file:
        report = json.load(file)

    output_dir = os.path.dirname(args.out)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.out, "w") as file:
        file.write(render_svg(report))

    print("wrote:", args.out)


if __name__ == "__main__":
    main()
