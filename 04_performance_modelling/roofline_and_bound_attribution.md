# The Roofline and Bound Attribution — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Operational intensity, the roofline and its ridge point, bound attribution, hot-spots, analytic lower bounds
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Explain the roofline model.

**Answer:**

The roofline model (Williams, Waterman and Patterson, 2009) bounds the attainable performance of a kernel on a machine by two ceilings:

$$P_{\text{attainable}} = \min\left(P_{\text{peak}},\; I \times B_{\text{peak}}\right)$$

where **I** is the kernel's **operational (arithmetic) intensity**: FLOPs per byte moved to and from memory, and B is the memory bandwidth. Plotted on log–log axes, performance against intensity is a sloped line (memory-bound region) that meets a flat line (compute-bound region) at the **ridge point**, I* = P_peak / B_peak.

- I < I*: **memory-bound**. More bandwidth helps; more compute does not.
- I > I*: **compute-bound**. More compute helps; more bandwidth does not.

Its value: in one plot, it says which resource limits a kernel and how far the kernel is from that limit.

**Go deeper on this GitHub:** [InfSim 03, "The Roofline"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-04) · [Glossary: roofline, arithmetic intensity and ridge point](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-roofline)

### Q2. Compute the ridge point of a device with 989 TFLOP/s and 3.35 TB/s, and with realistic efficiencies.

**Answer:**

At peak: I* = 989e12 / 3.35e12 ≈ **295 FLOP/byte**.

With achievable fractions (say 55% of peak FLOP/s and 80% of peak bandwidth, the defaults of the LLM serving simulator on this GitHub): I* = (989e12 × 0.55) / (3.35e12 × 0.80) ≈ **203 FLOP/byte**.

Interpretation for LLM inference in BF16 (2 bytes per weight, 2 FLOPs per weight per token):
- **Decode at batch b** has intensity of roughly b FLOP/byte (each weight is read once and used for b tokens). At batch 1 it is about 1; at batch 64 about 32. Far below 203: **memory-bound**.
- **Prefill of 2,048 tokens** reuses each weight 2,048 times: intensity in the thousands: **compute-bound**.

Derating moves the ridge point, so always say which numbers you used.

