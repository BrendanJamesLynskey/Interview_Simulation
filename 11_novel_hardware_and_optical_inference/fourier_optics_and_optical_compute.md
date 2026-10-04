# Fourier Optics and Optical Compute — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** The lens as a Fourier transformer, the 4f system, coherence and detection, optical MACs against transform engines, ENOB and precision passes, conversion energy, static power, mask capacity, integrated photonics
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. How does a lens compute a Fourier transform, and what does a 4f system add?

**Answer:**

- In **coherent** light, the field in a lens's back focal plane is the 2-D Fourier transform of the field in its front focal plane. A point at distance x from the axis holds spatial frequency x/(λf). The transform is done by propagation: one pass of light, every pixel at once.
- A **4f system** is two lenses separated by 2f: input plane, lens, Fourier plane, lens, output plane. A **mask** in the Fourier plane multiplies the spectrum pointwise, and the second lens transforms back. By the convolution theorem the output is the input convolved with the mask's inverse transform: a whole convolution per pass.
- What it does not give for free: the result is analogue (precision is limited by noise and the converters), the mask must be loaded with the filter's spectrum, and a linear convolution needs zero-padding to avoid circular wrap-around.

**Go deeper on this GitHub:** [FOptInf 01, "The Lens as a Fourier Transformer"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-02) · [FOptInf 01, "The 4f System and the Convolution Theorem"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-03) · [Glossary: the lens as a Fourier transformer](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-lens)

### Q2. A camera measures intensity, not field. Why is that a problem for optical computing, and what are the remedies?

**Answer:**

- Detectors are **square-law**: they measure |E|², so the **phase** (and therefore the sign) of a coherent result is lost. A Fourier-domain result is complex; a convolution of signed data has signed outputs.
- Remedies: **coherent detection** (interfere the result with a reference beam, homodyne or heterodyne, to recover amplitude and phase); **offsets and repeated passes** (add a known bias so the result stays positive, or run a second pass and subtract, which roughly doubles the work); or design the computation so only magnitudes matter.
- **Incoherent** light adds intensities, which is simpler and robust but supports only non-negative operations.
- A simulator should charge the remedy explicitly: in this GitHub's transform-engine model, intensity detection doubles the number of passes.

**Go deeper on this GitHub:** [FOptInf 01, "Detectors and the Phase Problem"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-07) · [FOptInf 01, "Coherent and Incoherent Light"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-05) · [Glossary: square-law detection and the phase problem](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-phaseproblem)

### Q3. What is the difference between an optical MAC and an optical transform engine, and why does it matter for a standard LLM?

**Answer:**

- An **optical MAC** (for example an interferometer mesh) multiplies matrices: it would speed up every dense FLOP of a transformer.
- An optical **transform engine** (a 4f system) computes Fourier transforms and convolutions: it speeds up only FFT and Fourier-domain work, and leaves matrix multiplies to a digital part.
- A standard decoder-only transformer contains **no FFT**: projections, the MLP, the LM head and attention are all matmuls or dot products. A transform engine therefore has nothing to do for it. Phase A of this GitHub's analysis checked this against the serving simulator's FLOP count exactly.
- In the simulator the two are different devices: `optical` (a "what if compute were nearly free" MAC probe) and `optical-fft` (the transform engine). A transformer on `optical-fft` runs exactly as on its digital part, plus the engine's static power.

**Go deeper on this GitHub:** [FOptInf 02, "A Standard Decoder Has No FFT"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-02) · [FOptInf 03, "What Was Added to the Simulator"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-02) · [Glossary: transform engine against optical MAC](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-transformengine)

---

## Intermediate

### Q4. What does ENOB mean for an analogue optical result, and how much does a floating-point workload need?

**Answer:**

- **ENOB** (effective number of bits) summarises the whole chain, DAC → optics → detector → ADC, as an ideal quantiser with the same noise. With the full scale set to each pass's peak, the relative RMS error is about crest × 2^−ENOB × 2/√12, where crest is the output's peak-to-RMS ratio.
- For floats the right target is the format's **own rounding error**, not exactness. The phase-A analysis measured the ENOB that matches each format on a 4,096-point causal convolution: **10.3 for BF16, 8.0 for INT8, 6.3 for FP8 E4M3**.
- This differs from FHE, where results must round **exactly**. FHESim 04's exactness rule needs far more bits at sequence length, so digit planes are the FHE answer and the noise rule is the float answer.

