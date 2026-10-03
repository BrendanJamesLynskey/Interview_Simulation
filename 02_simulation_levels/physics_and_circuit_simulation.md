# Physics and Circuit Simulation — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Field solvers (FDTD, FEM, MoM), the CFL condition, SPICE (MNA, Newton–Raphson, implicit integration, timestep control), stiffness
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Compare FDTD, FEM and the method of moments as electromagnetic field solvers.

**Answer:**

| | FDTD (finite-difference time-domain) | FEM (finite element) | MoM (method of moments) |
|---|---|---|---|
| Unknowns | E and H fields on a staggered (Yee) grid, over the whole volume | Fields on an unstructured mesh of the volume | Currents on surfaces (integral equation) |
| Domain | Time domain: one run gives a broadband response | Usually frequency domain: one solve per frequency | Usually frequency domain |
| Matrix | None: explicit update, cell by cell | Large, sparse | Smaller, but **dense** |
| Strengths | Simple, parallel, broadband, transients | Complex geometry and materials, curved boundaries | Open radiating structures, mostly-metal geometry |
| Weaknesses | Staircased geometry, fine features force small cells and small steps | Mesh generation, one solve per frequency | Dense matrices scale badly; inhomogeneous dielectrics are harder |

The choice follows the problem: a broadband transient on a PCB via suits FDTD; a package with curved, layered materials suits FEM; an antenna in free space suits MoM.

**Go deeper on this GitHub:** [Introduction to Simulation, "Field Solvers: FDTD, FEM and MoM"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/6) · [Introduction to Simulation, "Level 1: Physics and Numerical Methods"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/5)

### Q2. What is the CFL condition, and what does it mean for FDTD run time?

**Answer:**

The Courant–Friedrichs–Lewy condition limits the time step of an explicit scheme: information must not travel more than one cell per step. For the 3-D Yee scheme with cubic cells of size Δx in a medium where light travels at c:

$$\Delta t \le \frac{\Delta x}{c\sqrt{3}}$$

Consequence: the time step is tied to the smallest cell. Halving the cell size (to resolve a finer feature) gives **8× the cells** in 3-D and needs **2× the time steps**, so about **16× the work** for the same simulated time. Fine geometric detail is expensive in FDTD, which is why local mesh refinement and subgridding exist.

**Common mistake:** thinking a smaller time step only improves accuracy. In an explicit scheme, exceeding the CFL limit makes the solution blow up, not just become less accurate.

**Go deeper on this GitHub:** [Introduction to Simulation, "Field Solvers: FDTD, FEM and MoM"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/6) · [Introduction to Simulation, "Stiffness, Stability and Step Control"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/20)

### Q3. What does SPICE actually do in a transient simulation?

**Answer:**

Four ideas, nested:

1. **Modified nodal analysis (MNA).** The unknowns are node voltages plus the currents in voltage sources and inductors. Each element "stamps" a few entries into one sparse matrix system.
2. **Implicit integration.** Capacitors and inductors are replaced, for each time step, by companion models (a conductance plus a current source) from backward Euler, trapezoidal or Gear (BDF) integration.
3. **Newton–Raphson.** Nonlinear devices (diodes, transistors) are linearised around the current guess; the sparse linear system is solved by LU factorisation; repeat until the node voltages converge.
4. **Timestep control.** The step is chosen from an estimate of the local truncation error. Steps are forced to land on source corners (**breakpoints**). If Newton fails to converge, the step is cut and retried.

Every time step can therefore involve several sparse LU solves. That is why SPICE is slow on large circuits and long transients.

**Go deeper on this GitHub:** [Introduction to Simulation, "Level 2: Circuits, and What SPICE Does"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/8)

---

## Intermediate

### Q4. Why does SPICE use implicit integration? Explain with the RC circuit.

**Answer:**

Circuits are **stiff**: they contain time constants spanning many orders of magnitude (picosecond parasitics next to microsecond control loops). An explicit method's stable step is limited by the *fastest* time constant, even after that transient has died away.

For an RC low-pass, dv/dt = (u − v)/τ:

- **Forward Euler (explicit):** the error is multiplied by (1 − h/τ) each step. It is stable only if |1 − h/τ| < 1, that is **h < 2τ**. Beyond that, errors grow geometrically.
- **Backward Euler (implicit):** the error is multiplied by 1/(1 + h/τ), which is below 1 for every h > 0: **stable at any step size** (A-stable). Accuracy still depends on h, but nothing blows up.

Measured on this GitHub's RC demo (τ = 1, square-wave input, 20τ simulated): at h = 2.2τ forward Euler is 25.8 V off on a 1 V signal, while backward Euler is 0.708 V off.

An implicit method costs a linear (or nonlinear) solve per step, but for stiff systems it allows steps sized by accuracy, not stability, which is a net win.

