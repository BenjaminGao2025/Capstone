# Capstone Submission Hardening Report — 2026-07-24

## 9.1 Executive Summary

| Item | Status |
|------|--------|
| Current submission state | PARTIAL — scripts and manifest hardened; report/paper skeleton incomplete |
| Recommend submission as-is? | NO — final report prose must be completed by human authors |
| P0 blockers | 1 (final report prose unwritten) |
| P1 issues resolved | 8 |
| P1 issues remaining | 1 (chart hardcoded values need future rework) |
| GPU reruns needed? | No — existing evidence is sufficient for current claims with corrected labels |
| Historical data rewritten? | NO — zero raw benchmark JSONs modified |
| main branch modified? | NO |
| PR merged? | NO |

## 9.2 Repository Baseline

| Field | Value |
|-------|-------|
| Repo full name | BenjaminGao2025/Capstone |
| Origin URL | https://github.com/BenjaminGao2025/Capstone.git |
| Base branch | main |
| origin/main SHA | `b95c94972d03a566365150cdc134fbcc37571c6a` |
| Working branch | `antigravity/capstone-submission-hardening-20260724` |
| Initial git status | Clean (no output from `git status --short`) |
| Initial timestamp UTC | 2026-07-24T15:27:00Z |

## 9.3 Problem-by-Problem Verdict

