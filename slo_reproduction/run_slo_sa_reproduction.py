from __future__ import annotations

import csv
import math
import random
import statistics
from dataclasses import dataclass
from pathlib import Path


OUT_DIR = Path(__file__).parent / "outputs_sa"
RANDOM_SEED = 6806
SEEDS = [6806, 6807, 6808, 6809, 6810]
MAX_BATCH_SIZE = 8
MEMORY_LIMIT = 10_000
CANDIDATE_LIMIT = 18


@dataclass(frozen=True)
class Request:
    request_id: int
    arrival_time: float
    input_len: int
    output_len: int
    slo_deadline: float
    memory_need: int


@dataclass
class ServedRequest:
    request_id: int
    request_rate: float
    policy: str
    arrival_time: float
    start_time: float
    finish_time: float
    latency: float
    batch_size: int
    slo_deadline: float
    met_slo: bool


def generate_requests(num_requests: int, request_rate: float, seed: int) -> list[Request]:
    rng = random.Random(seed)
    requests: list[Request] = []
    now = 0.0

    for request_id in range(num_requests):
        now += rng.expovariate(request_rate)

        if rng.random() < 0.70:
            input_len = rng.randint(80, 700)
            output_len = rng.randint(40, 450)
        else:
            input_len = rng.randint(700, 2600)
            output_len = rng.randint(450, 1700)

        single_time = predict_single_request_time(input_len, output_len)

        # Mixed SLO classes, similar to the paper's motivation: some requests
        # are interactive and strict; others are more tolerant.
        if rng.random() < 0.60:
            slo_deadline = single_time * rng.uniform(1.25, 2.05)
        else:
            slo_deadline = single_time * rng.uniform(2.10, 3.80)

        # Approximate KV-cache pressure from total sequence length.
        memory_need = input_len + output_len
        requests.append(
            Request(
                request_id=request_id,
                arrival_time=now,
                input_len=input_len,
                output_len=output_len,
                slo_deadline=slo_deadline,
                memory_need=memory_need,
            )
        )

    return requests


def predict_single_request_time(input_len: int, output_len: int) -> float:
    return 0.08 + 0.00045 * input_len + 0.0032 * output_len


def predict_batch_time(batch: list[Request]) -> float:
    batch_size = len(batch)
    max_input = max(req.input_len for req in batch)
    max_output = max(req.output_len for req in batch)

    # Transparent approximation of LLM batch latency:
    # prefill follows the largest prompt in the batch; decode follows the
    # largest output length, with a small batch-size overhead.
    prefill = 0.08 + 0.00045 * max_input + 0.018 * batch_size
    decode = (0.0032 * max_output) * (1.0 + 0.035 * (batch_size - 1))
    return prefill + decode


def make_batches(order: list[Request], target_batch_size: int) -> list[list[Request]]:
    batches: list[list[Request]] = []
    batch: list[Request] = []
    memory = 0

    for req in order:
        would_exceed_batch = len(batch) >= target_batch_size
        would_exceed_memory = memory + req.memory_need > MEMORY_LIMIT
        if batch and (would_exceed_batch or would_exceed_memory):
            batches.append(batch)
            batch = []
            memory = 0
        batch.append(req)
        memory += req.memory_need

    if batch:
        batches.append(batch)

    return batches


def objective(order: list[Request], target_batch_size: int, now: float) -> float:
    time = now
    met_count = 0
    latency_sum = 0.0

    for batch in make_batches(order, target_batch_size):
        finish = time + predict_batch_time(batch)
        for req in batch:
            latency = finish - req.arrival_time
            latency_sum += latency
            if latency <= req.slo_deadline:
                met_count += 1
        time = finish

    if latency_sum <= 0:
        return 0.0
    return met_count / latency_sum


