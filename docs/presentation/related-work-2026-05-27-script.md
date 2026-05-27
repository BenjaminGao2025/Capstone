# Related Work Presentation Speaker Notes

This is not a word-for-word script. Each speaker should turn their section into
4-5 personal bullets and practice without reading this file.

Target total: 10-12 minutes.

## Ben - Opening, Slides 1-4, about 2:00

Use your own words, but keep this spine:

- We are working on LLM serving latency optimization.
- More specifically, the direction is prefix-aware KV-cache scheduling: when many requests share the same system prompt, tool schema, retrieved document, or other long prefix, can the serving system reuse work and respond faster?
- The four papers cover different layers of that problem:
  - vLLM: KV-cache memory layout.
  - SGLang: prefix reuse with RadixAttention.
  - PromptCache: reusable prompt modules and prefill savings.
  - Hydragen: shared-prefix attention work during decode.
- The point of the related-work section is not that one paper solves our project. The point is that the papers divide the latency problem into memory layout, prefix storage, prefill reuse, and attention compute.

Handoff:

- Shun, please start with vLLM and PagedAttention.

## Shun Huang - vLLM / PagedAttention, Slides 5-6, about 1:30

Goal: explain vLLM as the memory-management paper.

Suggested bullets:

- The problem vLLM cares about is GPU memory waste from KV cache. Each request has a different sequence length, so a large contiguous allocation wastes space.
- PagedAttention borrows the paging idea from operating systems. KV cache is split into blocks, and the runtime maps logical blocks to physical GPU blocks.
- In the paper's evaluated settings, vLLM reports about 2-4x higher throughput than earlier serving systems while keeping latency similar.
- For us, the takeaway is that cache layout changes batching capacity, memory pressure, and latency.
- What vLLM does not solve for us: it does not decide which prefix-sharing requests should be admitted together before the cache is evicted.

Be ready for:

- If vLLM already manages KV cache, why add a scheduler?
- Short answer: PagedAttention reduces fragmentation, but it does not choose admission order for prefix-sharing requests under cache pressure.

Handoff:

- Chenxi, please take us to SGLang and RadixAttention.

## Chenxi Li - SGLang / RadixAttention, Slides 7-8, about 1:30

Goal: explain SGLang as the closest prefix-reuse related work.

Suggested bullets:

- SGLang treats many LLM applications as programs, not one-off prompts. Agent and tool workflows often repeat the same prefix.
- RadixAttention stores prefixes and their KV cache in a radix tree. A new request can reuse cached prefix states when it overlaps with earlier requests.
- In the paper's evaluated workloads, SGLang reports up to 6.4x throughput and 3.7x latency improvement.
- For us, the takeaway is that prefix structure is a real serving-system signal, not just an application-level detail.
- The difference from our project: SGLang is a separate runtime and programming model. Our proposed experiment asks what a smaller scheduler/cache-policy layer can do around vLLM.

Be ready for:

- Why not just use SGLang?
- Short answer: SGLang is the strongest related system, so it should be cited. Our capstone is smaller: test whether vLLM scheduling and cache policy can recover part of the prefix-reuse benefit without adopting a new runtime.

Handoff:

- Mengze, please cover PromptCache and prefill reuse.

## Mengze Hu - PromptCache, Slides 9-10, about 1:30

Goal: explain PromptCache as the prefill-reuse paper.

Suggested bullets:

- PromptCache focuses on repeated prompt components: system prompts, templates, retrieved documents, or long context blocks that appear again and again.
- Developers mark reusable modules with Prompt Markup Language, or PML.
- The system precomputes attention states for those modules and reuses them during inference, which mainly reduces prefill cost.
- In the paper's evaluated settings, PromptCache reports 1.5-10x lower GPU time-to-first-token, with larger CPU reductions.
- For us, the takeaway is that prefill dominates TTFT for long shared prompts. The difference is that PromptCache depends on explicit modules, while our scheduler should look for reuse from request structure.

Be ready for:

- What does PML stand for?
- Does precomputed KV always remain exact when surrounding context changes?
- Short answer: not automatically. PromptCache uses explicit modules and position handling. We should mention this as a tradeoff and avoid claiming that precomputed KV is universally reusable.

Handoff:

- Yuhjen, please cover Hydragen and shared-prefix attention compute.

## Yuhjen Sun - Hydragen, Slides 11-12, about 1:30

Goal: explain Hydragen as the decode-side shared-prefix attention paper.

Suggested bullets:

- Hydragen points out that shared prefixes are not only a storage issue. The attention kernel can still repeatedly read the same shared prefix keys and values across a batch.
- The paper separates attention over the shared prefix from attention over each request's unique suffix, then batches the shared-prefix work.
- In the paper's evaluated settings with large batches and long shared prefixes, Hydragen reports very large decode-throughput improvements, including up to 32x in one setup.
- For us, the takeaway is that shared-prefix cost exists in attention compute and memory bandwidth too.
- The difference from our project: Hydragen is kernel-level and decode-side. Our capstone should cite it as complementary related work, not try to implement it.

Be ready for:

- Why cite Hydragen if our scope is scheduling?
- Short answer: it shows prefix sharing matters beyond KV storage. It is orthogonal to our scheduler layer and could be stacked with it later.

Handoff:

- Ben, please close with the synthesis and proposed evaluation.

## Ben - Synthesis and Scope, Slides 13-15, about 2:00

Use your own words, but make these points clear:

- The synthesis is that each paper handles a different part of the serving stack.
- What is missing for our capstone question is an operational policy: when cache capacity is limited, which prefix-sharing requests should run together so reuse actually happens?
- Proposed evaluation:
  - Model: Llama-3-8B-Instruct.
  - Workload: synthetic agent/RAG-style traces with repeated prefixes.
  - Hardware: one AMD RX 7900 XTX, if the environment works as planned.
  - Baseline: vanilla vLLM first; SGLang comparison is a question for the professor.
  - Metrics: TTFT, p95 latency, throughput, GPU memory, and cache hit rate.
- Specific ask for the professor: should the baseline be only vanilla vLLM, or should we also compare against SGLang because it already has prefix reuse?

Closing line:

- That baseline question is the main feedback we want before we lock the methodology.

## Emergency 6-7 Minute Version

- Ben: slide 1 and slide 4 only, 1:00.
- Shun: slide 5 only, 0:45.
- Chenxi: slide 7 only, 0:45.
- Mengze: slide 9 only, 0:45.
- Yuhjen: slide 11 only, 0:45.
- Ben: slide 14 only, 1:00.

In the emergency version, skip speedup numbers and focus on one takeaway per
paper.
