# Modelling Styles and SystemC TLM-2.0 — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Analytical, trace-driven and execution-driven models; SystemC TLM-2.0 loosely timed and approximately timed styles; temporal decoupling and the quantum; sampling
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Compare analytical, trace-driven and execution-driven performance models.

**Answer:**

| | Analytical | Trace-driven | Execution-driven |
|---|---|---|---|
| Input | Workload characteristics (counts, sizes, rates) | A recorded sequence of operations or memory accesses | The program itself, executed inside or alongside the model |
| What drives the timing model | Formulas | The trace, replayed | Functional execution, step by step |
| Feedback from timing to workload | None | **None**: the trace is fixed | **Yes**: timing can change what executes (spin loops, scheduling, adaptive algorithms) |
| Speed | Instant | Fast | Slowest |
| Typical failure | Ignores contention and dynamics | Trace not representative; misses timing-dependent behaviour | Slow; harder to build |

Trace-driven models are the workhorse of accelerator and memory-system studies: record a kernel-level or memory-access trace once, replay it against many hardware variants. They fail when the workload's behaviour depends on timing (a scheduler that batches differently under load, a lock that spins longer on a slower machine).

**Go deeper on this GitHub:** [Introduction to Simulation, "Architecture: Transaction-Level and Cycle-Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/16) · [Glossary: kernel-level trace](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-trace) · [FHESim 03, "The Trace: Contract Between Scheme and Hardware"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-03)

### Q2. What is transaction-level modelling, and what does TLM-2.0 standardise?

**Answer:**

**Transaction-level modelling** represents communication between components as transactions (a read of 64 bytes from an address, a DMA transfer) passed by function call, rather than as signal-level handshakes cycle by cycle. A transaction costs one function call instead of tens of signal events, which is why TLM models run orders of magnitude faster than RTL.

**SystemC TLM-2.0** (part of IEEE 1666) standardises how models interoperate:
- the **generic payload** (command, address, data pointer, length, byte enables, response status, extensions);
- **initiator and target sockets** connecting components;
- the **blocking transport** interface `b_transport(payload, delay)` for loosely timed models;
- the **non-blocking transport** interface `nb_transport_fw/bw(payload, phase, delay)` with the **base protocol's four phases** (BEGIN_REQ, END_REQ, BEGIN_RESP, END_RESP) for approximately timed models;
- the **direct memory interface (DMI)** for fast pointer access to memory, and a debug transport interface.

Standard interfaces let IP models from different vendors plug into one virtual platform.

**Go deeper on this GitHub:** [SimEng 03, "TLM-2.0: Payloads, Sockets and Coding Styles"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-05) · [Glossary: TLM-2.0 generic payload and sockets](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-payload) · [Glossary: transaction-level modelling](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-tlm)

### Q3. Contrast the loosely timed (LT) and approximately timed (AT) coding styles.

**Answer:**

- **Loosely timed (LT):** one blocking call per transaction (`b_transport`); the target adds its latency to a delay argument. Initiators may run ahead of simulation time (temporal decoupling) and synchronise rarely. Fast enough to boot an OS. Timing is approximate; contention is modelled crudely or not at all.
- **Approximately timed (AT):** non-blocking calls with the four-phase protocol, so a transaction's request and response are separate timed events. Pipelining, outstanding transactions, arbitration and back-pressure can be modelled. Slower, but suitable for architecture exploration and performance analysis.

Rule of thumb: LT for software development and functional virtual platforms; AT when contention and timing are the questions.

**Go deeper on this GitHub:** [SimEng 03, "Approximately Timed: the Four-Phase Protocol"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-06) · [SimEng 03, "Loosely Timed: Temporal Decoupling and the Quantum"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-07) · [Glossary: approximately timed (AT) and the base protocol](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-atstyle) · [Glossary: loosely timed (LT) and temporal decoupling](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-ltstyle)

---

## Intermediate

### Q4. What is temporal decoupling, and how should you choose the global quantum?

**Answer:**

With temporal decoupling, an LT initiator keeps a **local time offset** and executes ahead of the SystemC kernel's time, calling `wait()` (a context switch) only when the offset exceeds the **global quantum**, or when it must interact. Fewer context switches means much faster simulation.

Choosing the quantum:
- **Larger quantum**: faster, but interactions between initiators (shared resources, interrupts, synchronisation through memory) are seen up to one quantum late or out of order.
- **Smaller quantum**: more accurate interactions, slower.
- Choose it **relative to the timescale of the interactions that matter**: if the question involves contention between two engines over a shared channel at microsecond granularity, a millisecond quantum is meaningless.

Measure, don't guess. On this GitHub's FHE accelerator model: with a quantum up to 1 µs, the LT end time matched the AT model to 1e-13 relative; at 10 µs it was 0.8% late and at 1 ms 3.6% late; every LT run was about 7× faster than AT.

**Go deeper on this GitHub:** [SimEng 03, "Interactive: The Quantum Trade-Off"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-10) · [Glossary: global quantum](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-quantum)

### Q5. Why might a trace-driven simulation of a GPU or accelerator give misleading results under a different hardware configuration?

**Answer:**

Because the trace was produced under one set of conditions and replays them regardless:

- **Scheduling decisions are baked in**: a runtime that launches kernels in a different order, batches differently, or fuses differently on other hardware is not captured.
- **Timing-dependent behaviour is lost**: busy-waiting, dynamic load balancing, work stealing.
- **Data-dependent control flow** follows the recorded path only.
- **Inter-arrival times** recorded from a slow machine embed that machine's speed; replay them as dependencies, not timestamps.

Mitigations: record traces at a level above these decisions (an operator graph with dependencies, not timestamps); regenerate traces for each configuration when the runtime adapts; or use execution-driven simulation for the parts that adapt.

**Go deeper on this GitHub:** [InfSim 04, "Workloads and Traces"](https://brendanjameslynskey.github.io/InfSim_04_Simulator_Landscape/#slide-07) · [FHESim 03, "Where Traces Come From"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-04)

### Q6. How do sampling methods (e.g. SimPoint- or SMARTS-style) make detailed simulation of long programs feasible?

**Answer:**

Detailed (cycle-level) simulation of a full benchmark can take weeks. Sampling simulates only part of it in detail and estimates the whole:

- **Representative sampling (SimPoint-style):** profile the program's phase behaviour (basic-block vectors per interval), cluster the intervals, simulate one representative interval per cluster in detail, and weight the results by cluster size.
- **Statistical sampling (SMARTS-style):** simulate many short, systematically spaced intervals in detail; fast-forward between them with functional simulation that keeps caches and predictors warm. Sampling theory gives a confidence interval on the estimate.

Key issues: **warming** state (caches, branch predictors, TLBs) before each detailed interval; **checkpointing** so intervals can be simulated in parallel; and checking that the sampled estimate agrees with full simulation on a few cases.

**Go deeper on this GitHub:** [InfSim 08, "Sampling, Checkpoints and Mode Switching"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-11) · [Glossary: sampling, checkpoints and mode switching](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-sampling)

---

## Advanced

### Q7. You must build a model of an accelerator tile (compute units, a scratchpad, a DMA engine, a NoC port) to be shared with the software team and the architects. Which style do you choose?

**Answer:**

Two consumers, two needs:

- **Software** needs speed and functional correctness: run the compiler's output and the runtime, boot the firmware. → **LT** with temporal decoupling and DMI for memory.
- **Architects** need contention, pipelining and arbitration: DMA and compute competing for the scratchpad, NoC back-pressure. → **AT** (or a cycle-approximate model) for the shared resources.

A practical answer is **one model with switchable timing**: the functional behaviour (what each transaction does) is shared; the timing layer is LT or AT, selected at elaboration. Keep the cost model (per-operation latencies, bandwidths) in one place so both styles use the same numbers, and check them against each other: on a single initiator with no contention, LT and AT must give the same times.

Also: make **arbitration and tie-breaking explicit** (e.g. oldest request first). Otherwise the result depends on the kernel's implementation-defined process order, which IEEE 1666 does not specify.

**Go deeper on this GitHub:** [SimEng 03, "The Modelled Tile"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-04) · [SimEng 03, "Why a C++ Model in SystemC?"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-01) · [SystemC_Accelerator_Model](https://github.com/BrendanJamesLynskey/SystemC_Accelerator_Model)

### Q8. Your AT SystemC model and a Python DES of the same hardware give the same end time but different per-operation end times. Is one of them wrong?

**Answer:**

Not necessarily. Equal end times, equal busy times and equal bytes, with permuted per-operation times, usually mean **simultaneous requests are granted in different orders**. Both are valid executions of an under-specified model.

To decide whether it matters, ask whether per-operation timing feeds a decision (tail latency per operation, cache eviction order). If it does, make the order **part of the specification** (for example, grant the oldest operation's request among those arriving at the same instant) and implement it explicitly in both models. In SystemC that means waiting until the instant has settled (e.g. a delta cycle or a zero-time notification) before arbitrating, rather than granting whichever process the kernel happens to run first.

On this GitHub that change made the SystemC model agree with the SimPy model operation by operation on the main configurations; with the kernel's own order, 6 to 24 operations per run differed while the end time still agreed.

**Go deeper on this GitHub:** [SimEng 03, "Ties Are Part of the Model"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-08) · [the recorded comparison (section 2)](https://github.com/BrendanJamesLynskey/SystemC_Accelerator_Model/blob/main/examples/results.md)

### Q9. When would you write a performance model in C++/SystemC rather than Python, and what do you lose?

**Answer:**

**Choose C++/SystemC when:**
- the model must plug into a virtual platform or vendor IP models (TLM-2.0 interoperability);
- it must run fast at fine granularity (millions of transactions);
- it will be maintained by a hardware team that works in SystemC already;
- it must be delivered to customers as a compiled model.

**Choose Python when:**
- the questions are system-level (requests, batches, kernels) and the event count is modest;
- iteration speed matters more than run speed: exploring ideas, frequent model changes;
- integration with the ML stack (PyTorch, ONNX) and data analysis is central.

**What you lose with C++:** development speed, easy plotting and notebooks, and simple integration with ML front ends; you gain speed, type safety and tool support (sanitizers, GoogleTest). A common compromise is a Python front end over a compiled core (via PyO3 or pybind11), with differential tests between the two.

**Go deeper on this GitHub:** [SimEng 03, "Modern C++ for Models"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-02) · [InfSim 02, "Beyond Python: C++, Rust, SystemC"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-12) · [SimEng 02, "Should You Port at All?"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-01)
