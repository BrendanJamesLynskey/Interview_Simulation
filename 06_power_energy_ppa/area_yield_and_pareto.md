# Area, Yield and PPA Trade-offs — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Estimating area before layout (CACTI, McPAT, Accelergy), dies per wafer and yield models, cost, chiplets, perf/W, perf/mm², Pareto fronts
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What does "PPA" mean, and why must a performance simulator eventually report all three?

**Answer:**

**Power, performance and area**: the three axes every chip design trades. Performance without power ignores the thermal and energy budget; performance without area ignores cost (area sets dies per wafer and yield, hence silicon cost per chip).

A simulator that reports only latency will recommend "more of everything". With power and area attached, it can answer the real questions: which upgrade buys the most latency **per mm²**, **per watt**, **per dollar**; which designs are not dominated on all three axes.

Who trades what: architects trade units and memories against area; physical designers trade area and timing against power; product teams trade cost against performance targets.

**Go deeper on this GitHub:** [SimEng 13, "What PPA Is, and Who Trades It"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-01) · [Glossary: PPA](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-ppa)

### Q2. How can you estimate a chip's area before any layout exists?

**Answer:**

- **SRAM and caches: CACTI.** An analytical model of SRAM arrays (banks, subarrays, wires, peripheral circuits) that reports area, access time, energy per access and leakage for a given capacity, organisation and technology node.
- **Processors: McPAT.** Area, power and timing for cores, caches and NoCs from a high-level configuration.
- **Accelerators: Accelergy (with Timeloop).** Energy and area from a component library and action counts, often paired with a dataflow mapper.
- **Published designs**: per-unit areas from papers at a stated node, scaled linearly by unit count.

All of these are **models**, typically validated against published or SPICE results at the component level, and node scaling factors are approximate. State the node and the source of every coefficient, and label scaled numbers as illustrative.

