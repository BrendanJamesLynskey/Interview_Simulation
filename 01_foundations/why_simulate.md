# Why Simulate — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** What a simulator is for, the questions it answers, and when a spreadsheet is enough
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What is a simulation, and how does it differ from an analytical model and from a measurement?

**Answer:**

A **simulation** executes a model of a system forward in time (or over events) and observes what happens. An **analytical model** solves the model's equations in closed form. A **measurement** observes the real system.

| | Analytical model | Simulation | Measurement |
|---|---|---|---|
| What it needs | Equations you can solve | A model you can execute | The real system (or a prototype) |
| Answers | Means, bounds, asymptotes | Distributions, transients, interactions | Ground truth for that system and workload |
| Cost per question | Seconds | Seconds to days | Weeks to months (if the system exists at all) |
| Typical failure | Assumptions too strong (e.g. no contention) | Model wrong or uncalibrated | Not representative, noisy, or too late |

The three are complementary. A good team uses the analytical model to bound and sanity-check the simulator, the simulator to explore what cannot be measured yet, and measurements to calibrate and validate both.

**Common mistake:** treating the simulator as the truth. A simulator is a hypothesis about the system that happens to be executable. Its numbers are only as good as its validation.

**Go deeper on this GitHub:** [Introduction to Simulation, "What a Simulation Is"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/2) · [InfSim 01, "Four Jobs a Simulator Does"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-02)

### Q2. Why do hardware teams simulate before silicon exists?

**Answer:**

Because the expensive decisions are made long before there is anything to measure, and they are hard to undo.

1. **Cost of a mistake.** Mask sets at advanced nodes are widely reported to cost tens of millions of dollars, and a respin costs months. A wrong choice of memory bandwidth, on-chip SRAM size or core count is baked in at architecture freeze.
2. **Time to market.** Software, compilers and system integration must start before silicon. A model of the chip lets that work proceed in parallel.
3. **The design space is large.** Dozens of parameters interact (compute units, SRAM, bandwidth, clocks, interconnect). You cannot build every variant, but you can simulate thousands.
4. **Verification.** The RTL needs a reference: a model that says what the right answer (and roughly the right timing) is.

A simulator typically does four jobs: **architecture exploration** (which design?), **performance prediction** (how fast, how much power?), **software enablement** (run code before the chip exists) and **verification support** (golden models, reference timing).

**Common mistake:** answering only "to find bugs". Functional verification is one job; for a performance-modelling role the main value is making architecture decisions with evidence.

**Go deeper on this GitHub:** [InfSim 01, "The Pre-Silicon Problem"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-01) · [InfSim 01, "Four Jobs a Simulator Does"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-02)

### Q3. Why simulate rather than build a prototype?

**Answer:**

A prototype (an FPGA build of the RTL, a test chip, a bench model) is the real design in another implementation. It is the right tool once the design is settled enough to build. Simulation wins earlier and wider:

| | Simulation | Prototype |
|---|---|---|
| Available | From the first idea | Only once the design, or its RTL, exists |
| Cost of a variant | A parameter change and a re-run | A rebuild: long FPGA compiles, or months for a test chip |
| Design points | Hundreds or thousands in a sweep | A handful |
| Visibility | Every signal, every queue, every piece of state | Only what you can probe |
| Experiments | Overloads, failures and extreme conditions on demand | Only those that are safe and affordable to cause |
| Fidelity | Only what the model includes, so it must be validated | Real behaviour, including effects nobody modelled |
| Speed | Large SoCs run at tens to thousands of cycles per second in RTL simulation (indicative) | An FPGA prototype runs at tens of megahertz (indicative) |

The usual answer is both, in sequence: simulate to choose and de-risk the design, prototype to run real software at speed and catch what the model left out, then use the prototype's measurements to calibrate the model.

**Common mistake:** treating it as either/or, or treating the prototype as the truth. An FPGA prototype runs at a different clock, with different memories and I/O, from the final chip; its timing is no more the product's than a model's is.

