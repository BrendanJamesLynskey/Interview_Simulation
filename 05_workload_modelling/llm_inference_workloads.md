# LLM Inference Workloads — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Prefill and decode, the KV cache, batching, disaggregated serving, TTFT/TPOT/goodput, sizing a serving cluster
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Why are prefill and decode so different as workloads?

**Answer:**

- **Prefill** processes the whole prompt in one forward pass: every weight is multiplied by thousands of token vectors. Arithmetic intensity is in the thousands of FLOPs per byte: **compute-bound**. It produces the KV cache and the first output token.
- **Decode** generates one token per sequence per step: every weight is read once to produce one token per sequence in the batch. Intensity is roughly the batch size in FLOPs per byte: **memory-bound** for any practical batch.

For Llama-3-8B on one H100 in the closed-form model on this GitHub: a 2,048-token prefill has intensity 2,081.7 FLOP/byte and takes 59.0 ms (compute-bound); a batch-1 decode step at context 2,048 has intensity 1.1 and takes 6.2 ms (memory-bound), almost all of it reading 15.3 GB of weights and KV cache.

Consequences: they want different hardware (compute vs bandwidth), different batching, and they interfere when they share a device.

**Go deeper on this GitHub:** [InfSim 03, "Two Phases: Prefill and Decode"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-01) · [Glossary: prefill and decode](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-prefill) · [coding challenge 05](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_05_prefill_decode_model.py)

### Q2. How big is the KV cache, and why does it limit batch size?

**Answer:**

Per token, the cache stores a key and a value vector for every layer and every KV head:

$$\text{KV bytes per token} = 2 \times n_{\text{layers}} \times n_{\text{kv heads}} \times d_{\text{head}} \times \text{bytes per element}$$

Llama-3-8B (32 layers, 8 KV heads of dimension 128, BF16): 2 × 32 × 8 × 128 × 2 = **131,072 bytes (128 KiB) per token**. A 2,048-token context costs 256 MiB per sequence. Grouped-query attention (8 KV heads instead of 32) already cut this by 4×.

On an 80 GB device holding 16 GB of weights, about 400k tokens of cache fit at 90% memory use: 200 sequences of 2,048 tokens, or far fewer long-context ones. Batch size, and therefore decode throughput, is often limited by **KV memory**, not by compute. That is why paging (PagedAttention), quantised KV caches and offloading matter.

**Go deeper on this GitHub:** [InfSim 03, "KV-Cache Arithmetic"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-06) · [Glossary: KV cache](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-kvcache) · [Glossary: PagedAttention](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-paged)

### Q3. Define TTFT, TPOT, inter-token latency and goodput.

**Answer:**

- **TTFT (time to first token):** arrival to the first output token: queueing + prefill (+ KV transfer in disaggregated serving).
- **TPOT (time per output token):** average time between output tokens after the first, per request: `(end − first token time) / (output tokens − 1)`.
- **Inter-token latency (ITL):** each individual gap between consecutive tokens. Its distribution exposes stalls (a decode step delayed by a prefill) that the per-request TPOT average hides.
- **Goodput:** the rate of requests that meet **all** their service-level objectives (e.g. TTFT ≤ 1 s and TPOT ≤ 50 ms). Throughput counts every request; goodput counts only useful ones.

Report these as **distributions** (p50, p90, p99), at a stated offered load.

**Go deeper on this GitHub:** [InfSim 03, "The Metrics Users Feel: TTFT, TPOT, Goodput"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-09) · [Glossary: TTFT, TPOT and inter-token latency](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-ttft) · [Glossary: goodput and SLO attainment](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-goodput)

---

## Intermediate

### Q4. Compare static batching, continuous batching, chunked prefill and paged KV memory.

**Answer:**

- **Static batching:** form a batch, run it until every sequence finishes. Short sequences wait for long ones; new requests wait for the whole batch. Poor utilisation and latency.
- **Continuous (iteration-level) batching:** the batch is re-formed every decode step: finished sequences leave, new ones join. Keeps the batch full; now standard.
- **Chunked prefill:** split a long prefill into chunks and mix them with decode steps, so a big prompt does not stall every running decode for its whole duration. Smooths inter-token latency in colocated serving.
- **Paged KV memory (PagedAttention):** allocate the KV cache in fixed-size blocks rather than one contiguous region per sequence, removing fragmentation and allowing sharing (e.g. common prefixes). Raises the number of sequences that fit.

**In a simulator**: each changes the per-step batch composition and therefore step time; model them in the scheduler, with the cost model unchanged.

**Go deeper on this GitHub:** [InfSim 03, "Batching: Static, Continuous, Chunked, Paged"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-07) · [Glossary: continuous batching](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-batching) · [Glossary: chunked prefill](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-chunked)

### Q5. What is prefill–decode interference, and how does disaggregation remove it?

**Answer:**

On a shared device, a long prefill step occupies the device for tens to hundreds of milliseconds; every running decode sequence waits, so its inter-token latency spikes. Prefill wants big compute-bound batches; decode wants frequent short steps.

**Disaggregation** runs prefill and decode on separate pools of devices. After prefill, the KV cache is transferred to a decode instance over a fast link. Each pool can be sized and configured for its phase.

Measured in the simulator on this GitHub (Llama-3-70B, 4×H100 per instance, 4 req/s): colocated (2 instances) had a TPOT p99 of 25.9 ms; disaggregated (1 prefill + 1 decode) 15.2 ms, and its p99 inter-token latency was 12.4× lower. The price: TTFT p99 rose from 630.2 ms to 854.2 ms (one prefill instance plus the KV transfer), and the link becomes a new resource to size.

