# GPU Server Backup (`/hy-tmp`)

This directory contains a backup of the crucial files from the rented GPU machine (`i-2.gpushare.com`), specifically taken before shutting down the instance to save costs.

## Contents
- `results/`: Contains the `.json` output metrics of all `vllm-*.json` sweeps (Rate 4, Rate 8, FCFS baselines), `sanity.log`, and `preempt_sweep*.log`.
- `scripts/`: Contains the `run_*.sh` execution scripts used to boot the server and start the benchmarks.

## Restoration Guide
When booting a new 3090 instance for the Capstone:
1. **Transfer Scripts**: Run `scp -r capstoneGitHub/server_backup/scripts/* root@<new-ip>:/hy-tmp/scripts/` to restore the run scripts.
2. **Clone Repo**: Re-clone the `feat/aging-gate-validation` branch to the new server to get the cleaned code.
3. **Environment**: Ensure that the datasets (`.jsonl`), the tokenizer, and the models are placed in the appropriate `/hy-tmp/models/` directories.
