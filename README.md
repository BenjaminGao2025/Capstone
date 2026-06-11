# LLM Scheduling Capstone

FDU MSACS Capstone project (CSCI 6806 / INFO 4205, Summer 2026) on latency-aware
LLM serving. The current experiment compares the FCFS scheduler in vLLM with
the learning-to-rank (LTR) scheduler from
[vllm-ltr](https://github.com/hao-ai-lab/vllm-ltr).

The committed smoke test uses `facebook/opt-1.3b` to verify the complete
pipeline before running the larger Llama workload. It is a functional check,
not a statistically meaningful performance claim.

## Repository Layout

```text
.
├── scripts/                 # data, benchmark, sweep, and plotting helpers
├── results/                 # committed benchmark JSON files
├── figures/                 # generated plots
├── docs/                    # roadmap, papers, notes, and presentation material
└── report/                  # presentation artifacts
```

## Reference Environment

The smoke results in this repository were produced with:

- `vllm-ltr` commit `13bbf6ff`
- Python 3.11.8, using the system `pip` rather than Conda
- PyTorch `2.2.1+cu121`
- CUDA 12.1
- NVIDIA GeForce RTX 3090, 24 GB
- XFormers attention with `--enforce-eager`; FlashAttention was not installed

The serving engine must be built on a CUDA Linux host. Plot generation can be
run separately on macOS or Linux.

## Reproduction

### 1. Build vllm-ltr

The working setup used Python 3.11.8 and the system `pip`. Check out the pinned
revision, install PyTorch for CUDA 12.1, build from source, and then pin the
legacy-compatible Transformers and FastAPI versions:

```bash
git clone https://github.com/hao-ai-lab/vllm-ltr.git
cd vllm-ltr
git checkout 13bbf6ff

python3.11 -m pip install \
  torch==2.2.1+cu121 torchvision==0.17.1+cu121 torchaudio==2.2.1+cu121 \
  --index-url https://download.pytorch.org/whl/cu121
pip install -e .
pip install transformers==4.40.1 fastapi==0.110.3
pip install numpy==1.26.4 fschat accelerate gcsfs scikit-learn scipy \
  matplotlib evaluate
```

Do not install `flash-attn` for this setup. The tested runtime uses XFormers
and the serving scripts pass `--enforce-eager`. The explicit dependency pins
are required because current `pip` resolution can select Transformers 5.x and
FastAPI 0.136, which are incompatible with the vLLM 0.4.1 code at this pinned
revision and cause build or runtime failures. A Conda environment with Python
3.10 remains an alternative, but it was not used for the committed smoke run.

Confirm the pinned environment:

```bash
git rev-parse --short=8 HEAD
python -c 'import fastapi, torch, transformers; print(torch.__version__, torch.version.cuda, transformers.__version__, fastapi.__version__)'
```

### 2. Download the trace and predictor

Run these commands from `vllm-ltr/benchmarks`:

```bash
huggingface-cli download LLM-ltr/Llama3-Trace \
  --local-dir ./Llama3-Trace --repo-type dataset
mv Llama3-Trace/*.jsonl .

mkdir -p MODEL/results
huggingface-cli download LLM-ltr/OPT-Predictors --local-dir MODEL/results
```

The smoke scripts expect the LMSYS trace
`lmsys-Meta-Llama-3-8B-Instruct-t1.0-s0-l8192-c10000-rFalse.jsonl` and the
predictor configuration under `MODEL/results/`.

### 3. Run FCFS and LTR

Set `EXPERIMENT_ROOT` to a writable experiment workspace containing
`vllm-ltr/`. The scripts default to `/hy-tmp`, but the location is configurable:

```bash
export EXPERIMENT_ROOT=/path/to/experiment
export VLLM_LTR_DIR=/path/to/vllm-ltr
export RESULT_DIR="$PWD/results"

bash scripts/run_fcfs.sh
bash scripts/run_ltr.sh
```

The default smoke configuration is:

- model: `facebook/opt-1.3b`
- requests: 50
- request rate: 8
- generated output length: 128 tokens
- random seed: 0

Each script starts the serving process, waits for its health check, runs
`benchmark_serving_real.py`, and writes a JSON result to `RESULT_DIR`.

For the full 8B probe and rate sweep, use:

```bash
bash scripts/run_llama_probe.sh
bash scripts/run_rate_sweep.sh
```

### 4. Plot the comparison

From this repository root:

```bash
python scripts/plot_compare.py results/*.json
```

The plot includes request-latency CDF, mean latency, p99 latency, and normalized
latency in seconds per output token.

## Smoke Result

| Scheduler | Completed | Throughput (req/s) | Mean TTFT (ms) | Mean latency (s) | P99 latency (s) | Mean normalized latency (s/token) |
|-----------|----------:|-------------------:|---------------:|-----------------:|----------------:|----------------------------------:|
| FCFS | 50 | 4.5597 | 129.2 | 4.34 | 5.24 | 0.0377 |
| LTR | 50 | 4.7334 | 154.9 | 4.15 | 5.41 | 0.0394 |

![FCFS versus LTR smoke result](figures/fcfs_vs_ltr.png)

Both runs completed all 50 requests. In this small smoke test, LTR had slightly
lower mean request latency and slightly higher measured throughput, while FCFS
had lower mean TTFT, p99 request latency, and normalized latency. Larger,
repeated runs are required before drawing scheduling conclusions. The near tie
is expected: the predictor was trained to rank Llama-3-8B output lengths, but
its ranking on `facebook/opt-1.3b` is effectively noise (Kendall's Tau about
-0.09), so LTR behaves approximately like random scheduling in this smoke test.

## Project Documents

- [Roadmap](docs/roadmap-v0.1.md)
- [Related-work summaries](docs/related-work/)
- [Presentation material](docs/presentation/)
