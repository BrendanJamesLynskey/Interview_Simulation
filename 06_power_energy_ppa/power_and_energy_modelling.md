# Power and Energy Modelling — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Dynamic and static power, energy per operation, DVFS, power caps and TDP enforcement in a simulator, energy proportionality
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What are the components of a chip's power, and how does a simulator usually model them?

**Answer:**

- **Dynamic power**: charging and discharging capacitance when signals switch, P = α C V² f (activity factor, switched capacitance, supply voltage, clock frequency).
- **Static (leakage) power**: current flowing even when nothing switches; depends strongly on voltage, temperature and transistor type, and does not scale with activity.

An architecture simulator rarely knows capacitances, so it models power from **activity counts and energy per operation**:

$$P = P_{\text{static}} + \frac{\sum_{\text{ops}} n_{\text{op}} \, E_{\text{op}}}{t}$$

with energies per FLOP, per byte moved from DRAM, per SRAM access, per link byte. The LLM serving simulator on this GitHub uses exactly this form, with clearly illustrative H100-class coefficients: 100 W idle, 1.0 pJ per FLOP, 60 pJ per HBM byte.

**Common mistake:** reporting power without energy. A design that draws more power but finishes much sooner can use less energy.

**Go deeper on this GitHub:** [InfSim 07, "Where the Joules Go: Static, Dynamic, and Data Movement"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-02) · [InfSim 07, "The Simulator's Power Model"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-03) · [Glossary: static and dynamic power](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-staticdyn)

### Q2. Why is data movement so expensive in energy?

**Answer:**

