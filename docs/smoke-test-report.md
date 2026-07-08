---

## Smoke Test: vLLM-LTR Reproduction Pipeline

### 1. Purpose

This smoke test verifies that the vLLM-LTR reproduction pipeline can run end-to-end before launching the full Llama-3-8B experiment. The goal is not to make a final performance claim, but to confirm that the environment, vLLM server, benchmark client, LMSYS trace, predictor configuration, and result-writing pipeline are all working correctly.

The original LLM scheduling paper studies latency reduction for LLM inference serving. Its main idea is to improve over FCFS scheduling by using a learning-to-rank scheduler. Instead of processing requests only in arrival order, the LTR scheduler predicts the expected output length of incoming prompts and prioritizes requests that are expected to finish earlier. This smoke test follows the same basic comparison:

* **FCFS**: first-come-first-served baseline scheduler.
* **LTR / opt-xxx**: predictor-based scheduling using an OPT predictor configuration.

This test is smaller than the full paper reproduction. It uses `facebook/opt-1.3b`, 20 prompts, and one request rate. Therefore, it should be treated as a functional validation test rather than a final performance result.

### 2. Environment

| Item                    | Setting                                                            |
| ----------------------- | ------------------------------------------------------------------ |
| Platform                | RunPod                                                             |
| GPU                     | NVIDIA GeForce RTX 3090 24GB                                       |
| Python                  | 3.11.15                                                            |
| PyTorch                 | 2.2.1+cu121                                                        |
| CUDA visible to PyTorch | 12.1                                                               |
| Transformers            | 4.40.1                                                             |
| FastAPI                 | 0.110.3                                                            |
| Repository              | `hao-ai-lab/vllm-ltr`                                              |
| Commit                  | `13bbf6ff`                                                         |
| Test model              | `facebook/opt-1.3b`                                                |
| Dataset trace           | `lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-18192-c10000-rFalse.jsonl` |
| Number of prompts       | 20                                                                 |
| Request rate            | 2.0 qps                                                            |
| Output length           | 128 tokens                                                         |

### 3. Setup Commands

The repository was cloned and fixed to the target commit:

```bash
cd /workspace
git clone https://github.com/hao-ai-lab/vllm-ltr.git
cd vllm-ltr
git checkout 13bbf6ff
```

A Python 3.11 virtual environment was created:

```bash
python3.11 -m venv vllm-ltr-env
source vllm-ltr-env/bin/activate
python -m pip install --upgrade pip
```

PyTorch with CUDA 12.1 was installed:

```bash
python -m pip install \
  torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
```

The GPU setup was verified with:

```bash
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

Expected output:

```text
2.2.1+cu121 12.1 True
```

The project dependencies were installed:

```bash
pip install -e .
pip install transformers==4.40.1 fastapi==0.110.3
pip install numpy==1.26.4 fschat accelerate gcsfs scikit-learn scipy matplotlib evaluate huggingface_hub
```

The trace and predictor files were downloaded:

```bash
cd benchmarks

export HF_HUB_ENABLE_HF_TRANSFER=0

huggingface-cli download LLM-ltr/Llama3-Trace \
  --local-dir ./Llama3-Trace --repo-type dataset

find Llama3-Trace -name "*.jsonl" -exec mv {} . \;

mkdir -p MODEL/results

huggingface-cli download LLM-ltr/OPT-Predictors \
  --local-dir MODEL/results
```

### 4. FCFS Smoke Test

The FCFS server was launched with:

```bash
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model facebook/opt-1.3b \
  --swap-space 16 \
  --disable-log-requests \
  --schedule-type fcfs \
  --enable-chunked-prefill \
  --enforce-eager \
  --port 3343 &
```

The benchmark was run with:

```bash
DATASET=$(ls lmsys-Meta-Llama-3-8B-Instruct-*c10000*.jsonl | head -n 1)

python benchmark_serving_real.py \
  --backend vllm \
  --model facebook/opt-1.3b \
  --tokenizer facebook/opt-1.3b \
  --dataset "$DATASET" \
  --num-prompts 20 \
  --request-time 30 \
  --schedule-type fcfs \
  --output-len 128 \
  --request-rate 2 \
  --result-dir RESULTS \
  --port 3343