**Go deeper on this GitHub:** [Introduction to Simulation, "Why Simulate?"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/3) · [Introduction to Simulation, "When Simulation Is the Wrong Tool"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/5) · [Introduction to Simulation, "Gate Level, Emulation and FPGA Prototypes"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/14)

### Q4. Give examples of questions a performance simulator answers that a datasheet cannot.

**Answer:**

A datasheet gives peaks: FLOP/s, bandwidth, capacity. A simulator answers questions about **behaviour under a workload**:

- **Latency distributions under load.** Not "what is the latency" but "what is the p99 time to first token at 4 requests per second with this arrival pattern?" Queueing makes tail latency grow non-linearly as load rises.
- **Contention and interference.** Two phases sharing one device (for example LLM prefill and decode) slow each other down; a datasheet has no notion of that.
- **Where the bottleneck is.** Which resource is saturated (compute, memory, a link), and does it move when you change the design?
- **Sensitivity.** How much does latency improve per extra GB/s, per extra MiB of SRAM, per extra compute unit?
- **Policy questions.** Batching rules, scheduling, placement, power capping. These are software decisions whose effect depends on dynamics.
- **Energy.** Joules per useful operation, which depend on utilisation and static power, not just peak power.

**Go deeper on this GitHub:** [InfSim 05, "The Simulator: Model and Assumptions"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-05) · [InfSim 06, "From Events to Evidence"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-01)

---

## Intermediate

### Q5. When does a spreadsheet beat a simulator? When does it stop being enough?

**Answer:**

A spreadsheet (a closed-form or roofline model) wins when:

- you need **bounds or steady-state averages**: peak throughput, the minimum time a step can take, capacity limits;
- the system has **no significant contention or queueing** at the load you care about;
- you are **early**: comparing ten candidate architectures to cut them to three;
- you need **explainability**: every number traces to a formula a reviewer can check.

It stops being enough when **dynamics** matter: queueing near saturation, bursty arrivals, scheduling policy, interference between workloads, feedback (power capping, back-pressure), or when you need a **distribution** (p99) rather than a mean.

A concrete example from this GitHub: an analytic capacity bound for a disaggregated LLM serving setup says the prefill pool saturates at 7.49 requests per second. A bisection search over the discrete-event simulator finds that the largest rate still meeting the latency target for 90% of requests is 5.97 requests per second. The spreadsheet is a correct ceiling; the simulator shows where queueing breaks the service-level objective well before the ceiling.

**Best practice:** build both. The analytic model brackets the search and acts as a test oracle for the simulator.