Moving a byte costs energy proportional to the distance and capacitance of the wires it crosses. Reading from off-chip DRAM costs far more energy per byte than an arithmetic operation on it; on-chip SRAM sits in between, and a register file read is cheapest. Widely quoted figures (e.g. [Horowitz, "Computing's energy problem", ISSCC 2014](https://doi.org/10.1109/ISSCC.2014.6757323), at 45 nm) put a DRAM access orders of magnitude above an add or multiply.

Consequences:
- **Memory-bound workloads are energy-bound too**: decode in LLM inference spends most of its dynamic energy reading weights and KV cache.
- Architectures that **reuse data on chip** (systolic arrays, large scratchpads, fusion) save energy as well as time.
- A simulator that counts only FLOPs badly underestimates energy for memory-heavy workloads.

**Go deeper on this GitHub:** [InfSim 07, "Where the Joules Go: Static, Dynamic, and Data Movement"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-02) · [Glossary: energy of data movement](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-datamovement)

### Q3. What is DVFS, and why does lowering frequency save energy only for some workloads?

**Answer:**

Dynamic voltage and frequency scaling lowers the clock and, with it, the supply voltage. Since dynamic energy per operation scales roughly with V², and V roughly tracks f in the operating range, running slower saves energy per operation; power falls faster still (roughly f³ in the simple model).

But time goes up, and static power is paid for longer:
- For a **compute-bound** step, halving the clock doubles the time: static energy doubles, dynamic energy falls. Net saving only if static power is small.
- For a **memory-bound** step, compute is waiting on memory anyway: lowering the compute clock until compute just keeps up with memory costs **no time** and saves dynamic energy. That is the ideal case.

On this GitHub's serving simulator, DVFS saved 17.1% of a memory-bound decode step's dynamic energy at the same step time, while compute-bound prefill steps were unchanged.

**Go deeper on this GitHub:** [InfSim 07, "DVFS and Power Caps: The Third Roof"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-05) · [Glossary: DVFS and power caps (the third roof)](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-dvfs) · [SimEng 13, "Power: Dynamic, Static, DVFS and Dark Silicon"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-03)

---

## Intermediate

### Q4. How should a simulator enforce a TDP or a power cap?

**Answer:**

A real part throttles: when its power would exceed the limit, the clock (and voltage) drop. A simulator that ignores this overestimates performance for power-hungry phases.

Approaches, from simple to faithful:
1. **Worst-case fixed clock**: choose one clock at which the worst-case phase fits the TDP, and run everything at it. Simple, pessimistic for light phases.
2. **Per-step closed-form throttling**: for each step, compute the clock at which its power (static + dynamic energy / time) equals the cap, and stretch the step accordingly. The LLM serving simulator on this GitHub does this, solving the resulting cubic in closed form.
3. **A dynamic power manager**: track the instantaneous power of all concurrent activity and grant each new kernel the highest clock that fits the remaining headroom (or make it wait). Closer to how firmware power management behaves.

On this GitHub's FHE model at 250 W, a design with 4× the compute units ran a bootstrap in 6.20 ms under the dynamic manager against 8.28 ms with worst-case clocking; its worst-case power at full clock would have been 462 W.

**Go deeper on this GitHub:** [InfSim 07, "Interactive: One Step Under a Power Cap"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-06) · [Glossary: dynamic power manager against worst-case clocking](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-powermgr) · [Glossary: TDP and peak power](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-tdp)

### Q5. What is energy proportionality, and why does it matter for serving systems?

**Answer:**

A system is energy-proportional if its power scales with its load: zero power at zero load. Real accelerators have large static power (leakage, clocks, memory refresh, fans' share), so at low utilisation the energy **per useful operation** is high.

On this GitHub's serving simulator (illustrative coefficients, one prefill and one decode instance): at 0.5 req/s, 11.8 J per output token with static power 54% of energy; at 4 req/s, 2.8 J per token with static 30%.

Consequences:
- Under-utilised clusters waste most of their energy on static power. Consolidating load onto fewer devices (and powering the rest down) saves energy.
- Comparisons of "energy per token" must state the load. A design with high static power (e.g. lasers and thermal tuning in photonic compute) looks good only when busy.

**Go deeper on this GitHub:** [InfSim 07, "Energy Proportionality: Static Power and Load"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-08) · [Glossary: energy proportionality](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-proportionality)

### Q6. Power cap at 250 W meets the SLO; at 200 W almost nothing does. Explain the cliff.

**Answer:**

Latency under load is a queueing phenomenon: as service time rises, utilisation rises, and waiting time grows like 1/(1 − ρ). A power cap stretches service times (lower clock). While the system has headroom, a modest stretch costs a little latency. Once the stretched service rate approaches the arrival rate, queues grow without bound and the SLO collapses.

On this GitHub's serving simulator (Llama-3-70B, 4 req/s, disaggregated, with DVFS), capping the decode devices at 250 W kept 99.7% of requests within the SLO; at 200 W only 12.6% met it, while energy per token improved only from 2.59 to 2.43 J.

The general lesson: **power caps interact with load non-linearly**. Simulate the cap together with the arrival process; a per-step power model alone will miss the cliff.

**Go deeper on this GitHub:** [InfSim 07, "System Results: Latency Against Energy"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-07) · [Glossary: energy per token and energy–delay trade-off](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-jtoken) · [the recorded table (section 3)](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md)

---

## Advanced

### Q7. How would you calibrate a simulator's power coefficients?

**Answer:**

1. **Static power**: measure the device idle at its operating clocks (board telemetry, or RAPL on CPUs where available); separate fixed board power if the question is about the chip.
2. **Energy per FLOP**: run a compute-bound microbenchmark at several sizes; fit energy = static × time + E_flop × FLOPs.
3. **Energy per byte**: run a bandwidth-bound microbenchmark (a stream) and fit E_byte the same way.
4. **Validate** on mixed workloads not used for fitting; check power is within the measurement's own error.

Pitfalls:
- **Telemetry sampling**: GPU power counters are averaged or sampled at coarse intervals; short kernels are invisible. Measure long, steady runs.
- **Temperature**: leakage rises with temperature; warm the device first.
- **Clock behaviour**: boost clocks change under load; pin or record them.
- **Permissions**: on Linux, RAPL energy counters typically need elevated privileges; on this GitHub's measurement machine they were not readable as a normal user, so energy cards there are documented, not measured.

For pre-silicon designs, coefficients come from RTL power analysis of key blocks, from estimators (McPAT, CACTI, Accelergy) and from published numbers, and must be labelled as such.

**Go deeper on this GitHub:** [SimEng 12, "GPU Telemetry: nvidia-smi, NVML, DCGM and Zeus"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-07) · [SimEng 12, "CPU and Wall Energy: RAPL and Power Analysers"](https://brendanjameslynskey.github.io/SimEng_12_Measurement_Tools_and_Methods/#slide-08) · [InfSim 07, "From the Simulator to RTL Power and Thermal Analysis"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-09)

### Q8. Why does the energy–delay product have a minimum as voltage varies, and why use EDP or ED²P instead of energy?

**Answer:**

Lowering voltage reduces dynamic energy per operation (∝ V²) but makes circuits slower; as V approaches the threshold voltage, delay grows sharply and static energy (static power × longer time) grows with it. So energy per operation has a minimum near (often somewhat above) the threshold, and delay increases monotonically as V falls.

Minimising energy alone drives the design to very low voltage and very slow operation. **EDP** (energy × delay) weights both; **ED²P** weights delay more, and is roughly invariant to voltage scaling in the simple model (since E ∝ V² and delay ∝ 1/V, E·D² is constant), making it a fairer comparison of architectures that could each be voltage-scaled.

Which metric fits:
- **energy per operation (perf/W)**: battery or power-limited deployments;
- **EDP**: balanced;
- **ED²P**: performance-first comparisons independent of operating point.

**Go deeper on this GitHub:** [SimEng 13, "Composite Metrics: perf/W, perf/mm², EDP and TCO"](https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-07) · [Glossary: EDP and ED²P](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-edp)

### Q9. A photonic or other novel accelerator claims 10× better energy per operation. What would you model before believing it at system level?

**Answer:**

1. **Static power**: lasers, thermal tuning of optical components, and other always-on blocks burn power whether or not work arrives. At realistic utilisation, static energy can dominate.
2. **Conversions**: data must cross from digital to analogue and back (DACs and ADCs). Their energy per sample grows with precision (ENOB) and often dominates the optical core's own energy.
3. **Data movement**: the energy to bring operands from memory is unchanged by a faster multiplier. If the workload is memory-bound, compute energy savings are a small part of the total.
4. **Precision overhead**: lower native precision may need multiple passes per operation.
5. **Utilisation under real workloads**: peak efficiency at full utilisation is not the efficiency of a real serving load.

On this GitHub's serving simulator, a hypothetical optical part with 10× lower energy per FLOP but higher idle power landed at 2.28 J per token at 4 req/s, against 2.77 J for the GPU baseline and 2.26 J for the GPU under a 400 W cap with DVFS. Decode is memory-bound, so cheap FLOPs barely help, and static power made up 65% of the optical system's energy.

**Go deeper on this GitHub:** [InfSim 07, "Power in Photonic and Novel Compute"](https://brendanjameslynskey.github.io/InfSim_07_Power_and_Energy/#slide-10) · [Glossary: power in photonic compute](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-photonicpower) · [FHESim 04, "Conversion Energy and Static Power"](https://brendanjameslynskey.github.io/FHESim_04_Optical_NTT_Engines/#slide-08)
