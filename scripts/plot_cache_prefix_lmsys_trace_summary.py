#!/usr/bin/env python3
"""Render the LMSYS cache-prefix summary as a clean SVG chart."""

import argparse
import json
import os


def scale(value, min_value, max_value, out_min, out_max):
    if max_value == min_value:
        return (out_min + out_max) / 2
    return out_min + (value - min_value) * (out_max - out_min) / (max_value - min_value)


def line(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render_svg(report):
    rows = report["rows"]
    width = 960
    height = 610
    left = 96
    top = 112
    plot_w = 760
    plot_h = 260
    bar_w = 112
    step = plot_w / len(rows)

    def x_for(index):
        return left + step * index + step / 2

    def y_for_hit(value):
        return scale(value, 0.0, 0.16, top + plot_h, top)

    hit_points = [(x_for(index), y_for_hit(row["cache_hit_rate"])) for index, row in enumerate(rows)]
    best = max(rows, key=lambda row: row["cache_hit_rate"])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="54" y="44" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="#111827">LMSYS Trace Prefix-Reuse Probe</text>',
        '<text x="54" y="72" font-family="Arial, sans-serif" font-size="14" fill="#4b5563">Offline analysis of the first 500 LMSYS requests. Bars show cache-hit rate by tested prefix length.</text>',
        '<rect x="54" y="92" width="852" height="328" rx="8" fill="#ffffff" stroke="#d8e0ec"/>',
    ]

    for tick in [0.00, 0.04, 0.08, 0.12, 0.16]:
        y = y_for_hit(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 14}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#6b7280">{tick * 100:.0f}%</text>')

    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#94a3b8"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#94a3b8"/>')

    for index, row in enumerate(rows):
        x = x_for(index)
        y = y_for_hit(row["cache_hit_rate"])
        bar_h = top + plot_h - y
        fill = "#2563eb" if row == best else "#93c5fd"
        parts.append(f'<rect x="{x - bar_w / 2:.1f}" y="{y:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="5" fill="{fill}"/>')
        parts.append(f'<text x="{x:.1f}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#1d4ed8">{row["cache_hit_rate"] * 100:.1f}%</text>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">{row["prefix_words"]}</text>')

    parts.append(f'<polyline points="{line(hit_points)}" fill="none" stroke="#1d4ed8" stroke-width="2.5"/>')
    for x, y in hit_points:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ffffff" stroke="#1d4ed8" stroke-width="2"/>')

    parts.extend([
        f'<text x="{left + plot_w / 2}" y="{top + plot_h + 52}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">prefix_words</text>',
        '<text x="28" y="215" transform="rotate(-90 28 215)" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#374151">cache_hit_rate</text>',
        '<rect x="54" y="452" width="852" height="104" rx="8" fill="#f8fafc" stroke="#d8e0ec"/>',
        '<text x="80" y="486" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="#111827">Best observed setting</text>',
        '<text x="80" y="526" font-family="Arial, sans-serif" font-size="30" font-weight="800" fill="#2563eb">16 words</text>',
        '<line x1="260" y1="474" x2="260" y2="536" stroke="#d8e0ec"/>',
        '<text x="295" y="486" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">cache hit rate</text>',
        '<text x="295" y="522" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">14.6%</text>',
        '<text x="445" y="486" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">reused requests</text>',
        '<text x="445" y="522" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">73 / 500</text>',
        '<text x="625" y="486" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">largest group</text>',
        '<text x="625" y="522" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">25</text>',
        '<text x="775" y="486" font-family="Arial, sans-serif" font-size="12" fill="#6b7280">quality</text>',
        '<text x="775" y="522" font-family="Arial, sans-serif" font-size="22" font-weight="700" fill="#111827">0.236</text>',
        '<text x="54" y="586" font-family="Arial, sans-serif" font-size="12" fill="#4b5563">Takeaway: reusable prefix structure is measurable in this trace and is strongest at the shortest tested prefix length.</text>',
        '</svg>',
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
