# vLLM / PagedAttention — Summary

**Author**: Shun Huang  
**Paper**: Efficient Memory Management for Large Language Model Serving with PagedAttention  
**Date**: 2026-05-24  

## 1. What problem does this paper solve?

This paper focuses on the memory management problem in large language model serving. During autoregressive generation, each request needs to store a KV cache for previous tokens. The KV cache can become very large as the number of requests and sequence lengths increase. Existing serving systems usually store each request’s KV cache in contiguous memory and reserve memory based on the maximum sequence length. This causes reserved memory waste, internal fragmentation, and external fragmentation, which limits batch size and reduces serving throughput.

## 2. Key idea / contribution

- The paper proposes PagedAttention, an attention algorithm inspired by virtual memory and paging in operating systems.
- PagedAttention stores the KV cache in fixed-size blocks instead of requiring one large contiguous memory area.
- vLLM builds an LLM serving system on top of PagedAttention.
- The system reduces KV cache memory waste and allows more requests to be batched together.
- It also supports memory sharing for parallel sampling, beam search, and shared-prefix workloads.

## 3. How does it work?

PagedAttention divides each request’s KV cache into logical KV blocks. These logical blocks are mapped to physical KV blocks in GPU memory through block tables. The physical blocks do not need to be contiguous. As new tokens are generated, vLLM allocates new blocks only when needed instead of reserving memory for the maximum possible sequence length in advance. This design is similar to operating-system paging, where logical pages are mapped to physical pages. It reduces memory fragmentation and improves GPU memory utilization.

## 4. Main results

The paper shows that vLLM improves LLM serving throughput by about 2–4 times compared with systems such as FasterTransformer and Orca, while maintaining a similar latency level. The improvement is stronger for longer sequences, larger models, and more complex decoding algorithms. The paper also shows that KV cache sharing can save memory in parallel sampling and beam search workloads.

## 5. Why it matters for our project

Our project focuses on LLM latency optimization. vLLM is directly related because it improves LLM serving efficiency through better KV cache memory management. The paper helps us understand how memory fragmentation, batch size, KV cache design, and scheduling affect latency and throughput. It can also guide our future experiments, such as comparing latency, throughput, and memory usage under different request lengths or batch sizes.

## 6. Questions I still have

- How can we reproduce a small-scale vLLM benchmark without access to large GPUs?
- How does the block size affect latency and memory usage in different workloads?
- Can we design a simple experiment to compare normal KV cache allocation with paged KV cache allocation?
