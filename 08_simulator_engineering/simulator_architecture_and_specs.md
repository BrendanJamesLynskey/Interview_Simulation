# Simulator Architecture, Specifications and Requirements — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Structuring a simulator (workload, hardware model, engine, metrics), traces as contracts, specifications, EARS requirements, the V-model and traceability
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What are the main components of a well-structured performance simulator?

**Answer:**

Keep four concerns separate, with narrow interfaces between them:

1. **Workload**: what work arrives and what it consists of. A generator (arrival process, size distributions, seeded) or a trace (recorded or produced by a front end).
2. **Hardware model**: the resources (units, memories, links) and a **cost model** that answers "how long and how much energy does this operation take on this resource?".
3. **Engine**: the event list, scheduling and policy logic (batching, routing, arbitration), which asks the cost model for durations.
4. **Metrics and outputs**: timestamps, utilisation, hot-spots, traces, energy, summaries.

Plus **configuration** (one declarative file per experiment, recorded with results) and an **experiment layer** (sweeps, search, replications) on top.

Why: you can replace a roofline cost model with a calibrated table or an RTL-derived cycle model without touching the engine; swap workloads without touching hardware; and test each part on its own.

**Go deeper on this GitHub:** [InfSim 02, "Structuring a Simulator That Lasts"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-09) · [Glossary: cost model](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-costmodel) · [InfSim 05, "Reading the Code"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-09)

### Q2. Why is a trace format a "contract", and what should it contain?

**Answer:**

When a front end (a compiler, a framework tracer, a scheme model) produces work for a simulator, the trace format is the interface between two teams and two codebases. If it changes silently, both sides break or, worse, keep running and produce wrong answers.

A good trace contains:
- **operations** with type, shapes or sizes, and derived FLOPs and bytes (or enough to derive them);
- **operand identities** (which tensor, key or buffer), so the simulator can model reuse and caching;
- **dependencies** (which operations must finish first), rather than timestamps from the machine that produced the trace;
- **metadata**: producer, version, model and configuration, code path (device, attention backend).

Version it, validate it with a schema, and test that every front end produces identical traces for the same input where they should.

**Go deeper on this GitHub:** [FHESim 03, "The Trace: Contract Between Scheme and Hardware"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-03) · [SimEng 10, "One Trace Format, Four Front Ends"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-02) · [Glossary: kernel-level trace](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-trace)

### Q3. What makes a good requirement? Give a bad and a good example for a simulator.

**Answer:**

A good requirement is **necessary, unambiguous, verifiable, singular** (one thing), **feasible** and **traceable** to a need and to a test.

- **Bad:** "The simulator shall be fast and accurate." (Two requirements; neither verifiable.)
- **Good:** "The simulator shall complete a 3,000-request serving run with the default configuration in under 5 seconds on the reference CI machine." (Verifiable by a timed test.)
- **Good:** "When two events have equal time and priority, the simulator shall process them in the order they were scheduled." (Verifiable by a unit test.)
- **Good:** "The simulator shall reproduce the recorded step time of each calibration kernel to within 5%." (Verifiable against a stated data set.)

**Go deeper on this GitHub:** [SimEng 09, "What Makes a Good Requirement"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-02) · [Glossary: requirement quality](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-reqquality)

---

## Intermediate

### Q4. What is EARS, and how do its patterns apply to simulator requirements?

**Answer:**

EARS (the Easy Approach to Requirements Syntax) constrains requirements to a few templates that remove common ambiguity:

| Pattern | Template | Simulator example |
|---|---|---|
| Ubiquitous | The \<system\> shall \<response\>. | The simulator shall record the seed with every result file. |
| Event-driven | **When** \<trigger\>, the \<system\> shall … | When a request completes, the simulator shall record its first-token and completion times. |
| State-driven | **While** \<state\>, the \<system\> shall … | While the KV memory of a decode instance is full, the router shall not admit new requests to it. |
| Unwanted behaviour | **If** \<condition\>, **then** the \<system\> shall … | If a configuration places weights that exceed device memory, then the simulator shall exit with an error naming the instance. |
| Optional feature | **Where** \<feature\>, the \<system\> shall … | Where DVFS is enabled, the simulator shall lower the compute clock on memory-bound steps. |

Each requirement gets an ID, and tests reference the IDs they verify.

**Go deeper on this GitHub:** [SimEng 09, "EARS: Five Patterns for Requirements"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-03) · [SimEng 09, "Interactive: Check a Requirement"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-04) · [Glossary: EARS](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-ears)

### Q5. What non-functional requirements matter for a simulator?

**Answer:**

- **Performance**: run time for reference workloads; memory footprint; scaling with workload size.
- **Determinism and reproducibility**: same configuration and seed → identical outputs; results regenerable from the repository.
- **Accuracy**: stated tolerance against named references, per quantity and range.
- **Portability**: supported platforms and versions; behaviour identical across them (or documented).
- **Usability**: configuration validation with clear errors; documented outputs.
- **Maintainability and extensibility**: adding a cost model or a policy without touching the engine.
- **Interoperability**: trace formats, framework front ends, output formats consumable by other tools.

