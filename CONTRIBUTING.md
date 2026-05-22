# Contributing to the Capstone Repo

Welcome — this doc is how we work together. **Read it before submitting anything.**

Quick reference: every deliverable goes in via a Pull Request to `main`, reviewed by Ben. No direct pushes to `main`.

---

## Team & Roles

We are a 5-person team (professor-approved exception to the 3–4 guideline).

The 4 role-claim issues map 1:1 to the 4 teammates. Ben holds Project Lead / Integration outside of those four issues.

| Issue | Role | Owner | Paper |
|---|---|---|---|
| [#1](https://github.com/BenjaminGao2025/Capstone/issues/1) | Infra / Integration | TBD | SGLang — https://arxiv.org/abs/2312.07104 |
| [#2](https://github.com/BenjaminGao2025/Capstone/issues/2) | Eval / Data | TBD | PromptCache — https://arxiv.org/abs/2311.04934 |
| [#3](https://github.com/BenjaminGao2025/Capstone/issues/3) | Systems / Engine | TBD | vLLM / PagedAttention — https://arxiv.org/abs/2309.06180 |
| [#4](https://github.com/BenjaminGao2025/Capstone/issues/4) | Research / Writing | TBD | Hydragen — https://arxiv.org/abs/2402.05099 |
| n/a | Project Lead / Integration | Ben (@BenjaminGao2025) | (cross-cutting) |

Ben's role:
- Final integration of all 4 streams
- Coordination, deliverable timelines, communication with prof
- Glue code: `run.sh`, end-to-end demo, CI setup
- Code commits via integration PRs (so individual contribution still shows up per syllabus)

---

## Week 1 (now) — Claim + First PR

**Deadline: 2026-05-24, 23:59 PST.**

Three steps.

### Step 1 — Claim your role

Pick one of issues #1–#4. Comment with:

```
GitHub: @your-handle
I claim [Role Name]
Background: [2 lines about your relevant experience]
Concerns: [or "none"]
```

First come first served (with one note — see the @yusun1218 reservation on issue #4).

### Step 2 — Read your paper, write a 1-page summary

Read **abstract + intro + method section** of your assigned paper. You do not need to understand every equation. ~1 hour of focused reading is enough.

Save your summary at: `docs/related-work/<paper-short-name>-<your-firstname>.md`

Examples:
- `docs/related-work/sglang-yujen.md`
- `docs/related-work/promptcache-mengze.md`

Template:

```markdown
# [Paper Title] — Summary

**Author**: [your name]
**Paper**: [arxiv link]
**Date**: 2026-05-2X

## What problem does it solve?
(2–3 sentences)

## Key idea / contribution
(3–5 bullets)

## How does it work? (method)
(1 paragraph, plain English)

## Results they show
(2–3 bullets — main numbers)

## Why this matters for our project
(2–3 sentences — connect to LLM latency, KV cache, or prefix reuse)

## Open questions for me
(things you didn't fully understand — honest gaps here are better than fake confidence)
```

Keep it to **1 page**. If it's 3 pages, you're transcribing, not summarizing — cut it down.

### Step 3 — Submit via Pull Request

Comments on issues do **not** count. Files must land via a Pull Request to `main`.

**Option A — Web only (easiest, no install)**

1. Go to https://github.com/BenjaminGao2025/Capstone
2. Click **"Add file" → "Create new file"**
3. Filename: `docs/related-work/<paper>-<yourname>.md` (the `/` auto-creates the folder)
4. Paste your summary into the editor
5. Scroll down to **"Commit new file"**
6. Select **"Create a new branch for this commit and start a pull request"**. Branch name: `yourname/related-work-papername` (e.g. `yujen/related-work-sglang`)
7. Click **"Propose new file"**
8. On the next page:
   - Title: `Add [paper] summary — [your name]`
   - Description: `Part of #N` (your role-claim issue number)
9. Click **"Create pull request"**
10. On the right sidebar, request review from **@BenjaminGao2025**

**Option B — Local git (recommended if you want to actually learn the workflow)**

```bash
# one-time setup
git clone https://github.com/BenjaminGao2025/Capstone.git
cd Capstone

# every time you start new work
git checkout main
git pull
git checkout -b yourname/related-work-papername

# create your file at docs/related-work/papername-yourname.md
# (use VS Code, vim, whatever)

git add docs/related-work/papername-yourname.md
git commit -m "Add <paper> summary — Your Name"
git push origin yourname/related-work-papername
```

Then on GitHub, click the yellow **"Compare & pull request"** banner → fill in title/description like Option A step 8 → create PR → request review from `@BenjaminGao2025`.

Ben will review within 24 hours.

---

## Git Rules (going forward)

- **Never push directly to `main`.** Always feature branch → PR → review → merge.
- **Branch naming**: `yourname/short-description` (e.g. `mengze/related-work-promptcache`, `yujen/eval-script-v1`).
- **One PR per deliverable.** Don't dump unrelated changes in one PR.
- **PR title format**: `<verb> <what> — <your name>` (e.g. `Add SGLang summary — Yu Jen`).
- **PR description**: link the issue it relates to (`Closes #1`, `Part of #1`).
- **Review**: tag `@BenjaminGao2025` as reviewer. 24h review SLA.
- **Commits**: per syllabus, individual contribution is tracked via GitHub commits. Doc-only contribution is OK this week, but code is required from week 4 onward.

---

## Repo Layout

```
docs/
  lessons/           # Class notes
  related-work/      # 1-page paper summaries (week 3)
  background.md      # week 2 — coming
  methodology.md     # week 4 — coming
src/
  scheduler/         # Prefix-aware scheduler (week 6+)
  cache/             # Cache eviction policy (week 6+)
experiments/
  results/           # Benchmark output (week 7+)
  figures/           # Plots (week 7+)
  scripts/           # Workload + benchmark harness
report/              # Final paper (week 11)
CONTRIBUTING.md      # this file
```

---

## AI Usage Policy (per syllabus)

- ✅ Use AI (ChatGPT, Claude, Copilot) to help you **understand** papers, look up terms, debug code, brainstorm structure.
- ❌ Do NOT have AI **write** your summaries, report sections, or code wholesale.
- The prof has detection tools. AI-generated text loses **the whole group** 0 points.
- Write in your own English. Imperfect English is fine. AI-perfect English with no thinking is not.

---

## Communication

- **GitHub Issues / PRs** — all task discussion, technical questions, deliverable submissions
- **WeChat group** — quick coordination, scheduling, "I'm stuck for 10 min"
- **Ben's DM** — anything you'd rather not discuss in public, or genuine help requests
- **EdStem / WebCampus** — official course channels (when active)

If you're stuck for more than ~1 day, ping someone. Silently stuck is the worst failure mode.

---

## Specific Notes for Week 1

- **@yusun1218** — you said you're interested in both Research/Writing (#4) and Eval/Data (#2). Please pick one and comment. Research/Writing is the higher-priority seat right now (we need paper summaries by 5/27). I'll record you for #4 unless you tell me otherwise by 2026-05-23.
- **@Mengze-Hu** — Issues #5 and #6 you opened are good practice with GitHub, but they don't count as task submission. Please claim either #1 (Infra) or #2 (Eval) by 5/24.
- **Other two teammates** — please introduce yourselves in any of the role-claim issues with your GitHub handle so Ben can add you as collaborators.

---

## Timeline This Week

| Date | What |
|---|---|
| Today (5/22) | Read this doc, claim role |
| 5/24 23:59 PST | PR opened with 1-page paper summary |
| 5/25–5/26 | Ben reviews PRs, we iterate, merge to `main` |
| **5/27 09:30 PST** | **Class — related-work presentation. Each member presents their paper 3–5 min. Cameras on, professional environment.** |
| 5/28+ | Background doc, methodology |

---

Questions? Comment on the relevant issue, or DM Ben.

— Last updated 2026-05-22
