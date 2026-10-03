# Quiz — Foundations and Simulation Levels

**Subject:** Simulation and Performance Modelling
**Topics covered:** Why simulate, the fidelity ladder, verification/validation/calibration, field solvers and SPICE, RTL simulation, virtual platforms, Monte Carlo, co-simulation
**Format:** Multiple-choice and short-answer questions. Answers at the end.

---

### Q1. Which statement best describes the difference between verification and validation of a simulation model?

a) Verification uses measurements; validation uses unit tests.
b) Verification asks whether the model is built right; validation asks whether it is the right model for its purpose.
c) They are synonyms; "validation" is the hardware term.
d) Validation fits the model's parameters to data.

---

### Q2. A model is calibrated on 10 workloads and then reported as "within 5% of measurement" on the same 10. What is wrong with the claim?

---

### Q3. Order these from fastest to slowest, in simulated time per wall-clock second for a large chip (typical): RTL simulation, analytical model, cycle-level model, discrete-event system model, FPGA prototype.

---

### Q4. An analytical bound says a serving pool saturates at 7.5 req/s. A discrete-event simulation finds the latency target is met by 90% of requests only up to about 6 req/s. Which is wrong?

a) The analytical bound, because it disagrees with the simulator.
b) The simulator, because it should match the bound.
c) Neither: the bound ignores queueing, which degrades latency before saturation.
d) Both: they should agree at every load.

---

### Q5. For the 3-D Yee FDTD scheme with cubic cells, halving the cell size multiplies the work for the same simulated time by roughly:

a) 2×
b) 4×
c) 8×
d) 16×

---

### Q6. Why does SPICE use implicit integration methods such as backward Euler or Gear?

---

### Q7. Forward Euler on dv/dt = −v/τ is stable only if the step h satisfies:

a) h < τ/2
b) h < τ
c) h < 2τ
d) any h > 0

---

### Q8. What is a "breakpoint" in an adaptive circuit simulator, and why does it reduce work?

---

### Q9. Which simulator style is most likely to run a large synchronous RTL design fastest, once compiled?

a) Event-driven, four-state
b) Cycle-based, two-state, compiled to C++
c) Gate-level with SDF timing
d) An interpretive instruction-set simulator

---

### Q10. Explain in two sentences why delta cycles exist in VHDL and SystemC.

---

### Q11. A functional instruction-set simulator reports 2 billion instructions for a program. What can you say about its run time on the real chip?

a) 2 billion cycles at 1 IPC
b) Nothing precise: a functional ISS models what instructions do, not their timing
c) 2 seconds at 1 GHz, exactly
d) Half that, because modern cores are superscalar

---

### Q12. Monte Carlo error scales as σ/√N. How many more samples are needed to cut the error by 10×?

---

### Q13. Which variance-reduction technique is most useful for comparing two designs on the same workload?

a) Antithetic variates
b) Importance sampling
c) Common random numbers
d) Stratified sampling

---

### Q14. In hardware-in-the-loop testing, what constraint does the plant simulation have that an offline simulation does not?

---

### Q15. A team calls its pre-silicon performance model a "digital twin". Using the definition with a two-way data link to a physical system, is that correct?

---

## Answers

**A1.** (b). Verification checks the implementation against the intended model (tests, closed-form cases, differential tests). Validation checks the model's outputs against the real system for the intended use. (d) describes calibration.

**A2.** It shows the model can be fitted, not that it predicts. Validation needs held-out workloads not used in calibration, over the range of conditions the decisions need, with errors reported separately for calibration and validation sets.

**A3.** Analytical (instant) → discrete-event system model → FPGA prototype (tens of MHz) → cycle-level model → RTL simulation. (FPGA prototypes run real hardware, so they are much faster than software cycle-level or RTL simulation; the analytical and DES models are fastest because they abstract the most.)

**A4.** (c). The bound is a correct ceiling on throughput; queueing makes latency targets fail well before it. The two must agree only where queueing is negligible (low load). On this GitHub's serving simulator the recorded values are 7.49 and 5.97 req/s.

**A5.** (d). 8× more cells (2³) and 2× more time steps (the CFL limit halves Δt), so about 16×.

**A6.** Circuits are stiff: fast and slow time constants coexist. Explicit methods must take steps smaller than the fastest time constant to stay stable; implicit methods are stable at any step size (A-stable), so the step can be chosen for accuracy instead.

**A7.** (c) h < 2τ. The error is multiplied by (1 − h/τ) each step, which must have magnitude below 1.

**A8.** A time at which a source has a corner or discontinuity, given to the solver in advance. The solver lands a step exactly on it and restarts cleanly, instead of discovering the discontinuity by repeatedly rejecting and shrinking steps. On this GitHub's RC demo, breakpoints cut right-hand-side evaluations from 2,660 to 560 at the same tolerance.

**A9.** (b). Cycle-based compiled simulation (e.g. Verilator) evaluates the design once per clock as native code; on this GitHub it ran 131× more cycles per second than an event-driven simulator on the same core, after a 4.38 s compile.

**A10.** Delta cycles split one simulated instant into evaluate and update phases, repeated until nothing changes, so concurrent processes all read the old values before any new value is visible. This makes the result independent of the order in which the simulator happens to run the processes.

**A11.** (b). Timing needs a micro-architectural model or measurement; IPC varies widely with the program and the core.

**A12.** 100× more samples (error ∝ 1/√N).

**A13.** (c). Driving both designs with the same random inputs makes their outputs positively correlated, so the variance of the difference shrinks.

**A14.** It must run in hard real time: every step must finish before its wall-clock deadline, because the real controller cannot be paused.

**A15.** No. There is no physical twin yet to update it from, so it is a model. A twin needs continual data assimilation from a specific physical system and decisions fed back to it.