**Go deeper on this GitHub:** [InfSim 03, "Interactive: Put a Batch on the Roofline"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-05) · [the recorded intensities (section 1)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

### Q3. What is "bound attribution", and why report it alongside a latency?

**Answer:**

Bound attribution labels each phase, kernel or interval with the resource that limits it: compute, memory, a link, power, or a specific unit. Reporting it with a latency explains the latency and predicts which design changes would help.

Example from the FHE accelerator simulator on this GitHub (one bootstrap on an ARK-class design):

```text
bootstraps 1   latency 13.94 ms   per bootstrap 13.94 ms   clock 100% (dynamic)
utilisation  ntt 13%  mac 29%  auto 2%  hbm 89%
verdict      memory-bound
hot-spots    modraise->ntt  cts->hbm  evalmod->mac  stc->hbm   (dominant: cts -> hbm)
...
analytic lower bound 10.01 ms
```

This says: memory (HBM) is busy 89% of the time; the compute units are mostly idle; adding NTT throughput will not help; reducing key traffic or adding bandwidth will. The analytic lower bound (10.01 ms) says how much of the latency is irreducible traffic and how much is scheduling and overlap loss.

**Go deeper on this GitHub:** [FHESim 03, "Metrics and Hot-Spots"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-08) · [Glossary: NTT-, MAC-, memory- and power-bound](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-bound) · [Glossary: hot-spot attribution](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-hotspot)

---

## Intermediate

### Q4. A kernel's measured performance is 40% of its roofline. What explains the gap?

**Answer:**

The roofline is an upper bound with assumptions; the gap comes from what it leaves out:

1. **Achievable vs peak**: peak FLOP/s needs ideal instruction mix and full occupancy; peak bandwidth needs perfect streaming. Measured achievable ceilings (from microbenchmarks) are often well below peak.
2. **Wrong byte count**: the real kernel moves more than the minimum: poor cache reuse, spills, uncoalesced accesses, re-reading data that a better tiling would keep on chip.
3. **Other ceilings**: instruction issue, special-function units, on-chip bandwidth (shared memory, caches), and the interconnect between chips.
4. **Latency, not bandwidth**: too little parallelism to hide memory latency (small batches, dependent accesses).
5. **Overheads outside the kernel**: launch latency, synchronisation, host interaction, which dominate small kernels.
6. **Power and thermal limits**: the clock drops under load.

A **hierarchical roofline** (one memory line per level: DRAM, L2, L1/shared) often locates the problem.

**Go deeper on this GitHub:** [InfSim 03, "The Roofline"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-04) · [InfSim 06, "Utilisation and Efficiency"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-03) · [Glossary: utilisation, MFU and MBU](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-mfu)

### Q5. Why is a summed per-operator roofline an upper bound on time, and what is the matching lower bound?

**Answer:**

Summing per-operator roofline times assumes every operator reads its inputs from memory and writes its outputs back (no fusion), and that operators run one after another. It is an **upper bound** for a perfect implementation of that unfused graph.

An ideally **fused** implementation would keep intermediates on chip, so only "essential" traffic remains (weights, the KV cache, model inputs and outputs). One roofline over the whole graph then gives a **lower bound**:

$$t \ge \max\left(\frac{\sum \text{FLOPs}}{F},\; \frac{\text{essential bytes}}{B}\right)$$

Real implementations land between. On this GitHub, a Llama-3-8B prefill trace costed this way gave 126.68 ms unfused (meta-device trace, unfused attention) against a 71.01 ms fused bound, with the simulator's closed form at 58.53 ms (all before a fixed step overhead). The gap between unfused and fused is the case for fusion (e.g. flash attention).

**Go deeper on this GitHub:** [SimEng 10, "Costing the Trace"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-10) · [Glossary: unfused and ideal-fusion bounds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-fusionbound) · [coding challenge 03](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_03_roofline_classifier.py)

### Q6. How do you compute hot-spots in a discrete-event simulator, rather than in a profile of real hardware?

**Answer:**

Instrument the simulator to record, for every interval of simulated time, what each request or operation is doing and which resource it is waiting for:

1. **Per-resource busy time** (utilisation): sum of intervals each resource is in use.
2. **Per-stage time** for each request: queueing, service, transfer, waiting for memory, etc. Aggregate over requests (mean and tail).
3. **Critical-path attribution**: for each request, which stage dominated its latency; for each stage, which resource it waited on.
4. **Saturation flags**: resources busy more than, say, 90% of the time.

Then the hot-spot is the resource on which the largest share of critical time is spent. On this GitHub, an LLM serving simulator reports, for one overloaded configuration:

```text
where time goes  prefill 1%  kv_wait 81%  kv_transfer 1%  decode 18%
hot-spot     stage=kv_wait -> kv-link (busy 96%)   busy>90%: decode-0, kv-link
```

so the KV-transfer link, not compute, is the problem in that configuration.

**Go deeper on this GitHub:** [InfSim 06, "Hot-Spot Attribution"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-04) · [the example report (section 7)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Advanced

### Q7. A design is memory-bound. You can add either SRAM or compute. How would a simulator decide, and what could make it change its mind?

**Answer:**

Simulate both upgrades at equal **area** (or cost) and compare the latency gained per mm²:

On this GitHub's FHE accelerator model (illustrative 7 nm area model), starting from a 256 MiB scratchpad:
- with the baseline algorithm (memory-bound), +128 MiB of SRAM saved **3.74 ms per 100 mm²**, against **0.21 ms per 100 mm²** for doubling the NTT and MAC units;
- with algorithmic techniques that cut key traffic (the design becomes MAC-bound), the two were about even: **1.71** against **1.68**.

What changes the decision:
- **The algorithm**: reducing traffic moves the bound from memory to compute, and with it the best use of area.
- **The workload size**: SRAM helps only while the working set (here, evaluation keys) does not fit; past that point extra SRAM is pure cost.
- **Coefficients**: area per MiB, bandwidth, unit areas. Check that the ranking survives their plausible range.

**Go deeper on this GitHub:** [SimEng 13, "Compute or SRAM, and When to Split the Die"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-11) · [FHESim 05, "NTT-Bound Against Memory-Bound"](https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-03) · [the recorded table (section 23)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)

### Q8. When does the roofline mislead you?

**Answer:**

- **Overlap and dependencies**: the roofline assumes compute and memory overlap perfectly. Dependent phases (load, then compute, then store, with no double buffering) take the *sum*, not the max.
- **Capacity effects**: whether the working set fits on chip changes the bytes moved discontinuously; the roofline takes bytes as given.
- **Contention**: two kernels or two tenants sharing bandwidth each see less than the roofline assumes.
- **Latency-bound regimes**: small transfers or pointer chasing are limited by latency, not bandwidth.
- **Memory-system efficiency varies with access pattern**: the "B" in the roofline is not one number (see the memory-system questions).
- **Power**: at a power cap, compute-heavy kernels may not reach peak FLOP/s at all; a third roof appears.

The roofline is the right first model and a necessary sanity check, but a DES or cycle model is needed whenever these effects decide the answer.

**Go deeper on this GitHub:** [InfSim 07, "DVFS and Power Caps: The Third Roof"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-05) · [SimEng 04, "Why "Bandwidth × Efficiency" Fails"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-01)

### Q9. Derive the analytic lower bound for an FHE bootstrap's latency on an accelerator. What does the gap to the simulated latency mean?

**Answer:**

A lower bound takes, for each resource, the total work it must do divided by its rate, and takes the maximum:

$$t \ge \max\left( \frac{\text{total HBM bytes}}{B},\; \frac{\text{NTT butterflies}}{\text{butterfly rate}},\; \frac{\text{MACs}}{\text{MAC rate}},\; \dots \right)$$

because no schedule can make any resource do its work faster than its peak rate. Dependencies only add to this.

The gap between the simulated latency and the bound is **scheduling loss**: phases where the bottleneck resource is idle because it waits for another (e.g. HBM waiting for a key-switch to finish computing, or compute waiting for keys). On this GitHub, a bootstrap simulated at 13.94 ms has a bound of 10.01 ms: about 28% of the time is lost to dependencies and imperfect overlap. That suggests a different kind of optimisation from adding hardware: better prefetching, scheduling, or algorithm ordering.

**Go deeper on this GitHub:** [FHESim 03, "Metrics and Hot-Spots"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-08) · [Glossary: analytic lower bounds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-bounds) · [the default run (section 4)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)