On this GitHub, an FHE accelerator area model takes functional-unit areas from a published 7 nm design (ARK's per-unit table) and SRAM density from a CACTI sweep at 22 nm, scaled to 7 nm by one anchor point.

**Go deeper on this GitHub:** [SimEng 13, "Estimating Area Before Layout"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-05) · [SimEng 12, "Architecture Estimators: McPAT, CACTI, Accelergy and Timeloop"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-12) · [Glossary: CACTI](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-cacti) · [Glossary: an area model calibrated from papers and CACTI](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-areamodel)

### Q3. Why does a larger die cost disproportionately more?

**Answer:**

Two effects compound:

1. **Fewer dies per wafer**, and more wasted wafer edge. A common approximation for a wafer of diameter d and die area A:

$$\text{DPW} \approx \frac{\pi (d/2)^2}{A} - \frac{\pi d}{\sqrt{2A}}$$

2. **Lower yield**: random defects with density D₀ (per unit area) kill a die if one lands on it. The simplest (Poisson) model gives

$$Y = e^{-A D_0}$$

so yield falls exponentially with area.

Cost per good die = wafer cost / (DPW × Y). With illustrative numbers on this GitHub (300 mm wafer, D₀ = 0.1 per cm², $10,000 per wafer), silicon cost per good mm² is 2.54× higher at 858 mm² than at 100 mm².

**Go deeper on this GitHub:** [SimEng 13, "Why Area Is Cost: Dies per Wafer and Yield"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-06) · [Glossary: dies per wafer](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-diesperwafer) · [Glossary: Poisson yield](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-poissonyield)

---

## Intermediate

### Q4. Compare the Poisson and Murphy yield models. When do they diverge?

**Answer:**

- **Poisson**: Y = exp(−A D₀). Assumes defects are uniformly and independently distributed: every die sees the same defect density.
- **Murphy (1964)**: averages the Poisson yield over a distribution of defect densities across the wafer (in its common form, a triangular approximation to a Gaussian), giving

$$Y = \left(\frac{1 - e^{-A D_0}}{A D_0}\right)^2$$

Real defects cluster, so some regions are worse and others better than average. Clustering raises yield compared with Poisson at the same mean density, because defects "waste themselves" on dies that were already dead.

They agree for small A·D₀ and diverge as A·D₀ grows. On this GitHub's illustrative table for a 457.9 mm² die: at D₀ = 0.1/cm², Poisson 63.3% vs Murphy 64.4%; at D₀ = 0.5/cm², 10.1% vs 15.4%.

**Implementation note:** compute 1 − e^(−x) as `-expm1(-x)`. For tiny dies the naive form cancels to zero; property-based tests on this GitHub found exactly that bug.

**Go deeper on this GitHub:** [Glossary: Murphy yield](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-murphyyield) · [SimEng 13, "Interactive: PPA Explorer"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-09) · [FHE results (section 24)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)

### Q5. Define perf/W, perf/mm², EDP and TCO. Which does each kind of customer optimise?

**Answer:**

- **perf/W**: performance per watt. For a fixed amount of work, perf/W = 1 / (energy per operation). Optimised by power- or energy-limited deployments: datacentres with power-capped racks, edge devices, batteries.
- **perf/mm²** (and **perf/$**): performance per unit of silicon area (or cost). Optimised by whoever pays for the silicon: high-volume products, cost-sensitive accelerators.
- **EDP / ED²P**: energy × delay (× delay). Balances energy and speed; a single figure for comparing operating points.
- **TCO (total cost of ownership)**: capital cost (chips, boards, systems) plus operating cost (energy, cooling, space) over the lifetime, per unit of useful work. What a datacentre operator ultimately optimises.

Different metrics pick different designs from the same sweep, so **say which metric a recommendation optimises**.

**Go deeper on this GitHub:** [SimEng 13, "Composite Metrics: perf/W, perf/mm², EDP and TCO"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-07) · [Glossary: perf/W](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-perfperwatt) · [Glossary: perf/mm² and perf/$](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-perfpermm2) · [Glossary: TCO](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-tco)

### Q6. What is a Pareto front, and how do you use one in a design review?

**Answer:**

With several objectives to minimise (latency, energy, area), design A **dominates** design B if A is no worse in every objective and better in at least one. The **Pareto front** is the set of designs nothing dominates. Everything off the front is wasteful: some front design is better in every respect.

In a review:
1. Show the sweep and the front; discard dominated designs.
2. Apply hard constraints (fits the reticle, under the power budget, meets the latency target).
3. Choose along the remaining front with an explicit preference (a metric like perf/mm², or a cost target).

On this GitHub's FHE scratchpad sweep, every size from 128 to 2,048 MiB was on the latency–energy–area front with the baseline algorithm, but with traffic-reducing techniques only 128 to 512 MiB were: past 512 MiB, more SRAM bought no latency or energy and only added area.

**Go deeper on this GitHub:** [SimEng 13, "Pareto Fronts: Why There Is No Single Best Design"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-08) · [Glossary: Pareto front and dominance](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-paretofront) · [coding challenge 06](https://github.com/BrendanJamesLynskey/Interview_Simulation/blob/main/09_coding_challenges/challenge_06_pareto_front.py)

---

## Advanced

### Q7. When does it make sense to split a design into chiplets? What does a silicon-only cost model miss?

**Answer:**

Split when:
- the monolithic die would exceed the **reticle limit** (about 26 × 33 mm = 858 mm² for a single exposure field), so it cannot be built at all;
- yield at the monolithic size is low enough that smaller dies save more than the integration costs;
- parts of the design benefit from **different process nodes** (I/O and analogue on an older node, compute on the newest).

On this GitHub's illustrative model, splitting a 1,182 mm² design into 1, 2, 4 and 8 equal chiplets gave silicon costs of $727, $381, $267 and $219.

What a silicon-only model misses (and the table says so):
- **die-to-die interfaces** (PHY area and power on every chiplet);
- the **interposer or advanced package** and its own yield;
- **assembly yield** and **known-good-die testing**;
- performance and energy cost of crossing between chiplets (latency, bandwidth, pJ per bit).

So the silicon-only numbers **overstate the saving**; they are the start of the analysis, not the answer.

**Go deeper on this GitHub:** [SimEng 13, "Compute or SRAM, and When to Split the Die"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-11) · [Glossary: reticle limit and chiplets](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-reticle)

### Q8. Your area model scales a published design's unit areas linearly with unit count. What could go wrong?

**Answer:**

- **Wiring grows super-linearly**: a larger NTT or systolic array needs longer, wider interconnect; crossbars and permutation networks grow roughly with the square of their port count.
- **Uncore overheads** (register files, NoC, control) may not be a constant fraction of the rest.
- **Node and library differences**: the published design's node, cell library and memory compilers may differ from yours; one scaling factor between nodes hides real differences for logic, SRAM and analogue.
- **Assumptions hidden in the source**: e.g. an assumed lane count for a unit whose breakdown the paper does not give.
- **Area does not feed back into timing**: a bigger die has longer wires, so clocks or latencies may change, which a linear area model will not tell you.

Good practice (followed by the model on this GitHub): comment each coefficient with its source and any assumption, reproduce the published design's total as a check (its first table row reproduces the published 418.2 mm² by construction), label every scaled result as illustrative, and test the conclusions' sensitivity to the scaling assumption.

**Go deeper on this GitHub:** [SimEng 13, "Pitfalls"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-13) · [SimEng 13, "Area: What Sets It"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-04) · [Glossary: silicon area and the area model](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-area)

### Q9. A CACTI sweep says the 512 MiB SRAM leaks 0.14 W with one cell type and 179 W with another. What do you conclude?

**Answer:**

That the **cell type is a first-order design choice**, not a detail. CACTI's high-performance (`itrs-hp`) cells trade leakage for speed; low-standby-power (`itrs-lstp`) cells leak orders of magnitude less but are slower. For a large scratchpad holding keys or weights, accessed in large sequential chunks, the slower cells are usually fine, and the high-performance option would make the SRAM's leakage alone exceed most accelerators' power budgets.

Also note what the numbers are: CACTI model outputs at **22 nm** from ITRS-based technology data (on this GitHub's sweep, with 4 MiB banks), not silicon measurements, and leakage is reported per bank (so multiply by the bank count). Use them to choose and to bound, state the assumption ("lstp cells"), and do not feed 22 nm leakage into a 7 nm power model without a stated scaling.

**Go deeper on this GitHub:** [SimEng 12, "CACTI on This Machine: SRAM Against Capacity"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-13) · [Glossary: CACTI](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-cacti) · [FHE results (section 21)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)