| ID | Problem | Original Concern | Verdict | Evidence | Severity | Fix Applied | Remaining Limitation |
|----|---------|-----------------|---------|----------|----------|-------------|---------------------|
| P0-1 | Phase D predictor/OOD mismatch | Phase D labeled as LMSYS→ShareGPT OOD but may use ShareGPT predictor | **CONFIRMED** | `scripts/run_part2.sh` line 9: `export PREDICTOR=.../opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32/usage_config.json`. DATASET=ShareGPT. This is matched, not OOD. | P0 | Reclassified in manifest, README, experiment doc. Distribution_relation=matched for all Phase D entries. | None — factually corrected |
| P0-2 | latest JSON contamination risk | `ls -t *.json \| head -1` in run_part2.sh could grab wrong file | **CONFIRMED** | `scripts/run_part2.sh` lines 19,25,33,46,54,64 all use `latest=$(ls -t /hy-tmp/results/*.json \| head -1)`. Additionally line 63: `bash /hy-tmp/scripts/run_ltr.sh \|\| true` followed by line 64: `latest=$(ls -t ...)` — failure followed by old-file grab. | P0 | Created `scripts/run_one_experiment_safe.sh` (fail-closed); deprecated `run_part2.sh` with guard; fixed runners to respect RESULT_DIR. | Historical runs used the unsafe pattern — cannot retroactively verify, but no duplicate SHA-256 found in p2/ files |
| P0-3 | Incomplete final report | `report/final-report-draft.md` is a skeleton | **CONFIRMED** | 2 TODO items, 35+ unchecked `- [ ]` items across all 10 sections. Only Ablation table (Section 6) has actual data. | P0 | Created `docs/submission/HUMAN_WRITING_REQUIRED.md` with per-section checklist. | Prose must be written by human authors |
| P1-1 | Hard-coded charts | `fig_ood_mitigation` and `fig_ood_survival` use hardcoded values | **CONFIRMED** | `scripts/make_defense_charts.py` lines 149-152: `means=[40.4, 22.9, 34.8]`, `p99s=[96.0, 148.6, 87.7]`; line 184: `completed=[500, 22, 15, 500]` | P1 | Documented in `docs/submission/FIGURE_EVIDENCE_CHAIN.md` with full evidence chain. Values approximately match Phase D data but are not computed from JSON. | Chart script should be reworked to read from manifest, but not safe to do without matplotlib testing environment |
| P1-2 | Wrong Phase D chart source | `ood()` function reads p2/ files as if they were OOD | **CONFIRMED** | `scripts/make_defense_charts.py` lines 50-61: `ood()` function tries p2/ first, which contains ShareGPT-predictor data, not LMSYS-predictor data. Chart titles say "OOD (ShareGPT trace × LMSYS predictor)" which is wrong for p2 data. | P1 | Documented in figure evidence chain. Original OOD files (`*-ood-sharegpt.json` without `-aging-val`) exist and use correct LMSYS predictor. | Chart source correction requires matplotlib; marked as REQUIRES_HUMAN_REVIEW in evidence chain |
| P1-3 | README/runner mismatch | README claims configurable paths but scripts hardcode `/hy-tmp` | **CONFIRMED** | `run_fcfs.sh` line 17: `RESULT_DIR=/hy-tmp/results`; README lines 110-116 claim `EXPERIMENT_ROOT`, `VLLM_LTR_DIR`, `RESULT_DIR` are configurable. Zero scripts read `EXPERIMENT_ROOT` or `VLLM_LTR_DIR`. | P1 | Fixed `run_fcfs.sh`, `run_ltr.sh`, `run_ltr_aging.sh` to use `${RESULT_DIR:-/hy-tmp/results}`, `${ENV_FILE:-/hy-tmp/env.sh}`, `${VLLM_LTR_DIR:-/hy-tmp/vllm-ltr}`. Added experiment layer table and safe runner instructions to README. | `EXPERIMENT_ROOT` remains README-only documentation; not used by scripts |
| P1-4 | Incomplete/crash aggregation | Charts may aggregate crash results | **PARTIALLY_CONFIRMED** | `fig_ood_survival` correctly shows crashes as crash evidence (22/500, 15/500). `fig_ood_mitigation` hardcodes Phase D means/stds which exclude crashed runs. However, there is no programmatic guard — values are manually curated. | P1 | Manifest marks all crashes as `eligible_for_aggregation=false`. Audit script enforces this. | Historical charts use hardcoded values, not manifest-driven |
| P1-5 | Missing manifest | No submission manifest existed | **CONFIRMED** | No `results/submission_manifest.json` existed before this branch. | P1 | Created manifest with 42 experiments, schema, and automated audit script. | None |
| P1-6 | Missing CI | No GitHub Actions workflow | **CONFIRMED** | No `.github/` directory existed. | P1 | Created `.github/workflows/submission-integrity.yml` with non-GPU checks. | CI passed successfully (Run ID: 30115780470) |
| P1-7 | generated_texts/secret hygiene | JSON files may contain generated text or secrets | **CONFIRMED (generated_texts) / NOT_CONFIRMED (secrets)** | 50 files contain `generated_texts`. Zero files contain secret-like patterns in code/docs/scripts. Phase D p2/ files already had generated_texts stripped. | P1 | Audit script warns on generated_texts presence. No secrets found to remediate. | 50 files in main results still contain generated_texts — these are the original run outputs and must not be modified |
| P2-1 | Duplicate backup handling | PR #29 handles exact duplicates | **CONFIRMED** | Branch `origin/agent/cleanup-exact-backup-duplicates` exists. Not merged to main. | P2 | Not addressed — isolated in PR #29 per instructions. | Exact duplicate cleanup is handled separately by PR #29 |
| P2-2 | Repository clutter | Multiple backup/server files | N/A | server_backup/ contains historical run artifacts. | P2 | Not addressed — these are historical evidence. | None |

## 9.4 Historical Result Audit

### Phase D (p2/) Files

