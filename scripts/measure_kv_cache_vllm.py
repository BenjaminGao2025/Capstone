import csv
import time
import requests
import subprocess

URL = "http://localhost:8000/v1/completions"
MODEL = "meta-llama/Meta-Llama-3-8B-Instruct"

# 测试不同输入长度和并发 batch size 对 KV Cache 显存占用与延迟的影响
PROMPT_LENGTHS = [128, 256, 512, 1024, 2048]
BATCH_SIZES = [1, 2, 4, 8, 16, 32]

def gpu_memory_mb():
    # 通过 nvidia-smi 获取当前 GPU 已使用显存，单位为 MB
    out = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]
    )
    return int(out.decode().strip().split("\n")[0])

def make_prompt(n_words):
    # 构造指定词数的简单 prompt，便于控制输入长度
    return " ".join(["hello"] * n_words)

def run_batch(prompt_len, batch_size):
    # 为当前 batch 生成相同长度的多个 prompt
    prompts = [make_prompt(prompt_len) for _ in range(batch_size)]

    # 请求前记录显存和时间，用于计算显存增量与端到端延迟
    before = gpu_memory_mb()
    start = time.time()

    payload = {
        "model": MODEL,
        "prompt": prompts,
        "max_tokens": 32,
        "temperature": 0
    }

    try:
        # 调用本地 vLLM OpenAI-compatible completions 接口
        r = requests.post(URL, json=payload, timeout=300)
        latency = time.time() - start
        after = gpu_memory_mb()

        # 非 200 响应通常表示请求失败或显存不足，保留前 200 个字符方便排查
        success = r.status_code == 200
        error = "" if success else r.text[:200]

        return {
            "prompt_len_words": prompt_len,
            "batch_size": batch_size,
            "success": success,
            "latency_sec": round(latency, 3),
            "gpu_mem_before_mb": before,
            "gpu_mem_after_mb": after,
            "gpu_mem_delta_mb": after - before,
            "error": error
        }

    except Exception as e:
        # 网络错误、超时或 nvidia-smi 调用异常都会进入这里
        after = gpu_memory_mb()
        return {
            "prompt_len_words": prompt_len,
            "batch_size": batch_size,
            "success": False,
            "latency_sec": -1,
            "gpu_mem_before_mb": before,
            "gpu_mem_after_mb": after,
            "gpu_mem_delta_mb": after - before,
            "error": str(e)[:200]
        }

def main():
    rows = []

    # 逐组测试：先遍历 prompt 长度，再遍历 batch size
    for prompt_len in PROMPT_LENGTHS:
        for batch_size in BATCH_SIZES:
            print(f"Testing prompt_len={prompt_len}, batch_size={batch_size}")
            row = run_batch(prompt_len, batch_size)
            rows.append(row)

            # 如果某个 batch size 已经失败，继续增大 batch size 意义不大，直接进入下一个 prompt 长度
            if not row["success"]:
                break

            # 给服务一点恢复时间，减少连续请求造成的测量干扰
            time.sleep(2)

    # 将每次实验的延迟、显存和错误信息写入 CSV，方便后续画图或分析
    with open("results/kv_cache_batch_results.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("Saved to results/kv_cache_batch_results.csv")

if __name__ == "__main__":
    main()