**Go deeper on this GitHub:** [Introduction to Simulation, "Interactive: One Circuit, Four Solvers"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/21) · [the solver code and recorded results](https://github.com/BrendanJamesLynskey/Introduction_to_Simulation/blob/main/demo/results.md)

### Q5. What is "trapezoidal ringing", and how do simulators deal with it?

**Answer:**

The trapezoidal rule is A-stable and second-order accurate, but it is not **L-stable**: for very fast decaying modes (large h/τ) its amplification factor tends to −1 rather than 0. A component that should decay instantly instead flips sign every step, producing a numerical oscillation ("ringing") after a sharp edge, often on inductor currents or capacitor voltages driven by ideal sources.

Remedies:
- switch to backward Euler or Gear (BDF2, which is L-stable) around discontinuities, or for the whole run;
- limit the step after a breakpoint so the fast mode is resolved;
- use damped variants of the trapezoidal rule.

**Interview point:** recognising ringing as a numerical artefact, not circuit behaviour, is the skill. Halve the step: if the "oscillation" changes period with the step, it is numerical.

**Go deeper on this GitHub:** [Introduction to Simulation, "Stiffness, Stability and Step Control"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/20)

### Q6. Why do breakpoints matter so much for an adaptive-step solver?

**Answer:**

An adaptive solver estimates its local error and shrinks the step when the error is too large. At a discontinuity (a pulse edge, a switch event) the solution's derivatives jump, and the error estimate explodes for any step that straddles it. Without being told where the edge is, the solver discovers it by trial: reject, shrink, reject, shrink. Then it has to grow the step again afterwards.

Telling the solver the edge times (**breakpoints**) lets it land exactly on each edge and restart cleanly.

Measured on this GitHub's RC demo with an adaptive Dormand–Prince 5(4) solver at tolerance 1e-6: without breakpoints, 2,660 right-hand-side evaluations with 218 rejected steps; with the edges as breakpoints, 560 evaluations, and a maximum error about 1,000× smaller (2.5e-7 V against 2.39e-4 V).

**Go deeper on this GitHub:** [Introduction to Simulation, "Interactive: One Circuit, Four Solvers"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/21) · [Introduction to Simulation, "Level 2: Circuits, and What SPICE Does"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/8)

### Q7. Why are piecewise-linear switching simulators so much faster than SPICE on power converters?

**Answer:**

A switching converter spends almost all its time in a few linear topologies (switch on, switch off, diode conducting). Within each topology the circuit is linear, so its response has a closed form (matrix exponentials). A piecewise-linear simulator:

1. models switches as ideal or piecewise-linear,
2. solves each linear interval exactly, and
3. finds the switching instants as **events**.

There is no Newton iteration and no local-truncation-error stepping inside an interval; work scales with the number of switching events, not with time-step count.

The RC demo on this GitHub shows the principle in miniature: its event-driven exact solver uses 10 events for 10 edges, and its error (5.6e-17 V) is at the level of floating-point rounding.

The cost: device detail is lost (no nonlinear switching transients, simplified losses). Use it for control-loop design and long transients; use SPICE with full device models for switching-node ringing and loss detail.

**Go deeper on this GitHub:** [Introduction to Simulation, "Switching and Behavioural Models"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/9) · [Introduction to Simulation, "Time-Stepping and Event-Driven"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/19)

---

## Advanced

### Q8. You need to simulate signal integrity on a 10 cm, 56 Gb/s PAM4 channel. Which methods do you combine, and why?

**Answer:**

No single solver handles both the physics and the statistics:

1. **Field solver (2-D or 3-D)** for the interconnect pieces: a 2-D cross-section solver for uniform transmission-line segments (giving per-unit-length R, L, G, C over frequency), a 3-D full-wave solver (FEM or FDTD) for discontinuities like vias, connectors and package transitions. Output: S-parameters.
2. **Circuit-level cascade** of those S-parameters into a channel model, checked for passivity and causality.
3. **Behavioural models of the transmitter and receiver**: equalisation (FFE, CTLE, DFE), clock recovery. Industry-standard IBIS-AMI models fill this role, so silicon vendors can share behaviour without sharing transistor netlists.
4. **Statistical or long-bit-sequence simulation** using the channel's pulse response: millions of bits to estimate eye opening and bit-error rate at levels like 1e-12, which transistor-level simulation could never reach.

The general principle: **use the highest-fidelity method only where the physics demands it, and hand off to faster abstractions** through a well-defined interface (S-parameters, pulse responses).

**Go deeper on this GitHub:** [Introduction to Simulation, "Switching and Behavioural Models"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/9) · [Introduction to Simulation, "One Accelerator, Every Level"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/17)

### Q9. A transient SPICE run of a large mixed-signal block takes two days. What can you do?

**Answer:**

Work through the causes of the cost:

- **Too many unknowns:** replace digital sections with behavioural or Verilog-A models; reduce extracted parasitics (model-order reduction of RC networks); simulate only the analog section with the digital side as ideal stimuli.
- **Too many time steps:** relax tolerances where accuracy allows (check the answer does not change); avoid unnecessary fast edges in stimuli; add breakpoints; shorten the simulated interval by starting from a pre-computed operating point.
- **Newton struggles:** convergence aids (source stepping, gmin stepping), better initial conditions, fixing discontinuous device models.
- **Different simulator class:** a "fast SPICE" simulator (table models, partitioning, multi-rate) for large post-layout runs, at reduced accuracy; or a piecewise-linear switching simulator for power stages.
- **Co-simulation:** keep transistor-level SPICE for the analog core and run the digital part in an RTL simulator.

And always **check the faster setup against the slow one** on a short run before trusting it.

**Go deeper on this GitHub:** [Introduction to Simulation, "Level 2: Circuits, and What SPICE Does"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/8) · [Introduction to Simulation, "Co-Simulation and Hardware-in-the-Loop"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/23)