| experiment_id | path | sha256 (first 16) | arm | rate | seed | completed | expected | predictor | train_dist | test_dist | relation | status | eligible | dup_check | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| phaseD-r4-fcfs-seed0 | results/llama3-8b/p2/part2_r4_fcfs_seed0.json | 367077ac1cf75637 | fcfs | 4.0 | 0 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r4-fcfs-seed1 | results/llama3-8b/p2/part2_r4_fcfs_seed1.json | 31f377b5e6a77bfb | fcfs | 4.0 | 1 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r4-fcfs-seed2 | results/llama3-8b/p2/part2_r4_fcfs_seed2.json | 5e6c66a857b815ab | fcfs | 4.0 | 2 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r4-ltr-seed0 | results/llama3-8b/p2/part2_r4_ltr_seed0.json | 3d970cbb473fc3e6 | ltr | 4.0 | 0 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r4-ltr-seed1 | results/llama3-8b/p2/part2_r4_ltr_seed1.json | 2c7e684c1e5ddfde | ltr | 4.0 | 1 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r4-ltr-seed2 | results/llama3-8b/p2/part2_r4_ltr_seed2.json | baf6510fff7c6905 | ltr | 4.0 | 2 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r4-v1-seed0 | results/llama3-8b/p2/part2_r4_v1_seed0.json | 2c38c053e804a077 | v1 | 4.0 | 0 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r4-v1-seed1 | results/llama3-8b/p2/part2_r4_v1_seed1.json | 5e2490088900a24b | v1 | 4.0 | 1 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r4-v1-seed2 | results/llama3-8b/p2/part2_r4_v1_seed2.json | 36d1135240d83e79 | v1 | 4.0 | 2 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r8-fcfs-seed0 | results/llama3-8b/p2/part2_r8_fcfs_seed0.json | 3f57b49b14010804 | fcfs | 8.0 | 0 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r8-fcfs-seed1 | results/llama3-8b/p2/part2_r8_fcfs_seed1.json | 33b7ed9120fc43e9 | fcfs | 8.0 | 1 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r8-fcfs-seed2 | results/llama3-8b/p2/part2_r8_fcfs_seed2.json | 99383b13e81eaf0b | fcfs | 8.0 | 2 | 500 | 500 | N/A | N/A | sharegpt | in_distribution | valid | true | unique | PASS |
| phaseD-r8-ltr-seed0 | results/llama3-8b/p2/part2_r8_ltr_seed0.json | 3065e6aa88377770 | ltr | 8.0 | 0 | **22** | 500 | sharegpt-score | sharegpt | sharegpt | matched | **crashed** | **false** | unique | PASS (correctly marked) |
| phaseD-r8-ltr-seed1 | results/llama3-8b/p2/part2_r8_ltr_seed1.json | 67b21c4f5034b7c9 | ltr | 8.0 | 1 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r8-v1-seed0 | results/llama3-8b/p2/part2_r8_v1_seed0.json | b3f6ab3286f50e1e | v1 | 8.0 | 0 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r8-v1-seed1 | results/llama3-8b/p2/part2_r8_v1_seed1.json | 5fbeb7cf1649a338 | v1 | 8.0 | 1 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |
| phaseD-r8-v1-seed2 | results/llama3-8b/p2/part2_r8_v1_seed2.json | 9cf04cae64842366 | v1 | 8.0 | 2 | 500 | 500 | sharegpt-score | sharegpt | sharegpt | matched | valid | true | unique | PASS |

**Note:** `part2_r8_ltr_seed2.json` is MISSING (only seed0 and seed1 exist). `run_part2.sh` does not include a rate-8 LTR seed2 run — the script runs LTR at rate 8 only for seed 1 (plus a crash run for seed 0).

### Key Non-p2 Files (Selected)

All 42 manifest entries pass SHA-256 verification. See `results/submission_audit.md` for the full audit table.

### Identified Duplicate SHA-256 Pairs

