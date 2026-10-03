# Making Simulators Fast, and Keeping Ports Honest — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Event abstraction, exact fast paths, sampling, Rust/PyO3 and C++ ports, bit-exact differential testing, floating-point operation order, Amdahl's law for ports
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. A simulator is too slow. In what order do you consider speed-ups?

**Answer:**

From biggest typical payoff and lowest risk to the most expensive:

1. **Profile first**: find where the time goes. Intuition about simulator hot spots is often wrong (metrics code, logging and probes are frequent culprits).
2. **Fewer events**: choose a coarser abstraction where the question allows (one event per batch step, not per token or per layer).
3. **Cheaper events**: incremental state instead of recomputation, hoisting invariants out of the loop, removing per-event logging and probes.
4. **Exact macro-stepping**: advance many identical steps in one event when nothing can change in between.
5. **Smarter experiments**: fewer runs (bisection instead of grids, analytic brackets), parallel independent runs.
6. **Faster execution of the same code**: a faster interpreter, a compiled core (Rust, C++).
7. **Approximation**: sampling, surrogates, lower-fidelity models, only with measured accuracy.

**Go deeper on this GitHub:** [InfSim 08, "Why Simulator Speed Matters, and a Taxonomy"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-01) · [InfSim 08, "Step Zero: Profile"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-02) · [Glossary: profiling a simulator](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-profiling)

### Q2. What is an "exact" fast path, and how do you prove it is exact?

**Answer:**

An exact fast path produces **identical results** to the slow path, just faster: no approximation. Examples:
- **Macro-stepping**: if a decode batch will run k more steps before any arrival, completion or other change, compute those k steps in one event, using the same arithmetic as k separate steps.
- **Incremental state**: keep a running sum of context lengths instead of summing over the batch each step.
- **Lazy bookkeeping**: record per-token timestamps only when needed, computing them from step boundaries.

Proof is empirical and strict: run both paths on many configurations (including edge cases: simultaneous events, empty batches, power caps) and compare **every output bit for bit** (timestamps with `==`, summaries for equality). Keep that comparison in CI.

On this GitHub, an exact fast path made a serving simulator 2.0–2.5× faster with a maximum timestamp difference of exactly 0.

**Go deeper on this GitHub:** [InfSim 08, "Exact Macro-Stepping"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-05) · [InfSim 08, "Cheaper Events: Incremental State and Hoisting"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-04) · [Glossary: macro-stepping (time skipping)](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-macro)

### Q3. Why does logging or probing slow a simulator so much, and what do you do about it?

**Answer:**

Each probe or log line runs on every event: string formatting, allocation and I/O in the inner loop. A periodic sampling probe also adds its own events to the event list.

Measured on this GitHub: a serving simulator took 0.55 s with its time-series probe effectively off, 0.61 s sampling every 50 ms of simulated time, and 1.02 s sampling every 5 ms.

What to do:
- make probes **optional** and off by default for sweeps;
- sample at the coarsest interval the analysis needs;
- record compact numeric arrays, and format or write them at the end;
- log at a level that is checked before formatting.

