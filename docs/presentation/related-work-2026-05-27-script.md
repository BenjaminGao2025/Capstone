# Related Work Presentation Script — Short Version

This is a **practice script**, not text to read word-for-word. Rewrite your part in your own English before class.

Target total: **10-12 minutes**.

## Ben — Opening, Slides 1-4, about 2:00

**Slide 1**

Good morning. Our capstone topic is prefix-aware KV-cache scheduling for LLM agent workloads. The general problem is LLM serving latency. In agent and RAG systems, many requests share long repeated prefixes, such as system prompts, tool descriptions, or retrieved documents. Our project asks whether the serving system can use that repeated structure to reduce time-to-first-token and tail latency.

**Slide 2**

We organized the related work into four layers. vLLM focuses on KV-cache memory layout. SGLang focuses on shared prefix reuse. PromptCache focuses on reusable prompt modules and prefill savings. Hydragen focuses on shared-prefix attention work during decoding.

**Slide 3**

This pipeline shows where the papers fit. PromptCache mainly reduces prefill work. vLLM manages the KV cache. SGLang stores and reuses shared prefixes. Hydragen reduces repeated attention work during decode.

**Slide 4**

The main point is that these papers are complementary. They do not all solve the same problem. Together, they show that latency is affected by memory layout, cache reuse, prompt structure, and attention computation.

Shun, over to you for vLLM and PagedAttention.

## Shun Huang — vLLM / PagedAttention, Slides 5-6, about 1:30

**Slide 5**

vLLM solves a memory management problem in LLM serving. During generation, every request stores a KV cache. If the system allocates one large contiguous memory area for each request, it wastes GPU memory because sequence lengths are different and unpredictable.

PagedAttention fixes this using an idea similar to operating-system paging. It divides KV cache into fixed-size logical blocks and maps them to physical GPU blocks. This reduces fragmentation and allows the server to batch more requests.

**Slide 6**

In the paper's evaluated settings, vLLM reports about 2 to 4 times higher throughput compared with earlier systems, while keeping latency at a similar level. For our project, the lesson is that cache layout affects batching, GPU memory pressure, and latency. Its limitation for us is that it does not decide which prefix-similar requests should be served together.

Chenxi, please take us to SGLang, which is closer to prefix reuse.

## Chenxi Li — SGLang / RadixAttention, Slides 7-8, about 1:30

**Slide 7**

SGLang starts from the idea that many LLM applications are programs, not single prompts. They include system prompts, tool schemas, few-shot examples, branches, and structured outputs. These workloads often repeat the same prefixes.

The main runtime idea is RadixAttention. It stores previous prompt prefixes and their KV cache in a radix tree. When a new request shares a prefix with an old request, the runtime can reuse the cached KV states instead of recomputing them.

**Slide 8**

In the paper's evaluated workloads, SGLang reports up to 6.4 times higher throughput and 3.7 times lower latency. This matters for our project because agent workloads naturally share prefixes. SGLang shows that exposing prefix structure can improve serving performance. Its limitation for us is that it is a separate runtime and programming model, while our base system is vLLM.

Mengze, please explain PromptCache, which focuses more directly on prefill reuse.

## Mengze Hu — PromptCache, Slides 9-10, about 1:30

**Slide 9**

PromptCache focuses on repeated prompt components. In real applications, prompts often reuse system instructions, templates, retrieved documents, or context blocks. Standard KV cache helps within one request, but after the request ends, the same text may be recomputed again in the next request.

PromptCache introduces Prompt Markup Language, or PML. Developers define reusable prompt modules. The system precomputes attention states for those modules and reuses them during inference. This reduces repeated prefill work.

**Slide 10**

In the paper's evaluated settings, PromptCache reports 1.5 to 10 times lower GPU time-to-first-token, and even larger reductions on CPU. This matters for our project because TTFT is often dominated by prefill for long shared prompts. Its limitation for us is that PromptCache requires explicit prompt modules, while our scheduler should try to exploit shared prefixes more automatically.

Yuhjen, please cover Hydragen, which looks at another cost of shared prefixes.

## Yuhjen Sun — Hydragen, Slides 11-12, about 1:30

**Slide 11**

Hydragen points out that shared prefixes can still be expensive. Systems like vLLM can reduce duplicated KV storage, but the attention kernel may still read the same shared prefix keys and values many times across a batch.

Hydragen decomposes attention into two parts: attention over the shared prefix, and attention over each request's unique suffix. It batches the shared-prefix attention across requests, then merges the outputs with the suffix attention.

**Slide 12**

In the paper's evaluated settings with large batches and long shared prefixes, Hydragen reports very large improvements, including up to 32 times decode throughput in one setup. This matters because shared prefixes affect not only storage, but also memory bandwidth and attention computation. Its limitation for us is that the kernel-level implementation is outside our current capstone scope.

I will close by connecting the four papers to our project scope.

## Ben — Synthesis and Scope, Slides 13-15, about 2:00

**Slide 13**

Here is the synthesis. vLLM makes KV memory less fragmented. SGLang detects and stores shared prefix paths. PromptCache precomputes reusable prompt modules. Hydragen avoids repeated attention reads for shared prefixes.

A practical angle for our capstone is scheduling. Under cache limits, requests that share prefixes may need to be grouped deliberately so reuse actually matters.

**Slide 14**

Our proposed scope is therefore not to reimplement all four papers. It is smaller and more realistic. We will build a vLLM benchmark, add prefix grouping plus a simple cache policy, and measure TTFT, p95 latency, throughput, GPU memory, and cache hit rate.

**Slide 15**

After this related-work milestone, our next steps are methodology, environment setup, implementation, and evaluation. The key feedback we want is whether our related-work positioning and evaluation direction are reasonable: using vLLM as the base system, with SGLang, PromptCache, and Hydragen as related work, and focusing our implementation on prefix-aware scheduling and cache policy.

Thank you. We are happy to take questions.

## If You Need To Cut Your Section

If you are running out of time, say only these three sentences:

- "The problem is..."
- "The key idea is..."
- "This matters for our project because..."

Do not explain every detail of the paper.
