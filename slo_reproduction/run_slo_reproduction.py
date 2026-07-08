from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path


OUT_DIR = Path(__file__).parent / "outputs"
RANDOM_SEED = 6806


@dataclass(frozen=True)
class Request:
    request_id: int
    arrival_time: float
    input_len: int
    output_len: int
    service_time: float
    slo_deadline: float


@dataclass
class ServedRequest:
    request_id: int
    policy: str
    request_rate: float
    arrival_time: float
    start_time: float
    finish_time: float
    latency: float
    service_time: float
    slo_deadline: float
    met_slo: bool


def generate_requests(num_requests: int, request_rate: float, seed: int) -> list[Request]:
    rng = random.Random(seed)
    requests: list[Request] = []
    current_time = 0.0

    for request_id in range(num_requests):
        current_time += rng.expovariate(request_rate)

        # Synthetic prompt/output lengths with a long-tail mix.
        if rng.random() < 0.72:
            input_len = rng.randint(80, 650)
            output_len = rng.randint(40, 420)
        else:
            input_len = rng.randint(650, 2200)
            output_len = rng.randint(420, 1500)

        # A simple latency model in seconds. It is intentionally transparent:
        # prefill cost scales with input length, decode cost scales with output length.
        service_time = 0.08 + 0.00045 * input_len + 0.0032 * output_len

        # Mixed application SLOs. Interactive requests have stricter deadlines;
        # offline-ish requests have looser deadlines.
        if rng.random() < 0.62:
            slo_deadline = service_time * rng.uniform(1.35, 2.25)
        else:
            slo_deadline = service_time * rng.uniform(2.25, 4.0)

        requests.append(
            Request(
                request_id=request_id,
                arrival_time=current_time,
                input_len=input_len,
                output_len=output_len,
                service_time=service_time,
                slo_deadline=slo_deadline,
            )
        )

    return requests


def simulate_fcfs(requests: list[Request], request_rate: float) -> list[ServedRequest]:
    time = 0.0
    served: list[ServedRequest] = []

    for req in requests:
        start = max(time, req.arrival_time)
        finish = start + req.service_time
        latency = finish - req.arrival_time
        served.append(
            ServedRequest(
                request_id=req.request_id,
                policy="FCFS",
                request_rate=request_rate,
                arrival_time=req.arrival_time,
                start_time=start,
                finish_time=finish,
                latency=latency,
                service_time=req.service_time,
                slo_deadline=req.slo_deadline,
                met_slo=latency <= req.slo_deadline,
            )
        )
        time = finish

    return served


def slo_priority(req: Request, now: float) -> tuple[int, float, float, int]:
    wait_time = max(0.0, now - req.arrival_time)
    remaining_slack = req.slo_deadline - wait_time - req.service_time
    slack_ratio = remaining_slack / max(req.service_time, 1e-9)

    # Paper-inspired simplification:
    # Requests that can still meet their SLO are prioritized by urgency.
    # Requests that are already unlikely to meet SLO are demoted, because
    # serving them first can make several feasible requests miss their SLOs.
    feasible_group = 0 if remaining_slack >= 0 else 1
    return (feasible_group, slack_ratio, req.service_time, req.request_id)


def simulate_slo_aware(requests: list[Request], request_rate: float) -> list[ServedRequest]:
    time = 0.0
    idx = 0
    ready: list[Request] = []
    served: list[ServedRequest] = []
    ordered = sorted(requests, key=lambda r: r.arrival_time)

    while idx < len(ordered) or ready:
        if not ready and idx < len(ordered) and time < ordered[idx].arrival_time:
            time = ordered[idx].arrival_time

        while idx < len(ordered) and ordered[idx].arrival_time <= time:
            ready.append(ordered[idx])
            idx += 1

        req = min(ready, key=lambda r: slo_priority(r, time))
        ready.remove(req)

        start = max(time, req.arrival_time)
        finish = start + req.service_time
        latency = finish - req.arrival_time
        served.append(
            ServedRequest(
                request_id=req.request_id,
                policy="SLO-aware",
                request_rate=request_rate,
                arrival_time=req.arrival_time,
                start_time=start,
                finish_time=finish,
                latency=latency,
                service_time=req.service_time,
                slo_deadline=req.slo_deadline,
                met_slo=latency <= req.slo_deadline,
            )
        )
        time = finish

    return served


def summarize(served: list[ServedRequest]) -> dict[str, float | str]:
    n = len(served)
    met = sum(1 for req in served if req.met_slo)
    latencies = sorted(req.latency for req in served)
    return {
        "request_rate": served[0].request_rate,
        "policy": served[0].policy,
        "num_requests": n,
        "slo_attainment": met / n,
        "average_latency": sum(latencies) / n,
        "p95_latency": latencies[max(0, math.ceil(0.95 * n) - 1)],
    }


