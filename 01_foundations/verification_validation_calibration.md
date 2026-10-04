# Verification, Validation and Calibration — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Is the model built right, is it the right model, and how its coefficients are fitted
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Define verification, validation and calibration for a simulation model.

**Answer:**

- **Verification:** *is the model built right?* Does the code implement the intended model? Checked with tests, closed-form cases, invariants, code review and comparisons with independent implementations.
- **Validation:** *is it the right model?* Does the model represent the real system well enough for its intended use? Checked against measurements or trusted references, for the quantities and operating range that matter.
- **Calibration:** *fitting the model's free parameters* (efficiencies, per-operation costs, energy coefficients) to reference data.

The order matters: calibrating an unverified model fits coefficients to compensate for bugs, and the fit then fails on the next workload. Verify first, calibrate second, then validate on data **not** used for calibration.

A widely used framing in the simulation literature (Sargent's) separates the conceptual model's validity, the computerised model's verification, and operational validity (does the output match the system for the purpose?).

**Common mistake:** saying "validated" when the model was only calibrated to the same data it is compared against.

**Go deeper on this GitHub:** [Introduction to Simulation, "Verification, Validation and Calibration"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/28) · [SimEng 09, "The V-Model"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-07) · [Glossary: the V-model; verification and validation](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-vmodel)

### Q2. What is the "verification ladder" for a simulator?

**Answer:**

A sequence of increasingly demanding checks, each cheap enough to run often:

1. **Unit tests** of components (a cost function, a queue, an arbiter).
2. **Closed-form checks**: configurations where theory gives the answer. An M/M/1 or M/D/1 queue against its formula; a single kernel against its roofline time; DRAM row-hit latency equal to `CL + BL/2` cycles.
3. **Invariants and properties**: conservation (every request finishes once), no resource over-subscribed, monotonicity (more bandwidth never makes things slower, unless you can explain why). Checked over random inputs with property-based testing.
4. **Differential tests**: two independent implementations (Python and Rust, SimPy and SystemC) must agree.
5. **Golden runs**: recorded outputs of reviewed runs, re-checked in CI so behaviour changes are deliberate.
6. **Validation** against measurements or published results.

**Go deeper on this GitHub:** [InfSim 06, "The Verification Ladder"](https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-08) · [Glossary: the verification ladder](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-ladder)

### Q3. Give three closed-form checks you could use to verify a memory-system model.

**Answer:**

From DRAM timing parameters (in clock cycles):

1. **Read to a closed bank:** activate then read, latency `tRCD + CL + BL/2`.
2. **Read hit to an open row:** `CL + BL/2`.
3. **Read to a bank with a different row open (conflict):** precharge, activate, read: `tRP + tRCD + CL + BL/2`.

And throughput-style checks:

4. **Same bank, next row every access:** one burst per row cycle, so bandwidth fraction `(BL/2) / tRC`.
5. **Refresh loss on a long stream:** about `tRFC / tREFI` of the time.
6. **Random reads with closed pages:** bounded by the four-activate window: at most four activates per `tFAW`, so the fraction is at most `4 (BL/2) / tFAW`.

A memory model on this GitHub reproduces all of the per-access latencies exactly, and lands near the throughput bounds (for example 0.457 against a bound of 0.471 for random closed-page reads on its DDR4 device).

**Go deeper on this GitHub:** [SimEng 04, "How We Know the Model Is Right"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-10) · [Glossary: DRAM commands and timing parameters](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-dramtiming) · [the recorded checks (section 2)](https://github.com/BrendanJamesLynskey/Memory_System_Sim/blob/main/examples/results.md)

---

## Intermediate

### Q4. How do you calibrate a simulator without over-fitting it?

**Answer:**

1. **Few free parameters, physically meaningful.** Achievable compute fraction, achievable bandwidth fraction, a fixed per-step overhead, energy per FLOP and per byte. Each should be explainable, and its fitted value plausible.
2. **Fit on a calibration set, validate on a held-out set.** Different workloads, sizes or configurations from those used to fit. Report both errors separately.
3. **Fit the simplest quantity first.** Single-kernel times before end-to-end latency; the model's structure, not its coefficients, should produce the end-to-end behaviour.
4. **Record the fit**: the data, the method, the fitted values and residuals, in the repository, so a re-fit is one command.
5. **Watch for compensating errors.** If one coefficient must take an implausible value to fit, the model is missing a mechanism.

An example of honest reporting from this GitHub: an FHE accelerator model fitted one throughput rate to a measured homomorphic multiplication on a CPU library (0% error by construction), then *predicted* a rotation (−10%) and a full bootstrap (−30%) without refitting. Replaying the library's actual recorded operation trace instead of the model's own schedule brought the bootstrap to −11%: the remaining gap is what the scheme model leaves out.

**Go deeper on this GitHub:** [FHESim 02, "Checked Against a Real OpenFHE Bootstrap"](https://brendanjameslynskey.github.io/FHESim_02_Anatomy_of_Bootstrapping/#slide-12) · [Glossary: calibration and out-of-sample prediction](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-calibration) · [the recorded calibration (section 12)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)

### Q5. What is differential testing, and why is it especially effective for simulators?

**Answer:**

Run two independent implementations of the same model on the same inputs and compare outputs. Any difference is a bug in one of them (or an ambiguity in the specification).

It suits simulators because:

- there is often **no oracle** for complex outputs (what *should* the p99 be under this workload?), but two implementations should agree exactly;
- simulators are deterministic given a seed, so outputs can be compared **bit for bit**;
- ports (Python to Rust or C++) are common for speed, and the slow original becomes the oracle for the fast port.

To compare bit for bit, both must perform the same floating-point operations in the same order, generate the same random numbers, and break ties the same way. On this GitHub a Rust port of a SimPy simulator is compared timestamp by timestamp (6,000 timestamps per configuration, zero differing) and the whole summary dictionary for equality.

**Go deeper on this GitHub:** [SimEng 02, "Testing the Port: Golden and Differential"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-09) · [Glossary: differential testing](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-differential) · [the parity table](https://github.com/BrendanJamesLynskey/Rust_DES_Kernel/blob/main/examples/results.md)

### Q6. Your model matches measurements within 5% on the calibration workloads. Is it validated?

**Answer:**

Not yet. You know it can be *fitted*, not that it *predicts*.

Questions to ask:

- **Held-out data:** what is the error on workloads not used for fitting?
- **Range:** do the validation points span the operating region of the decision (load levels, sizes, configurations)? Models often fail near saturation or at sizes outside the fitted range.
- **Mechanism:** are the bounds right (compute vs memory) for each workload, or does the model reach the right total for the wrong reason?
- **Distributions:** does it match the tail (p99), not just the mean?
- **Stability:** do small changes in the fitted coefficients change conclusions?

Validation is always *for a purpose*: "valid for ranking these designs at these loads within this error" is a defensible claim; "validated" with no qualifier is not.

**Go deeper on this GitHub:** [Introduction to Simulation, "Verification, Validation and Calibration"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/28) · [FHESim 05, "Against Published Numbers"](https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-08)

---

## Advanced

### Q7. How would you validate a simulator for hardware that does not exist yet?

**Answer:**

You cannot validate the whole against reality, so validate the **parts** and the **method**:

1. **Validate the method on hardware that exists.** Model a GPU or a CPU that you can measure, with the same modelling approach, and check the error. If the methodology gets a known device right, its predictions for the new one are more credible.
2. **Validate components separately.** RTL or FPGA prototypes of key blocks give cycle counts and energy; vendor or published numbers for memories and links; test chips for novel devices.
3. **Reproduce published results.** If papers report numbers for similar designs, set the model to those designs and compare (documenting every assumption needed to match).
4. **Cross-check across rungs.** Analytic bound ≤ DES ≤ cycle-level on shared kernels; two independent implementations agree.
5. **State the residual uncertainty** and propagate it: sweep the unvalidated coefficients over a plausible range and show whether conclusions survive.

**Go deeper on this GitHub:** [FHESim 03, "Validation"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-11) · [SimEng 04, "Cross-Checked Against DRAMsim3"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-11) · [Glossary: cross-checking against another simulator](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-crosssim)

### Q8. Two simulators disagree by 50% on one traffic pattern and within 3% on every other. What does that tell you, and what do you do?

**Answer:**

It tells you the disagreement is **mechanistic**, not a coefficient error: something about that pattern exercises a behaviour the two models implement differently. Coefficient errors usually shift every pattern.

On this GitHub, a command-level DRAM model agreed with DRAMsim3 to within a few percent on most traces but differed by +53.5% on four interleaved streams under one address mapping. That pattern depends heavily on scheduler details (how row hits are prioritised across streams, queue depths, page-closing policy).

What to do:
1. Shrink the failing case to the smallest trace that reproduces the gap.
2. Compare command traces (activate, read, precharge) side by side, not just bandwidth.
3. Identify the differing policy, and decide which matches the hardware you care about.
4. Document the remaining difference and its cause if you cannot remove it; mark which conclusions depend on it.

**Go deeper on this GitHub:** [SimEng 04, "Cross-Checked Against DRAMsim3"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-11) · [the recorded cross-check (section 7)](https://github.com/BrendanJamesLynskey/Memory_System_Sim/blob/main/examples/results.md)

### Q9. How do digital twins differ from simulation models, and why is the term risky in an interview?

**Answer:**

A widely cited definition (used by the US National Academies, from an AIAA committee) describes a digital twin as a set of virtual information constructs that mimic the structure, context and behaviour of a physical system, are **dynamically updated with data from the physical twin**, have predictive capability, and inform decisions. The key extra ingredient over an ordinary model is the **two-way, continuing data link** with a specific physical asset.

A pre-silicon performance simulator is therefore a model, not a twin: there is no physical system yet to update it from. After silicon, a model that is continuously recalibrated from fleet telemetry and used to steer operations could become one.

The risk: "digital twin" is often used loosely for any detailed simulation. Use the precise term, or define it when you use it.

**Go deeper on this GitHub:** [Introduction to Simulation, "Digital Twins, Defined Carefully"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/27)
