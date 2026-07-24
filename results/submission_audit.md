| experiment_id | phase | arm | rate | seed | predictor | train_dist | test_dist | relation | completed/expected | SHA status | eligible | audit_verdict | warnings |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sweep-r2-fcfs | sweep | fcfs | 2.0 | 0 | None | None | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r2-ltr | sweep | ltr | 2.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r4-fcfs | sweep | fcfs | 4.0 | 0 | None | None | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r4-ltr | sweep | ltr | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r8-fcfs | sweep | fcfs | 8.0 | 0 | None | None | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r8-ltr | sweep | ltr | 8.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r16-fcfs | sweep | fcfs | 16.0 | 0 | None | None | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r16-ltr | sweep | ltr | 16.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r32-fcfs | sweep | fcfs | 32.0 | 0 | None | None | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| sweep-r32-ltr | sweep | ltr | 32.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| ood-r4-fcfs | ood_characterization | fcfs | 4.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| ood-r4-ltr | ood_characterization | ltr | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| ood-r8-fcfs | ood_characterization | fcfs | 8.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| ood-r8-ltr-crash | ood_characterization | ltr | 8.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 15/500 | PASS | False | PASS | generated_texts found in results |
| phaseA-r4-fcfs | A | fcfs | 4.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseA-r4-ltr | A | ltr | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseA-r4-aging120 | A | ltr-aging-120 | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseA-r8-fcfs | A | fcfs | 8.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseC-r4-protect30 | C | v1-gate30 | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseC-r4-protect60 | C | v1-gate60 | 4.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseC-r8-protect30 | C | v1-gate30 | 8.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseC-r8-protect60 | C | v1-gate60 | 8.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS | generated_texts found in results |
| v1val-r8-fcfs | A | fcfs | 8.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| v1val-r8-v1 | A | v1 | 8.0 | 0 | opt-125m-llama3-8b-lmsys-score-trainbucket10-b32 | lmsys | sharegpt | ood | 500/500 | PASS | True | PASS |  |
| ablation-r8-ourshead | ablation | ltr-ourshead | 8.0 | 0 | internal-head (EGTP) | lmsys | lmsys | in_distribution | 500/500 | PASS | True | PASS | generated_texts found in results |
| phaseD-r4-fcfs-seed0 | D | fcfs | 4.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r4-fcfs-seed1 | D | fcfs | 4.0 | 1 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r4-fcfs-seed2 | D | fcfs | 4.0 | 2 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r4-ltr-seed0 | D | ltr | 4.0 | 0 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r4-ltr-seed1 | D | ltr | 4.0 | 1 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r4-ltr-seed2 | D | ltr | 4.0 | 2 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r4-v1-seed0 | D | v1 | 4.0 | 0 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r4-v1-seed1 | D | v1 | 4.0 | 1 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r4-v1-seed2 | D | v1 | 4.0 | 2 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r8-fcfs-seed0 | D | fcfs | 8.0 | 0 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r8-fcfs-seed1 | D | fcfs | 8.0 | 1 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r8-fcfs-seed2 | D | fcfs | 8.0 | 2 | None | None | sharegpt | in_distribution | 500/500 | PASS | True | PASS |  |
| phaseD-r8-ltr-seed0 | D | ltr | 8.0 | 0 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 22/500 | PASS | False | PASS |  |
| phaseD-r8-ltr-seed1 | D | ltr | 8.0 | 1 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r8-v1-seed0 | D | v1 | 8.0 | 0 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r8-v1-seed1 | D | v1 | 8.0 | 1 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |
| phaseD-r8-v1-seed2 | D | v1 | 8.0 | 2 | opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32 | sharegpt | sharegpt | matched | 500/500 | PASS | True | PASS |  |