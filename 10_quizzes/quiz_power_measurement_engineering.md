# Quiz — Power, Measurement and Simulator Engineering

**Subject:** Simulation and Performance Modelling
**Topics covered:** Power and energy models, DVFS and power caps, area and yield, PPA metrics and Pareto fronts, profilers and counters, output statistics, ports and parity, testing and CI
**Format:** Multiple-choice and short-answer questions. Answers at the end.

---

### Q1. A simulator models power as P = P_static + (Σ n_op · E_op) / t. Why is reporting energy per operation often more useful than average power?

---

### Q2. For which kind of step can DVFS save energy without increasing step time?

a) Compute-bound
b) Memory-bound
c) Both equally
d) Neither

---

### Q3. Why can a power cap that looks harmless per step cause a sudden collapse in SLO attainment?

---

### Q4. Using the Poisson yield model with D₀ = 0.1 defects per cm², what is the yield of a 100 mm² die (to two significant figures)?

a) 99%
b) 90%
c) 63%
d) 37%

---

### Q5. Compared with the Poisson model at the same mean defect density, Murphy's yield model (which allows defects to cluster) gives:

a) Lower yield
b) Equal yield
c) Higher yield, increasingly so for large dies
d) Higher yield only for small dies

---

### Q6. Design A has (latency 10 ms, energy 1.0 J, area 400 mm²); design B has (10 ms, 1.0 J, 450 mm²). Is B on the Pareto front if only these two designs exist?

---

### Q7. Which metric is roughly invariant to voltage scaling in the simple model (E ∝ V², delay ∝ 1/V)?

a) Energy
b) EDP
c) ED²P
d) Power

---

### Q8. Which profiler adds overhead on every function call?

a) A sampling profiler at 100 Hz
b) An instrumenting profiler such as cProfile
c) Linux `perf stat`
d) A flame graph renderer

---

### Q9. `perf stat` prints "counted for 30%" next to an event. What does that mean?

---

### Q10. Why should a CI performance gate compare medians of several runs, and how do you choose its margin?

---

### Q11. Why is a confidence interval computed from the individual latencies of one run misleading?

---

### Q12. The mean of two servers' p99 latencies is 505 ms. Is the p99 of all requests 505 ms?

---

### Q13. A Python simulator uses `x ** (1/3)`; its Rust port uses `cbrt(x)`. Differential tests compare timestamps with `==`. What happens, and what is the fix?

---

### Q14. Python 3.12's built-in `sum()` of floats differs from a naive loop in another language because:

a) It sums in reverse order
b) It uses compensated summation
c) It converts to decimal
d) It uses 80-bit extended precision on all platforms

---

### Q15. A test suite has 100% line coverage. What does mutation testing tell you that coverage does not?

---

### Q16. Name the three kinds of CI gate commonly used for a simulator.

---

### Q17. A declarative Jenkins pipeline defines `parameters { string(name: 'TOOLS', defaultValue: "${env.HOME}/tools") }`. What value does `TOOLS` get, and why?

---

## Answers

**A1.** Because time and power trade against each other: a design or setting that draws more power but finishes sooner can use less energy. Energy per operation (equivalently perf/W for a fixed amount of work) is what batteries, power-limited racks and electricity bills see.

**A2.** (b). A memory-bound step waits on memory anyway, so the compute clock can drop until compute just keeps up, costing no time and saving dynamic energy. (On this GitHub's serving simulator, 17.1% of a decode step's dynamic energy.)

**A3.** The cap stretches service times; latency under load grows like 1/(1 − ρ), so once the stretched service rate approaches the arrival rate, queues grow without bound. On this GitHub's model, a decode cap of 250 W kept 99.7% of requests within SLO and 200 W only 12.6%.

**A4.** (b). A·D₀ = 1 cm² × 0.1 = 0.1; e^(−0.1) ≈ 0.905, so about 90%.

**A5.** (c). Clustered defects concentrate on some dies, leaving more good dies; the gap grows with A·D₀.

**A6.** No. A is no worse in every objective and strictly better in area, so A dominates B.

**A7.** (c). E·D² ∝ V² · V⁻² = constant.

**A8.** (b).

**A9.** The PMU had fewer counters than requested events, so the kernel multiplexed them: the event was actually counted for 30% of the run, and perf scaled the count up by about 1/0.3. The value is an estimate whose accuracy depends on how steady the program is.

**A10.** Timings are noisy, skewed distributions; a single-run comparison fires on noise. Use medians of k interleaved runs, and choose the margin from an A/A test (identical code) so the false-alarm rate is acceptable while a known slowdown is still detected. (On this GitHub's measurements: 1 run and a 2% margin gave 38.4% false alarms; 10 runs and 5% gave 4.8%, still detecting a 10% slowdown 94.6% of the time.)

**A11.** Successive latencies are autocorrelated (queues persist), so the effective sample size is far smaller than the count; the naive interval is far too narrow. Use independent replications or batch means.

**A12.** No. Percentiles do not average. Merge the distributions (or mergeable sketches) and take the percentile of the union; it can be far lower or higher than the mean of p99s.

**A13.** The two functions can differ in the last bit, so timestamps diverge and later event orders can change. Port as `powf(1/3)` (the same operation as Python's `**`), keeping the same operation order everywhere.

**A14.** (b).

**A15.** Whether the tests would notice a change in the covered code. Mutants that survive mark code that runs under test but whose behaviour no assertion checks.

**A16.** Exact (bit-identical outputs), speed (run time within a margin of the baseline) and drift (headline results within a tolerance of their recorded values).

**A17.** The literal string `null/tools`. The `parameters` directive is evaluated before any agent exists, so `env.HOME` is null there. Resolve agent paths inside the step's shell instead.
