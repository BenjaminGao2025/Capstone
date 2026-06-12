# P3: Scheduler Integration of the Model-Internal Predictor

Date: 2026-06-13

## Status

The stage-2 head is integrated into the vllm-ltr serving engine (four-file
patch, no block-manager changes, no recompilation). In distribution it works
end to end and beats the OPT-125M baseline under every policy tested. Off
distribution, both post-prefill scheduling policies (v1, v2) crash the engine,
and the failure analysis surfaced P3's most important finding: a structural
trade-off between **information timing and information quality** in
length-prediction scheduling. One ablation cell (original policy + our head on
ShareGPT) is pending — the run was accidentally terminated by operator error
during shutdown and will be the first job of the next GPU session.

## Integration design

- The worker lazy-loads the exported MLP head (`egtp_head_last32.pt`) and
  scores the sampled hidden-state rows each step; the first score a request
  receives is produced exactly at prefill completion (the stage-2 `last32`
  feature). Scores travel through the fork's existing
  `aux_model_score` output pipe; the scheduler's `ipt` mode sorts on them.
- Patch: `patches/p3-ipt-scheduler.patch` (196 lines across
  `llama.py`, `model_runner.py`, `llm_engine.py`, `scheduler.py`, plus the
  benchmark client dispatch).
- Smoke (50 prompts): 50/50, serving-loop tau -0.836 — scores verifiably flow
  through scheduling and back to the client.

## Policies tested

- **v1** — unscored requests first (FCFS), scored shortest-predicted-first.
  Every new arrival could preempt running work.
- **v2** — running scored work is never preempted by new arrivals; unscored
  requests admit only into leftover budget; starvation valve
  (`IPT_STARVE_S`, default 30 s). Change confined to
  `_get_ipt_ordered_requests`.
- **Ablation (head-vs-policy attribution)** — the ORIGINAL opt policy,
  unmodified, with our head's scores injected at the original pre-prefill
  timing via an offline-precomputed prompt→score table (`FileAuxScorer`).
  **Provenance note:** at serving time the scores arrive before prefill, but
  they were *produced* from cached full-prefill features of these exact
  prompts. This arm is therefore an attribution instrument (an oracle-cache),
  not a deployable pre-prefill architecture: our head cannot score unseen
  prompts before prefill. Any "two-mode deployment" story is unsupported
  until a deployable early-scoring variant exists (see v3 candidate).

## Results (Meta-Llama-3-8B, 500 prompts, seed 0, swap-space 4)

Mean TTFT / mean latency / p99 latency in seconds; n = completed of 500;
tau = serving-side Kendall tau (predictor score vs realized length).

| Setting | FCFS | LTR-OPT | Ablation (orig policy + our head) | v1 (post-prefill) | v2 (post-prefill, safe) |
|---|---|---|---|---|---|
| lmsys r8 | 16.36 / 48.6 / 120.9 (n=500) | 2.03 / 41.4 / 148.4 (n=500, τ -.641) | **1.84 / 36.4 / 134.2** (n=500, τ -.722) | 0.26 / 40.3 / 141.8 (n=500, τ -.712) | 1.33 / 37.9 / 134.0 (n=500, τ -.701) |
| lmsys r32 | 21.22 / 63.6 / 141.8 (n=500) | 6.10 / 48.3 / 146.1 (n=500, τ -.642) | — (not in plan) | 0.56 / 53.2 / 155.9 (n=500, τ -.674) | 7.11 / 50.3 / 141.1 (n=500, τ -.650) |
| OOD (ShareGPT) r4 | 40.89 / 78.5 / 150.2 (n=500) | 23.81 / 74.9 / 231.0 (n=500, τ -.420) | **PENDING** (run killed by operator error; first job next session) | **CRASH** n=91 | **CRASH** n=124 |
| OOD (ShareGPT) r8 | ~40.9 (n=500) | **CRASH** n=15 | — (not in plan) | **CRASH** n=10 | **CRASH** n=91 |

Attribution at lmsys r8 (mean TTFT): FCFS 16.36 → OPT 2.03 → ablation 1.84 →
v2 1.33 → v1 0.26. The head alone (identical policy) contributes ~9% TTFT and
~12% mean latency over OPT-125M; the post-prefill admission policies buy the
rest of v1's headline number — and v1's aggression is exactly what dies off
distribution. At r32, v2 (7.11 s) loses to OPT (6.10 s): under extreme load
the unscored-admission budget thrashes. Honest bottom line: **the deployable
TTFT gain from the head is ~1.1×, not 8×**; the 8× belonged to a policy that
cannot survive long-sequence traces.

## Structural finding: information timing vs information quality

The OPT-125M baseline scores requests **before** prefill: a predicted-long
request is deprioritized while it still occupies zero KV memory. Our head
produces a better and cheaper signal, but only **after** prefill: every
request must first acquire its full prompt KV before it can be ranked. Under
memory pressure this converts queue-wait into KV residency — long ShareGPT
sequences acquire KV, get deprioritized, are swapped out (~0.5 GB per 8k-token
sequence), and exhaust the 4 GB swap pool regardless of the ordering rule
(v1: 2460 preemption events, engine abort; v2's no-preemption-of-running rule
delayed but did not prevent exhaustion: 124/500 at r4 where pre-prefill
LTR-OPT completes 500/500).

The general statement: **a length predictor's value to the scheduler is
gated by when its information arrives, not only by how accurate it is.**
Post-prefill signals are near-free and more accurate, but they price every
admission decision in KV memory; pre-prefill signals are weaker but free to
act on. This dimension is absent from the base paper and is the main
analytical product of P3.

## v3 candidate (logged, not executed): prefix-probe scoring

Score with the hidden state at token k (e.g. k=256) of a **bounded prefix
prefill** instead of the full prompt: bounded scoring cost, bounded KV
acquisition before ranking, and the model-internal signal is preserved —
between "reading the resume" (OPT) and "a full work trial" (our v1/v2).

Offline validation note for teammates: the cached features on the Mac are
full-prompt states (last-token / pooled) and **cannot** validate
prefix-probe quality; a one-off extraction pass over k-truncated prompts is
required first (~15 GPU-minutes, can ride along with the next boot). After
that, head training and tau evaluation are laptop-only.

## Next session queue

1. Rerun the killed ablation cell: original policy + our head, ShareGPT r4.
2. Prefix-probe feature extraction (k ∈ {128, 256, 512}) for offline v3
   validation.
