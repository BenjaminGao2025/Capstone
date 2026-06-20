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
    width = 1120
    height = 560
    left = 82
    top = 118
    plot_w = 610
    plot_h = 290
    x_values = [row["prefix_words"] for row in rows]

    def x_for(prefix_words):
        return scale(prefix_words, min(x_values), max(x_values), left, left + plot_w)

    def y_for_hit(value):
        return scale(value, 0.0, 0.16, top + plot_h, top)

    hit_points = [(x_for(row["prefix_words"]), y_for_hit(row["cache_hit_rate"])) for row in rows]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="72" y="46" font-family="Arial, sans-serif" font-size="24" font-weight="700" fill="#0f172a">LMSYS Trace Cache-Prefix Summary</text>',
        '<text x="72" y="74" font-family="Arial, sans-serif" font-size="14" fill="#475569">Offline prefix reuse analysis over the first 500 LMSYS requests.</text>',
        '<rect x="54" y="94" width="680" height="365" rx="12" fill="#f8fafc" stroke="#dbe3ef"/>',
    ]

    for tick in [0.00, 0.04, 0.08, 0.12, 0.16]:
        y = y_for_hit(tick)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e2e8f0"/>')
        parts.append(f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{tick * 100:.0f}%</text>')

    parts.append(f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#94a3b8"/>')
    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#94a3b8"/>')

    for row in rows:
        x = x_for(row["prefix_words"])
        parts.append(f'<text x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#334155">{row["prefix_words"]}</text>')

    parts.append(f'<polyline points="{line(hit_points)}" fill="none" stroke="#2563eb" stroke-width="4"/>')

    for row, (x, y) in zip(rows, hit_points):
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#2563eb"/>')
        parts.append(f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#1d4ed8">{row["cache_hit_rate"] * 100:.1f}%</text>')

    parts.extend([
        f'<text x="{left + plot_w / 2}" y="{height - 104}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#334155">prefix_words</text>',
        '<text x="24" y="282" transform="rotate(-90 24 282)" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#334155">cache_hit_rate</text>',
        '<rect x="770" y="100" width="300" height="188" rx="12" fill="#eff6ff" stroke="#bfdbfe"/>',
        '<text x="792" y="134" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#1e3a8a">Best setting</text>',
        '<text x="792" y="176" font-family="Arial, sans-serif" font-size="38" font-weight="800" fill="#2563eb">16 words</text>',
        '<text x="792" y="210" font-family="Arial, sans-serif" font-size="14" fill="#1e40af">14.6% cache hit rate</text>',
        '<text x="792" y="236" font-family="Arial, sans-serif" font-size="14" fill="#1e40af">73 reused requests out of 500</text>',
        '<text x="792" y="262" font-family="Arial, sans-serif" font-size="14" fill="#1e40af">largest shared group: 25</text>',
        '<rect x="770" y="318" width="300" height="112" rx="12" fill="#f8fafc" stroke="#dbe3ef"/>',
        '<text x="792" y="350" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#0f172a">Interpretation</text>',
        '<text x="792" y="377" font-family="Arial, sans-serif" font-size="13" fill="#475569">Shorter prefix keys expose more</text>',
        '<text x="792" y="397" font-family="Arial, sans-serif" font-size="13" fill="#475569">shared-prefix reuse in this trace.</text>',
        '<text x="792" y="417" font-family="Arial, sans-serif" font-size="13" fill="#475569">That is the opportunity signal.</text>',
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