**Go deeper on this GitHub:** [FOptInf 01, "Precision: ENOB, Noise and Crosstalk"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-09) · [Glossary: the noise rule for floating-point workloads](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-floatenob) · [analysis/results.md, section 6](https://github.com/BrendanJamesLynskey/LLM_Hub_Fourier_Optics_Inference/blob/main/analysis/results.md)

### Q5. Your optical engine delivers ENOB 8 but the workload needs BF16-level error. What can you do, and what does it cost?

**Answer:**

- **Average repeated passes.** Averaging k noisy passes cuts the noise by √k, buying ½·log₂ k bits: each extra bit costs **4× the passes**. The phase-A analysis puts BF16-level error at ENOB 8 at **26 averaged passes**.
- In the serving simulator the required ENOB is rounded up to an integer (11 for BF16), so the pass count is an exact integer, 4^(11 − ENOB): **64 passes at ENOB 8**, 1 at ENOB 11. Integers keep the Python and JavaScript ports bit-identical.
- **Digit planes do not help** a float workload: the top plane carries almost all of the signal and is read at the same ENOB relative to its own peak.
- The cost lands everywhere: conversions (and their energy) scale with the passes, and so does the engine's time. In the simulator, the circulant variant's prefill step takes 297.82 ms at ENOB 8 against 18.78 ms at ENOB 11.

**Go deeper on this GitHub:** [FOptInf 01, "Buying Precision: Passes and Planes"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-10) · [FOptInf 03, "Static Power and Energy per Token"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-08) · [Glossary: dynamic precision by repeated passes](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-averaging)

### Q6. Where does the energy of an optical engine go, and why can "the optics is passive" mislead?

**Answer:**

- **Conversions.** Every value entering or leaving the optics costs a DAC or ADC sample, at roughly Walden FoM × 2^ENOB per sample. With illustrative FoMs (10 fJ DAC, 20 fJ ADC), a Hyena-style long convolution breaks even with a 1 pJ/FLOP digital FFT at about **ENOB 12.0**; above that the converters cost more than the digital work they replace.
- **Static power.** Lasers and thermal tuning of resonant devices burn power whether or not work arrives, so idle time costs energy. In the simulator, 20 W of lasers and tuning on the optimistic engine is 5.3% of the whole cluster's energy; 200 W is 36.1%.
- **The digital part** still runs everything that is not a transform, and the data still moves through memory.
- "Passive" is true of the propagation, not of the system. A credible model counts conversions, static power and the digital remainder.

**Go deeper on this GitHub:** [FOptInf 01, "Conversion Energy and Static Power"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-11) · [Glossary: conversion-bound optics and the break-even ENOB](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-conversion) · [Disaggregated_Inference_Sim results.md, section 12](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Advanced

### Q7. Why is Fourier-plane mask capacity a first-order cost for a convolution workload?

**Answer:**

- A 4f pass multiplies by **one mask**, so every filter's spectrum must be on the mask while its inputs pass. The mask is held by a spatial light modulator (SLM) with a fixed number of pixels and a frame (rewrite) rate.
- Count the values: a Hyena-2 forward pass at 2,048 tokens needs **537,133,056** complex filter-spectrum values. On a 2-megapixel device that is **269 rewrites**: 261 ms at an 8-bit DMD's 1,031 Hz, against **59.0 ms** for the whole GPU prefill of a 2,048-token prompt.
- The rewrite is amortised over the batch (the filters are weights), but it does not shrink with batch size. In the serving simulator the circulant variant needs 277 rewrites per step, so its TTFT p99 falls from 100.6 s at 1,031 Hz to 90.5 ms at 20 kHz and 16.5 ms at a hypothetical 1 MHz.
- This is the kind of cost a FLOP count never shows, and a system simulator must.

**Go deeper on this GitHub:** [FOptInf 02, "Holding the Weights: Fourier-Plane Mask Capacity"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-11) · [FOptInf 03, "Where the Time Goes: Mask Rewrites and Passes"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-07) · [Glossary: Fourier-plane mask capacity](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-maskcap)

### Q8. Compare free-space 4f optics with integrated-photonic alternatives for transforms.

**Answer:**

- **Free-space 4f:** enormous parallelism (megapixel planes), a transform per pass at the speed of light; but bulky, alignment-sensitive, and limited by SLM frame rates and by getting data on and off the optical planes.
- **Integrated photonics:** Mach–Zehnder interferometer meshes can implement unitary matrices, including DFTs; on-chip lenses and star couplers can do transforms in a planar waveguide. They are compact and fast to reconfigure, but sizes are far smaller (tens to hundreds of ports), insertion loss grows with depth, and thermal phase shifters need tuning power.
- **What a simulator should parameterise either way:** transform size per pass, samples per second at the converters, ENOB, reconfiguration time, static power, and how the workload's transforms tile onto the device. The architecture choice changes the coefficients, not the structure of the model.

**Go deeper on this GitHub:** [FOptInf 01, "Integrated-Photonic Alternatives"](https://brendanjameslynskey.github.io/FOptInf_01_Fourier_Optics_for_Engineers/#slide-08) · [Glossary: Mach–Zehnder interferometer (MZI) meshes](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-mzimesh) · [Glossary: integrated optical Fourier transforms](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-onchipfft)

### Q9. (System design) You are asked whether a Fourier-optical engine is worth building for a new workload. What do you model, and in what order?

**Answer (structure):**

1. **Is there a transform at all, and how big a share?** Build an op ledger of the workload and compute the **Amdahl bound**. For a Llama-3-8B-shaped Hyena-2 model the transforms are 0.20% of prefill FLOPs: a bound of 1.002×. Stop here if the share is small; it usually is.
2. **Weight it by time, not FLOPs.** How fast does the incumbent run that work? GPUs run FFTs below their matmul rate, which raises the share of time (an assumption to sweep, not a constant).
3. **Precision.** Which ENOB does the result need (Q4), and how many passes does that cost at the device's ENOB (Q5)?
4. **Data movement and the mask.** Conversions in and out per value, and mask rewrites per pass (Q7).
5. **Energy.** Conversions at Walden FoM × 2^ENOB, static lasers and tuning for the whole run, plus the digital remainder (Q6).
6. **The whole system.** Put the device into a system simulator with the real request stream: the queue, the batch, the other pool. Find the **break-even** values by bisection (static power, ENOB, mask rate, the incumbent's FFT efficiency).
7. **Area and cost**, and a clear list of what is illustrative.

Say up front that the answer may be "no", and that a negative result found cheaply in a simulator is a success.

**Go deeper on this GitHub:** [FOptInf 02, "The Amdahl Analysis: Prefill FLOP Shares"](https://brendanjameslynskey.github.io/FOptInf_02_Transforms_in_Inference_Workloads/#slide-06) · [FOptInf 03, "The Break-Even Point"](https://brendanjameslynskey.github.io/FOptInf_03_Optical_Prefill_Pools/#slide-09) · [Glossary: optical share and the Amdahl bound](https://brendanjameslynskey.github.io/LLM_Hub_Fourier_Optics_Inference/#g-opticalshare)
