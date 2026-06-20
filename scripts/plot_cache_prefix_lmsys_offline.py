#!/usr/bin/env python3
"""Render the LMSYS offline cache-prefix probe as an original SVG chart."""

import argparse
import json
import os


def scale(value, min_value, max_value, out_min, out_max):
    if max_value == min_value:
        return (out_min + out_max) / 2
    return out_min + (value - min_value) * (out_max - out_min) / (max_value - min_value)


def polyline(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def render_svg(report):
    rows = report["rows"]
    width = 1120
    height = 640
    left = 86
    top = 122
    plot_w = 640
    plot_h = 330
    x_values = [row["prefix_words"] for row in rows]

    def x_for(prefix_words):
        return scale(prefix_words, min(x_values), max(x_values), left, left + plot_w)

    def y_rate(value):
        return scale(value, 0.0, 0.16, top + plot_h, top)

    def y_quality(value):
        return scale(value, 0.18, 0.25, top + plot_h, top)

    hit_points = [(x_for(row["prefix_words"]), y_rate(row["cache_hit_rate"])) for row in rows]
    quality_points = [(x_for(row["prefix_words"]), y_quality(row["cache_only_quality"])) for row in rows]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="72" y="48" font-family="Arial, sans-serif" font-size="25" font-weight="700" fill="#111827">LMSYS Trace Prefix-Reuse Probe</text>',
        '<text x="72" y="76" font-family="Arial, sans-serif" font-size="14" fill="#475569">First 500 LMSYS requests; lower prefix length captures more reusable prompt structure.</text>',
        f'<rect x="{left - 28}" y="{top - 38}" width="{plot_w + 70}" height="{plot_h + 90}" rx="10" fill="#ffffff" stroke="#dbe3ef"/>',
    ]

    for tick in [0.00, 0.04, 0.08, 0.12, 0.16]:
        y = y_rate(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{tick * 100:.0f}%</text>')

    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#94a3b8"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#94a3b8"/>')

    for row in rows:
        x = x_for(row["prefix_words"])
        parts.append(f'<line x1="{x:.1f}" y1="{top + plot_h}" x2="{x:.1f}" y2="{top + plot_h + 6}" stroke="#94a3b8"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 25}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#334155">{row["prefix_words"]}</text>')

    parts.append(f'<polyline points="{polyline(hit_points)}" fill="none" stroke="#2563eb" stroke-width="4"/>')
    parts.append(f'<polyline points="{polyline(quality_points)}" fill="none" stroke="#f59e0b" stroke-width="4" stroke-dasharray="8 7"/>')

    for row, (x, y) in zip(rows, hit_points):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#2563eb"/>')
        parts.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#1d4ed8">{row["cache_hit_rate"] * 100:.1f}%</text>')

    for row, (x, y) in zip(rows, quality_points):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#f59e0b"/>')

    parts.extend([
        f'<text x="{left + plot_w / 2}" y="{height - 118}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#334155">prefix_words</text>',
        '<rect x="770" y="112" width="286" height="230" rx="10" fill="#ffffff" stroke="#dbe3ef"/>',
        '<text x="790" y="145" font-family="Arial, sans-serif" font-size="17" font-weight="700" fill="#111827">Best observed setting</text>',
        '<text x="790" y="184" font-family="Arial, sans-serif" font-size="36" font-weight="800" fill="#2563eb">16 words</text>',
        '<text x="790" y="217" font-family="Arial, sans-serif" font-size="14" fill="#475569">cache_hit_rate: 14.6%</text>',
        '<text x="790" y="242" font-family="Arial, sans-serif" font-size="14" fill="#475569">reused requests: 73 / 500</text>',
        '<text x="790" y="267" font-family="Arial, sans-serif" font-size="14" fill="#475569">largest shared group: 25</text>',
        '<text x="790" y="292" font-family="Arial, sans-serif" font-size="14" fill="#475569">cache-only quality: 0.236</text>',
        '<rect x="770" y="370" width="286" height="112" rx="10" fill="#eff6ff" stroke="#bfdbfe"/>',
        '<text x="790" y="402" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#1e3a8a">Interpretation</text>',
        '<text x="790" y="429" font-family="Arial, sans-serif" font-size="13" fill="#1e40af">Prefix reuse is measurable in the</text>',
        '<text x="790" y="449" font-family="Arial, sans-serif" font-size="13" fill="#1e40af">LMSYS trace and is strongest at</text>',
        '<text x="790" y="469" font-family="Arial, sans-serif" font-size="13" fill="#1e40af">the shortest tested prefix length.</text>',
        '<rect x="94" y="530" width="14" height="14" fill="#2563eb"/>',
        '<text x="116" y="542" font-family="Arial, sans-serif" font-size="13" fill="#334155">cache hit rate (left axis)</text>',
        '<line x1="300" y1="537" x2="340" y2="537" stroke="#f59e0b" stroke-width="4" stroke-dasharray="8 7"/>',
        '<text x="350" y="542" font-family="Arial, sans-serif" font-size="13" fill="#334155">cache-only quality (scaled trend)</text>',
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