def simulated_annealing_schedule(candidates: list[Request], now: float, seed: int) -> tuple[list[Request], int]:
    rng = random.Random(seed)

    fcfs_order = sorted(candidates, key=lambda req: (req.arrival_time, req.request_id))
    edf_order = sorted(candidates, key=lambda req: (req.arrival_time + req.slo_deadline, req.request_id))
    initial_batch = min(MAX_BATCH_SIZE, max(1, len(candidates)))

    current_order = max(
        (fcfs_order, edf_order),
        key=lambda order: objective(order, initial_batch, now),
    )
    current_batch = initial_batch
    current_score = objective(current_order, current_batch, now)

    best_order = list(current_order)
    best_batch = current_batch
    best_score = current_score

    temperature = 1.0
    min_temperature = 0.01
    cooling = 0.86

    while temperature > min_temperature:
        for _ in range(50):
            new_order = list(current_order)
            new_batch = current_batch

            mutation = rng.random()
            if mutation < 0.55 and len(new_order) >= 2:
                i, j = rng.sample(range(len(new_order)), 2)
                new_order[i], new_order[j] = new_order[j], new_order[i]
            elif mutation < 0.85 and len(new_order) >= 2:
                i, j = rng.sample(range(len(new_order)), 2)
                item = new_order.pop(i)
                new_order.insert(j, item)
            else:
                new_batch = min(MAX_BATCH_SIZE, max(1, new_batch + rng.choice([-1, 1])))

            new_score = objective(new_order, new_batch, now)
            delta = new_score - current_score
            accept = delta >= 0 or rng.random() < math.exp(delta / max(temperature, 1e-9))

            if accept:
                current_order = new_order
                current_batch = new_batch
                current_score = new_score

            if new_score > best_score:
                best_order = list(new_order)
                best_batch = new_batch
                best_score = new_score

        temperature *= cooling

    return best_order, best_batch


def simulate_policy(requests: list[Request], request_rate: float, policy: str, seed: int = RANDOM_SEED) -> list[ServedRequest]:
    ordered = sorted(requests, key=lambda req: req.arrival_time)
    idx = 0
    ready: list[Request] = []
    time = 0.0
    served: list[ServedRequest] = []
    sa_round = 0

    while idx < len(ordered) or ready:
        if not ready and idx < len(ordered) and time < ordered[idx].arrival_time:
            time = ordered[idx].arrival_time

        while idx < len(ordered) and ordered[idx].arrival_time <= time:
            ready.append(ordered[idx])
            idx += 1

        if policy == "FCFS":
            selected_order = sorted(ready, key=lambda req: (req.arrival_time, req.request_id))
            batch = make_batches(selected_order, MAX_BATCH_SIZE)[0]
        elif policy == "SLO-aware-SA":
            candidates = sorted(ready, key=lambda req: (req.arrival_time, req.request_id))[:CANDIDATE_LIMIT]
            scheduled_order, target_batch_size = simulated_annealing_schedule(
                candidates,
                time,
                seed=seed + int(request_rate * 1000) + sa_round,
            )
            batch = make_batches(scheduled_order, target_batch_size)[0]
            sa_round += 1
        else:
            raise ValueError(f"Unknown policy: {policy}")

        batch_ids = {req.request_id for req in batch}
        ready = [req for req in ready if req.request_id not in batch_ids]

        start = time
        finish = start + predict_batch_time(batch)
        for req in batch:
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
                    batch_size=len(batch),
                    slo_deadline=req.slo_deadline,
                    met_slo=latency <= req.slo_deadline,
                )
            )
        time = finish

    return served


def summarize(served: list[ServedRequest]) -> dict[str, float | str]:
    latencies = sorted(req.latency for req in served)
    met_count = sum(1 for req in served if req.met_slo)
    n = len(served)
    return {
        "request_rate": served[0].request_rate,
        "policy": served[0].policy,
        "num_requests": n,
        "slo_attainment": met_count / n,
        "average_latency": sum(latencies) / n,
        "p95_latency": latencies[max(0, math.ceil(0.95 * n) - 1)],
        "average_batch_size": sum(req.batch_size for req in served) / n,
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
                "slo_deadline",
                "memory_need",
            ],
        )
        writer.writeheader()
        for req in requests:
            writer.writerow(req.__dict__)


def write_served(path: Path, served: list[ServedRequest]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(served[0].__dict__.keys()))
        writer.writeheader()
        for req in served:
            writer.writerow(req.__dict__)