Each should be verifiable: a benchmark in CI for performance, a golden run for determinism, a validation table for accuracy.

**Go deeper on this GitHub:** [SimEng 09, "Functional and Non-Functional Requirements for Simulators"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-05) · [Glossary: non-functional requirements for simulators](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-nfr)

### Q6. Explain the V-model and where a simulator fits in it.

**Answer:**

The V-model pairs each level of specification (left side, going down) with a level of verification (right side, going up):

- system requirements ↔ system validation / acceptance;
- architecture ↔ integration testing;
- component design ↔ component testing;
- implementation at the bottom.

**Verification** checks each level against its specification ("built right"); **validation** checks the whole against the stakeholders' needs ("right thing").

A simulator appears twice:
1. As a **product** with its own V: requirements (EARS), design, tests at each level, validation against measurements.
2. As a **tool** in the hardware's V: the architecture model is the executable specification on the left side, and later the reference against which RTL and silicon are verified on the right.

**Go deeper on this GitHub:** [SimEng 09, "The V-Model"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-07) · [Glossary: the V-model; verification and validation](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-vmodel)

---

## Advanced

### Q7. How would you produce a traceability matrix that stays correct as the code changes?

**Answer:**

Generate it, do not maintain it by hand:

1. Give every requirement an ID in the specification (e.g. `SF-07`).
2. Tag tests with the IDs they verify (a pytest marker, a docstring convention, or a naming scheme).
3. In CI, run the tests with a JUnit XML report, then a script joins requirement IDs to test results: for each requirement, which tests verify it and whether they passed **in this build**.
4. Publish the matrix as a build artefact; **fail the build** if a requirement has no test, or a test references an unknown ID.

This turns traceability from a document into a check. On this GitHub, generating the matrix for a simulator front end exposed a requirement that no test covered: exactly the gap a hand-written matrix tends to hide.

**Go deeper on this GitHub:** [SimEng 09, "Traceability, Generated From the Test Run"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-08) · [SimEng 08, "Traceability: Requirement, Work Item, Test, Build"](https://brendanjameslynskey.github.io/SimEng_08_Jira_and_Engineering_Metrics/#slide-08) · [Glossary: traceability matrix](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-traceability)

### Q8. System design: write the outline of a specification for a new accelerator performance simulator.

**Answer (a structured model answer):**

1. **Purpose and scope**: the decisions it supports; what it explicitly does not model.
2. **Stakeholders and use cases**: architects (design-space sweeps), software (performance estimates for compiler choices), product (capacity planning).
3. **Inputs**: workload formats (trace schema, front ends), hardware configuration schema, experiment definitions.
4. **Outputs**: metrics with definitions (latency percentiles by method, utilisation, energy), trace format, report format.
5. **Functional requirements** (EARS), grouped: workload, engine semantics (ordering, ties), each hardware component, power, metrics.
6. **Non-functional requirements**: speed targets, determinism, accuracy tolerances against named references, platforms.
7. **Assumptions and abstractions**: what each component leaves out, and why.
8. **Verification plan**: unit, closed-form, property, differential and golden tests; CI gates.
9. **Validation plan**: references, data sets, held-out cases, tolerance, how results are reported.
10. **Change control**: versioning of the trace format and of results; how re-baselining is approved.

**Go deeper on this GitHub:** [SimEng 09, "Template 1: a Simulator Specification"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-09) · [SimEng 09, "Template 2: a Test Plan"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-10) · [SimEng 09, "Why a Simulator Needs a Specification"](https://brendanjameslynskey.github.io/SimEng_09_Specs_Requirements_Test_Plans/#slide-01)

### Q9. Two teams want different things from the same simulator: architects want detail, software wants speed. How do you architect for both?

**Answer:**

- **One engine, pluggable fidelity**: the cost model is an interface; provide a fast analytic implementation and a detailed one (calibrated tables, cycle models), selectable per component.
- **Multi-fidelity workflow**: sweep widely with the fast model, then confirm the shortlisted designs with the detailed one. Check that both agree on the shortlist's ranking.
- **Exact fast paths**: optimisations that change speed but not results (macro-stepping, incremental state), guarded by tests that compare outputs bit for bit with the slow path.
- **Shared configuration and outputs**, so results from both fidelities are directly comparable.
- **Clear ownership** of each model and its validation status, visible in outputs ("this number came from the analytic model, validated to ±X% on Y").

The anti-pattern is two diverging simulators, one per team, that disagree and that nobody can reconcile.

**Go deeper on this GitHub:** [InfSim 08, "Smarter Experiments: Multi-Fidelity, Search, Surrogates"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-10) · [Glossary: multi-fidelity search and bisection](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-multifidelity)