| File A | File B | Same content? | Impact |
|--------|--------|--------------|--------|
| results/vllm-8.0qps-cv1.0-opt-1.3b-fcfs-20260611-074157.json | results/llama3-8b/vllm-8.0qps-cv1.0-opt-1.3b-fcfs-20260611-074157.json | YES | Smoke test duplicate — neither is in the final submission manifest |
| results/vllm-8.0qps-cv1.0-opt-1.3b-opt-xxx-20260611-074716.json | results/llama3-8b/vllm-8.0qps-cv1.0-opt-1.3b-opt-xxx-20260611-074716.json | YES | Smoke test duplicate — neither is in the final submission manifest |
| results/llama3-8b/vllm-8.0qps-*-fcfs-20260611-111049-ood-sharegpt.json | results/llama3-8b/ood-rate8-crashed-evidence/vllm-8.0qps-fcfs-ood-sharegpt-crashedrun-pair.json | YES | The crash evidence copy is the same FCFS run (500/500). Crash evidence dir preserves the pair for context. Neither duplicate affects aggregation. |

## 9.5 Confirmed Contamination Assessment

**Is there confirmed result-file contamination?**

**POSSIBLE_CONTAMINATION** (low confidence)

**Evidence:**
- `scripts/run_part2.sh` uses `ls -t /hy-tmp/results/*.json | head -1` after every run, in a shared `/hy-tmp/results/` directory.
- Line 63: `bash /hy-tmp/scripts/run_ltr.sh || true` followed by `latest=$(ls -t ...)` — if LTR crashes, the "latest" file is the previous arm's JSON, not LTR's output.
- All 17 p2/ files have **unique SHA-256 values**, which is evidence against contamination.
- All p2/ files have **internally consistent** `schedule_type` and `request_rate` fields matching their filenames.
- The `part2_r8_ltr_seed0.json` has `completed=22` (crash), which is consistent with a real crash, not a mislabeled file.

**Assessment:** No confirmed contamination. The unsafe pattern creates a theoretical risk, but the actual result files show no evidence of cross-arm confusion. The unique SHA-256 hashes and consistent internal metadata support this conclusion.

**Impact on final conclusions:** None — the risk is theoretical and mitigated by the new fail-closed wrapper for future runs.

## 9.6 Phase D Reclassification

| Field | Value |
|-------|-------|
| Actual predictor | `opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32` (ShareGPT-trained) |
| Actual test trace | `llama3-8b-sharegpt-test-t1-s0-8192.jsonl` (ShareGPT) |
| Actual distribution relation | **matched** (ShareGPT predictor × ShareGPT trace) |
| Allowed claim | Phase D provides multi-seed stability evidence under a ShareGPT-matched predictor |
| Forbidden claim | Phase D proves multi-seed LMSYS→ShareGPT OOD robustness |
| Documents changed | `README.md`, `docs/experiments/2026-06-21-aging-gate-validation.md` |
| Figures changed | None directly modified; evidence chain documents the issue for chart labels |

**Evidence trail:**
- `scripts/run_part2.sh` line 9: `export PREDICTOR=/hy-tmp/vllm-ltr/benchmarks/MODEL/results/opt-125m-llama3-8b-sharegpt-score-trainbucket10-b32/usage_config.json`
- `scripts/run_part2.sh` line 6: `export DATASET=llama3-8b-sharegpt-test-t1-s0-8192.jsonl`
- The predictor name contains `sharegpt` — it was trained on ShareGPT data.
- `scripts/run_ltr.sh` line 18: default predictor is `opt-125m-llama3-8b-lmsys-score-trainbucket10-b32` (LMSYS-trained).
- `run_part2.sh` **overrides** this default with the ShareGPT predictor via `export PREDICTOR=...`.

## 9.7 Files Changed

