# The Fidelity Ladder and the Speed–Accuracy–Effort Trade-off — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Analytical → discrete-event → TLM → cycle-level → RTL → emulation → silicon; choosing a level
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Describe the fidelity ladder for a chip, from the cheapest model to silicon.

**Answer:**

| Rung | What it models | Typical speed (indicative) | Typical use |
|---|---|---|---|
| **Analytical** (roofline, queueing formulas, spreadsheet) | Rates and capacities; no time-ordering | Instant | Bounds, early exploration, sanity checks |
| **Discrete-event (DES)** | Operations as events on shared resources; queues, contention | Very fast: whole workloads in seconds | Serving and system studies, scheduling policy, sizing |
| **Transaction-level (TLM, e.g. SystemC TLM-2.0)** | Transactions between components (reads, writes, DMA) with approximate timing | Fast | Virtual platforms, architecture models, early software |
| **Cycle-level / cycle-accurate model** | Pipeline stages, arbitration, queues per cycle | Slow (thousands to millions of simulated cycles per second) | Micro-architecture tuning |
| **RTL simulation** | The actual design, signal by signal | Slower still on large designs | Functional verification, exact cycle counts |
| **Emulation / FPGA prototype** | The RTL mapped to special hardware | MHz-class | Full-chip verification, firmware and OS bring-up |
| **Silicon** | Reality | Real time | Validation of everything above |

Each rung up adds detail, accuracy (if built right) and confidence, and costs speed and building effort. The ladder is a menu, not a sequence: a team uses several rungs at once and checks them against each other.

**Common mistake:** believing that a higher rung is always "better". A cycle-accurate model that cannot run the workload in a day answers nothing.

**Go deeper on this GitHub:** [InfSim 01, "The Fidelity Ladder"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-03) · [Introduction to Simulation, "The Levels at a Glance"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/3) · [Glossary: the fidelity ladder](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-fidelity)

### Q2. What does each rung of the ladder throw away?

**Answer:**

- **Analytical:** time-ordering. It cannot see queueing, burstiness or interference; it gives means and bounds.
- **DES:** the inside of an operation. A kernel takes "t seconds" from a cost model; the pipeline and memory behaviour inside it are folded into that number.
- **TLM:** signal-level protocol detail. A transaction is one function call with a delay, not a handshake per cycle. Loosely timed models also let processes run ahead of each other in time.
- **Cycle-level:** gate-level timing and exact RTL corner cases; usually a hand-written model of the micro-architecture, not the design itself.
- **RTL:** analogue effects, physical timing (unless back-annotated gate-level), and the speed to run real software.
- **Emulation:** visibility (fewer signals observable at once) and some flexibility.

The question to ask of any model: **is the effect that drives my answer above or below the line this rung draws?** If DRAM bank conflicts decide whether a design is memory-bound, a model with a flat "bandwidth × efficiency" memory is below the line.

**Go deeper on this GitHub:** [InfSim 01, "What Each Level Throws Away"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-04) · [SimEng 04, "Why "Bandwidth × Efficiency" Fails"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-01)

### Q3. What is the speed–accuracy–effort trade-off?

**Answer:**

Three costs pull against each other:

- **Speed**: simulated time per wall-clock second. It decides how many experiments you can run and how big a workload you can afford.
- **Accuracy**: closeness to the real system on the quantities you care about.
- **Effort**: engineering time to build, calibrate and maintain the model.

You can usually have two. A fast, accurate model needs much effort (calibration, careful abstraction). A fast, cheap model is approximate. An accurate, cheap model (run the RTL) is slow.

Two measured points from this GitHub show the scale of speed differences even within one rung:

- Two RTL simulators on the same NTT core: an event-driven simulator (Icarus) ran 6,416 clock cycles per second and a cycle-based compiled simulator (Verilator) ran 837,883, 131× more. Verilator paid a 4.38 s compile first.
- A SimPy DES of LLM serving simulated 770.9 s of serving 835× faster than real time; an exact macro-stepped fast path reached 1,566× real time with identical results.

