from __future__ import annotations

import csv
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path


OUT_DIR = Path(__file__).parent / "outputs_aptserve"
RANDOM_SEED = 6806
SEEDS = [6806, 6807, 6808, 6809, 6810]
MAX_BATCH_SIZE = 16
KV_MEMORY_LIMIT = 11_500
HYBRID_MEMORY_LIMIT = 11_500


@dataclass(frozen=True)
class Request:
    request_id: int
    arrival_time: float
    input_len: int
    output_len: int
    slo_deadline: float
    kv_memory: int
    hidden_memory: int


@dataclass
class ServedRequest:
    request_id: int
    request_rate: float
    policy: str
    arrival_time: float
    start_time: float
    finish_time: float
    latency: float
    slo_deadline: float
    met_slo: bool
    batch_size: int
    cache_mode: str
    memory_used: int


def generate_requests(num_requests: int, request_rate: float, seed: int) -> list[Request]:
    rng = random.Random(seed)
    now = 0.0
    requests: list[Request] = []

    for request_id in range(num_requests):
        now += rng.expovariate(request_rate)

        if rng.random() < 0.68:
            input_len = rng.randint(100, 900)
            output_len = rng.randint(60, 520)
        else:
            input_len = rng.randint(900, 3600)
            output_len = rng.randint(520, 1900)

        base_time = estimate_request_time(input_len, output_len, cache_mode="kv")
        if rng.random() < 0.62:
            slo_deadline = base_time * rng.uniform(1.35, 2.20)
        else:
            slo_deadline = base_time * rng.uniform(2.20, 4.00)

        total_tokens = input_len + output_len
        kv_memory = total_tokens * 2
        hidden_memory = math.ceil(total_tokens * 1.05)

        requests.append(
            Request(
                request_id=request_id,
                arrival_time=now,
                input_len=input_len,
                output_len=output_len,
                slo_deadline=slo_deadline,
                kv_memory=kv_memory,
                hidden_memory=hidden_memory,
            )
        )

    return requests


def estimate_request_time(input_len: int, output_len: int, cache_mode: str) -> float:
    prefill = 0.10 + 0.00042 * input_len
    decode = 0.0030 * output_len
    if cache_mode == "hidden":
        # Hidden cache saves memory but requires extra recomputation to rebuild
        # KV-like values when reused.
        return prefill + decode * 1.18 + 0.00016 * (input_len + output_len)
    return prefill + decode


def estimate_batch_time(batch: list[tuple[Request, str]]) -> float:
    batch_size = len(batch)
    max_input = max(req.input_len for req, _ in batch)
    max_output = max(req.output_len for req, _ in batch)
    hidden_count = sum(1 for _, mode in batch if mode == "hidden")

    prefill = 0.10 + 0.00042 * max_input + 0.014 * batch_size
    decode = 0.0030 * max_output * (1.0 + 0.028 * (batch_size - 1))
    hidden_overhead = 0.045 * hidden_count
    return prefill + decode + hidden_overhead


def request_memory(req: Request, cache_mode: str) -> int:
    return req.hidden_memory if cache_mode == "hidden" else req.kv_memory


def simulate_fcfs_kv(requests: list[Request], request_rate: float) -> list[ServedRequest]:
    return simulate(requests, request_rate, policy="FCFS-KV")


def simulate_adaptive_hybrid(requests: list[Request], request_rate: float) -> list[ServedRequest]:
    return simulate(requests, request_rate, policy="Adaptive-Hybrid")


def simulate(requests: list[Request], request_rate: float, policy: str) -> list[ServedRequest]:
    ordered = sorted(requests, key=lambda req: req.arrival_time)
    idx = 0
    ready: list[Request] = []
    time = 0.0
    served: list[ServedRequest] = []

    while idx < len(ordered) or ready:
        if not ready and idx < len(ordered) and time < ordered[idx].arrival_time:
            time = ordered[idx].arrival_time

        while idx < len(ordered) and ordered[idx].arrival_time <= time:
            ready.append(ordered[idx])
            idx += 1

        if policy == "FCFS-KV":
            selected = select_fcfs_kv(ready)
        elif policy == "Adaptive-Hybrid":
            selected = select_adaptive_hybrid(ready, time)
        else:
            raise ValueError(policy)

        selected_ids = {req.request_id for req, _ in selected}
        ready = [req for req in ready if req.request_id not in selected_ids]

        start = time
        finish = start + estimate_batch_time(selected)
        for req, cache_mode in selected:
            latency = finish - req.arrival_time
            served.append(
                ServedRequest(
                    request_id=req.request_id,
                    request_rate=request_rate,
                    policy=policy,
                    arrival_time=req.arrival_time,
                    start_time=start,
                    finish_time=finish,
                    latency=latency,
                    slo_deadline=req.slo_deadline,
                    met_slo=latency <= req.slo_deadline,
                    batch_size=len(selected),
                    cache_mode=cache_mode,
                    memory_used=sum(request_memory(r, m) for r, m in selected),
                )
            )
        time = finish

    return served