def write_results(path: Path, rows: list[dict[str, float | str]]) -> None:
    fieldnames = [
        "seed",
        "request_rate",
        "policy",
        "num_requests",
        "slo_attainment",
        "average_latency",
        "p95_latency",
        "average_batch_size",
        "num_runs",
        "slo_attainment_mean",
        "slo_attainment_std",
        "average_latency_mean",
        "average_latency_std",
        "p95_latency_mean",
        "p95_latency_std",
        "average_batch_size_mean",
        "average_batch_size_std",
    ]
    used_fields = [field for field in fieldnames if any(field in row for row in rows)]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=used_fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def summarize_across_seeds(rows: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    keys = sorted({(float(row["request_rate"]), str(row["policy"])) for row in rows})
    summary: list[dict[str, float | str]] = []
    metrics = ["slo_attainment", "average_latency", "p95_latency", "average_batch_size"]

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


def write_summary(path: Path, rows: list[dict[str, float | str]]) -> None:
    fieldnames = [
        "request_rate",
        "policy",
        "num_runs",
        "num_requests",
        "slo_attainment_mean",
        "slo_attainment_std",
        "average_latency_mean",
        "average_latency_std",
        "p95_latency_mean",
        "p95_latency_std",
        "average_batch_size_mean",
        "average_batch_size_std",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_svg(path: Path, rows: list[dict[str, float | str]], metric: str, title: str, y_label: str, y_max: float | None = None) -> None:
    width, height = 900, 560
    left, right, top, bottom = 82, 44, 58, 104
    plot_w = width - left - right
    plot_h = height - top - bottom
    rates = sorted({float(row["request_rate"]) for row in rows})
    policies = ["FCFS", "SLO-aware-SA"]
    colors = {"FCFS": "#8f3f2f", "SLO-aware-SA": "#245b7a"}
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
            f'<rect x="{width - 190}" y="68" width="14" height="14" fill="{colors["FCFS"]}"/>',
            f'<text x="{width - 168}" y="80" font-family="Arial" font-size="13" fill="#222">FCFS</text>',
            f'<rect x="{width - 190}" y="94" width="14" height="14" fill="{colors["SLO-aware-SA"]}"/>',
            f'<text x="{width - 168}" y="106" font-family="Arial" font-size="13" fill="#222">SLO-aware-SA</text>',
            '<text x="82" y="540" font-family="Arial" font-size="10.5" fill="#555">Synthetic workload generated by our group; simulated annealing reproduction of scheduling effect.</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    request_rates = [0.20, 0.26, 0.32, 0.38, 0.44, 0.50]
    rows: list[dict[str, float | str]] = []
    all_served: list[ServedRequest] = []

    for seed in SEEDS:
        for rate in request_rates:
            requests = generate_requests(num_requests=260, request_rate=rate, seed=seed + int(rate * 1000))
            if seed == SEEDS[0] and rate == request_rates[0]:
                write_workload(OUT_DIR / "workload.csv", requests)

            for policy in ["FCFS", "SLO-aware-SA"]:
                served = simulate_policy(requests, rate, policy, seed=seed)
                row = summarize(served)
                row["seed"] = seed
                rows.append(row)
                all_served.extend(served)

    summary_rows = summarize_across_seeds(rows)
    write_results(OUT_DIR / "results_by_seed.csv", rows)
    write_results(OUT_DIR / "results.csv", summary_rows)
    write_summary(OUT_DIR / "results_summary.csv", summary_rows)
    write_served(OUT_DIR / "served_requests.csv", all_served)
    make_svg(OUT_DIR / "slo_attainment.svg", summary_rows, "slo_attainment", "FCFS vs Simulated-Annealing SLO-aware Scheduling", "SLO attainment", y_max=1.0)
    make_svg(OUT_DIR / "average_latency.svg", summary_rows, "average_latency", "Average Latency under Increasing Request Rate", "Average latency (s)")

    print(f"Wrote outputs to: {OUT_DIR}")
    for row in summary_rows:
        print(
            f"rate={row['request_rate']:.2f}, policy={row['policy']}, "
            f"SLO={row['slo_attainment_mean']:.3f}±{row['slo_attainment_std']:.3f}, "
            f"avg_latency={row['average_latency_mean']:.3f}±{row['average_latency_std']:.3f}s, "
            f"avg_batch={row['average_batch_size_mean']:.2f}"
        )


if __name__ == "__main__":
    main()
