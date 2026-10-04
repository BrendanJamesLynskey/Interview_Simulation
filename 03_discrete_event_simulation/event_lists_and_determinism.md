# Event Lists, Ordering and Determinism — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Event lists and heaps, simultaneous events and tie-breaking, determinism and seeds, time-stepped vs event-driven simulation
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What is discrete-event simulation (DES), and what is the core loop?

**Answer:**

DES models a system whose state changes only at discrete instants (**events**): a request arrives, a job starts, a transfer completes. Between events nothing changes, so the simulator jumps straight from one event to the next instead of stepping time uniformly.

The core loop:

```python
# pseudocode: the DES kernel loop
while event_list and now <= end_time:
    time, event = pop_earliest(event_list)
    now = time
    event.handle()        # updates state, may schedule new events
```

Everything else (processes, resources, statistics) is built on top. The kernel's two jobs are to keep the event list ordered and to make the order of **simultaneous** events well defined.

**Go deeper on this GitHub:** [InfSim 02, "Anatomy of a Discrete-Event Simulator"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-01) · [InfSim 02, "Step 1 — A Kernel in 30 Lines"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-02) · [Glossary: discrete-event simulation](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-des)

### Q2. Which data structure holds the event list, and why?

**Answer:**

A **binary heap** (priority queue) keyed on event time is the default: O(log n) insert and O(log n) remove-minimum, simple, cache-friendly as an array. Python's `heapq`, C++'s `std::priority_queue` and Rust's `BinaryHeap` (a max-heap, so wrap keys in `Reverse`) all serve.

Alternatives:
- **Calendar queues** (bucketed by time, like a time wheel): O(1) amortised when event times are well spread; used in some logic simulators and network simulators.
- **Sorted lists**: fine for tiny lists, O(n) insertion otherwise.
- **Ladder queues / splay trees**: specialised high-performance variants.

**Cancellation** (timeouts that rarely fire) is usually done lazily: mark the event dead, skip it when it surfaces, instead of searching the heap.

**Go deeper on this GitHub:** [SimEng 01, "The Event List: BinaryHeap and Reverse"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-02) · [Glossary: BinaryHeap and Reverse](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-binaryheap) · [coding challenge 01](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_01_des_kernel.py)

### Q3. Why must a simulator define the order of simultaneous events?

**Answer:**

Because simultaneous events are common (fixed service times, clock-aligned hardware, batch completions) and their order often changes the result: which of two requests arriving at the same instant gets the free server, whether a completion frees a resource before or after a new request asks for it.

If the order is left to chance, results depend on:
- the heap's internal layout (which depends on insertion history);
- Python's comparison of payloads (`heapq` falls back to comparing the second tuple element on equal times, which raises `TypeError` for callables or, worse, silently orders by an arbitrary field);
- hash or dictionary iteration order, thread scheduling, or the simulator implementation.

The fix is a **total order**: key events on (time, priority, sequence number), where the sequence number is a global insertion counter. Then equal-time, equal-priority events fire first-in, first-out, and every run is reproducible.

**Go deeper on this GitHub:** [SimEng 01, "Ordering Floats, Breaking Ties"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-03) · [Glossary: deterministic tie-breaking](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-tiebreak)

---

## Intermediate

### Q4. What does "deterministic" mean for a stochastic simulator, and how do you achieve it?

**Answer:**

It means **the same configuration and seed always produce bit-identical output**, on any run, on any machine you support. Randomness is in the *model*, not in the *execution*.

Ingredients:
1. **Explicit seeds**, recorded with every result.
2. **Separate random streams per purpose** (arrivals, sizes, service times, per replication), each derived from the seed. Then adding a random draw in one part of the model does not shift every draw elsewhere.
3. **Total ordering of events** (time, priority, sequence).
4. **No dependence on unordered iteration** (sets, dictionaries keyed by object identity, file-system listing order).
5. **Deterministic parallelism**: parallelise across independent runs, each with its own seed, and combine results in a fixed order.
6. **Floating-point care**: the same operations in the same order (compilers, fused multiply-add, and different summation orders can change the last bit).

Why it matters: you can bisect a behaviour change to a commit, keep golden outputs in CI, compare designs with common random numbers, and port the simulator to another language with bit-exact differential tests.

**Go deeper on this GitHub:** [InfSim 02, "Time, Ordering and Determinism Pitfalls"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-10) · [Glossary: determinism, tie-breaking and RNG streams](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-determinism)

### Q5. What problems does floating-point simulated time cause, and what are the alternatives?

**Answer:**

Problems:
- **Accumulation error:** `0.1 + 0.2 != 0.3`, so events that "should" coincide may land a few ulps apart, changing their order relative to other events.
- **Loss of resolution late in a run:** at t = 1e6 s, a double's spacing is about 1e-10 s, which may be coarser than a fine-grained delay you add.
- **Cross-language parity:** two implementations that compute the same time with a different operation order disagree in the last bit, so the event order diverges.

