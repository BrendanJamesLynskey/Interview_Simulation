# Parallel DES and Queueing Sanity Checks — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Little's law and the operational laws, M/M/1 and M/D/1 checks, conservative and optimistic parallel discrete-event simulation
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. State Little's law and explain why it is useful for checking a simulator.

**Answer:**

For any system in steady state,

$$L = \lambda W$$

the average number of items in the system equals the arrival (throughput) rate times the average time each item spends in it. It needs **no assumptions about distributions, scheduling or service order**; it holds for any boundary you draw (a queue, a server, a whole cluster) as long as what goes in comes out.

As a simulator check: measure the time-average occupancy L of a component (e.g. average batch size in a decode engine, average requests in a queue), its throughput λ and the average residence time W independently. If L ≠ λW within statistical error, the bookkeeping is wrong: requests counted twice, lost, or timestamps taken at the wrong point.

**Common mistake:** applying it to a system that is not in steady state (a run still filling up, or overloaded and growing without bound).

**Go deeper on this GitHub:** [Glossary: Little's law and the operational laws](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-little) · [InfSim 02, "Step 2 — A Queue, Checked Against Theory"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-03)

### Q2. State the M/M/1 results you would use as a simulator test.

**Answer:**

For Poisson arrivals at rate λ, exponential service at rate μ, one server, FIFO, utilisation ρ = λ/μ < 1:

| Quantity | Formula |
|---|---|
| Mean number in system | L = ρ / (1 − ρ) |
| Mean time in system | W = 1 / (μ − λ) |
| Mean wait in queue | W_q = ρ / (μ − λ) |
| Probability the server is busy | ρ |

At ρ = 0.8 and μ = 1, W_q = 4 service times; at ρ = 0.9, 9; at ρ = 0.95, 19. The steep growth near saturation is the lesson: **latency explodes long before utilisation reaches 100%**.

For deterministic service (M/D/1), W_q is exactly half the M/M/1 value: ρ / (2μ(1 − ρ)). More generally (M/G/1, the Pollaczek–Khinchine formula):

$$W_q = \frac{\rho\,(1 + C_s^2)}{2(1-\rho)}\,\mathbb{E}[S]$$

where C_s is the coefficient of variation of the service time. Variability, not just utilisation, sets the queueing delay.

**Go deeper on this GitHub:** [Glossary: queueing theory checks (M/M/1, M/D/1)](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-queueing) · [coding challenge 02: M/M/1 against theory](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_02_mm1_queue.py)

### Q3. What are the operational laws, and how do they help in a design review?

**Answer:**

Simple identities between measurable quantities, valid without stochastic assumptions:

- **Utilisation law:** U = X · S (utilisation = throughput × service time per job at that resource).
- **Forced flow law:** X_k = V_k · X (throughput at resource k = visits per job × system throughput).
- **Little's law:** L = X · W.
- **Bottleneck bound:** the system throughput is at most 1 / max_k D_k, where D_k = V_k S_k is the total demand per job at resource k.

In a review, they let you sanity-check claims quickly: if a design claims 10,000 requests per second and each request needs 0.2 ms on a single shared unit, that unit would be at U = 10,000 × 0.0002 = 2.0, i.e. 200%: the claim is impossible without more units.

**Go deeper on this GitHub:** [Glossary: Little's law and the operational laws](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-little) · [Glossary: analytic lower bounds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-bounds)

---

## Intermediate

### Q4. Your simulated M/M/1 queue at ρ = 0.9 reports W_q = 6.1 instead of 9. List possible causes.

**Answer:**

1. **Initialisation bias.** The run starts empty and is too short: at ρ = 0.9 the queue takes hundreds of service times to reach steady state. Delete a warm-up period and/or run longer. (Coding challenge 02 shows short empty-start runs of 200 customers averaging about 6 against 9.)
2. **Too few replications** or a CI computed as if successive waits were independent: the estimate may just be noisy, with an over-confident interval.
3. **Wrong rate parameterisation.** Passing the mean where the API wants a rate (or the reverse): `expovariate(lambd)` takes a rate.
4. **Measuring the wrong quantity.** Time in system vs time in queue; waits measured only for customers that finished (biased towards short waits at the end of a run).
5. **Service order or capacity wrong**: two servers by mistake, or a policy that is not FIFO (fine for the mean in work-conserving single-server queues with identical jobs, but a bug elsewhere).
6. **Correlated or reused random streams** between arrivals and service.

**Go deeper on this GitHub:** [InfSim 06, "Statistics That Survive Review"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-06) · [Glossary: warm-up, replications and confidence intervals](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-warmup)

### Q5. Why can't you just parallelise one discrete-event simulation across threads?

**Answer:**

Because events must be processed in timestamp order, and an event on one part of the model can schedule an event on another part at any later time. If processor A runs ahead to t = 100 while processor B is at t = 50, B may send A an event for t = 60, which A has already "passed": a **causality violation**.

So parallel DES (PDES) partitions the model into logical processes (LPs) that exchange timestamped messages, and needs a synchronisation protocol:

- **Conservative** (Chandy–Misra–Bryant): an LP processes an event only when it is sure no earlier message can arrive. It relies on **lookahead** (a guaranteed minimum delay before an LP can affect another, e.g. a link latency) and **null messages** ("I will send nothing before t") to avoid deadlock.
- **Optimistic** (Time Warp): LPs process events speculatively; if a straggler message arrives in an LP's past, it **rolls back** (restoring saved state) and sends **anti-messages** to cancel messages it sent in error. **Global virtual time (GVT)**, the minimum time any rollback could reach, bounds how far back you might need to go and lets old saved state be reclaimed.

**Go deeper on this GitHub:** [InfSim 08, "Parallel Discrete-Event Simulation"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-12) · [Glossary: parallel discrete-event simulation (PDES)](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-pdes)

### Q6. When does PDES pay off, and what is usually the better first move?

**Answer:**

PDES pays off when one simulation is too big or too long for one core **and** the model has:
- natural partitions with little communication (e.g. nodes of a large network);
- good **lookahead** (large minimum delays between partitions) for conservative methods, or rare causality violations for optimistic ones;
- enough work per event to amortise synchronisation.

Most architecture and serving simulators have small lookahead (shared resources, tight coupling), so speed-ups are modest and the engineering cost is high.

The better first moves:
1. **Run independent replications and sweep points in parallel** ("embarrassingly parallel"): near-linear speed-up, no synchronisation, deterministic. Most studies need many runs anyway.
2. **Make each run cheaper**: fewer events, exact macro-steps, a compiled core.
3. Only then, PDES for the single runs that remain too slow.

On this GitHub, an eight-run sweep of a SimPy simulator gained 1.6× from eight processes on a 4-core/8-thread desktop (process start-up and the shortest runs limit it); a Rust port's thread-parallel sweep gained 3.0–3.3×.

**Go deeper on this GitHub:** [InfSim 08, "Parallel Runs"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-09) · [Glossary: parallel runs and Amdahl's law](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-parallelruns) · [SimEng 01, "Fearless Parallel Sweeps"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-10)

---

## Advanced

### Q7. Explain lookahead in conservative PDES with an example, and why it limits performance.

**Answer:**

Lookahead is a guarantee from an LP: "any message I send will have a timestamp at least L later than my current clock." In a network simulator, if every link has at least 1 µs latency, a router LP at time t cannot affect its neighbour before t + 1 µs. Its neighbour can then safely process all events before t + 1 µs.

With large lookahead, LPs advance in big independent chunks. With small lookahead (or zero, e.g. a shared bus where a request can be answered immediately), LPs must synchronise constantly: almost every step waits for null messages, and the overhead can exceed the useful work.

Ways to improve it: restructure the model so delays are explicit at partition boundaries; partition along high-latency interfaces (chip-to-chip links rather than inside a core); or switch to optimistic synchronisation if violations are rare.

**Go deeper on this GitHub:** [InfSim 08, "Parallel Discrete-Event Simulation"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-12) · [SimEng 03, "Loosely Timed: Temporal Decoupling and the Quantum"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-07)

### Q8. How is a loosely timed SystemC model's "quantum" related to PDES?

**Answer:**

Temporal decoupling in SystemC TLM-2.0 lets an initiator (e.g. a processor model) run ahead of the global simulation time by up to a **global quantum**, accumulating a local time offset, before synchronising with the kernel. This removes most context switches and is why loosely timed models are fast.

It is the same bargain as PDES without the safeguards: processes run ahead in local time, and interactions that should have happened "in the past" of another process are seen late or in a different order. There is no rollback, so the result is a **bounded timing inaccuracy**, not a correct result. Larger quantum: faster, less accurate.

Measured on this GitHub (4 bootstraps on an FHE accelerator model): with a quantum up to 1 µs the loosely timed model's end time matched the approximately timed model and SimPy to 1e-13; at 10 µs to 1 ms the end time was 0.8% to 3.6% late. Every loosely timed run took about 42–45 ms against 329.5 ms for the approximately timed model, roughly 7× faster.

**Go deeper on this GitHub:** [SimEng 03, "Interactive: The Quantum Trade-Off"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-10) · [Glossary: global quantum](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-quantum) · [the recorded quantum sweep (section 3)](https://github.com/BrendanJamesLynskey/SystemC_Accelerator_Model/blob/main/examples/results.md)

### Q9. You suspect a serving simulator's latency accounting is wrong. Design a set of queueing-theory checks to run on it.

**Answer:**

1. **Reduce to a textbook case**: one instance, batch size limited to 1, fixed or exponential step times, Poisson arrivals. Now it is an M/D/1 or M/M/1 queue: compare the mean wait with the formula at ρ = 0.3, 0.6, 0.9, with replications and CIs.
2. **Little's law at every boundary**: queue, engine, whole system. Time-average occupancy versus throughput × mean residence.
3. **Utilisation law**: busy fraction of each resource versus throughput × service time.
4. **Capacity bound**: throughput never exceeds 1 / max demand; latency grows without bound as offered load approaches it.
5. **Low-load limit**: at very low load, latency equals the sum of service times (no queueing).
6. **Conservation**: arrivals = completions + in-flight + rejected, at every instant.

Each check is cheap, needs no reference hardware, and catches a different class of bug: arithmetic, time-stamping, double counting, wrong resource capacity.

**Go deeper on this GitHub:** [InfSim 06, "The Verification Ladder"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-08) · [SimEng 06, "A Test Strategy for a Simulator"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-01)