def write_workload(path: Path, requests: list[Request]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "request_id",
                "arrival_time",
                "input_len",
                "output_len",
                "service_time",
                "slo_deadline",
            ],
        )
        writer.writeheader()
        for req in requests:
            writer.writerow(req.__dict__)


def write_results(path: Path, rows: list[dict[str, float | str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "request_rate",
                "policy",
                "num_requests",
                "slo_attainment",
                "average_latency",
                "p95_latency",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def make_svg(
    path: Path,
    rows: list[dict[str, float | str]],
    metric: str,
    title: str,
    y_label: str,
    y_max: float | None = None,
) -> None:
    width, height = 900, 560
    margin_left, margin_right, margin_top, margin_bottom = 82, 44, 58, 104
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    rates = sorted({float(row["request_rate"]) for row in rows})
    policies = ["FCFS", "SLO-aware"]
    colors = {"FCFS": "#8f3f2f", "SLO-aware": "#245b7a"}
    max_y = y_max or max(float(row[metric]) for row in rows) * 1.08
    min_x, max_x = min(rates), max(rates)

    def x_pos(rate: float) -> float:
        return margin_left + (rate - min_x) / (max_x - min_x) * plot_w

    def y_pos(value: float) -> float:
        return margin_top + plot_h - value / max_y * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{margin_left}" y="32" font-family="Arial" font-size="22" font-weight="700" fill="#222">{title}</text>',
        f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#333"/>',
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#333"/>',
    ]

    for i in range(6):
        value = max_y * i / 5
        y = y_pos(value)
        parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_w}" y2="{y:.1f}" stroke="#e5e5e5"/>')
        label = f"{value:.0%}" if metric == "slo_attainment" else f"{value:.1f}"
        parts.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" font-family="Arial" font-size="12" text-anchor="end" fill="#444">{label}</text>')

    for rate in rates:
        x = x_pos(rate)
        parts.append(f'<text x="{x:.1f}" y="{height - 72}" font-family="Arial" font-size="12" text-anchor="middle" fill="#444">{rate:.2f}</text>')

    for policy in policies:
        points = []
        for rate in rates:
            row = next(row for row in rows if row["policy"] == policy and float(row["request_rate"]) == rate)
            points.append((x_pos(rate), y_pos(float(row[metric]))))
        point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(f'<polyline fill="none" stroke="{colors[policy]}" stroke-width="3" points="{point_str}"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{colors[policy]}"/>')

    parts.extend(
        [
            f'<text x="{margin_left + plot_w / 2}" y="{height - 42}" font-family="Arial" font-size="14" text-anchor="middle" fill="#222">Request rate (requests/sec)</text>',
            f'<text transform="translate(20 {margin_top + plot_h / 2}) rotate(-90)" font-family="Arial" font-size="14" text-anchor="middle" fill="#222">{y_label}</text>',
            f'<rect x="{width - 174}" y="68" width="14" height="14" fill="{colors["FCFS"]}"/>',
            f'<text x="{width - 152}" y="80" font-family="Arial" font-size="13" fill="#222">FCFS</text>',
            f'<rect x="{width - 174}" y="94" width="14" height="14" fill="{colors["SLO-aware"]}"/>',
            f'<text x="{width - 152}" y="106" font-family="Arial" font-size="13" fill="#222">SLO-aware</text>',
            '<text x="82" y="540" font-family="Arial" font-size="10.5" fill="#555">Synthetic workload generated by our group; simulation-level reproduction starter.</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    request_rates = [0.22, 0.28, 0.34, 0.40, 0.46, 0.52]
    rows: list[dict[str, float | str]] = []

    for rate in request_rates:
        requests = generate_requests(num_requests=240, request_rate=rate, seed=RANDOM_SEED + int(rate * 1000))
        if rate == request_rates[0]:
            write_workload(OUT_DIR / "workload.csv", requests)

        fcfs = simulate_fcfs(requests, rate)
        slo_aware = simulate_slo_aware(requests, rate)
        rows.append(summarize(fcfs))
        rows.append(summarize(slo_aware))

    write_results(OUT_DIR / "results.csv", rows)
    make_svg(
        OUT_DIR / "slo_attainment.svg",
        rows,
        metric="slo_attainment",
        title="FCFS vs SLO-aware Scheduling",
        y_label="SLO attainment",
        y_max=1.0,
    )
    make_svg(
        OUT_DIR / "average_latency.svg",
        rows,
        metric="average_latency",
        title="Average Latency under Increasing Request Rate",
        y_label="Average latency (s)",
    )

    print(f"Wrote outputs to: {OUT_DIR}")
    print("Summary:")
    for row in rows:
        print(
            f"rate={row['request_rate']:.2f}, policy={row['policy']}, "
            f"SLO={row['slo_attainment']:.3f}, avg_latency={row['average_latency']:.3f}s"
        )


if __name__ == "__main__":
    main()
