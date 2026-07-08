# KV Cache Observation

This experiment evaluates how request length affects achievable batch size using vLLM with Meta-Llama-3-8B-Instruct. Different prompt lengths from 512 to 4096 words were tested with increasing batch sizes from 1 to 2048.

The results show that longer requests reduce the maximum achievable batch size. For shorter prompts (512 and 1024 words), vLLM successfully handled batch sizes up to 2048. However, when the prompt length increased to 2048 and 4096 words, the maximum successful batch size decreased to 1024, while batch size 2048 failed.

This happens because longer requests require more KV-cache storage during inference, increasing memory pressure inside the vLLM PagedAttention cache system. The prompt length in this experiment is generated using repeated words as an approximate workload rather than exact tokenizer-level token counts.