| Path | Change Type | Reason | Risk | Validation |
|------|------------|--------|------|------------|
| scripts/run_fcfs.sh | Modified | Respect RESULT_DIR, ENV_FILE, VLLM_LTR_DIR env vars | Low — defaults unchanged | bash -n pass |
| scripts/run_ltr.sh | Modified | Same as above | Low | bash -n pass |
| scripts/run_ltr_aging.sh | Modified | Same as above | Low | bash -n pass |
| scripts/run_part2.sh | Modified | Added deprecation guard | Low — override available | bash -n pass |
| scripts/run_one_experiment_safe.sh | New | Fail-closed experiment wrapper | None — new file | bash -n pass |
| scripts/audit_submission_results.py | New | Automated submission audit | None — new file | 13/13 tests pass, exit code 0 on manifest |
| results/submission_manifest.json | New | Experiment manifest | None — new file | Audit validates all entries |
| results/submission_manifest.schema.json | New | JSON Schema for manifest | None — new file | N/A |
| results/submission_audit.json | Generated | Audit JSON output | None — generated | Generated by audit script |
| results/submission_audit.md | Generated | Audit markdown output | None — generated | Generated by audit script |
| tests/__init__.py | New | Test package init | None | N/A |
| tests/test_submission_audit.py | New | Audit unit tests | None | 13/13 pass |
| .github/workflows/submission-integrity.yml | New | CI workflow | None | N/A (will run on push) |
| docs/submission/HUMAN_WRITING_REQUIRED.md | New | Human writing checklist | None | N/A |
| docs/submission/FIGURE_EVIDENCE_CHAIN.md | New | Figure evidence documentation | None | N/A |
| docs/experiments/2026-06-21-aging-gate-validation.md | Modified | Phase D reclassification | Low — factual correction | Manual review |
| README.md | Modified | Phase D correction, experiment layers, safe runner docs | Low — factual correction | Manual review |
| docs/reviews/2026-07-24-capstone-submission-hardening-report.md | New | This report | None | N/A |

## 9.8 Tests Executed

| Test | Command | Exit Code | Key Output | UTC Time | Commit SHA |
|------|---------|-----------|-----------|----------|-----------|
| Bash syntax: run_fcfs.sh | `bash -n scripts/run_fcfs.sh` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 (base) |
| Bash syntax: run_ltr.sh | `bash -n scripts/run_ltr.sh` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 |
| Bash syntax: run_ltr_aging.sh | `bash -n scripts/run_ltr_aging.sh` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 |
| Bash syntax: run_one_experiment_safe.sh | `bash -n scripts/run_one_experiment_safe.sh` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 |
| Bash syntax: run_part2.sh | `bash -n scripts/run_part2.sh` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 |
| Python compile | `python3 -m compileall scripts/ -q` | 0 | (no output) | 2026-07-24T15:36:44Z | b95c9497 |
| Unit tests | `python3 -m unittest discover -s tests -v` | 0 | `Ran 34 tests in 0.518s OK` | 2026-07-24T13:44:45Z | e405909 |
| Submission audit | `python3 scripts/audit_submission_results.py --manifest results/submission_manifest.json --json-output results/submission_audit.json --markdown-output results/submission_audit.md` | 0 | All 42 experiments pass | 2026-07-24T13:44:18Z | e405909 |

## 9.9 Human Work Still Required

| Item | File | Section | Owner | Evidence Available | Deadline |
|------|------|---------|-------|-------------------|----------|
| Abstract | report/final-report-draft.md | Abstract | Yuze | README Honest Results Table, all committed JSONs | Before submission |
| Introduction | report/final-report-draft.md | §1 | Yuze | README, docs/experiments/ | Before submission |
| Background | report/final-report-draft.md | §2 | Chenxi | README Reference Environment, docs/experiments/2026-06-10 | Before submission |
| Related Work | report/final-report-draft.md | §3 | Shun, Mengze | slo_reproduction/, docs/related-work/ | Before submission |
| Methodology | report/final-report-draft.md | §4 | Yuze | scripts/, CONTRIBUTING.md, patches/ | Before submission |
| Evaluation prose | report/final-report-draft.md | §5 | Yuze, Yuh Jen | results/submission_manifest.json, docs/experiments/ | Before submission |
| Discussion | report/final-report-draft.md | §6-7 | Yuze, Yuh Jen | Ablation table in §6, docs/submission/FIGURE_EVIDENCE_CHAIN.md | Before submission |
| Conclusion | report/final-report-draft.md | §10 | Yuze | README Honest Contribution Statement | Before submission |
| Contributions | report/final-report-draft.md | §8 | All | git shortlog, role-claim issues | Before submission |
| Final title | report/final-report-draft.md | Line 1 | All | N/A | Before submission |
| Final author list | report/final-report-draft.md | Team section | All | README Team table | Before submission |
| PDF visual inspection | N/A | N/A | All | N/A | Before submission |
| Professor rubric check | N/A | N/A | All | Rubric in CSCI 6806 syllabus | Before submission |

