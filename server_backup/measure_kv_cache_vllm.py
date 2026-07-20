import csv
import json
import time
import requests

URL = "http://localhost:8000/v1/completions"
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

PROMPT_LENGTHS = [128, 256, 512, 1024, 2048, 4096]
BATCH_SIZES = [1, 2, 4, 8, 16, 32, 64]

CSV_PATH = "results/kv_cache_batch_results.csv"
JSON_PATH = "results/kv_cache_batch_results.json"


def make_prompt(length):
    return "hello " * length


def test_batch(prompt_length, batch_size):
    prompts = [make_prompt(prompt_length) for _ in range(batch_size)]

    payload = {
        "model": MODEL,
        "prompt": prompts,
        "max_tokens": 32,
        "temperature": 0
    }

    start = time.time()

    try:
        response = requests.post(URL, json=payload, timeout=300)
        latency = time.time() - start

        if response.status_code == 200:
            return True, round(latency, 3), ""

        return False, round(latency, 3), response.text[:300]

    except Exception as e:
        return False, -1, str(e)[:300]


def main():
    results = []

    for prompt_length in PROMPT_LENGTHS:
        max_success_batch = 0
        last_success_latency = None
        failed_batch = None
        error_message = ""

        for batch_size in BATCH_SIZES:
            print(f"Testing prompt_length={prompt_length}, batch_size={batch_size}")

            success, latency, error = test_batch(prompt_length, batch_size)

            if success:
                print(f"OK: prompt_length={prompt_length}, batch_size={batch_size}, latency={latency}s")
                max_success_batch = batch_size
                last_success_latency = latency
            else:
                print(f"FAIL: prompt_length={prompt_length}, batch_size={batch_size}")
                failed_batch = batch_size
                error_message = error
                break

            time.sleep(2)

        results.append({
            "model": MODEL,
            "prompt_length": prompt_length,
            "max_success_batch_size": max_success_batch,
            "first_failed_batch_size": failed_batch,
            "last_success_latency_sec": last_success_latency,
            "error": error_message
        })

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "model",
                "prompt_length",
                "max_success_batch_size",
                "first_failed_batch_size",
                "last_success_latency_sec",
                "error"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    with open(JSON_PATH, "w") as f:
        json.dump(results, f, indent=4)

    print(f"Saved CSV to {CSV_PATH}")
    print(f"Saved JSON to {JSON_PATH}")


if __name__ == "__main__":
    main()