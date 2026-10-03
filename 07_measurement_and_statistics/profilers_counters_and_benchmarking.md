# Profilers, Hardware Counters and Benchmarking — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Instrumenting vs sampling profilers and their overheads, flame graphs, hardware counters and multiplexing, Cachegrind, benchmarking noise and regression gates
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Compare instrumenting and sampling profilers.

**Answer:**

- **Instrumenting (deterministic) profilers** record every function entry and exit (Python's `cProfile`, compiler instrumentation). They give exact call counts and complete call graphs, but add overhead to **every call**, which inflates small, frequently called functions and distorts the profile itself.
- **Sampling profilers** interrupt the program periodically (say 100 times per second) and record the current stack (py-spy, `perf record`). Overhead is low and roughly proportional to the sampling rate, independent of call frequency; results are statistical, so short or rare functions may be missed.

Measured on this GitHub, the same simulator run (3,000 requests, 1.23 s without a tool):
- cProfile: **2.04×** slower;
- py-spy at 100 Hz: **1.05×**; at 500 Hz: **1.45×** (py-spy pauses the target for each sample by default, which explains most of that);
- line coverage: 2.59×; with branch coverage 2.85×;
- tracemalloc with 1 frame: 4.72×; with 25 frames: 25.63×.

Use sampling first to find where time goes; use instrumentation when you need exact counts for a specific region.

**Go deeper on this GitHub:** [SimEng 12, "Time: Instrumenting Against Sampling Profilers"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-03) · [cProfile card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-cprofile) · [py-spy card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-pyspy) · [the recorded overheads (T12)](https://github.com/BrendanJamesLynskey/SimEng_Hub_Toolkit/blob/main/snippets/RESULTS.md)

### Q2. How do you read a flame graph? What is the difference between self time and total time?

**Answer:**

A flame graph stacks sampled call stacks: the x-axis is the **proportion of samples** (not time order), the y-axis is stack depth, with callers below callees. A wide box is a function that appears in many samples; a wide box at the **top** of a tower is where the CPU actually was.

- **Total (inclusive) time**: samples where the function is anywhere on the stack: itself plus everything it calls.
- **Self (exclusive) time**: samples where the function is at the top: its own code only.

Optimise functions with large **self** time (or a large total time whose callees are not themselves hot, meaning the overhead is in the calls). A function with huge total but tiny self time is just a caller of something hot.

Off-CPU flame graphs (time blocked on I/O, locks, sleeps) answer a different question: why is the program *not* running.

**Go deeper on this GitHub:** [SimEng 11, "Reading a Profile: Self and Total Time"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-07) · [SimEng 12, "Flame Graphs, On-CPU and Off-CPU"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-04) · [Glossary: flame graphs](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-flamegraph)

### Q3. What are hardware performance counters, and what is counter multiplexing?

**Answer:**

CPUs have a small number of programmable counters in the performance monitoring unit (PMU) that count events: cycles, instructions retired, cache references and misses, branch mispredictions, TLB misses. Tools like `perf stat` read them with negligible overhead.

When you ask for **more events than there are counters**, the kernel **multiplexes**: it time-slices the events across the counters and scales each count by (total time / time counted). The result is an estimate, accurate when the program's behaviour is steady and less so for short or bursty programs.

Measured on this GitHub (12 events on a CPU with fewer counters): each event was counted for only 18–45% of the run; instructions read +1.4% against counting them alone, cycles +0.3%. Lesson: request only the events you need, or run several passes, and check the "counted for" percentage that `perf stat` prints.

**Go deeper on this GitHub:** [SimEng 11, "Linux perf: Counters and Call Stacks"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-04) · [hardware counters card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-hwcounters) · [Glossary: hardware performance counters and multiplexing](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-hwcounters)

---

## Intermediate

### Q4. When would you use Cachegrind instead of a sampling profiler?

**Answer:**

Cachegrind (a Valgrind tool) runs the program on a simulated CPU and counts **instructions** (and optionally simulated cache and branch events) per line of source. It is **deterministic**: the same input gives the same counts, run after run, on any machine.

Use it when:
- you need to measure a small change reliably (instruction counts do not suffer timing noise, so a 1% change is visible);
- you want a stable metric for CI regression gates;
- you need per-line attribution in compiled code.

The costs: it is slow (measured on this GitHub, 93× slower for a Rust simulator and 67× for a Python one), and instructions are not time: cache misses, branch mispredictions and memory stalls change the time without changing the instruction count much. Confirm important wins with wall-clock measurements.

**Go deeper on this GitHub:** [SimEng 11, "Counting Instructions With Cachegrind"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-08) · [Cachegrind card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-cachegrind) · [Glossary: Cachegrind and instruction counts](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-cachegrind)

### Q5. Why are benchmark timings distributions, and how should you summarise them?

**Answer:**

Repeated runs of the same program vary: frequency scaling and boost, other processes, interrupts, cache and memory layout, the operating system's scheduling. The distribution is usually skewed with a long right tail (occasional slow runs), not Gaussian.

Summarise with:
- the **median** (robust to outliers) rather than the mean;
- a robust spread: the **median absolute deviation (MAD)** or interquartile range;
- a **confidence interval for the median** (e.g. by bootstrap resampling);
- the **minimum** for "best achievable", with care (it can be optimistic).

On this GitHub, 40 whole-process runs of a Rust simulator: median 51.9 ms, mean 52.7 ms, min 48.1, max 67.4, coefficient of variation 7.0%, bootstrap 95% CI of the median 50.6–53.0 ms. Report the run count and the machine with every number.

**Go deeper on this GitHub:** [SimEng 11, "Benchmarks Are Distributions"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-10) · [Glossary: benchmark distributions](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-benchdist)

### Q6. How do you profile a simulator effectively? Walk through the loop.

**Answer:**

1. **Fix the workload**: a representative configuration and seed, long enough to be dominated by steady-state work, short enough to iterate quickly.
2. **Measure end to end first** (wall time, peak memory with `/usr/bin/time -v`), several runs.
3. **Sample profile** (py-spy or perf) to find the hot functions by self time.
4. **Form a hypothesis** about why they are hot (too many events, recomputation, sorting, allocation).
5. **Change one thing**, check **outputs are identical** (golden comparison), re-measure.
6. **Keep or revert**, and record the result.

On this GitHub, profiling a SimPy simulator showed its metrics summary sorting the same 763,474 latencies three times (once per percentile). Sorting once made the summary 2.25× faster with identical outputs; end to end 1.17×.

**Go deeper on this GitHub:** [SimEng 11, "Measure Before You Optimise"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-01) · [SimEng 11, "Closing the Loop: Sort Once"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-09) · [Glossary: the profile-first loop](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-profileloop)

---

## Advanced

### Q7. Design a performance-regression gate for a simulator's CI. How do you avoid false alarms?

**Answer:**

A gate compares a new build's benchmark against a baseline and fails if it is slower by more than a margin. On noisy timings, a naive gate (one run each, 2% margin) fires constantly.

Design choices:
- **Compare medians of k runs**, interleaving baseline and candidate runs to share machine conditions.
- **Choose the margin from measured noise**: run an **A/A test** (identical code on both sides) to measure the false-alarm rate, and a known injected slowdown to measure detection power.
- **Prefer deterministic metrics** where possible: instruction counts (Cachegrind) or event counts are far less noisy than wall time.
- **Pin the environment**: dedicated runner, fixed CPU frequency where possible, no other jobs.
- **Two-stage gate**: a cheap check flags, a longer rerun confirms.

Measured on this GitHub by resampling 40 real runs: with 1 run each and a 2% margin, the false-alarm rate was 38.4%; with 10 runs each and a 5% margin, it fell to 4.8% while still detecting a real 10% slowdown 94.6% of the time.

**Go deeper on this GitHub:** [SimEng 11, "Interactive: Designing a Regression Gate"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-11) · [SimEng 11, "Regression Detection in CI"](https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-12) · [Glossary: A/A tests and regression-gate design](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-gatedesign) · [Glossary: performance-regression gate](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-perfgate)

### Q8. A load generator reports p99 latency of 5 ms for a server, but users see much worse. What might be wrong?

**Answer:**

**Coordinated omission.** Many closed-loop load generators send the next request only after the previous one returns. When the server stalls for 1 s, the generator stops sending, so it records **one** slow request instead of the hundreds that real users (arriving independently, on a schedule) would have experienced during the stall. The measured tail looks far better than reality.

Fixes:
- use an **open-loop** generator that sends on a fixed schedule regardless of responses;
- or correct the measurement by recording latency from each request's **intended** send time;
- report throughput achieved alongside latency, so a generator that silently backed off is visible.

The same trap exists in simulators: a closed-loop workload model (fixed number of users, think time) and an open-loop one (Poisson arrivals) give very different tails near saturation. Choose the one that matches how load arrives in reality.

**Go deeper on this GitHub:** [SimEng 12, "Benchmarks and Load Generators"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-05) · [load generator card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-loadgen) · [Glossary: load generators and coordinated omission](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-loadgen)

### Q9. You need to measure GPU energy for a workload. What tools exist, and what are their pitfalls?

**Answer:**

- **nvidia-smi / NVML**: board power readings. The reading is averaged or sampled over intervals; one study cited on this GitHub found only 25 ms of every 100 ms sampled on A100/H100 for the default power field, so short kernels can be missed entirely.
- **DCGM**: data-centre telemetry with field IDs for power and energy counters, configurable sampling (with a minimum interval), suitable for fleets.
- **Energy counters** (where the driver exposes a cumulative energy value) are better than integrating sampled power.
- **Zeus** and similar libraries wrap these for ML jobs.
- **External power analysers** measure the wall or board rail directly and are the reference for calibration.

Pitfalls: averaging windows, idle versus active baselines, other processes on the device, temperature and clock changes, and measuring board power when the question is about the chip. Measure long steady runs, subtract idle where the question requires it, and state the method.

(On the machine used for this GitHub's measurements there is no NVIDIA GPU, so these tools are documented rather than run.)

**Go deeper on this GitHub:** [SimEng 12, "GPU Telemetry: nvidia-smi, NVML, DCGM and Zeus"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-07) · [NVML card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-nvml) · [DCGM card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-dcgm) · [Zeus card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-zeus)
