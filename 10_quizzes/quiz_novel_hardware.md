# Quiz — Novel Hardware and Optical Inference

**Subject:** Simulation and Performance Modelling
**Topics covered:** Fourier optics and the 4f system, optical MACs against transform engines, ENOB and precision passes, conversion energy and static power, mask capacity, transforms in LLM inference, heterogeneous pools, break-even analysis, the KV hand-off and compute in transit
**Format:** Multiple-choice and short-answer questions. Answers at the end.

---

### Q1. A 4f optical system with a mask in its Fourier plane computes, in one pass:

a) A matrix–vector product
b) A convolution of the input with the mask's inverse transform
c) An exact integer Fourier transform
d) The magnitude of the input's spectrum only

---

### Q2. Why does a standard decoder-only transformer give a Fourier-optical transform engine nothing to do?

---

### Q3. A device's ENOB is 8, and the workload needs ENOB 11. By averaging repeated passes, how many passes does it take?

a) 3
b) 8
c) 16
d) 64

---

### Q4. Why do digit planes, which make optical FHE exact, not help a BF16 workload?

---

### Q5. Converter energy per sample is roughly Walden FoM × 2^ENOB. What happens to conversion energy per value when ENOB rises from 11 to 12 (one pass needed either way)?

a) It halves
b) It stays the same
c) It doubles
d) It quadruples

---

### Q6. FNet mixes tokens with a 2-D Fourier transform. Why can a decoder not use it as it stands?

---

### Q7. In a Llama-3-8B-shaped Hyena-2 model, transforms are 0.20% of prefill FLOPs. What is the Amdahl bound on prefill speed-up if they became free?

a) 1.002×
b) 1.2×
c) 2×
d) 500×

---

### Q8. Why is the Fourier-plane mask's rewrite rate a first-order cost, even though rewrites are shared by the whole batch?

---

### Q9. Which pool of a disaggregated server suits an optical transform engine, and why?

a) Decode, because it is memory-bound
b) Prefill, because its long transforms and batched filters suit one-pass optics
c) Both equally
d) Neither: the KV link

---

### Q10. When modelling heterogeneous pools, what is the first test to write?

---

### Q11. An in-transit compute stage has a budget of about 1.6 operations per byte at line rate. Which of these fits?

a) Prefill matmuls
b) Requantising BF16 KV to FP8 (about one operation per value)
c) A digital FFT along the token axis at line rate
d) Attention for the decode pool

---

### Q12. Compressing the KV hand-off to FP8 cut its p99 from 9.7 s to 0.17 s in a transport-bound simulation. Doing the same compression on the prefill GPU gave the same latency. What, then, is the in-transit stage's advantage?

---

### Q13. Which assumption moved the verdict on an optical prefill pool for the block-circulant model more than any optical parameter?

a) The KV link bandwidth
b) How fast the GPU baseline runs FFTs relative to its matmul rate
c) The decode batch size
d) The number of layers

---

### Q14. Name three costs of an optical engine that a FLOP count does not show.

---

## Answers

**A1.** (b). The second lens transforms the masked spectrum back; by the convolution theorem that is a convolution.

**A2.** It contains no Fourier transform: projections, the MLP, the LM head and attention are all matrix multiplies or dot products. A transform engine only takes FFT and Fourier-domain work, so its share is zero.

**A3.** (d). Averaging k passes buys ½·log₂ k bits, so 3 extra bits need 4³ = 64 passes.

**A4.** The top plane carries almost all of the signal and is read at the same ENOB relative to its own peak, so the relative error barely improves. Digit planes help exact modular arithmetic, where every partial result must round correctly; floats need noise below the format's own rounding error.

**A5.** (c). The 2^ENOB factor doubles per extra bit; above the ENOB the workload needs, extra bits cost energy for nothing.

**A6.** It is not causal: every output mixes every position, including later tokens, so a token's output would depend on tokens not yet generated.

**A7.** (a). 1 / (1 − 0.0020) ≈ 1.002.

**A8.** Every filter spectrum must be on the mask while its inputs pass. A Hyena-2 forward pass at 2,048 tokens needs 269 rewrites of a 2-megapixel mask: 261 ms at an 8-bit DMD's 1,031 Hz, longer than the whole 59.0 ms GPU prefill. Batching shares the rewrites but does not reduce them.

**A9.** (b).

**A10.** That naming the same device for both pools reproduces the homogeneous run bit-identically: every request's timestamps and every summary number.

**A11.** (b).

**A12.** GPU time and energy, not latency: the GPU does an elementwise pass over the KV nearly free, so the stage saves GPU cycles and a memory pass. Where its work exceeds the budget (FP4 with block scales), the stage is the bottleneck and is slower than the GPU.

**A13.** (b). With GPU FFTs at the matmul rate even an optimistic optical engine loses TTFT; it wins only below about 1/31 of the matmul rate, or at 1/16 with a much faster mask.

**A14.** Any three of: converter energy and time (every value in and out, times the precision passes); the passes needed to reach the required ENOB; mask (SLM) rewrites; static laser and thermal-tuning power, charged even when idle; the digital work that stays digital; data movement to and from the optics.

