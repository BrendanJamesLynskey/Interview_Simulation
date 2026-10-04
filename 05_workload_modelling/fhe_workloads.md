# FHE Workloads for Hardware Simulation — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** RNS polynomials and the NTT, key switching, bootstrapping, memory- vs compute-bound FHE accelerators, traffic-reducing techniques
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Why is fully homomorphic encryption (FHE) a hardware problem?

**Answer:**

FHE lets a server compute on encrypted data without decrypting it. The cost is enormous expansion of data and work:

- A ciphertext in a CKKS-style scheme is a pair of polynomials of degree N (often 2^16) with coefficients modulo a large Q, stored in **RNS form** as L+1 "limbs" of machine-word-sized residues. At the top level of one common parameter set (N = 2^16, L = 23), a ciphertext is 24 MiB.
- Each homomorphic multiplication or rotation needs **key switching**, which multiplies by an evaluation key of 120 MiB in that set.
- Noise grows with each multiplication; **bootstrapping** refreshes a ciphertext and costs hundreds of homomorphic operations.

On a CPU, one bootstrap takes seconds; dedicated accelerators in the literature target milliseconds. The work is dominated by a few kernels (NTTs, element-wise modular multiply-adds, base conversions, automorphisms) and by **moving keys**: exactly the kind of problem where architecture simulation decides the design.

