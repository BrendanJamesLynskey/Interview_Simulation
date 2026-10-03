# Statistics of Simulation Output — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Warm-up deletion, replications and confidence intervals, batch means, common random numbers, percentile pitfalls
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Why can't you compute a confidence interval from the individual latencies of one simulation run?

**Answer:**

Because successive observations in a simulation are **autocorrelated**: if request n waited a long time (a queue had built up), request n+1 probably will too. The standard CI formula, mean ± t·s/√n, assumes independent samples. With positive autocorrelation the true variance of the mean is much larger than s²/n, so the interval is far too narrow and misses the truth much more often than its nominal 5%.

Coding challenge 02 on this GitHub measures this: for an M/M/1 queue at ρ = 0.9, a CI from replications is more than 5× wider than the naive one computed from 45,000 waits of one run, and only the wide one is honest.

Fixes: **independent replications** (one summary number per run), or **batch means** (one long run cut into large batches whose means are nearly independent).

**Go deeper on this GitHub:** [InfSim 06, "Statistics That Survive Review"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-06) · [SimEng 12, "Statistics of Simulation Output"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-14) · [coding challenge 02](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_02_mm1_queue.py)

### Q2. What is initialisation bias, and how do you handle it?

**Answer:**

A simulation usually starts in an unrepresentative state: empty queues, idle servers, cold caches. Early observations reflect that start, not steady state. For latency, an empty start biases results **low**.