```

After the benchmark finished, the server was stopped:

```bash
pkill -f "api_server"
```

### 5. LTR / opt-xxx Smoke Test

The LTR / opt-xxx server was launched with the OPT predictor configuration:

```bash
CUDA_VISIBLE_DEVICES=0 python -m vllm.entrypoints.openai.api_server \
  --model facebook/opt-1.3b \
  --swap-space 32 \
  --disable-log-requests \
  --schedule-type opt-xxx \
  --enable-chunked-prefill \
  --enforce-eager \
  --prefill-predictor-model-config MODEL/results/opt-125m-llama3-8b-lmsys-score-trainbucket10-b32/usage_config.json \
  --port 3343 &
```

The benchmark was run with:

```bash
DATASET=$(ls lmsys-Meta-Llama-3-8B-Instruct-*c10000*.jsonl | head -n 1)

python benchmark_serving_real.py \
  --backend vllm \
  --model facebook/opt-1.3b \
  --tokenizer facebook/opt-1.3b \
  --dataset "$DATASET" \
  --num-prompts 20 \
  --request-time 30 \
  --schedule-type opt-xxx \
  --output-len 128 \
  --request-rate 2 \
  --result-dir RESULTS \
  --port 3343
```

The server was stopped after the test:

```bash
pkill -f "api_server"
```

### 6. Results

Both schedulers completed all 20 requests.

| Metric             |         FCFS | LTR / opt-xxx |
| ------------------ | -----------: | ------------: |
| Completed requests |        20/20 |         20/20 |
| Request throughput | 1.5997 req/s |  1.5748 req/s |
| Mean TTFT          |    1474.0 ms |      370.2 ms |
| P99 TTFT           |    4731.9 ms |     1925.1 ms |
| Mean TPOT          |     13.74 ms |      18.50 ms |
| P99 TPOT           |     23.06 ms |      20.97 ms |

In this smoke test, LTR / opt-xxx reduced mean TTFT from 1474.0 ms to 370.2 ms, about a 74.9% reduction. It also reduced p99 TTFT from 4731.9 ms to 1925.1 ms, about a 59.3% reduction.

However, FCFS had slightly higher request throughput, and LTR / opt-xxx had higher mean TPOT. Therefore, the result should be interpreted carefully. The test shows that the LTR scheduling path is functioning, but it does not prove the final performance claim.

### 7. Important Figures

The following figures were generated from the smoke test result files:

* `chart_ttft_comparison.png`: compares mean TTFT and p99 TTFT between FCFS and LTR / opt-xxx.
* `chart_throughput_comparison.png`: compares request throughput.
* `chart_tpot_comparison.png`: compares mean TPOT and p99 TPOT.
* `chart_request_latency_distribution.png`: shows the derived request latency distribution.

For presentation, the TTFT comparison figure is the most important because TTFT is closely related to user-perceived responsiveness in LLM serving.

### 8. Interpretation

The smoke test confirms that the reproduction pipeline is working. Both FCFS and LTR / opt-xxx can start the vLLM server, read the same LMSYS trace, complete benchmark requests, and generate valid result files.

The lower TTFT of LTR / opt-xxx is consistent with the motivation of the original LLM scheduling paper: ranking-based scheduling can reduce waiting time by prioritizing requests more intelligently than FCFS. However, because this test uses a small model, only 20 prompts, and one request rate, it should be reported as a functional validation result rather than a final reproduction result.

### 9. Limitations

This smoke test has several limitations:

1. It uses `facebook/opt-1.3b`, not `Meta-Llama-3-8B-Instruct`.
2. It uses only 20 prompts.
3. It tests only one request rate, 2.0 qps.
4. The LTR predictor is associated with Llama-3-8B traces, while the served model is `facebook/opt-1.3b`.
5. It is designed to validate the pipeline, not to replace the full FCFS vs LTR rate sweep.

### 10. Next Steps

The next step is to run the formal reproduction with `Meta-Llama-3-8B-Instruct`. Recommended follow-up experiments include:

1. Run FCFS with the full Llama-3-8B setup.
2. Run LTR / opt-xxx with the same workload.
3. Compare request rates such as 2, 4, 8, 16, and 32 qps.
4. Report mean TTFT, p99 TTFT, throughput, mean latency, p99 latency, and failure cases.
5. Compare in-distribution and out-of-distribution workloads if possible.

### 11. Conclusion

This smoke test successfully validated the vLLM-LTR reproduction pipeline on RunPod. Both FCFS and LTR / opt-xxx completed all requests and produced valid result files. LTR / opt-xxx showed lower mean TTFT and lower p99 TTFT than FCFS in this small test, suggesting that the predictor-based scheduling path is working.

The main conclusion is that the environment and benchmark workflow are ready for the formal Llama-3-8B reproduction.
