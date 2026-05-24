# Hydragen: High-Throughput LLM Inference with Shared Prefixes Summary

**Author**: Yuhjen Sun (@yusun1218)  
**Paper**: https://arxiv.org/abs/2402.05099  
**Date**: 2026-05-24

## 1. Problem
Hydragen fixes the inefficiency problem in batched LLM inference, and shared prefixes are very common in LLM inference, such as chatbot system prompts, few-shot examples, long documents, and programming tasks. Systems including vLLM and PagedAttention can reduce duplicated KV cache storage. However, the downside is that they are still repeatedly reading the shared prefix keys and values for each sequence in the batch when computing attention. Therefore, when the batch size is large or the shared prefix is long, the GPU spends too much time on repeatedly reading the same prefix keys and values, which slows down decoding. The paper mentioned that shared prefixes in the current attention implementations can create issues and inefficiency, but Hydragen turns this into an opportunity to improve throughput.

## 2. Key Idea / Contribution
The key idea of Hydragen is to combine two methods: attention decomposition and inter-sequence batching. For attention decomposition, it splits into two ways, first is the attention over shared prefix and second, is the attention over each sequence's unique suffix. After working with these two parts, they are then merged together with softmax normalization. This method is very useful, the reason is because the final result for attention decomposition is still attention so Hydragen can improve this without changing the model. For inter-sequence batching, the idea behind it is to batch all the attention from different sequence, therefore, instead of doing prefix attention separately, Hydragen will batch the queries from different requests altogether to create one large operation. The result for this method is to reduce the repeating reads from KV cache memory and also changes many matrix vector operations into matrix- matrix operations which becomes a lot more efficient.

## 3. Method
Instead of computing attention in the whole sequence for each request, what Hydragen does is to first splitting attention into shared prefix and unique suffix parts. Shared prefix is computed using inter-sequence batching whereas suffix computed separately because sequence have different tokens. After computing, Hydragen then merge the outputs from these two parts with softmax normalization into the final attention result. 

## 4. Main Results
The main results show that Hydragen is much more efficient and faster in large batch size and long prefix. One evidence show that on CodeLlama-13B, Hydragen improves decoding throughput by 32x. In addition, whenever the prefix gets longer, by comparing different models, such as vLLM, hydragen outperformed it with its stability, since it avoids reading the same prefix during attention. Another interesting finding shows that Hydragen processes 256 questions in less time than FlashAttention that can only answers 64 questions in a long document task. These findings show how important and useful Hydragen is when dealing with large batches and long shared contexts. 

## 5. Relevance to Our Project
Hydragen is relevant to our project because it directly connects to the topics we are currently studying, which include LLM latency, throughput, KV-cache reuse, prefix sharing, and benchmarking. The goal of the project is to understand and figure out how LLM inference can become more efficient; therefore, Hydragen is a good related work paper for it because it shows how shared prefixes can actually bring downsides in both memory usage and attention efficiency. Not only that, it also provides different inference systems for us to compare, and the findings show how Hydragen handles problems in KV cache and prefix reuse well.

## 6. Open Questions
- In real life, how often do we encounter with large batches and long shared prefixies? 
- Can the serving systems like vLLM or SGLang detect shared prefixes by themselves? 
- What are some challenges using Hydragen in LLM systems in real life?
- How difficult is it implementing Hydragen comapred to other systems like  vLLM, PagedAttention, SGLang, and RadixAttention?
- Is Hydragen useful for small batches? 

## 7. Background / Related Work Outline
- LLM inference have to be efficient in order to have users send multiple requests at the same time.
- Many requests share the same prefix such as the chatbot prompts, few-shot examples and long documents. 
- In Hydragen's discussion, method using KV cache helps to reduce the repeating computations but it does not remove all memory and  attention costs. 
- Serving systems such as vLLM and PageAttention help to manage the KV cache efficiently. 
- FlashAttention is one of the attention discussed in paper that helps attention run faster on the GPUs. 
- SGLang and RadixAttention are used to avoid repeated shared prefixes to make LLM inference more efficient. 
- Hydragen makes the shared prefix attention a lot faster, helping LLM interfernce become more efficient. 