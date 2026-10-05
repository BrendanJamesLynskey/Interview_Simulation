# Simulation and Performance Modelling — Interview Preparation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Subject: Simulation](https://img.shields.io/badge/Subject-Simulation%20and%20Performance%20Modelling-blue)](https://en.wikipedia.org/wiki/Computer_architecture_simulator)
[![Tests](https://github.com/BrendanJamesLynskey/Interview_Simulation/actions/workflows/tests.yml/badge.svg)](https://github.com/BrendanJamesLynskey/Interview_Simulation/actions/workflows/tests.yml)

## Overview

This repository provides interview preparation material for simulation and performance modelling, as practised by computer architects, hardware engineers and the engineers who build simulation frameworks. Every new chip, accelerator or serving system is designed with simulators long before it can be measured, so these roles are expected to explain what a simulator is for, choose the right level of fidelity, build and verify discrete-event models, model workloads, power and area, and report results that survive review.

The material runs from the foundations (why simulate, the fidelity ladder, verification and validation) through the levels of simulation used across engineering, discrete-event simulation, performance and memory-system modelling, LLM and FHE workloads, power, energy and PPA, measurement and statistics, to the engineering of simulators themselves: architecture, speed, honest ports, testing and CI.

Unlike a generic question bank, every answer ends with a **"Go deeper on this GitHub"** line linking the slide, glossary entry, code or recorded result that explains the topic in depth: [Introduction to Simulation](https://brendanjameslynskey.github.io/Introduction_to_Simulation/), the [LLM Inference Simulators](https://github.com/BrendanJamesLynskey/LLM_Hub_Inference_Simulators), [FHE Accelerator Simulators](https://github.com/BrendanJamesLynskey/FHE_Hub_Accelerator_Simulators) and [Simulation Engineering Toolkit](https://github.com/BrendanJamesLynskey/SimEng_Hub_Toolkit) series, their glossaries, and the simulator code repositories. Where an answer quotes a number from those projects, it is quoted as recorded in the project's results file and linked to it.

## Table of Contents

- [01 Foundations](#01-foundations)
- [02 Simulation Levels](#02-simulation-levels)
- [03 Discrete-Event Simulation](#03-discrete-event-simulation)
- [04 Performance Modelling](#04-performance-modelling)
- [05 Workload Modelling](#05-workload-modelling)
- [06 Power, Energy and PPA](#06-power-energy-and-ppa)
- [07 Measurement and Statistics](#07-measurement-and-statistics)
- [08 Simulator Engineering](#08-simulator-engineering)
- [09 Coding Challenges](#09-coding-challenges)
- [10 Quizzes](#10-quizzes)
- [11 Novel Hardware and Optical Inference](#11-novel-hardware-and-optical-inference)
- [How to Use](#how-to-use)
- [Related Repositories](#related-repositories)
- [Contributing](#contributing)

### 01 Foundations

What a simulator is for, how fidelity trades against speed and effort, and how models earn trust.

- [`why_simulate.md`](01_foundations/why_simulate.md) — Simulation vs analysis vs measurement, why simulate rather than prototype, the four jobs of a simulator, which level for exploration vs verification, when a spreadsheet is enough, scoping from the question
- [`fidelity_ladder_and_tradeoffs.md`](01_foundations/fidelity_ladder_and_tradeoffs.md) — Analytical → DES → TLM → cycle-level → RTL → emulation → silicon; the speed–accuracy–effort trade-off
- [`verification_validation_calibration.md`](01_foundations/verification_validation_calibration.md) — Verification vs validation vs calibration, the verification ladder, held-out validation, digital twins

### 02 Simulation Levels

The simulation methods used across engineering, from fields and circuits to whole systems.

- [`physics_and_circuit_simulation.md`](02_simulation_levels/physics_and_circuit_simulation.md) — FDTD, FEM and MoM, the CFL condition, SPICE (MNA, Newton–Raphson, implicit integration, timestep control), stiffness
- [`digital_logic_simulation.md`](02_simulation_levels/digital_logic_simulation.md) — Event-driven vs cycle-based RTL simulation, delta cycles, gate level, emulation and FPGA prototypes
- [`virtual_platforms_monte_carlo_cosim.md`](02_simulation_levels/virtual_platforms_monte_carlo_cosim.md) — ISS and virtual platforms, Monte Carlo and variance reduction, co-simulation, hardware-in-the-loop

### 03 Discrete-Event Simulation

The engine behind most architecture and system simulators.

- [`event_lists_and_determinism.md`](03_discrete_event_simulation/event_lists_and_determinism.md) — Event lists and heaps, simultaneous events and tie-breaking, seeds and reproducibility, time-stepped vs event-driven
- [`simpy_and_process_interaction.md`](03_discrete_event_simulation/simpy_and_process_interaction.md) — Processes as generators, resources and stores, modelling hardware in SimPy, its gotchas and speed limits
- [`parallel_des_and_queueing_checks.md`](03_discrete_event_simulation/parallel_des_and_queueing_checks.md) — Little's law, M/M/1 and M/D/1 checks, operational laws, conservative and optimistic PDES

### 04 Performance Modelling

Bounding, attributing and modelling performance at the architecture level.

- [`roofline_and_bound_attribution.md`](04_performance_modelling/roofline_and_bound_attribution.md) — Operational intensity, ridge points, bound attribution and hot-spots, unfused and fused bounds
- [`modelling_styles_and_systemc_tlm.md`](04_performance_modelling/modelling_styles_and_systemc_tlm.md) — Analytical vs trace- vs execution-driven, SystemC TLM-2.0 LT and AT, the temporal-decoupling quantum, sampling
- [`memory_system_modelling.md`](04_performance_modelling/memory_system_modelling.md) — DRAM organisation and timing, FR-FCFS, address mapping, refresh and tFAW, why "bandwidth × efficiency" fails

### 05 Workload Modelling

Turning real workloads into FLOPs, bytes and traces a simulator can cost.

- [`llm_inference_workloads.md`](05_workload_modelling/llm_inference_workloads.md) — Prefill vs decode, the KV cache, batching, disaggregated serving, TTFT/TPOT/goodput, sizing a cluster
- [`fhe_workloads.md`](05_workload_modelling/fhe_workloads.md) — RNS polynomials and the NTT, key switching, bootstrapping, memory- vs compute-bound FHE accelerators
- [`model_graph_frontends.md`](05_workload_modelling/model_graph_frontends.md) — Counting FLOPs and bytes, PyTorch and ONNX front ends, the meta device, operator coverage

### 06 Power, Energy and PPA

The other two axes of every design decision.

- [`power_and_energy_modelling.md`](06_power_energy_ppa/power_and_energy_modelling.md) — Static and dynamic power, data movement, DVFS, TDP enforcement, energy proportionality, calibration
- [`area_yield_and_pareto.md`](06_power_energy_ppa/area_yield_and_pareto.md) — Area estimation (CACTI, McPAT, Accelergy), dies per wafer, Poisson and Murphy yield, chiplets, perf/W, perf/mm², Pareto fronts

### 07 Measurement and Statistics

Measuring simulators and real systems, and treating simulation output statistically.

- [`profilers_counters_and_benchmarking.md`](07_measurement_and_statistics/profilers_counters_and_benchmarking.md) — Instrumenting vs sampling profilers and their measured overheads, counters and multiplexing, Cachegrind, regression gates
- [`output_statistics.md`](07_measurement_and_statistics/output_statistics.md) — Warm-up deletion, replications and CIs, batch means, common random numbers, percentile pitfalls

### 08 Simulator Engineering

Building simulators that are fast, correct and maintainable.

- [`simulator_architecture_and_specs.md`](08_simulator_engineering/simulator_architecture_and_specs.md) — Workload, hardware model, engine and metrics; traces as contracts; EARS requirements, the V-model, generated traceability
- [`speed_and_honest_ports.md`](08_simulator_engineering/speed_and_honest_ports.md) — Event abstraction, exact fast paths, Rust/PyO3 ports, bit-exact parity and float operation order, the GIL
- [`testing_and_ci.md`](08_simulator_engineering/testing_and_ci.md) — Property-based, golden and mutation testing, CI gates, matrix builds, Jenkins and dependency pitfalls

### 09 Coding Challenges

Six problems, each with a statement, constraints, a worked solution and pytest tests. Two of them reproduce numbers recorded by the simulators on this GitHub.

- [`challenge_01_des_kernel.py`](09_coding_challenges/challenge_01_des_kernel.py) — A minimal discrete-event kernel with deterministic tie-breaking and O(1) cancellation
- [`challenge_02_mm1_queue.py`](09_coding_challenges/challenge_02_mm1_queue.py) — An M/M/1 queue simulated two ways and checked against the analytic mean wait with a confidence interval
- [`challenge_03_roofline_classifier.py`](09_coding_challenges/challenge_03_roofline_classifier.py) — A roofline bound classifier and hot-spot report for an operator list, with a fused lower bound
- [`challenge_04_streaming_percentiles.py`](09_coding_challenges/challenge_04_streaming_percentiles.py) — A mergeable log-bucket percentile sketch with a relative-error guarantee, and why averaging p99s is wrong
- [`challenge_05_prefill_decode_model.py`](09_coding_challenges/challenge_05_prefill_decode_model.py) — A prefill/decode step-time model from model dimensions, reproducing Disaggregated_Inference_Sim's recorded closed form
- [`challenge_06_pareto_front.py`](09_coding_challenges/challenge_06_pareto_front.py) — A Pareto-front filter (general and O(n log n) 2-D), reproducing FHE_Accelerator_Sim's recorded Pareto column

Each challenge has a matching `test_challenge_NN_*.py`. Run them all with:

```bash
python -m pip install pytest
python -m pytest          # from the repository root
```

### 10 Quizzes

Self-assessment quizzes covering the major topic areas.

- [`quiz_foundations_and_levels.md`](10_quizzes/quiz_foundations_and_levels.md) — Why simulate, the fidelity ladder, V&V, field solvers and SPICE, RTL simulation, virtual platforms, Monte Carlo
- [`quiz_des_and_modelling.md`](10_quizzes/quiz_des_and_modelling.md) — Event lists, SimPy, queueing, PDES, roofline, TLM, memory systems, LLM and FHE workloads, front ends
- [`quiz_power_measurement_engineering.md`](10_quizzes/quiz_power_measurement_engineering.md) — Power and energy, yield and PPA, profilers and statistics, ports and parity, testing and CI
- [`quiz_novel_hardware.md`](10_quizzes/quiz_novel_hardware.md) — Fourier optics, optical MACs against transform engines, precision passes, conversion and static energy, mask capacity, heterogeneous pools, break-even analysis, compute in transit

### 11 Novel Hardware and Optical Inference

Modelling a novel engine before it exists, worked through optical computing for LLM inference: the physics and its costs, then the engine inside a disaggregated-serving simulator. Answers quote the [Fourier Optics for Inference](https://github.com/BrendanJamesLynskey/LLM_Hub_Fourier_Optics_Inference) series and Disaggregated_Inference_Sim's recorded results.

- [`fourier_optics_and_optical_compute.md`](11_novel_hardware_and_optical_inference/fourier_optics_and_optical_compute.md) — The lens and the 4f system, the phase problem, optical MACs against transform engines, ENOB and averaging passes, conversion and static energy, mask capacity, integrated photonics, evaluating a proposed engine
- [`optical_inference_system_modelling.md`](11_novel_hardware_and_optical_inference/optical_inference_system_modelling.md) — Where transforms appear in LLM inference, why prefill, heterogeneous pools, adding a transform device to a serving simulator, Amdahl and break-even analysis, compute in transit for the KV hand-off, trusting a model without hardware

## How to Use

This repository is structured as a progressive simulation and performance-modelling course:

1. **Start with the foundations.** Be able to say what question a simulator answers, why a particular level of fidelity fits it, and how you would know the model is right. These come up in every interview for this kind of role.

2. **Know the levels.** Even if you work at the architecture level, interviewers expect you to place your work among circuit, RTL, emulation and virtual-platform simulation, and to know what each throws away.

3. **Master discrete-event simulation.** Event ordering, determinism, SimPy's semantics and queueing checks are the core technical skill for system-level simulator roles.

4. **Model workloads, power and area.** A performance number without the workload's FLOPs and bytes, or without power and area, rarely survives a design review.

5. **Treat output statistically and engineer the simulator properly.** Confidence intervals, honest ports, tests and CI separate a research script from a tool a team can rely on.

6. **Write the code.** Each coding challenge is short enough for an interview and is tested; try them before reading the solutions.

7. **Use the quizzes** to identify weak areas, then follow the "Go deeper on this GitHub" links into the decks and code.

8. **Practise on novel hardware.** Section 11 applies everything above to an engine that does not exist yet (optical computing for LLM inference), including how to reach and defend a negative result.

The system-design questions (for example, sizing the prefill and decode pools of a serving cluster, or building a novel accelerator's first simulator) have structured model answers; practise giving them aloud in about ten minutes.

## Related Repositories

- **[Introduction_to_Simulation](https://github.com/BrendanJamesLynskey/Introduction_to_Simulation)** — An on-ramp deck: every level of simulation in engineering, with measured speeds and an interactive solver demo
- **[LLM_Hub_Inference_Simulators](https://github.com/BrendanJamesLynskey/LLM_Hub_Inference_Simulators)** — Eleven decks on simulating LLM inference hardware and serving, with a glossary
- **[FHE_Hub_Accelerator_Simulators](https://github.com/BrendanJamesLynskey/FHE_Hub_Accelerator_Simulators)** — Five decks taking an FHE accelerator from workload to design-space results
- **[LLM_Hub_Fourier_Optics_Inference](https://github.com/BrendanJamesLynskey/LLM_Hub_Fourier_Optics_Inference)** — Three decks on Fourier optics for disaggregated inference: the physics, where transforms appear, and simulated optical prefill pools
- **[SimEng_Hub_Toolkit](https://github.com/BrendanJamesLynskey/SimEng_Hub_Toolkit)** — Fourteen decks on the engineering around simulators: Rust, SystemC, memory systems, verification, CI, specifications, measurement, PPA and an accelerator model in SimPy end to end
- **[Disaggregated_Inference_Sim](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim)** and **[FHE_Accelerator_Sim](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim)** — The SimPy simulators whose recorded results many answers quote
- **[Interview_Computer_Architecture](https://github.com/BrendanJamesLynskey/Interview_Computer_Architecture)** — Pipelines, out-of-order execution and the memory hierarchy behind the models
- **[Interview_AI_Accelerator_Architecture](https://github.com/BrendanJamesLynskey/Interview_AI_Accelerator_Architecture)** — The accelerator designs these simulators evaluate
- **[Interview_Software_Testing](https://github.com/BrendanJamesLynskey/Interview_Software_Testing)** — Testing practice in general, beyond simulators

## Contributing

Contributions are welcome. Please ensure:

1. Content is technically accurate, and numbers quoted from the linked projects match their recorded results files
2. Code samples run, and coding-challenge solutions keep their tests passing (`python -m pytest`)
3. Every "Go deeper on this GitHub" link resolves to the slide, glossary entry or file it names
4. Questions stay generic: no company-specific interview content

For significant additions, please open an issue first to discuss scope and approach.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