**Go deeper on this GitHub:** [InfSim 08, "Smarter Experiments: Multi-Fidelity, Search, Surrogates"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-10) · [Glossary: multi-fidelity search and bisection](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-multifidelity) · [the recorded numbers (section 8 and 9)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

### Q6. "Start from the question." What does that mean when scoping a simulator?

**Answer:**

The question decides the abstraction level, the inputs, the outputs and the accuracy needed. Write it down before writing code:

| Question | What must be modelled | What can be dropped |
|---|---|---|
| "How many prefill and decode devices for 50 req/s at a p99 TTFT of 1 s?" | Request arrivals, batching, per-step cost, queues, KV transfer | Instruction-level detail, individual DRAM commands |
| "Does doubling HBM bandwidth help this kernel?" | Bytes moved, compute time, overlap | Request-level queueing |
| "Is this scheduling policy starvation-free?" | Policy logic and event ordering | Accurate timing coefficients |

Then derive:

- **Outputs and metrics** (what will be plotted in the decision meeting).
- **Required accuracy** (relative ranking? ±10% absolute?). Ranking designs often needs much less accuracy than predicting absolute latency.
- **Validation plan** (what will the numbers be checked against?).

**Common mistake:** starting with "let's model the chip in detail" and discovering, months later, that the detail does not answer anyone's question and runs too slowly to sweep.

**Go deeper on this GitHub:** [InfSim 04, "A Map: Which Question, Which Level?"](https://brendanjameslynskey.github.io/InfSim_04_Simulator_Landscape/#slide-01) · [Introduction to Simulation, "How to Choose a Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/30)

### Q7. What outputs should every performance simulator produce, beyond "the answer"?

**Answer:**

1. **The metrics asked for**, as distributions where it matters (p50/p90/p99, not just means).
2. **Utilisation of every resource**, so a reader can see what is saturated.
3. **Bound attribution / hot-spots**: which resource limits each phase, and where time goes.
4. **A trace** that can be viewed on a timeline (e.g. Chrome trace events in Perfetto), for debugging and for convincing people.
5. **The configuration and the seed**, recorded with the results, so every number can be regenerated.
6. **Sanity counters**: events processed, simulated time, bytes moved. These catch silent errors (a resource never used, a queue that never drains).
7. **Power and energy**, if the design is power-limited. Most accelerators are.

**Why:** a single number invites "is that right?". Utilisation, hot-spots and a trace let a reviewer check the story behind the number.

**Go deeper on this GitHub:** [InfSim 06, "Hot-Spot Attribution"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-04) · [InfSim 06, "Traces: Seeing the Timeline in Perfetto"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-05) · [Glossary: hot-spot attribution](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-hotspot)

### Q8. Which level would you use for architectural exploration, and which for functional verification? Why?

**Answer:**

They answer different questions, so they need different trade-offs between speed and exactness.

| | Architectural exploration | Functional verification |
|---|---|---|
| Question | Which design should we build? | Does the design do what the specification says? |
| Accuracy needed | Enough to rank the options correctly | Exact logic, bit for bit |
| Speed needed | Very high: many design points, re-parameterised quickly | Enough to run the regression suite every night |
| Usual level | Analytical first, then architecture- or system-level DES or transaction-level models (levels 4 and 5) | RTL simulation (level 3), then emulation or FPGA prototypes for long software-driven tests |
| Typical tools | Rooflines and spreadsheets, SimPy, SystemC TLM, gem5-class models | Event-driven or cycle-based RTL simulators (Icarus, Verilator, commercial ones), cocotb or UVM testbenches, assertions, functional coverage |

- **Exploration** starts with an analytical model to prune the space, then a discrete-event or transaction-level model for the survivors. Cycle-level detail is added only for the blocks where the answer turns on the microarchitecture. RTL is too slow and arrives too late to explore with.
- **Verification** needs the design itself, so it runs at the RTL, against a **golden model** from a higher level acting as a scoreboard, with constrained-random stimulus, assertions and coverage closure. A performance model is not bit-exact, so it cannot sign off function.
- **The two meet:** the higher-level model becomes the verification reference, and RTL cycle counts flow back to calibrate the architecture model.

**Common mistake:** choosing by habit ("we always use the cycle-accurate model") instead of by the question. Detail that the question does not need costs speed, and detail you cannot calibrate is not accuracy.

**Go deeper on this GitHub:** [Introduction to Simulation, "Motivation, Level and Tool"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/4) · [Introduction to Simulation, "How to Choose a Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/30) · [Introduction to Simulation, "One Accelerator, Every Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/20) · [InfSim 01, "Four Jobs a Simulator Does"](https://brendanjameslynskey.github.io/InfSim_01_Why_Simulate/#slide-02) · [SimEng 05, "Two Golden Models and a Scoreboard"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-04)

---

## Advanced

### Q9. System design: a novel-hardware company asks you to build its first performance simulator. What do you deliver in the first month?

**Answer (a structured model answer):**

**1. Clarify the decisions (week 1).** Which architecture choices are open? Which workloads matter (and who owns them)? What accuracy is needed for each decision? Who consumes the results (architects, software, product)?

**2. Analytical baseline (week 1–2).** A roofline-style model per workload kernel: FLOPs and bytes from the model graph, peak rates, achievable efficiencies. It gives first answers within days, brackets later results, and becomes a test oracle.

**3. A minimal discrete-event simulator (week 2–4).**
- Separate the **workload** (a trace or generator of operations), the **hardware model** (resources plus a cost model) and the **engine** (event list, scheduling). Keep the cost model swappable.
- Model queues and contention only where the questions need them.
- Deterministic by construction: seeded random streams, explicit tie-breaking.

**4. Measurement and evidence.** Metrics with confidence intervals, utilisation, hot-spots, traces, energy. Results regenerated by one command.

**5. Verification from day one.** Unit tests, closed-form checks (an M/M/1 queue, a single kernel against its roofline), property-based tests for invariants, golden runs in CI.

**6. A calibration plan.** What will the model be checked against: published numbers, a prototype, an FPGA, RTL cycle counts of key blocks? Record the error per quantity.

**What you explicitly do not do in month one:** cycle-accurate models of everything, a GUI, or a general framework before the first question is answered.

**Go deeper on this GitHub:** [InfSim 02, "Structuring a Simulator That Lasts"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-09) · [SimEng 09, "Template 1: a Simulator Specification"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-09) · [FHESim 03, "What the Simulator Must Answer"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-01)

**See also:** [11 Novel Hardware and Optical Inference](../11_novel_hardware_and_optical_inference/): a worked example of simulating a novel engine before building it, including a negative result.

### Q10. How do you present simulator results so that they drive a decision rather than start an argument?

**Answer:**

- **Lead with the decision and the answer**, then the evidence.
- **State the assumptions** and which coefficients are illustrative or calibrated (and against what).
- **Show uncertainty**: confidence intervals over replications for stochastic metrics; sensitivity sweeps for uncertain coefficients. If the ranking of options flips within the plausible range of a coefficient, say so: that coefficient needs measuring first.
- **Show the mechanism**: which resource bounds each option, so the result is explicable, not oracular.
- **Compare against a bound and a known point** (an analytic bound, a published result, a measurement).
- **Regenerability**: one script turns the configuration and seeds into every table, so the numbers in the slides are the numbers in the repository.

**Common mistake:** reporting a single number to three significant figures from one seed with uncalibrated coefficients.

**Go deeper on this GitHub:** [SimEng 09, "Template 3: a Performance Report"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-11) · [InfSim 06, "Statistics That Survive Review"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-06)

### Q11. Your simulator predicted the new chip would be 2× faster than the old one. Silicon measures 1.3×. How do you investigate?

**Answer:**

Work from the outside in, and treat it as a calibration exercise, not a blame exercise.

1. **Same workload?** Check that silicon ran exactly the modelled workload: model shapes, batch sizes, precision, input lengths, software version. Mismatched workloads explain a surprising share of "model errors".
2. **Decompose the gap.** Measure the old and new chips per phase or per kernel and compare with the simulator's per-phase prediction. A 2× vs 1.3× aggregate gap usually comes from one or two components.
3. **Check the bound.** Did the simulator say "compute-bound" where silicon is memory-bound (or bound by something unmodelled: launch overhead, host interaction, synchronisation, the interconnect)? A model that makes compute twice as fast but leaves memory unchanged predicts 2× only if the workload was compute-bound.
4. **Check the efficiencies.** Achievable bandwidth and compute utilisation are usually below peak and differ between chips. Derating both chips by the same factor hides this.
5. **Check unmodelled effects.** Power or thermal throttling, clock frequency under load, DRAM refresh and bank conflicts, software overheads.
6. **Fix and record.** Update the model, re-run the old predictions, and record the error per quantity in a validation table so future predictions carry an honest error bar.

**Go deeper on this GitHub:** [InfSim 06, "The Verification Ladder"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-08) · [Glossary: calibration and correlation](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-correlation) · [SimEng 04, "Why "Bandwidth × Efficiency" Fails"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-01)