**Go deeper on this GitHub:** [InfSim 05, "The Interference Problem"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-01) · [InfSim 05, "The Idea: Split the Phases"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-02) · [Glossary: prefill–decode interference](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-interference) · [Glossary: disaggregated serving](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-disagg)

### Q6. How long does a KV-cache transfer take, and when does the link become the bottleneck?

**Answer:**

Transfer time ≈ latency + KV bytes / link bandwidth. KV bytes = prompt tokens × KV bytes per token. For Llama-3-70B (80 layers, 8 KV heads, head dimension 128, BF16) that is 2 × 80 × 8 × 128 × 2 = 327,680 bytes per token, so a 2,048-token prompt carries about 671 MB.

- Over a 400 Gb/s (50 GB/s) link: about 13 ms, small next to a 134 ms prefill.
- Over 25 Gb/s Ethernet (about 3.1 GB/s): over 200 ms per request, and at a few requests per second the link saturates.

The link becomes the bottleneck when `arrival rate × KV bytes per request` approaches its bandwidth. On this GitHub, a configuration with two prefill instances, 6 req/s and a 25 GbE link showed the KV link 96% busy, 81% of request time spent waiting for it, and almost no requests meeting the SLO.

**Go deeper on this GitHub:** [InfSim 05, "What the KV Transfer Costs"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-04) · [Glossary: KV-cache transfer](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-kvtransfer) · [the example report (section 7)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Advanced

### Q7. System design: design a simulator to size the prefill and decode pools of a serving cluster for a given SLO.

**Answer (a structured model answer):**

**1. Inputs.** Model shape and precision; hardware (FLOP/s, bandwidth, memory, interconnect); arrival process (rate, burstiness, or a production trace); prompt and output length distributions; SLOs (e.g. p99 TTFT ≤ 1 s, p99 TPOT ≤ 50 ms) and the required attainment (e.g. 90% of requests meet both).

**2. Analytic bracket first.** Per-instance capacity of each pool from the roofline cost model: prefill tokens per second; decode tokens per second at the KV-limited batch size; link bytes per second. This gives a lower bound on the number of instances of each type, and an upper bound on the load to search.

**3. The DES.** Workload generator → router → prefill engines (batching) → KV link → decode engines (continuous batching, KV memory as a container) → metrics. Cost model per step from FLOPs and bytes with calibrated efficiencies and a fixed overhead.

**4. Search.** For each (P prefill, D decode) configuration, find the maximum sustainable rate at the attainment target by **bisection** on the arrival rate, bracketed by the analytic bound. Use common random numbers across configurations and replications for CIs.

**5. Output.** The cheapest (P, D) meeting the target at the required rate, with margins; sensitivity to arrival burstiness and length distributions; the binding resource in each case.

**6. Validation.** Low-load latencies equal step times; queueing checks; if a real deployment exists, compare a measured operating point.

**Go deeper on this GitHub:** [InfSim 05, "Six Experiments to Try"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-07) · [InfSim 08, "Smarter Experiments: Multi-Fidelity, Search, Surrogates"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-10) · [Disaggregated_Inference_Sim](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim)

### Q8. How does tensor parallelism change the cost model, and what does a simple model usually ignore?

**Answer:**

Tensor parallelism splits each layer's weight matrices across n devices. Each device reads 1/n of the weights and does 1/n of the FLOPs per token, so a simple model treats the instance as one device with n× the compute and bandwidth.

What that ignores:
- **Communication:** two all-reduces per transformer layer (after attention and after the MLP) in the common Megatron-style split. Each moves activations of size batch × tokens × d_model. For decode at small batch these are latency-bound (microseconds each, times 2 × layers), which can be a significant fraction of a few-millisecond step.
- **Imperfect scaling**: smaller per-device matrices run at lower efficiency.
- **Synchronisation and stragglers.**

The serving simulator on this GitHub treats an instance as one bigger device and flags the missing all-reduce cost as a known optimism in its README. Naming such simplifications explicitly is part of a credible model.

**Go deeper on this GitHub:** [InfSim 03, "Parallelism and Its Communication Bill"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-08) · [Glossary: tensor, pipeline and expert parallelism](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-parallelism) · [InfSim 05, "Limitations and Extensions"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-10)

### Q9. A hypothetical accelerator has 4× the FLOP/s of a GPU but the same memory bandwidth. What happens to LLM serving performance?

**Answer:**

- **Prefill** (compute-bound) speeds up substantially, until it approaches the memory roof (its intensity is high, so there is room) or other limits (attention's quadratic work, overheads).
- **Decode** (memory-bound at practical batch sizes) **barely changes**: its step time is set by reading weights and KV cache. More FLOP/s raises the ridge point further above decode's intensity.

So TTFT improves, TPOT and decode throughput do not, and overall throughput for chat-like workloads (long outputs) improves little. To exploit the compute, the system must raise decode's intensity: larger batches (needs more KV memory), speculative decoding (several tokens verified per weight read), or quantised weights (fewer bytes per weight).

The serving simulator on this GitHub includes exactly such a deliberately hypothetical part ("abundant matmul throughput, ordinary memory") to make this point; its decode steps remain memory-bound.

**Go deeper on this GitHub:** [InfSim 03, "The Roofline"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-04) · [InfSim 01, "Why AI and Novel Compute Need System Simulators"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-09) · [InfSim 07, "Power in Photonic and Novel Compute"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-10)
