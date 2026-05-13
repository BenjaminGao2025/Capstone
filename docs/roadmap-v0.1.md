# Capstone Roadmap v0.1

> Status: **draft, pending team review**. Last updated 2026-05-13.

## TL;DR

We are proposing to work on **prefix-aware KV-cache scheduling for LLM agent workloads** using vLLM as the base inference engine and Llama-3-8B as the model. Hardware: 1 × AMD RX 7900 XTX (24GB, ROCm).

- **Track**: LLM Latency Optimization (option 1 of the three the professor offered).
- **One-line goal**: reduce time-to-first-token (TTFT) and tail latency for workloads where requests share long common prefixes (agent system prompts, RAG context, tool catalogs).
- **Final deliverable**: 2026-07-29 presentation.

## Project (one-liner)

> Reduce TTFT and tail latency for LLM serving workloads where requests share long common prefixes, by adding a prefix-aware scheduler and cache-eviction policy on top of vLLM, and measuring the impact vs vanilla vLLM and SGLang on synthetic + real agent traces.

## Why this topic

| Factor | Note |
|---|---|
| Maps to "core OS focus" the prof asked for | ✅ scheduling + cache management is core systems work |
| Base papers exist | ✅ vLLM (PagedAttention), SGLang (RadixAttention), Hydragen, PromptCache |
| Hardware fits | ✅ Llama-3-8B runs comfortably on 1 × 24GB |
| Reproducible | ✅ open model, open engine, public benchmarks |
| Ablation surface | ✅ cache size, eviction policy, prefix length threshold, scheduler on/off |
| Career value | ✅ directly relevant to LLM serving / AI infra / forward-deployed roles |

## Approach

1. **Baseline**: vanilla vLLM + Llama-3-8B serving an agent-like workload trace.
2. **Our contribution**:
   - Prefix-aware request scheduler (group requests by shared-prefix prefix-tree).
   - Hybrid LRU + LFU cache-eviction policy tuned for prefix reuse.
3. **Evaluation metrics**: TTFT, TPS, p50 / p95 / p99 latency, GPU memory usage, cache hit rate.
4. **Ablation**: cache size, eviction policy, prefix-length threshold, scheduler on/off.

## Tech stack

- **Engine**: vLLM (ROCm build)
- **Model (primary)**: `meta-llama/Llama-3-8B-Instruct`
- **Model (secondary, optional)**: `deepseek-ai/DeepSeek-R1-Distill-Llama-8B`
- **Hardware**: AMD RX 7900 XTX (24GB) + ROCm 6.x on Ubuntu 22.04. RunPod NVIDIA fallback if needed.
- **Workloads**:
  - Synthetic: fixed system prompt + variable user prompt + variable tool catalog.
  - Real: anonymized agent traces (Ben supplies from Hermes / MCP stack).
- **Benchmark**: vLLM `benchmark_serving.py` + custom harness.
- **Language**: Python 3.11+, PyTorch ROCm.
- **Repo**: this GitHub repo. Every member commits code — docs-only contribution does not count per syllabus.

## 12-week timeline (aligned with syllabus deadlines)

| Wk | Date | Syllabus deliverable | Our task |
|----|------|----------------------|----------|
| 1  | 2026-05-13 | — | Team forming, topic locked, roadmap v0.1 |
| 2  | 2026-05-20 | **Background (10%)** | Write background doc: LLM inference, KV cache, current serving systems |
| 3  | 2026-05-27 | **Related Work (10%)** | Read & summarize 4 base papers; present in class |
| 4  | 2026-06-03 | **Methodology (10%)** | Design our scheduler + cache policy; architecture diagram |
| 5  | 2026-06-10 | Lecture II | Env setup done (ROCm + vLLM + model); baseline running on 7900 XTX |
| 6  | 2026-06-17 | — | Implement prefix-aware scheduler v1 |
| 7  | 2026-06-24 | **Evaluation (20%)** | Full benchmark: baseline vs ours vs SGLang |
| 8  | 2026-07-01 | — | Debug, polish results, finalize figures |
| 9  | 2026-07-08 | **Ablation (10%) + VCS** | 3-axis ablation: cache size / eviction / prefix threshold |
| 10 | 2026-07-15 | **Abstract + Artifact (15%)** | Abstract / intro / conclusion + reproducible repo (README, scripts, figures) |
| 11 | 2026-07-22 | **Final Report (15%)** | Integrate everything into final report |
| 12 | 2026-07-29 | **Final Presentation (10%)** | Slides + dry run |
| 13 | 2026-08-05 | Present | Defend |