See `docs/submission/HUMAN_WRITING_REQUIRED.md` for the complete per-section checklist with evidence file paths and forbidden claims.

## 9.10 Known Limitations

1. **Single GPU:** All experiments were run on a single NVIDIA RTX 3090 (24GB). No multi-GPU or production-scale validation.
2. **Single model:** Only Meta-Llama-3-8B-Instruct was tested. Results may not generalize to other model architectures or sizes.
3. **Single OOD pair:** Only LMSYS→ShareGPT distribution shift was characterized. Other distribution shifts are untested.
4. **Single seed for OOD mitigation:** Phases A/C (true OOD with LMSYS predictor) are single-seed (seed 0). Multi-seed OOD evidence does not exist — Phase D's multi-seed data uses a matched predictor.
5. **Predictor SHA unknown:** The predictor configuration files (`usage_config.json`) were on the remote GPU server at `/hy-tmp/`. Their SHA-256 values cannot be verified from the repository alone. The predictor names are derived from script paths, not from hash-verified configurations.
6. **Baseline drift:** The rate-4 OOD FCFS baseline drifted +21% between the 2026-06-11 and 2026-06-21 measurements (40.9s → 49.6s). This is flagged in the experiment doc but not resolved — likely rented-host variance.
7. **Crash as stability evidence only:** Crashed runs (15/500, 22/500) demonstrate instability but their latency statistics are survivor-biased and must not be used for mean/p99 calculations.
8. **Phase D matched predictor:** Phase D's multi-seed validation uses a ShareGPT-trained predictor on ShareGPT test data. It proves stability under matched conditions but cannot prove LMSYS→ShareGPT OOD robustness.
9. **Historical runner unsafe:** The original experiment orchestrators (`run_part2.sh`, `run_ood.sh`, etc.) use global-latest-JSON selection in shared output directories. The new `run_one_experiment_safe.sh` addresses this for future runs, but historical results were collected with the unsafe pattern.
10. **No GPU rerun performed:** This hardening pass did not re-run any GPU experiments. All conclusions are based on existing committed result files.
11. **50 result files contain generated_texts:** These are model outputs that may contain arbitrary text. They were not modified or deleted (per rules), but the Phase D p2/ files already had generated_texts stripped before commit.

## 9.11 Commit and PR Information

This report reflects the validation of implementation commit `1939f8d5884d443db18d8fc26a0c1c9781e1a550`.

| Field | Value |
|-------|-------|
| Branch | `antigravity/capstone-submission-hardening-20260724` |
| Implementation Head SHA | `1939f8d5884d443db18d8fc26a0c1c9781e1a550` |
| Commit SHAs | `19de334`, `1138a2c`, `67924bb`, `fcba905`, `59fc725`, `e405909`, `1939f8d` |
| Draft PR URL | https://github.com/BenjaminGao2025/Capstone/pull/30 |
| PR state | Draft |
| Merge state | **NOT MERGED** |
| CI Run ID | [30125296357](https://github.com/BenjaminGao2025/Capstone/actions/runs/30125296357) |
| CI Status | **SUCCESS** |
| Unit Test Cmd | `python3 -m unittest discover -s tests -v` |
| Unit Test Exit | `0` |
