# Capstone

FDU MSACS Capstone project repo (CSCI 6806 / INFO 4205, Summer 2026).

## Project (v0.1 — draft)

- **Track**: LLM Latency Optimization
- **Proposed topic**: Prefix-aware KV-cache scheduling for LLM agent workloads. See [docs/roadmap-v0.1.md](docs/roadmap-v0.1.md).
- **Engine / model**: vLLM (ROCm) + Llama-3-8B-Instruct.
- **Hardware**: 1 × AMD RX 7900 XTX (24GB).
- **Final presentation**: 2026-07-29.
- **Team**: Ben, Shun Huang, Chenxi Li, Mengze Hu, Yuhjen Sun.

➤ **Start here if you're a teammate**: [`docs/roadmap-v0.1.md`](docs/roadmap-v0.1.md).
➤ **Base paper PDFs**: [`docs/papers/`](docs/papers/).
➤ **2026-05-27 related-work presentation**: start with the [`speaker guide`](docs/presentation/related-work-2026-05-27-guide.md), then use the [`PPTX`](report/slides/related-work-2026-05-27.pptx) and [`speaker notes`](docs/presentation/related-work-2026-05-27-script.md). Paper owners should stay near 90 seconds.

## Repo layout

```
.
├── README.md
├── docs/
│   ├── roadmap-v0.1.md         # ← START HERE
│   ├── papers/                 # Base paper PDFs for related work
│   ├── presentation/           # Slide guides, speaker scripts, role split
│   ├── lessons/                # Class meeting notes, one file per session
│   │   └── lesson-01-course-overview.md
│   └── related-work/           # (week 3) Paper summaries
├── src/                        # (later) Code: scheduler + cache policy
├── experiments/                # (later) Scripts, configs, results
│   └── figures/
└── report/
    └── slides/                 # Presentation decks and visual QA contact sheets
```

## Lessons

| #  | Date       | Topic                          | Notes |
|----|------------|--------------------------------|-------|
| 01 | 2026-05-13 | Course overview & topic intro  | [docs/lessons/lesson-01-course-overview.md](docs/lessons/lesson-01-course-overview.md) |

## Key rules (don't get burned)

- **No late submissions.** WebCampus closes at the deadline (PST). Late = 0 for the whole group.
- **No AI for the project/report.** ChatGPT/Claude allowed only for research, understanding, and debugging. Plagiarism = 0 for the whole group.
- **Every member must commit code.** GitHub commits track individual contribution. Docs-only contribution is not enough.
- **Bi-weekly meetings, 9:30 AM, camera on**, professional setting required.

## Platforms

- **WebCampus** — submissions, grades, announcements
- **EdStem** — all course/project Q&A (active ~1 week after start)
- **GitHub** (this repo) — code + docs + report artifacts
- Email professor only for personal issues; 48h response time.