Alternatives:
- **Integer time** in a fixed resolution (picoseconds or femtoseconds in a 64-bit integer). SystemC does this: time is an integer multiple of a global resolution. 2^64 femtoseconds is about 5 hours, 2^64 picoseconds about 213 days.
- **Rational time** for exactness (slow; rarely needed).
- If you keep floats: **never compare times for equality** to decide simultaneity; compute times in one place, in one consistent order; and total-order ties with sequence numbers.

**Go deeper on this GitHub:** [SimEng 01, "Ordering Floats, Breaking Ties"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-03) · [Glossary: total ordering of floats (total_cmp)](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-totalcmp)

### Q6. Compare time-stepped and event-driven simulation. When is each the right choice?

**Answer:**

| | Time-stepped | Event-driven |
|---|---|---|
| Advances time by | A fixed (or adaptive) step Δt | Jumping to the next event |
| Work per simulated second | Proportional to 1/Δt, whether or not anything happens | Proportional to the number of events |
| Natural for | Continuous dynamics (ODEs, fields, physics), dense synchronous activity | Sparse, asynchronous activity: queues, requests, transactions |
| Timing accuracy | Quantised to Δt (events between steps are delayed) | Exact event times |

A synchronous clocked design where everything changes every cycle is effectively time-stepped (and cycle-based RTL simulation is fast for that reason). A serving system where requests arrive every few milliseconds and each step lasts microseconds to milliseconds is event-driven.

Hybrids are common: event-driven at the system level, with an analytical or time-stepped model inside an event; or continuous dynamics integrated between discrete events (as in switching power-converter simulators).

**Go deeper on this GitHub:** [Introduction to Simulation, "Time-Stepping and Event-Driven"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/22) · [InfSim 02, "Interactive: Step Through the Event List"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-04)

---

## Advanced

### Q7. Your simulator gives different p99 latencies on two machines with the same seed. How do you track it down?

**Answer:**

1. **Confirm it is real**: same code version, same configuration file, same dependency versions (a library update can change a random-number algorithm or a summation).
2. **Dump the event trace** on both machines (time, event type, entity) and diff. Find the **first** divergence; everything after it is consequence.
3. Classify the first divergence:
   - **different random number** → a stream seeded from something machine-dependent (time, PID, hash randomisation), or a different RNG implementation;
   - **same events, different order at the same timestamp** → a tie broken by something non-deterministic (object identity, set or dict iteration order, thread timing);
   - **timestamps differ in the last bits** → floating-point differences: different CPU features (FMA), compiler flags, math library, or summation order (vectorised or parallel reductions).
4. Fix the cause and add a test: a golden trace or summary checked in CI on more than one platform.

**Go deeper on this GitHub:** [InfSim 02, "Time, Ordering and Determinism Pitfalls"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-10) · [SimEng 02, "Three Traps That Cost One ulp"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-08)

### Q8. Implement an event list with O(1) cancellation. What are the trade-offs?

**Answer:**

Keep callbacks in a dictionary keyed by event id, and heap entries `(time, priority, seq, id)`. Cancelling deletes the dictionary entry; the stale heap entry is discarded when it reaches the top ("lazy deletion").

Trade-offs:
- **Memory**: dead entries stay in the heap until popped. With many long timeouts that are usually cancelled (retransmission timers, watchdogs), the heap can fill with garbage. Rebuild it when the dead fraction exceeds a threshold.
- **Peek cost**: `peek()` must skip dead entries, so a single call can be O(k log n), though amortised it is still O(log n) per scheduled event.
- **Alternatives**: an indexed heap that tracks each entry's position supports true O(log n) removal at the cost of extra bookkeeping on every swap.

A complete tested implementation is in coding challenge 01.

**Go deeper on this GitHub:** [coding challenge 01: a DES kernel with deterministic ties](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_01_des_kernel.py) · [SimEng 01, "Events as Enums, Models as Traits"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-05)

### Q9. Two simulators of the same system (SimPy and SystemC) agree on totals but some individual operations finish at different times. Why might that be acceptable, and when is it not?

**Answer:**

Simultaneous requests for a resource can be served in either order without changing the **total** work, the busy time or the end of the run: the same multiset of service intervals is just permuted. So horizon, utilisation and bytes moved agree, while individual operations finish earlier or later.

That is acceptable if the questions are aggregate (throughput, energy, utilisation). It is **not** acceptable if:
- per-operation latency or its tail matters (one operation always loses the tie and suffers);
- the order feeds back into later decisions (cache replacement, which data is evicted);
- you want bit-exact differential testing between the two implementations.

The fix is to make tie-breaking **part of the model** (for example, oldest operation first) and implement it explicitly in both, instead of inheriting each kernel's implementation-defined process order. On this GitHub, doing that in the SystemC model removed every per-operation difference on the main configurations (0 of 203 differing, against 6 of 203 with the kernel's own order).

**Go deeper on this GitHub:** [SimEng 03, "Ties Are Part of the Model"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-08) · [Glossary: process order and explicit tie-breaks](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-procorder)