def select_fcfs_kv(ready: list[Request]) -> list[tuple[Request, str]]:
    batch: list[tuple[Request, str]] = []
    memory = 0
    for req in sorted(ready, key=lambda r: (r.arrival_time, r.request_id)):
        if len(batch) >= MAX_BATCH_SIZE:
            break
        if memory + req.kv_memory > KV_MEMORY_LIMIT:
            continue
        batch.append((req, "kv"))
        memory += req.kv_memory
    if not batch:
        # If one very large request exceeds the nominal limit, serve it alone.
        req = min(ready, key=lambda r: (r.arrival_time, r.request_id))
        batch.append((req, "kv"))
    return batch


def select_adaptive_hybrid(ready: list[Request], now: float) -> list[tuple[Request, str]]:
    candidates = sorted(
        ready,
        key=lambda req: adaptive_value(req, now),
        reverse=True,
    )

    batch: list[tuple[Request, str]] = []
    memory = 0
    for req in candidates:
        if len(batch) >= MAX_BATCH_SIZE:
            break

        # Try KV cache first for speed. If memory is tight, try hidden cache.
        if memory + req.kv_memory <= HYBRID_MEMORY_LIMIT:
            batch.append((req, "kv"))
            memory += req.kv_memory
        elif memory + req.hidden_memory <= HYBRID_MEMORY_LIMIT:
            batch.append((req, "hidden"))
            memory += req.hidden_memory

    if not batch:
        req = max(ready, key=lambda r: adaptive_value(r, now))
        mode = "hidden" if req.hidden_memory < req.kv_memory else "kv"
        batch.append((req, mode))
    return batch


def adaptive_value(req: Request, now: float) -> float:
    wait = max(0.0, now - req.arrival_time)
    kv_time = estimate_request_time(req.input_len, req.output_len, cache_mode="kv")
    slack = req.slo_deadline - wait - kv_time
    urgency = 1.0 / max(slack + 0.25, 0.25)
    memory_saving = (req.kv_memory - req.hidden_memory) / max(req.kv_memory, 1)
    short_job_bonus = 1.0 / max(kv_time, 1e-9)
    return 1.8 * urgency + 1.2 * memory_saving + 0.6 * short_job_bonus