Handling it:
- **Warm-up deletion**: discard observations from an initial period. Choose its length by looking at a running average or a plot of the output over time (e.g. Welch's method: average across replications, smooth, find where the curve flattens).
- **Run long** compared with the warm-up, so any residual bias is small.
- **Start in a representative state** where possible (e.g. pre-loaded queues from a previous run).

The bias is worst near saturation, where the system takes longest to reach steady state. In coding challenge 02, short runs of 200 customers at ρ = 0.9 started empty averaged a wait of about 6 against a true 9.

**Go deeper on this GitHub:** [Glossary: warm-up, replications and confidence intervals](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-warmup) · [replications card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-replications)

### Q3. How do you build a confidence interval from replications?

**Answer:**

Run R independent replications (independent random streams, same configuration), each with warm-up deleted, and take one summary per replication (e.g. its mean latency, or its p99). Those R numbers are independent and identically distributed, so:

$$\bar{X} \pm t_{R-1,\,0.975}\, \frac{s}{\sqrt{R}}$$

where s is the sample standard deviation of the R summaries. With R = 10, t ≈ 2.262; with R = 20, t ≈ 2.093.

To halve the CI width you need about four times as many replications. Decide R from a pilot run: estimate s, then solve for the width you need.

```python
import math, statistics

def ci95(per_replication_means):
    t975 = {4: 2.776, 9: 2.262, 19: 2.093}   # t quantiles for R = 5, 10, 20
    r = len(per_replication_means)
    m = statistics.fmean(per_replication_means)
    half = t975[r - 1] * statistics.stdev(per_replication_means) / math.sqrt(r)
    return m, half

print(ci95([4.1, 3.8, 4.3, 3.9, 4.0]))
# (4.02, 0.23880054941310322)
```

**Go deeper on this GitHub:** [InfSim 06, "Interactive: Replications, Confidence Intervals and Common Random Numbers"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-07) · [Glossary: warm-up, replications and confidence intervals](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-warmup)

---

## Intermediate

### Q4. What is the method of batch means, and when is it preferable to replications?

**Answer:**

Run **one long simulation**, delete the warm-up once, then divide the remaining observations into k contiguous batches of size m. Treat the k batch means as approximately independent samples and build a t-interval from them.

It works when batches are long compared with the autocorrelation time, so adjacent batch means are nearly uncorrelated. Choose m large enough (check the lag-1 correlation of the batch means) and k around 10–30.

Prefer it over replications when:
- the warm-up is expensive (you pay it once instead of R times);
- the steady state is the only thing of interest.

Prefer replications when warm-up is cheap, when you want trivially parallel runs, or when the transient itself matters.

**Go deeper on this GitHub:** [Glossary: batch means](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-batchmeans) · [InfSim 06, "Statistics That Survive Review"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-06)

### Q5. Explain common random numbers. When can they backfire?

**Answer:**

To compare designs A and B, drive both with the **same** random inputs (same arrival times, same request sizes) in each replication. The noise from the workload is then shared, and the **difference** A − B has much lower variance than with independent inputs: the CI on the difference shrinks, often dramatically, for the same number of runs.

Requirements:
- **Separate streams per purpose** (arrivals, sizes, service), so that a change in how B uses randomness (e.g. an extra draw for a routing decision) does not shift A's and B's arrival streams out of alignment.
- Compute the CI on the **paired differences** (A_i − B_i), not on A and B separately.

When it backfires: if the outputs respond to the shared inputs in **opposite** directions (negative correlation), the variance of the difference increases. This is rare for performance comparisons of similar designs, but check the correlation in a pilot.

**Go deeper on this GitHub:** [Glossary: common random numbers](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-crn) · [InfSim 06, "Interactive: Replications, Confidence Intervals and Common Random Numbers"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-07)

### Q6. List the common percentile pitfalls in performance reports.

**Answer:**

1. **Averaging percentiles**: the mean of per-instance or per-run p99s is not the p99 of the combined data. Merge the distributions (histograms, sketches) and then take the percentile. Coding challenge 04 shows an example where the mean of two p99s is 505 ms and the pooled p99 is 10 ms.
2. **Too few samples for the tail**: a p99.9 from 1,000 samples is one observation. Report sample counts; give CIs for tail percentiles (e.g. bootstrap).
3. **Unstated definitions**: nearest-rank, linear interpolation, or a sketch's approximation give different values; state the method.
4. **Per-request vs per-token**: p99 of TPOT averaged per request hides inter-token stalls that the p99 of individual gaps reveals.
5. **Coordinated omission** in load generation hides tail latency.
6. **Mixing warm-up and steady state** in the same distribution.
7. **Reporting only the mean** for a skewed distribution.

**Go deeper on this GitHub:** [InfSim 06, "Latency: Distributions, Not Averages"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-02) · [Glossary: percentiles and tail-latency CCDFs](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-percentiles) · [coding challenge 04](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_04_streaming_percentiles.py)

---

## Advanced

### Q7. How many replications do you need to tell two designs apart?

**Answer:**

It depends on the size of the difference and the noise of the **difference**:

1. Run a pilot with R₀ replications (say 10) using common random numbers.
2. Compute the paired differences dᵢ = Aᵢ − Bᵢ and their standard deviation s_d.
3. To get a CI half-width h on the mean difference, you need roughly R ≈ (t · s_d / h)². Choose h smaller than the difference you care about (e.g. half of it).
4. If the CI on the difference excludes zero, the designs differ at that confidence.

With CRN, s_d is often much smaller than the standard deviation of A or B alone, so R can be small. Without CRN, a 2% difference in a metric with 10% run-to-run variation can need hundreds of runs.

Also guard against **multiple comparisons**: comparing 20 designs pairwise at 95% will produce false "differences" by chance; adjust the confidence level (e.g. Bonferroni) or use a ranking-and-selection procedure.

**Go deeper on this GitHub:** [SimEng 12, "Statistics of Simulation Output"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-14) · [Glossary: common random numbers](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-crn)

### Q8. Your simulator matches a measured system on mean latency but not on p99. What does that suggest?

**Answer:**

The **mean** is set by average service times and utilisation; the **tail** is set by variability and rare events. Matching the mean but not the tail suggests the model's variability is wrong:

- **Service-time variability**: the model uses fixed or narrowly distributed step times where the real system varies (data-dependent kernels, cache effects, interference, garbage collection, OS jitter).
- **Arrival burstiness**: Poisson arrivals in the model, bursty or correlated arrivals in reality. Burstiness inflates tails at the same mean load.
- **Rare events not modelled**: preemption, retries, long prompts mixed with short ones, periodic background work, throttling.
- **Scheduling details**: head-of-line blocking, priority, batching rules that occasionally delay a request a lot.
- **Measurement**: the real system's p99 may include coordinated omission (in the opposite direction) or warm-up.

Fix by comparing **distributions** (CCDFs on log axes), not single percentiles, and by modelling the variability sources one at a time to see which closes the gap.

**Go deeper on this GitHub:** [InfSim 06, "Latency: Distributions, Not Averages"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-02) · [Glossary: calibration and correlation](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-correlation)

### Q9. How would you treat agreement between two simulators (or a simulator and hardware) as a measurement in its own right?

**Answer:**

Report agreement with the same care as any measurement:
- **Define the metric** (relative error per quantity, per configuration; bit-exact match of timestamps; correlation of rankings).
- **Report the distribution of errors**, not just the best case: per pattern, per size, worst case and typical.
- **State the conditions**: same traces, same timing parameters, same mapping, versions and commits.
- **Separate systematic from random disagreement**: a constant offset suggests a missing fixed cost; pattern-dependent differences suggest a policy difference.
- **Keep it reproducible**: the cross-check script and its outputs in the repository, so it can be re-run when either side changes.

On this GitHub this is done for a DRAM model against DRAMsim3 (per pattern, two mappings) and for an FHE model against a software library's recorded traces.

**Go deeper on this GitHub:** [SimEng 12, "Agreement as a Measurement"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-15) · [agreement card](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#card-agreement) · [Glossary: cross-checking against another simulator](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-crosssim)
