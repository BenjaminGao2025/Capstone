# Related Work Presentation Guide — 2026-05-27

This is the short speaking plan for the Week 3 related-work milestone.

Use the PPTX here:

- `report/slides/related-work-2026-05-27.pptx`

Use the practice script here:

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

Locally reviewed for timing, academic framing, clarity, and teammate readiness.

Main risks found:

- **Too much project pitch**: keep slides 13-15 short. The milestone is related work.
- **Too much paper detail**: each paper speaker should explain one problem, one mechanism, and one lesson for our project.
- **Weak transitions**: each speaker should end with one sentence connecting their paper to prefix reuse / KV cache / latency.
- **AI-sounding script**: do not read the script word-for-word. Rewrite it into your own English before presenting.
- **Time risk**: if anyone goes over 2 minutes, the final synthesis will feel rushed.

Changes applied:

- The deck is structured as a short 15-slide related-work narrative.
- Each paper has exactly two slides: mechanism + implication.
- The script below is short and has clear stop points.
- The final project-positioning section is kept to two minutes.

## What Each Teammate Should Do

### Everyone

1. Open the PPTX, read your assigned slides, then open the practice script and rehearse only your assigned section.
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
- End with: vLLM teaches us that cache layout affects batching and latency.

### Chenxi Li

- Own slides 7-8.
- Explain SGLang as prefix reuse for LLM programs and agent workflows.
- The key term is **RadixAttention**.
- End with: SGLang is the closest related work for our prefix-aware scheduler idea.

### Mengze Hu

- Own slides 9-10.
- Explain PromptCache as reusable prompt modules and precomputed attention states.
- The key metric is TTFT reduction.
- End with: PromptCache motivates our focus on prefill savings, but our scheduler should discover reuse automatically.

### Yuhjen Sun

- Own slides 11-12.
- Explain Hydragen as avoiding repeated reads of shared prefix attention.
- Keep the "32x" result as one quick evidence point, not the whole talk.
- End with: Hydragen is important related work, but its kernel-level implementation is outside our current capstone scope.

## Rehearsal Rules

- Say "this matters for our project because..." once in every paper section.
- Use the slides as visual support; do not read every bullet.
- If stuck, use this fallback structure:
  1. "The problem is..."
  2. "The key idea is..."
  3. "This matters for our project because..."
- Speak slower than normal. 90 seconds is enough.
- Camera on, professional background, join Zoom 5 minutes early.

## Last-Minute Cut Plan

If the professor gives us less time:

- Ben: slides 1, 3, 4 only for intro.
- Each paper speaker: explain the problem/key idea from the first slide, then say one project lesson from the second slide.
- Ben: finish with slide 14 only.

Cut version target: Ben intro 1:00, each paper speaker 45 seconds, Ben close 1:00.

That gives a 6-7 minute version.