def summarize(served: list[ServedRequest]) -> dict[str, float | str]:
    latencies = sorted(req.latency for req in served)
    n = len(served)
    met = sum(1 for req in served if req.met_slo)
    hidden = sum(1 for req in served if req.cache_mode == "hidden")
    return {
        "request_rate": served[0].request_rate,
        "policy": served[0].policy,
        "num_requests": n,
        "slo_attainment": met / n,
        "average_latency": sum(latencies) / n,
        "p95_latency": latencies[max(0, math.ceil(0.95 * n) - 1)],
        "average_batch_size": sum(req.batch_size for req in served) / n,
        "hidden_cache_ratio": hidden / n,
        "average_memory_used": sum(req.memory_used for req in served) / n,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def summarize_across_seeds(rows: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    keys = sorted({(float(row["request_rate"]), str(row["policy"])) for row in rows})
    metrics = [
        "slo_attainment",
        "average_latency",
        "p95_latency",
        "average_batch_size",
        "hidden_cache_ratio",
        "average_memory_used",
    ]
    summary: list[dict[str, float | str]] = []

    for request_rate, policy in keys:
        subset = [
            row for row in rows
            if float(row["request_rate"]) == request_rate and str(row["policy"]) == policy
        ]
        item: dict[str, float | str] = {
            "request_rate": request_rate,
            "policy": policy,
            "num_runs": len(subset),
            "num_requests": subset[0]["num_requests"],
        }
        for metric in metrics:
            values = [float(row[metric]) for row in subset]
            item[f"{metric}_mean"] = statistics.mean(values)
            item[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        summary.append(item)

    return summary


def make_svg(path: Path, rows: list[dict[str, float | str]], metric: str, title: str, y_label: str, y_max: float | None = None) -> None:
    width, height = 900, 560
    left, right, top, bottom = 82, 44, 58, 104
    plot_w = width - left - right
    plot_h = height - top - bottom
    rates = sorted({float(row["request_rate"]) for row in rows})
    policies = ["FCFS-KV", "Adaptive-Hybrid"]
    colors = {"FCFS-KV": "#8f3f2f", "Adaptive-Hybrid": "#245b7a"}
    metric_key = metric if metric in rows[0] else f"{metric}_mean"
    max_y = y_max or max(float(row[metric_key]) for row in rows) * 1.08
    min_x, max_x = min(rates), max(rates)

    def x_pos(rate: float) -> float:
        return left + (rate - min_x) / (max_x - min_x) * plot_w

    def y_pos(value: float) -> float:
        return top + plot_h - value / max_y * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="{left}" y="32" font-family="Arial" font-size="22" font-weight="700" fill="#222">{title}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" stroke="#333"/>',
    ]
    for i in range(6):
        value = max_y * i / 5
        y = y_pos(value)
        label = f"{value:.0%}" if metric == "slo_attainment" else f"{value:.1f}"
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="#e5e5e5"/>')
        parts.append(f'<text x="{left - 10}" y="{y + 4:.1f}" font-family="Arial" font-size="12" text-anchor="end" fill="#444">{label}</text>')
    for rate in rates:
        parts.append(f'<text x="{x_pos(rate):.1f}" y="{height - 72}" font-family="Arial" font-size="12" text-anchor="middle" fill="#444">{rate:.2f}</text>')
    for policy in policies:
        points = []
        for rate in rates:
            row = next(row for row in rows if row["policy"] == policy and float(row["request_rate"]) == rate)
            points.append((x_pos(rate), y_pos(float(row[metric_key]))))
        parts.append(f'<polyline fill="none" stroke="{colors[policy]}" stroke-width="3" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in points) + '"/>')
        for x, y in points:
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{colors[policy]}"/>')
    parts.extend(
        [
            f'<text x="{left + plot_w / 2}" y="{height - 42}" font-family="Arial" font-size="14" text-anchor="middle" fill="#222">Request rate (requests/sec)</text>',
            f'<text transform="translate(20 {top + plot_h / 2}) rotate(-90)" font-family="Arial" font-size="14" text-anchor="middle" fill="#222">{y_label}</text>',
            f'<rect x="{width - 210}" y="68" width="14" height="14" fill="{colors["FCFS-KV"]}"/>',
            f'<text x="{width - 188}" y="80" font-family="Arial" font-size="13" fill="#222">FCFS-KV</text>',
            f'<rect x="{width - 210}" y="94" width="14" height="14" fill="{colors["Adaptive-Hybrid"]}"/>',
            f'<text x="{width - 188}" y="106" font-family="Arial" font-size="13" fill="#222">Adaptive-Hybrid</text>',
            '<text x="82" y="540" font-family="Arial" font-size="10.5" fill="#555">Synthetic workload generated by our group; Apt-Serve-style adaptive hybrid-cache probe.</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    request_rates = [0.22, 0.30, 0.38, 0.46, 0.54, 0.62]
    rows: list[dict[str, float | str]] = []
    all_served: list[ServedRequest] = []

    for seed in SEEDS:
        for rate in request_rates:
            requests = generate_requests(280, rate, seed + int(rate * 1000))
            if seed == SEEDS[0] and rate == request_rates[0]:
                write_csv(OUT_DIR / "workload.csv", [req.__dict__ for req in requests])
            for policy_fn in [simulate_fcfs_kv, simulate_adaptive_hybrid]:
                served = policy_fn(requests, rate)
                row = summarize(served)
                row["seed"] = seed
                rows.append(row)
                all_served.extend(served)

    summary_rows = summarize_across_seeds(rows)
    write_csv(OUT_DIR / "results_by_seed.csv", rows)
    write_csv(OUT_DIR / "results.csv", summary_rows)
    write_csv(OUT_DIR / "results_summary.csv", summary_rows)
    write_csv(OUT_DIR / "served_requests.csv", [req.__dict__ for req in all_served])
    make_svg(OUT_DIR / "slo_attainment.svg", summary_rows, "slo_attainment", "Apt-Serve Probe: SLO Attainment", "SLO attainment", y_max=1.0)
    make_svg(OUT_DIR / "average_batch_size.svg", summary_rows, "average_batch_size", "Apt-Serve Probe: Batch Size under Memory Limit", "Average batch size")

    print(f"Wrote outputs to: {OUT_DIR}")
    for row in summary_rows:
        print(
            f"rate={row['request_rate']:.2f}, policy={row['policy']}, "
            f"SLO={row['slo_attainment_mean']:.3f}±{row['slo_attainment_std']:.3f}, "
            f"avg_batch={row['average_batch_size_mean']:.2f}, "
            f"hidden_ratio={row['hidden_cache_ratio_mean']:.2f}"
        )


if __name__ == "__main__":
    main()