**Go deeper on this GitHub:** [Introduction to Simulation, "Speed, Accuracy and Effort"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/26) · [the RTL speed measurement](https://github.com/BrendanJamesLynskey/Introduction_to_Simulation/blob/main/demo/rtl_speed/results.md) · [the DES speed measurement](https://github.com/BrendanJamesLynskey/Introduction_to_Simulation/blob/main/demo/des_speed/results.md)

---

## Intermediate

### Q4. A colleague says: "the analytical model and the DES disagree by 30%, so the DES must be wrong". How do you respond?

**Answer:**

Not necessarily. They answer different questions.

- An analytical throughput bound ignores queueing: at high load, real latency includes waiting time, which the bound does not have. A 30% gap in *latency* near saturation is expected.
- At **low load** (no queueing) and in **steady state**, the two should agree closely, because the DES's per-operation cost model *is* the analytical model. That is the regime to compare first.
- If they disagree at low load, one of them has a bug. Check the bookkeeping (bytes, FLOPs, units) and the DES's event logic (e.g. a resource held longer than intended).

So: compare them where they must agree, and explain the disagreement elsewhere by a mechanism (queueing, contention, batching). Agreement in the right regime is a powerful test.

**Go deeper on this GitHub:** [InfSim 02, "Step 2 — A Queue, Checked Against Theory"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-03) · [Glossary: queueing theory checks](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-queueing) · [Glossary: analytic lower bounds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-bounds)

### Q5. When is a cycle-accurate model worth building?

**Answer:**

When the decision depends on effects that only appear cycle by cycle, *and* the workload you need to run is short enough to simulate at that speed.

Worth it:
- tuning a pipeline, a scheduler or an arbiter whose behaviour depends on cycle-level interleaving;
- predicting the latency of a small kernel to within a few percent for a hardware/software contract;
- calibrating a faster model: run the cycle model on representative snippets and fit the faster model's coefficients.

Not worth it:
- capacity planning for a serving cluster (seconds to hours of simulated time);
- comparing ten architectures early, when their coefficients are guesses anyway.

A common compromise is **sampling**: run detailed simulation on representative intervals and fast-forward between them, or calibrate a fast model from cycle-level runs of key kernels.

**Go deeper on this GitHub:** [InfSim 08, "Sampling, Checkpoints and Mode Switching"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-11) · [SimEng 05, "RTL Cycle Counts and a Cycle Model"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-11) · [Glossary: cycle models from RTL](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-cyclemodel)

### Q6. How do models at different rungs feed each other in a real flow?

**Answer:**

In both directions:

- **Down the ladder (spec to RTL):** the architecture model is the executable specification. Its operation semantics become the RTL's golden reference; its predicted cycle counts become the RTL's performance targets.
- **Up the ladder (RTL to model):** RTL simulation gives measured cycle counts and switching activity for key blocks. Those calibrate the fast model's cost tables and power coefficients.

Example from this GitHub: an NTT core in RTL was verified bit-exactly against a Python golden model; its measured cycle counts fitted a closed form, `compute = log2(n) (n/2P + 6)`, matching every measured size; and that cycle model was fed back to the system simulator as an efficiency per core size.

The "co-flow" also catches mismatches early: if the RTL is slower than the model assumed, the model's conclusions need revisiting before tape-out, not after.

**Go deeper on this GitHub:** [InfSim 01, "The Co-Flow: Models and RTL Feeding Each Other"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-07) · [SimEng 05, "Feeding the RTL Back Into the Simulator"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-12) · [Glossary: calibrating a simulator from RTL](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-rtlcalib)

---

## Advanced

### Q7. You have one week to decide between two accelerator architectures. Which rungs do you use, and how?

**Answer:**

1. **Day 1–2: analytical.** For each architecture and each key workload kernel: FLOPs and bytes, roofline time, bound. This often decides the question outright (e.g. both are memory-bound, so the one with more bandwidth per dollar wins).
2. **Day 2–4: DES, if dynamics matter.** If the decision involves batching, contention, interference or tail latency, a small DES with the roofline as its cost model. Sweep load and the uncertain coefficients.
3. **Day 4–5: sensitivity.** Which coefficients flip the ranking? If an efficiency assumption flips it, that coefficient needs measuring: a microbenchmark on similar existing hardware, or a cycle-level run of the one kernel that matters.
4. **Report** the ranking, its robustness range, and what would change it.

What you do not do: build a cycle-accurate model of both. The detail would not be ready in a week, and the ranking question rarely needs it.

**Go deeper on this GitHub:** [InfSim 01, "Interactive: How Long Would It Take to Simulate?"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-05) · [Introduction to Simulation, "How to Choose a Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/27)

### Q8. What makes a model "accurate enough"? How would you set an accuracy target?

**Answer:**

Accuracy is relative to a decision, so set the target from the decision:

- **Ranking decisions** (A or B?) need the *difference* between options to be larger than the model's error on that difference. Errors common to both options often cancel, so ranking can be robust even with poor absolute accuracy.
- **Contract numbers** (a latency promised to a customer) need absolute accuracy with a stated error bar, validated on similar hardware.
- **Sizing** (how many devices?) needs accuracy near the operating point, especially near saturation, where small throughput errors become large latency errors.

Make it measurable: name the quantities (e.g. step time per kernel, p99 latency at a stated load), the reference they are checked against, and the tolerance (e.g. within 10% on step time for the calibration set and, separately, on a held-out set). Out-of-sample checks matter: a model fitted to the data it is checked on will look better than it is.

**Go deeper on this GitHub:** [Glossary: calibration and out-of-sample prediction](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-calibration) · [FHESim 02, "Checked Against a Real OpenFHE Bootstrap"](https://brendanjameslynskey.github.io/FHESim_02_Anatomy_of_Bootstrapping/#slide-12)

### Q9. Two models of the same hardware, at different rungs, give different answers for the same workload. How do you reconcile them?

**Answer:**

1. **Make the inputs identical.** Feed both the same trace (same operations, same order, same sizes). Many "model differences" are workload differences.
2. **Compare at the finest common granularity**: per operation start and end times, bytes per resource, busy time per unit. Aggregate numbers hide where the divergence starts.
3. **Find the first divergence** and classify it:
   - a **cost difference** (the two compute an operation's duration differently): check formulas and float operation order;
   - an **ordering difference** (simultaneous events served in different orders): make tie-breaking explicit in both;
   - a **modelling difference** (one models an effect the other ignores, e.g. a quantum in a loosely timed model letting processes run ahead).
4. **Decide which is right** for each class, against a third reference if one exists.

Example from this GitHub: a SystemC approximately-timed model and a SimPy model of the same FHE accelerator agreed op-by-op once the SystemC arbiter granted the *oldest* simultaneous request explicitly. With the kernel's implementation-defined process order instead, 6 of 203 operations differed on one bootstrap, although the overall horizon still agreed.

**Go deeper on this GitHub:** [SimEng 03, "Checked Against the SimPy Model"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-09) · [SimEng 03, "Ties Are Part of the Model"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-08) · [the recorded comparison](https://github.com/BrendanJamesLynskey/SystemC_Accelerator_Model/blob/main/examples/results.md)