## Team roles (proposed, 3–4 people)

| Role | Owner | Responsibilities |
|---|---|---|
| **Systems / engine** | Ben | Scheduler + cache policy inside vLLM; supply agent workload trace |
| **Infra / integration** | TBD | vLLM internals, benchmark harness, ROCm env, reproducibility scripts |
| **Research / writing** | TBD | Related-work survey, figures, report writing lead |
| **Eval / data** *(if 4 ppl)* | TBD | Run experiments, ablation matrix, data analysis |

Every member commits real code. Per the syllabus, GitHub commits are used to track individual contribution. Documentation-only contribution is **not sufficient**.

## What each teammate should do this week (before 2026-05-19)

**Everyone**:

- [ ] Confirm you're in this group and OK with this topic.
- [ ] Create a GitHub account if you don't have one. Share your handle so we can add you as collaborator.
- [ ] Skim **vLLM paper** ("Efficient Memory Management for Large Language Model Serving with PagedAttention", Kwon et al., 2023) — at least intro + section 3.
- [ ] Skim **SGLang paper** ("SGLang: Efficient Execution of Structured Language Model Programs", Zheng et al., 2024) — focus on RadixAttention.
- [ ] Pick one of the four roles above and tell the group.
- [ ] Make sure you can install Python 3.11 + git + can SSH; a Linux machine helps but is not required for week 1.

**By 2026-05-19**:

- [ ] All roles assigned.
- [ ] Group registered on the course spreadsheet (Ben to share once the prof posts it).

**By 2026-05-27 (Related Work presentation)**:

- [ ] Each person reads at least 2 of the base papers and contributes a 1-page summary to `docs/related-work/`.

## Open decisions (need team input)

1. **Lock topic?** Confirm prefix-aware KV-cache scheduling, or switch to one of the alternatives: continuous batching, speculative decoding, P-D split.
2. **Anchor base paper**: vLLM vs SGLang vs Hydragen vs PromptCache. Default: SGLang (RadixAttention) — the most direct precedent.
3. **Secondary model**: include DeepSeek-R1-Distill-Llama-8B, or stick to Llama-3-8B only?
4. **Communication channel**: WeChat (current) vs Discord vs Slack — see README.

## Reading list (base papers)

1. **vLLM / PagedAttention** — Kwon et al., 2023. <https://arxiv.org/abs/2309.06180>
2. **SGLang / RadixAttention** — Zheng et al., 2024. <https://arxiv.org/abs/2312.07104>
3. **Hydragen** — Juravsky et al., 2024. <https://arxiv.org/abs/2402.05099>
4. **PromptCache** — Gim et al., 2023. <https://arxiv.org/abs/2311.04934>

## Hardware notes (Ben's machine)

- AMD RX 7900 XTX, 24GB VRAM
- ROCm 6.x on Ubuntu 22.04
- vLLM has a working ROCm build but lags CUDA by ~1 release on new features. Expect 70–85% of NVIDIA performance for equivalent workloads.
- **DeepSeek V2/V3/V4 cannot run on this card** — they are 200–700B+ MoE models. We use Llama-3-8B (or DeepSeek-R1-Distill-Llama-8B) instead.

## Risks

- **ROCm vLLM trailing CUDA**: some features may be missing or unstable. Mitigation: stick to mature features; reserve ~$50 RunPod NVIDIA budget as fallback.
- **Real agent traces**: anonymization + cleaning take time. Mitigation: synthetic workload is sufficient for a passing grade; real traces are bonus.
- **Team velocity unknown**: first 2 weeks have hard syllabus deliverables. Mitigation: this roadmap.

## Repo conventions

- Lesson notes: `docs/lessons/lesson-NN-*.md`
- Related-work summaries: `docs/related-work/`
- Background, methodology, evaluation docs: `docs/`
- Code: `src/`
- Experiments / scripts: `experiments/`
- Figures: `experiments/figures/`
- Major reports: `report/`
- One PR per logical change. Every group member lands ≥1 PR per milestone week.