**Go deeper on this GitHub:** [FHESim 01, "Why FHE Is a Hardware Problem"](https://brendanjameslynskey.github.io/FHESim_01_FHE_for_Hardware_Engineers/#slide-01) · [FHESim 01, "How Big Things Are"](https://brendanjameslynskey.github.io/FHESim_01_FHE_for_Hardware_Engineers/#slide-04) · [Glossary: RNS polynomials and limbs](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-rns)

### Q2. What is the number-theoretic transform (NTT), and why do FHE accelerators build NTT units?

**Answer:**

The NTT is the discrete Fourier transform over a finite field (integers modulo a prime q with suitable roots of unity). It turns polynomial multiplication (a negacyclic convolution, O(N²)) into element-wise multiplication (O(N)) after an O(N log N) transform, exactly as the FFT does for real convolution, but with **exact** modular arithmetic: no rounding error.

An N-point NTT is (N/2) log₂ N butterflies, each a modular multiply and an add and subtract. For N = 2^16, that is 524,288 butterflies per limb, and FHE operations do NTTs on many limbs. So accelerators build wide NTT pipelines (thousands of butterflies per cycle) with efficient **modular reduction** (Barrett or Montgomery) in hardware.

**Go deeper on this GitHub:** [FHESim 01, "The Primitive Kernels"](https://brendanjameslynskey.github.io/FHESim_01_FHE_for_Hardware_Engineers/#slide-05) · [Glossary: number-theoretic transform (NTT)](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-ntt) · [Glossary: modular reduction (Barrett, Montgomery)](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-modred)

### Q3. Outline the four steps of CKKS bootstrapping.

**Answer:**

1. **ModRaise:** lift the exhausted ciphertext (at the lowest level) to a high modulus. The plaintext now carries unknown multiples of the old modulus q.
2. **CoeffToSlot:** a homomorphic (inverse) DFT that moves the coefficients into the slots, done as a few levels of sparse matrix–vector products with rotations (often baby-step giant-step).
3. **EvalMod:** evaluate an approximation of modular reduction (a scaled sine, via a Chebyshev polynomial and double-angle formulas) to remove the multiples of q.
4. **SlotToCoeff:** the inverse transform back to coefficients.

The result is a fresh ciphertext with levels to spare. Bootstrapping consumes many levels itself (16 of 23 in the parameter set above), dominates FHE run time, and is where most accelerator studies focus.

**Go deeper on this GitHub:** [FHESim 02, "Why Bootstrap, and the Four Steps"](https://brendanjameslynskey.github.io/FHESim_02_Anatomy_of_Bootstrapping/#slide-01) · [Glossary: bootstrapping](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-bootstrap)

---

## Intermediate

### Q4. Why does key switching dominate FHE accelerator design?

**Answer:**

Key switching runs after every multiplication (relinearisation) and every rotation. It:
- decomposes the ciphertext into dnum digits, raises each to an extended modulus (**ModUp**, with base conversion and NTTs),
- multiplies by an **evaluation key**: large, distinct per rotation amount,
- and reduces back (**ModDown**).

Its compute is large, but the bigger problem is **data**: each distinct rotation needs its own key (120 MiB each in the set above), a bootstrap uses dozens of distinct keys, and they do not fit on chip together. On this GitHub's ARK-class model, one bootstrap requested 6.74 GB of keys out of 12.44 GB of HBM traffic, and the design was memory-bound.

Design levers follow: bigger scratchpads (hold more keys), fewer distinct keys (algorithmic), generating keys on chip from seeds, and choosing dnum (fewer digits: smaller keys but more noise growth or fewer usable levels).

**Go deeper on this GitHub:** [FHESim 01, "Key Switching, Step by Step"](https://brendanjameslynskey.github.io/FHESim_01_FHE_for_Hardware_Engineers/#slide-07) · [FHESim 01, "Why Key Switching Dominates"](https://brendanjameslynskey.github.io/FHESim_01_FHE_for_Hardware_Engineers/#slide-08) · [Glossary: key switching and evaluation keys](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-keyswitch)

### Q5. How can algorithms move an FHE accelerator from memory-bound to compute-bound?

**Answer:**

By cutting off-chip traffic, mostly keys and plaintexts:

- **Min-KS** (minimum key-switching): restructure rotations so a few keys are reused many times.
- **Seeded keys**: store half of each key as a pseudo-random seed and regenerate it on chip.
- **On-the-fly plaintexts**: generate the constant plaintexts of the linear transforms on chip instead of streaming them.
- **Hoisting** and BSGS ordering: share work and keys across rotations of the same ciphertext.
- **SlotToCoeff first**: reorder bootstrapping so the transform runs at fewer levels.

On this GitHub's ARK-class model: baseline 13.94 ms, memory-bound, 6.74 GB of keys. With Min-KS + seeded keys + on-the-fly plaintexts, 7.19 ms, MAC-bound, with 0.58 GB of keys and 0.78 GB of total HBM traffic. Once compute-bound, more compute helps and more SRAM stops helping: the design question flips.

**Go deeper on this GitHub:** [FHESim 05, "Acceleration Techniques"](https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-04) · [FHESim 02, "Algorithmic Levers"](https://brendanjameslynskey.github.io/FHESim_02_Anatomy_of_Bootstrapping/#slide-11) · [Glossary: Min-KS, seeded keys and on-the-fly plaintexts](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-minks)

### Q6. A technique that reduces memory traffic made the simulated bootstrap *slower* on one design. How can that be?

**Answer:**

Because traffic reduction usually costs **compute**: fewer keys means more work per key-switch, regenerating seeds costs PRNG and NTT work, generating plaintexts on the fly costs encoding work.

- On a **memory-bound** design with idle compute, the trade is excellent.
- On an **NTT-starved** design (little compute), the extra work lands on the bottleneck.

On this GitHub's model, the same three techniques that took the ARK-class design from 13.94 ms to 7.19 ms took a small, NTT-bound design from 17.46 ms to 26.65 ms. The lesson for simulation: **an optimisation's value depends on the bound**, so evaluate algorithm and hardware together, not separately.

**Go deeper on this GitHub:** [FHESim 05, "Acceleration Techniques"](https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-04) · [Glossary: NTT-, MAC-, memory- and power-bound](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-bound) · [FHE results (section 5)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)

---

## Advanced

### Q7. How would you build a simulator for an FHE accelerator? What is the interface between the scheme and the hardware model?

**Answer:**

**The contract is a kernel-level trace.** The scheme side (parameters, algorithm choices, bootstrapping structure) emits a sequence of hardware kernels with sizes and data dependencies: NTT(limbs), iNTT, base conversion, modular multiply-add, automorphism, key loads, plaintext loads, with operand identities. The hardware side costs and schedules them.

**Components:**
1. **Trace generator** (from a scheme model, a compiler like HEIR, or a recorded library run).
2. **Scratchpad model**: what is on chip (LRU or smarter replacement), what must be fetched or spilled.
3. **Unit models**: NTT, MAC, automorphism units, each with a throughput and latency; HBM with a bandwidth (or a calibrated efficiency table).
4. **DES engine**: issue kernels respecting dependencies and resource availability.
5. **Power model**: static plus per-operation energy, with a power manager that caps the clock under a TDP.
6. **Metrics**: latency, per-unit utilisation, verdict (NTT-, MAC-, memory- or power-bound), hot-spots by stage, energy.

**Validation:** reproduce published accelerator results by configuring the model to them; calibrate kernel rates against a software library on a CPU; replay real library traces to check the operation counts.

**Go deeper on this GitHub:** [FHESim 03, "The Modelled Architecture"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-02) · [FHESim 03, "The SimPy Engine"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-05) · [FHE_Accelerator_Sim](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim)

### Q8. How much on-chip SRAM does an FHE accelerator need? How would a simulator answer that?

**Answer:**

Sweep the scratchpad size with everything else fixed, and watch latency, traffic and (if available) area:

On this GitHub's ARK-class model with the baseline algorithm, latency fell steeply from 128 MiB (26.98 ms) to 512 MiB (13.94 ms), then slowly to a plateau at 2,048 MiB (11.41 ms): beyond that, all keys of one bootstrap fit and extra SRAM does nothing. With traffic-reducing techniques the knee moved down: 256 MiB already gave 8.71 ms and the curve was flat from 512 MiB (7.19 ms).

Adding an (illustrative) area model shows the cost side: the 2,048 MiB design needs a die of about 1,182 mm², larger than the ~858 mm² reticle limit. The latency–energy–area Pareto front with all techniques runs from 128 to 512 MiB; past 512 MiB, SRAM is pure cost.

So the answer depends on the algorithm, which is why hardware and algorithm must be explored jointly.

**Go deeper on this GitHub:** [FHESim 05, "SRAM Against Key Traffic and Area"](https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-02) · [SimEng 13, "Worked Example: The Scratchpad Sweep"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-10) · [Glossary: scratchpad, LRU and spills](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-scratchpad)

### Q9. A novel-hardware company proposes an analogue or optical engine for the NTT. What would a simulator need to tell you before you believe the speed-up?

**Answer:**

1. **Precision**: the NTT needs **exact** modular arithmetic on 28–60-bit words. An analogue engine has a limited effective number of bits (ENOB), so operands must be decomposed into small digits, each transformed separately, and recombined, multiplying the work. Does the engine's ENOB allow exact rounding at the digit size chosen?
2. **Conversion cost**: every digit crosses DACs and ADCs; their energy and sample rate (not the optical transform itself) often set throughput and power.
3. **System bound**: if the accelerator is memory-bound, a faster NTT changes nothing (or makes things worse if it adds traffic). Simulate the whole bootstrap, not the kernel.
4. **Static power** (lasers, thermal tuning), and **area** of converters and the photonic die.

On this GitHub's model (with its stated, partly speculative assumptions), a realistic optical NTT engine made a bootstrap about 23× slower than a small digital design, and an idealised exact engine was 1.39× faster only on the NTT-starved design; on the memory-bound ARK-class design it was slower.

**Go deeper on this GitHub:** [FHESim 04, "The Precision Tax"](https://brendanjameslynskey.github.io/FHESim_04_Optical_NTT_Engines/#slide-07) · [FHESim 04, "When It Wins and When It Loses"](https://brendanjameslynskey.github.io/FHESim_04_Optical_NTT_Engines/#slide-10) · [Glossary: ENOB and exact rounding](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-enob)

**See also:** [11 Novel Hardware and Optical Inference](../11_novel_hardware_and_optical_inference/): optical transform engines for LLM inference, where the same precision and conversion arguments are applied to floats.
