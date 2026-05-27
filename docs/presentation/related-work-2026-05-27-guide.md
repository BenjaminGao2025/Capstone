# Related Work Presentation Guide — 2026-05-27

This is the short speaking plan for the Week 3 related-work milestone.

Use the PPTX here:

- `report/slides/related-work-2026-05-27.pptx`

Use the speaker notes here:

- `docs/presentation/related-work-2026-05-27-script.md`

Use the contact sheet here for quick review:

- `report/slides/related-work-2026-05-27-contact-sheet.png`

## Goal

This is a **related-work presentation**, not a final project demo. The professor should leave with three points:

1. We picked the LLM Latency Optimization track.
2. We understand the four base papers and how they connect.
3. Our capstone scope is realistic: prefix-aware scheduling and cache policy on top of vLLM.

## Timing

Target total time: **10-12 minutes**.

Do **not** make each person speak for 5 minutes. The paper speakers should each stay near **90 seconds**.

| Speaker | Slides | Time | Focus |
|---|---:|---:|---|
| Ben | 1-4 | 2:00 | project framing, pipeline, related-work map |
| Shun Huang | 5-6 | 1:30 | vLLM / PagedAttention |
| Chenxi Li | 7-8 | 1:30 | SGLang / RadixAttention |
| Mengze Hu | 9-10 | 1:30 | PromptCache |
| Yuhjen Sun | 11-12 | 1:30 | Hydragen |
| Ben | 13-15 | 2:00 | synthesis, our positioning, next steps |
| Buffer / transitions | — | 1:00 | handoffs, small pauses |

## Review Status

Locally reviewed for timing, academic framing, clarity, teammate readiness, and AI-text risk.

Main risks found:

- **Too much project pitch**: keep slides 13-15 short. The milestone is related work.
- **Too much paper detail**: each paper speaker should explain one problem, one mechanism, and one lesson for our project.
- **Weak transitions**: each speaker should end with one sentence connecting their paper to prefix reuse / KV cache / latency.
- **AI-sounding script**: do not read the script word-for-word. Rewrite it into your own English before presenting.
- **Time risk**: if anyone goes over 2 minutes, the final synthesis will feel rushed.

Changes applied:

- The deck is structured as a short 15-slide related-work narrative.
- Each paper has exactly two slides: mechanism + implication.
- The script has been changed into speaker notes, not a word-for-word script.
- Slide 13 now states the missing systems question more directly.
- Slide 14 now names the likely model, workload, hardware, baseline, and metrics.
- The final project-positioning section is kept to two minutes.

## Hard Block Before Class

Do this before the 2026-05-27 09:30 PST presentation:

1. Each paper speaker closes the script and explains their paper once in their own words.
2. Each paper speaker should keep only 4-5 bullets on their own note card.
3. Mengze must be able to answer: "What does PML stand for?" and "Why can precomputed KV have limitations when context changes?"
4. Ben should run the four likely professor questions below once with the team.

## What Each Teammate Should Do

### Everyone

1. Open the PPTX, read your assigned slides, then open the speaker notes and rehearse only your assigned section.
2. Rewrite your part in your own words.
3. Practice with a timer. Paper speakers stop at 90 seconds. Ben stops at 2 minutes for the opening and 2 minutes for the closing.
4. Do not add long paper background unless Ben asks.
5. Be ready to answer one question: "How does your paper help our project?"

### Ben

- Own slides 1-4 and 13-15.
- Keep the team on time.
- Make the scope clear: we are using the papers to compare design choices and identify a feasible implementation boundary around vLLM scheduling/cache policy.
- Ask whether our related-work positioning and evaluation direction are reasonable after slide 15.

### Shun Huang

- Own slides 5-6.
- Explain vLLM as memory management for KV cache.
- Do not spend time explaining transformer attention math.
- End with: vLLM fixes fragmentation, but it does not decide which prefix-sharing requests should be admitted together.

### Chenxi Li

- Own slides 7-8.
- Explain SGLang as prefix reuse for LLM programs and agent workflows.
- The key term is **RadixAttention**.
- End with: SGLang is the closest related work, but we need to explain why our vLLM-based scheduler experiment is still different.

### Mengze Hu

- Own slides 9-10.
- Explain PromptCache as reusable prompt modules and precomputed attention states.
- The key metric is TTFT reduction.
- End with: PromptCache motivates prefill savings, but explicit PML modules are a different assumption from automatic request grouping.

### Yuhjen Sun

- Own slides 11-12.
- Explain Hydragen as avoiding repeated reads of shared prefix attention.
- Keep the "32x" result as one quick evidence point, not the whole talk.
- End with: Hydragen is related because shared prefixes affect attention compute, but its decode-side kernel work is orthogonal to our scheduler scope.

## Likely Professor Questions

| Paper | Likely question | Short answer |
|---|---|---|
| vLLM | If vLLM already manages KV cache, why add a scheduler? | PagedAttention reduces fragmentation, but it does not choose admission order for prefix-sharing requests under cache pressure. |
| SGLang | Why not just use SGLang? | SGLang is the closest runtime-level prefix reuse system; our smaller experiment asks whether vLLM scheduling/cache policy can capture part of that benefit without moving to a separate programming model. |
| PromptCache | Does precomputed KV always remain exact when surrounding context changes? | Not automatically. PromptCache uses explicit prompt modules and position handling; our project avoids relying on developer-marked modules. |
| Hydragen | Why cite Hydragen if you are not doing kernels? | Hydragen shows shared-prefix cost is also attention compute, not only storage. It is complementary to scheduling, not our implementation target. |

## Rehearsal Rules

- Give one project takeaway in every paper section.
- Use the slides as visual support; do not read every bullet.
- If stuck, use this fallback structure:
  1. "The problem is..."
  2. "The key idea is..."
  3. "For our project, the takeaway is..."
- Speak slower than normal. 90 seconds is enough.
- Camera on, professional background, join Zoom 5 minutes early.

## Last-Minute Cut Plan

If the professor gives us less time:

- Ben: slides 1, 3, 4 only for intro.
- Each paper speaker: explain the problem/key idea from the first slide, then say one project lesson from the second slide.
- Ben: finish with slide 14 only.

Cut version target: Ben intro 1:00, each paper speaker 45 seconds, Ben close 1:00. Drop all paper speedup numbers if time is tight.

That gives a 6-7 minute version.
