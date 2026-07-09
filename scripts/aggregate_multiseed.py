import glob
import json
import numpy as np
import os

def process_file(path):
    with open(path) as f:
        d = json.load(f)
    
    completed = d["completed"]
    # TTFTs are in d["ttfts"]
    ttfts = np.array(d["ttfts"])
    mean_ttft = d.get("mean_ttft_ms", ttfts.mean()) / 1000.0
    p99_ttft = d.get("p99_ttft_ms", np.percentile(ttfts, 99)) / 1000.0 if len(ttfts) > 0 else 0
    return {"completed": completed, "mean_ttft": mean_ttft, "p99_ttft": p99_ttft}

def analyze():
    results = {}
    for rate in [4, 8]:
        for arm in ["fcfs", "ltr", "v1"]:
            if rate == 8 and arm == "ltr":
                seeds = [1] # Only crash run
            else:
                seeds = [0, 1, 2]
            
            stats = {"completed": [], "mean_ttft": [], "p99_ttft": []}
            for seed in seeds:
                path = f"results/llama3-8b/p2/part2_r{rate}_{arm}_seed{seed}.json"
                if os.path.exists(path):
                    res = process_file(path)
                    for k in stats:
                        stats[k].append(res[k])
                else:
                    print(f"Missing {path}")
            
            if stats["completed"]:
                results[f"r{rate}_{arm}"] = {
                    "completed_mean": np.mean(stats["completed"]),
                    "mean_ttft_mean": np.mean(stats["mean_ttft"]),
                    "mean_ttft_std": np.std(stats["mean_ttft"]),
                    "p99_ttft_mean": np.mean(stats["p99_ttft"]),
                    "p99_ttft_std": np.std(stats["p99_ttft"])
                }
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    analyze()
