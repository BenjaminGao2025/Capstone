# SGLang - Summary

**Author**: Chenxi Li  
**Paper**: https://arxiv.org/abs/2312.07104  
**Date**: 2026-05-24  

## What problem does it solve?

SGLang is designed to address inefficiencies in programming and executing complex language model programs. Many large language model (LLM) applications are no longer simple single-turn chat requests. They typically involve multiple generation calls, control flow, parallel branches, structured input and output, tool usage, retrieval, and multi-turn interactions. While existing inference systems excel at handling individual model calls, they fail to fully leverage the repetitive structures and shared prefixes found in these more program-like workloads.


## Key idea / contribution

- SGLang introduces a structured generative language embedded in Python for writing language model programs.
- It provides basic operations such as `gen`, `select`, `extend`, `fork`, `join`, `image`, and `video` to simplify generation, branching, parallel processing, and multimodal input.
- It includes not only a front-end programming interface but also an optimized back-end runtime.
- Its primary runtime optimization is RadixAttention, a technique that stores key-value cache entries in a radix tree and reuses shared prompt prefixes across different requests.
- It also uses compressed finite-state machines to accelerate constraint decoding for structured outputs like JSON.
- For API-only models, it supports speculative API execution to reduce redundant API calls and input token overhead.
  
## How does it work? (method)

SGLang divides the system into a frontend language and a backend runtime. The frontend allows users to express complex LLM workflows using Python-like code, including generation calls, option selection, prompt expansion, parallel branches, and structured output constraints. The backend runtime then efficiently executes these programs. To enable KV cache reuse, RadixAttention stores the prefix of previous prompts and their KV cache in a radix tree, rather than discarding them after each request. When a new request shares the same prefix as a previous one, the runtime can reuse cached results instead of recomputing the same tokens. For structured output, SGLang converts regular expression constraints into compressed finite-state machines, allowing fixed parts of formats like JSON to be decoded in larger chunks rather than processed token by token. These optimizations are particularly effective when a large number of requests share system prompts, few-shot examples, chat histories, or structured decoding templates.

## Results they show

- Across multiple LLM workloads, SGLang achieved up to 6.4x higher throughput and 3.7x lower latency compared to systems such as vLLM, Guidance, and LMQL.
- Evaluated workloads include MMLU, HellaSwag, ReAct agents, generative agents, thought trees, thought skeletons, LLM evaluation, JSON decoding, multi-turn conversations, and the DSPy RAG pipeline.
- The paper notes that higher KV cache hit rates lead to larger batch sizes, higher throughput, and lower latency.
- In the JSON decoding benchmark, the compressed finite-state machine boosted throughput by 1.6x by decoding multiple tokens at once.
- On the multimodal LLaVA workload, when multiple questions share the same image, SGLang similarly increased throughput by reusing the image-token KV cache.
## Why this matters for our project

This paper is directly relevant to our infrastructure/integration roles because it focuses not only on model quality but also on the system-level execution of large language model (LLM) applications. It demonstrates how service runtimes can improve throughput and reduce latency by reusing key-value caches, scheduling requests based on shared prefixes, and efficiently supporting structured generation. For our project, SGLang serves as a valuable reference for building reproducible LLM service workflows, designing benchmarking schemes, and understanding how infrastructure choices impact latency, throughput, and cache reuse.
## Open questions for me

- To understand the exact implementation details of RadixAttention, especially how the radix tree is maintained during concurrent requests.
- To compare RadixAttention with vLLM's PagedAttention because both are related to KV cache management but seem to optimize different aspects of serving.
- To check how much of the paper's design is implemented in the current open-source SGLang codebase.
