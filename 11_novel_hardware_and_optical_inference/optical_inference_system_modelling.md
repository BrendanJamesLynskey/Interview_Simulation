# Optical Inference System Modelling — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Where transforms appear in LLM inference, heterogeneous pools, putting an optical engine into a serving simulator, Amdahl and break-even analysis, the KV hand-off, compute in transit, validation without hardware
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Where could a Fourier transform appear in LLM inference at all?

**Answer:**

- **Token mixing by FFT:** FNet mixes tokens with a 2-D DFT, but it is an encoder method and **not causal**: every output depends on later tokens, so a decoder cannot use it as it stands. Long-convolution models (S4's convolution mode, H3, Hyena) compute causal convolutions over the sequence by FFT, zero-padded to at least twice the length.
- **Structured weights:** circulant or block-circulant matrices turn matmuls into FFT → pointwise multiply → inverse FFT. Speculative at LLM scale: phase A found no published model of this size that uses them throughout.
- **Transform-domain compression** of the KV cache or hidden states (keeping low-frequency DCT coefficients along the sequence, as FreqKV does). It saves memory; the transforms themselves are small.
- **Not here:** a standard transformer has no FFT; photonic **links** move data and compute nothing.

**Go deeper on this GitHub:** [FOptInf 02, "Where a Transform Could Hide in an LLM"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-01) · [FOptInf 02, "FNet: Fourier Token Mixing"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-03) · [Glossary: Hyena](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-hyena)

### Q2. Why would an optical transform engine go in the prefill pool of a disaggregated server, not the decode pool?

**Answer:**

- **Prefill** processes whole prompts: long FFT convolutions, with the filters held on the mask across the whole batch. That is the work a 4f engine does well.
- **Decode** generates one token per step. A long convolution is served by a cached direct dot product (O(context), no transform) or a distilled recurrence with a constant state. Relaxed tiling does use FFTs at decode, but in small, frequent passes on the latency-critical path: 6 conversion pairs per token per channel at context 2,048, against 1 at prefill.
- **Disaggregation** separates the pools, so each can use different hardware: the transform engine in prefill, HBM-rich digital parts for memory-bound decode.

**Go deeper on this GitHub:** [FOptInf 02, "Causality at Prefill and at Decode"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-05) · [FOptInf 02, "Why Disaggregation Fits"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-13) · [Glossary: relaxed (tiled) online convolution](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-relaxed)

### Q3. What are heterogeneous pools, and what does a simulator show for H100 prefill with A100 decode?

**Answer:**

- Disaggregated serving with **different hardware per phase**: compute-heavy parts for prefill, cheaper or bandwidth-rich parts for decode (Splitwise's proposal). It is generally useful, optics or not.
- In this GitHub's simulator (Llama-3-8B, one device per instance, 8 req/s): H100 prefill + A100 decode keeps TTFT p99 at 353.6 ms and meets the SLO for 100.0% of requests; TPOT p99 rises from 8.8 ms to 16.8 ms, and energy falls from 0.326 to 0.299 J/token. An A100 prefill pool alone cannot keep up (SLO 0.0%); two of them reach 96.9%.
- Modelling point: making the per-pool device explicit must not change a homogeneous run. Naming the same device for both pools reproduces the original run bit-identically, and the Rust port reproduces each mix bit-identically too.

**Go deeper on this GitHub:** [FOptInf 03, "Heterogeneous Pools: H100 Prefill, A100 Decode"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-04) · [Glossary: heterogeneous pools](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-hetpool) · [Disaggregated_Inference_Sim results.md, section 10](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Intermediate

### Q4. How would you add an optical transform device to an existing roofline-based serving simulator?

**Answer:**

- **Split the work.** Give the model an op ledger by class (dense matmul, attention, transform, Fourier-domain multiply, other). The engine takes transform + spectral work; the co-packaged digital part runs the rest on its existing roofline, with its own DVFS and power cap.
- **Charge the engine's own costs:** passes from the precision rule, conversions (pairs per token × tokens × passes) at the converters' sample rate, mask rewrites (an integer ceiling of values needed over values held) at the SLM rate. Step time = digital + optical (or the max, if they overlap).
- **Energy:** conversions at Walden FoM × 2^ENOB, plus static lasers and tuning for the whole run.
- **Keep existing results unchanged:** existing models take the old code path, so every recorded number regenerates identically.
- **Make it portable:** integer counts and a fixed float order let a JavaScript port match bit for bit.

**Go deeper on this GitHub:** [FOptInf 03, "The Transform Engine Model"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-03) · [hardware.py (TransformEngine, CostModel)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/src/disagg_sim/hardware.py) · [Glossary: transform engine against optical MAC](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-transformengine)

### Q5. Hyena-2's transforms are 0.20% of prefill FLOPs. What does that predict, and what did the full simulation show?

**Answer:**

- **Amdahl:** if that 0.20% became free, prefill would be at most **1.002×** faster. The FFT is what makes Hyena cheap; making a cheap operation free buys little.
- **Simulation** (Llama-3-8B shape, 8 req/s): with the default engine (ENOB 8, an 8-bit DMD mask) the optical prefill pool collapses (TTFT p99 172.0 s against 374.9 ms on H100s), because 64 averaging passes and hundreds of mask rewrites cost far more than the FLOPs saved. With an optimistic engine it only ties (372.8 ms).
- **The real problem lies elsewhere:** Hyena-2's direct-decode cache is 4× the GQA KV cache, so its TPOT p99 on H100s is 114.4 ms and no request meets the SLO; a distilled recurrence brings TPOT p99 to 6.9 ms. A simulator that only looked at prefill would miss it.

**Go deeper on this GitHub:** [FOptInf 02, "The Amdahl Analysis: Prefill FLOP Shares"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-06) · [FOptInf 03, "Optical Prefill Against All-GPU Baselines"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-05) · [Glossary: Amdahl's law](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-amdahl)

### Q6. What is "compute in transit", and what could it do for the prefill-to-decode KV hand-off?

**Answer:**

- Operations applied **in a link's data path**, between transmitter and receiver, on data that must move anyway. The deciding number is the compute budget per byte at line rate: about **1–2 operations per byte** (the simulator uses 1.6, illustrative).
- That rules out matmuls (prefill runs at thousands of FLOPs per byte of weights) and suits **streaming, low-intensity transforms** of the hand-off: requantising BF16 KV to FP8, or frequency-domain compression along the token axis if the transform is passive optics. Independent work (KIVI, KVQuant) reports 2–3-bit KV as tolerable, so 8- and 4-bit are within range.
- Simulated (Llama-3-8B, GQA KV over 25 GbE at 14 req/s): fp8 cuts the hand-off p99 from 9,657.8 ms to 166.6 ms and lifts SLO attainment from 41.0% to 100.0%. **But the same compression on the prefill GPU gives the same 166.6 ms**: an elementwise pass is nearly free on a GPU. The in-transit gain is GPU time and energy, not latency.
- For fp4 with block scales the stage is over budget (3.8 operations per line byte) and becomes the bottleneck: 196.6 ms in transit against 81.0 ms on the GPU, at 8 req/s.

**Go deeper on this GitHub:** [FOptInf 03, "Compute in the Transport, Not the Model"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-12) · [FOptInf 03, "Compressing the Hand-off: In Transit or at the GPU"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-13) · [Glossary: compute in transit](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-computetransit)

---

## Advanced

### Q7. How do you find the break-even point of a proposed device, and what did it look like for the optical prefill pool?

**Answer:**

- Pick the metrics that decide (here J/token and TTFT p99 of the whole cluster) and the parameters that are uncertain (static power, ENOB, mask rate, the incumbent's FFT efficiency). For each, **bisect on full simulator runs** for the value at which the new device equals the baseline, as you would bisect for the maximum sustainable load. Report "never" when no value in a stated range works.
- For the most transform-heavy variant (block-circulant weights, LM head on the last token), with an optimistic engine:
  - **Energy:** equal J/token only if lasers and tuning stay below **2.3 W** against GPUs that run FFTs at their matmul rate, **46.9 W** against GPUs at 1/16.
  - **Latency:** precision cannot rescue it (never, at ENOB 6–16); the optical pool wins TTFT p99 only below a GPU FFT efficiency of 0.032 (1/30.9), or, against GPUs at 1/16, with a mask rewriting at **47,942 Hz**.
- The lesson: the incumbent's assumed FFT efficiency moves the verdict more than any optical parameter, so it must be a swept input, not a hidden constant.

**Go deeper on this GitHub:** [FOptInf 03, "The Break-Even Point"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-09) · [Glossary: break-even point](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-breakeven) · [Glossary: GPU FFT efficiency](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-gpuffteff)

### Q8. There is no optical hardware to measure. How do you make such a model trustworthy?

**Answer:**

- **Pin it to independent calculations:** the simulator's op ledger equals the phase-A analysis script to the FLOP for every variant, and its transformer counts equal the original cost model's (tested).
- **Invariants as tests:** a transformer on the transform device equals its digital part exactly, plus static power; energy is monotone in static power (property-based); the pass count follows the stated rule for every format and ENOB; naming identical pools reproduces the homogeneous run bit-exactly.
- **Parity across implementations:** the JavaScript port matches the Python on every new configuration, bit for bit except where a cube root enters; the Rust port matches on heterogeneous pools and rejects the rest by name rather than simulate something else.
- **Honesty about inputs:** every coefficient labelled illustrative or speculative, sweeps over the uncertain ones, and a "what this does not show" list (no crosstalk or drift model, accuracy of compressed KV not modelled).
- **Calibrate when data arrives:** device ENOB, converter energy and mask rates are the first things to measure.

**Go deeper on this GitHub:** [FOptInf 03, "What This Does Not Show"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-15) · [Disaggregated_Inference_Sim results.md, sections 10–15](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md) · [Glossary: differential testing](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-differential)

### Q9. (System design) A team proposes disaggregated serving with an optical prefill pool and a photonic link between pools. How would you decide what to hand off, and over which link?

**Answer (structure):**

1. **Size the hand-off per request.** For a 2,048-token prompt: GQA KV cache 268.4 MB; a Hyena-2 direct-decode cache 1,073.7 MB; a distilled state 16.8 MB, constant in prompt length.
2. **Simulate it on each link** (link utilisation, hand-off share of end-to-end time, TPOT, SLO). In the simulator, the Hyena direct cache saturates 25 GbE (98.4% busy, 97.2% of end-to-end time, TPOT p99 1,338 ms); on every faster link it is a small share.
3. **The payload often beats the link:** a distilled state is a fraction of a percent of end-to-end time even on 25 GbE. Change what is handed off before buying faster links.
4. **Then consider compression,** at the GPU or in transit (Q6), only where the link is the bottleneck.
5. **Label the photonic link as interconnect,** not Fourier optics, and its numbers as illustrative unless measured.
6. **Close with the verdict and its conditions** (Q7), not with the most optimistic configuration.

**Go deeper on this GitHub:** [FOptInf 03, "The KV Hand-off: Link and Payload"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-11) · [FOptInf 02, "What Prefill Hands to Decode"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-12) · [Glossary: prefill-to-decode hand-off](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-handoff)