**Go deeper on this GitHub:** [InfSim 08, "The Cost of Watching: Probes and Traces"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-07) · [the recorded acceleration results (section 9)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Intermediate

### Q4. Should you port a Python simulator to Rust (or C++)? How do you decide?

**Answer:**

Port when:
- profiling shows the time is in the simulation core itself, not in I/O, analysis or a library;
- you have exhausted cheaper fixes (fewer events, fast paths);
- you need many more runs than you can afford (large sweeps, search, CI);
- the model is stable enough that maintaining two implementations is affordable.

Estimate the gain with **Amdahl's law**: if the core is 80% of the run time and the port makes it 70× faster, the whole run gets at most 1 / (0.2 + 0.8/70) ≈ 4.7× faster unless the rest is ported too. On this GitHub, the Rust core ran a 1,000-request simulation in 4.0 ms, but the whole PyO3 call took 13.2 ms, because summarising the results in Rust took 8.5 ms more: the "rest" became the bottleneck.

Keep the Python version as the **reference implementation** and the oracle for differential tests.

**Go deeper on this GitHub:** [SimEng 02, "Should You Port at All?"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-01) · [SimEng 02, "Interactive: What Should You Port?"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-11) · [Glossary: Amdahl's law for a port](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-amdahl)

### Q5. What does a bit-exact port require? List the traps.

**Answer:**

To compare a port with the original timestamp by timestamp, both must perform the **same floating-point operations in the same order**, consume the **same random numbers**, and break **ties** the same way.

Traps found on this GitHub:
1. **Different but "equivalent" functions**: Python's `x ** (1/3)` and a native `cbrt(x)` differ in the last bit; port it as `powf(1/3)`.
2. **Summation**: Python 3.12's built-in `sum()` of floats uses compensated summation, so a naive loop in another language differs. Use `math.fsum` (correctly rounded) on the Python side and implement the same algorithm in the port, or sum in an identical explicit order.
3. **Random numbers**: reproduce Python's Mersenne Twister and its exact transformation to floats and to distributions (e.g. `expovariate`) in the port.
4. **Serialisation**: JSON parsers may round floats on input unless told to round-trip exactly (e.g. `serde_json`'s `float_roundtrip` feature).
5. **Compiler optimisations**: fused multiply-add, re-association under fast-math, and vectorised reductions change results; disable them for the parity build.
6. **Ordering**: simultaneous events must be ordered identically (the reference's rule must be documented and reproduced).

**Go deeper on this GitHub:** [SimEng 02, "Bit-Exact: The Parity Checklist"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-06) · [SimEng 02, "Three Traps That Cost One ulp"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-08) · [SimEng 02, "Reproducing Python's Random Numbers"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-07) · [Glossary: bit-exact parity](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-bitexact)

### Q6. Why does a Rust extension help parallel Python sweeps when Python threads do not?

**Answer:**

CPython's **global interpreter lock (GIL)** allows only one thread to execute Python bytecode at a time. A pure-Python simulator in four threads runs no faster than in one (and can be slower, from contention). Processes avoid the GIL but pay start-up and data-copying costs.

A compiled extension can **release the GIL** while it runs pure native code that touches no Python objects. Then several Python threads can each run a simulation in parallel on different cores, with no inter-process copying.

Measured on this GitHub (8 runs of 4,000 requests): the Rust extension with 8 Python threads was 3.0× faster than sequential; a single call that ran the batch on a native thread pool was 3.3×. The SimPy version was **0.5×** with 4 threads (slower) and 3.7× with 4 processes.

**Go deeper on this GitHub:** [SimEng 02, "Releasing the GIL"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-05) · [Glossary: the GIL and releasing it](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-gil) · [the recorded table (section 3)](https://github.com/BrendanJamesLynskey/Rust_DES_Kernel/blob/main/examples/results.md)

---

## Advanced

### Q7. Design the testing strategy for a Rust port of a Python simulator.

**Answer:**

1. **Differential tests** (the core): for many configurations, run Python and Rust with the same seed and compare every timestamp with `==` and the summary for equality. Include edge cases: simultaneous events, power caps, empty phases.
2. **Property-based differential tests**: generate random configurations (Hypothesis on the Python side driving both), so the comparison covers inputs nobody thought of.
3. **Golden replays**: recorded Python outputs checked in, replayed by the Rust tests, so the Rust suite runs without Python too.
4. **Unit tests of the tricky primitives**: the RNG against CPython's sequence, `fsum` and floor division against CPython, ordering of equal keys.
5. **Native property tests** (e.g. proptest): invariants like conservation and ordering.
6. **Coverage and mutation testing** on the port, to find code the differential tests do not actually constrain.
7. **CI on several platforms**, since the point is reproducibility.

On this GitHub's Rust port: 47 tests, 97.5% line coverage, and a cargo-mutants score of 95% (813 of 857 viable mutants caught, excluding timeouts).

**Go deeper on this GitHub:** [SimEng 02, "Testing the Port: Golden and Differential"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-09) · [SimEng 01, "Testing in Rust: cargo test and proptest"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-12) · [Rust_DES_Kernel](https://github.com/BrendanJamesLynskey/Rust_DES_Kernel)

### Q8. Sorting a Python simulator's latencies once instead of once per percentile made its summary 2.25× faster. Cachegrind shows sorting is half the instructions of the Rust port. Should you expect a similar gain there?

**Answer:**

Not without reading the code. A profile tells you *where* the time goes, not *why*: half the instructions in sorting could mean redundant sorts (fixable) or one necessary O(n log n) sort (only a different algorithm helps).

This exact sequence happened on this GitHub. The Python summary sorted the same 763,474 latencies three times; sorting once gave 2.25× with identical outputs. The same gain was predicted for the Rust port, where sorting was about 51% of instructions, but the port already sorted each distribution once. The nearest change (an unstable sort, identical output for floats ordered by `total_cmp`) saved only 7% of the sorting instructions. The deck records the wrong prediction rather than hiding it.

A real gain needs a different algorithm: **selection** finds a few percentiles in O(n) without a full sort, or a **streaming sketch** gives bounded-error percentiles in O(1) memory per value.

**Lesson:** a prediction from a profile is a hypothesis; the measurement after the change is the evidence.

**Go deeper on this GitHub:** [SimEng 11, "Closing the Loop: Sort Once"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-09) · [SimEng 11, "Counting Instructions With Cachegrind"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-08) · [coding challenge 04](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_04_streaming_percentiles.py)

### Q9. When are approximate speed-ups (sampling, surrogates) acceptable, and how do you keep them honest?

**Answer:**

Acceptable when the question tolerates the error and the error is **measured**, not assumed:

- **Sampling** (detailed simulation of representative intervals): validate the sampled estimate against full simulation on a subset; report the sampling CI.
- **Surrogate models** (e.g. a regression or neural network fitted to simulator runs, used inside a search): use them to propose candidates, then confirm the best candidates with the real simulator.
- **Lower fidelity**: use for screening; confirm the shortlist at higher fidelity.

Keeping them honest:
- label every result with the fidelity that produced it;
- keep the exact path available and run it in CI on reference cases;
- track the approximation error over time, since model changes can invalidate a fitted surrogate silently.

**Go deeper on this GitHub:** [InfSim 08, "Smarter Experiments: Multi-Fidelity, Search, Surrogates"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-10) · [InfSim 08, "Sampling, Checkpoints and Mode Switching"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-11) · [InfSim 08, "Interactive: Amdahl's Law for Simulators"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-14)
