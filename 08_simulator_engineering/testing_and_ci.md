# Testing and CI for Simulators — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Test strategy, property-based testing, golden tests, mutation testing versus coverage, CI pipelines, exact/speed/drift gates, Jenkins and GitHub Actions pitfalls
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What makes testing a simulator different from testing ordinary application code?

**Answer:**

- **No simple oracle**: for most outputs (p99 latency under a complex workload) nobody knows the right answer. Tests must use other oracles: closed-form cases, invariants, a second implementation, recorded runs.
- **Numerical output**: results are floats; "close enough" must be defined, or the simulator must be deterministic so outputs can be compared exactly.
- **Wrong but plausible**: a bug often produces a believable number, not a crash. Bugs surface as bad decisions months later.
- **Behaviour changes are expected**: model improvements legitimately change outputs, so tests must distinguish intended changes (re-baselined deliberately) from accidental ones.
- **Performance is a feature**: a change that makes the simulator 3× slower may break the studies that depend on it.

**Go deeper on this GitHub:** [SimEng 06, "A Test Strategy for a Simulator"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-01) · [SimEng 07, "Why Simulators Need CI More Than Most Code"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-01)

### Q2. What is property-based testing, and what properties suit a simulator?

**Answer:**

Instead of hand-picking inputs, you state a **property** that must hold for all inputs, and a framework (Hypothesis in Python, proptest in Rust) generates many random inputs, checks the property, and **shrinks** any failing input to a minimal example.

Simulator properties:
- **Conservation**: every request that arrives completes, is rejected, or is still in flight; bytes in equal bytes out.
- **Causality and ordering**: no event before its cause; timestamps non-decreasing per request.
- **Resource limits**: no resource ever over-subscribed (capacity, power cap, memory).
- **Monotonicity** where the model implies it: more bandwidth never increases a memory-bound step's time.
- **Bounds**: simulated latency ≥ analytic lower bound.
- **Metamorphic relations**: doubling every arrival time and every service time doubles every latency.
- **Model ranges**: yields in (0, 1], probabilities sum to 1.

Real bugs found this way on this GitHub include a DRAM controller violating a write-to-read turnaround, and a yield formula that cancelled to zero for tiny dies.

**Go deeper on this GitHub:** [SimEng 06, "Hypothesis: Properties and Shrinking"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-04) · [Glossary: property-based testing (Hypothesis)](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-hypothesis) · [Glossary: shrinking](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-shrinking)

### Q3. What are golden tests, and what is the danger in "re-blessing"?

**Answer:**

A **golden test** runs a reviewed configuration and compares the output with a stored reference ("golden") file. Any difference fails the test. For deterministic simulators the comparison can be exact.

They catch **unintended** behaviour changes anywhere in the model, cheaply. But when a model change is **intended**, the golden files must be updated ("re-blessed").

The danger: re-blessing becomes routine. Someone runs the update command, the diff is huge, and nobody reads it, so a bug slips in alongside the intended change. Mitigations:
- keep golden outputs **small and readable** (summaries, not megabytes of trace);
- review golden diffs like code; explain each changed number in the commit;
- separate golden updates into their own commits;
- keep several narrow golden tests rather than one huge one, so a change affects only the expected ones.

**Go deeper on this GitHub:** [SimEng 06, "Golden Tests and Re-Blessing"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-06) · [Glossary: golden tests and re-blessing](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-golden)

---

## Intermediate

### Q4. Why is 100% line coverage not enough? What does mutation testing add?

**Answer:**

Coverage says which lines **ran** during tests, not whether any test would **notice** if they were wrong. A test that calls a function and checks nothing gives full coverage.

**Mutation testing** makes small deliberate changes (mutants) to the code (`>=` to `>`, `+` to `-`, a constant changed) and runs the tests against each. A mutant that no test fails ("survives") marks code the tests do not really check. The **mutation score** is the fraction of mutants killed.

Measured on this GitHub, on a small cost function: a medium-strength suite reached 100% line and branch coverage but killed only 67% of mutants; the survivors included `tc >= tm` changed to `tc > tm` and the step overhead's sign flipped. A strong suite killed 100%.

Costs: mutation testing is slow (it reruns tests per mutant); some mutants are **equivalent** (they do not change behaviour) and can never be killed. Run it periodically or on changed files, not on every commit.

**Go deeper on this GitHub:** [SimEng 06, "Mutation Testing"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-07) · [SimEng 06, "Interactive: Mutation Score versus Coverage"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-08) · [Glossary: mutation testing](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-mutation) · [Glossary: equivalent mutants](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-equivalent)

### Q5. Design a CI pipeline for a simulator. What stages and gates does it have?

**Answer:**

1. **Lint and type check** (fast feedback).
2. **Unit and property tests**, parallelised.
3. **Closed-form and golden tests** (exact comparisons for deterministic outputs).
4. **Differential tests** against other implementations (ports, a SystemC model, a JavaScript port used by an interactive demo).
5. **Performance gate**: a benchmark compared with the baseline, with margins chosen from measured noise (or deterministic instruction counts).
6. **Drift gate on key results**: headline numbers (e.g. a reference configuration's latency) must not change without an explicit re-baseline.
7. **Nightly**: long regressions, parameter sweeps (matrix builds), mutation testing, coverage reports.
8. **Artefacts**: test reports (JUnit XML), coverage, generated results tables, traceability matrix.

Three kinds of gate: **exact** (bit-identical outputs), **speed** (run time within a margin) and **drift** (a result within a tolerance of its recorded value).

**Go deeper on this GitHub:** [SimEng 07, "Gating on Performance and Accuracy"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-08) · [SimEng 06, "Running It All in CI"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-13) · [Glossary: exact, speed and drift gates](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-gatekinds)

### Q6. Your simulator is used by other repositories that install it from git. What CI problems should you anticipate?

**Answer:**

- **Dependents must be re-run** when the dependency changes: a passing build in the simulator's repository says nothing about the repositories that import it. Trigger their workflows after pushing (or schedule them).
- **Stale installs**: a reused virtual environment may keep an old `package @ git+…` install even after the upstream changes; pip considers the requirement satisfied. Force-reinstall the git dependency in CI.
- **Pinning**: pin to a commit or tag for reproducibility; update deliberately.
- **Ignored fixtures**: test data excluded by a broad `.gitignore` pattern (e.g. `*.json`) works locally and fails in CI. Add explicit exceptions for fixture paths.
- **Stale reports**: a reused workspace can leave old JUnit or coverage files; a failed build can then publish the previous run's passing results. Delete reports at the start of every build.

Each of these happened on this GitHub's simulator repositories and is now handled in their pipelines.

**Go deeper on this GitHub:** [SimEng 07, "The Real Runs"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-11) · [SimEng 07, "Test and Coverage Reports"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-06) · [Glossary: JUnit XML and Cobertura reports](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-junit)

---

## Advanced

### Q7. A Jenkins pipeline's first builds fail with paths like `null/tools/bin`. What is going on?

**Answer:**

In a declarative pipeline, the `parameters {}` directive is evaluated when the pipeline is defined, **before** any agent is allocated. A default value built from the agent's environment, such as `"${env.HOME}/tools"`, sees no `HOME` there and becomes the literal string `null/tools`. The null then flows into `environment {}` and into every `sh` step that uses it.

Fix: do not compute paths from the agent's environment in `parameters`. Use a plain default (or an empty string), and resolve paths **inside the step's shell** on the agent (e.g. `"${HOME}/tools"` evaluated by `sh`).

On this GitHub this broke an RTL co-simulation job's first three builds. Probes on a local Jenkins found that the often-repeated claims "parameters are null on a job's first build" and "a PATH set in `environment` doesn't reach `sh`" did **not** reproduce on the version tested; the `env`-in-`parameters` default did. (Behaviour can differ between Jenkins versions; test on yours.)

**Go deeper on this GitHub:** [SimEng 07, "Nightly Regressions and Parameters"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-07) · [Introduction to Jenkins](https://brendanjameslynskey.github.io/Introduction_to_Jenkins/) · [Glossary: nightly regressions and build parameters](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-nightly)

### Q8. How would you use a matrix build to run a parameter sweep in CI, and what are the risks?

**Answer:**

A matrix build expands one pipeline definition over the combinations of several axes (e.g. workload × hardware configuration × seed), running each cell as a separate parallel job. For a simulator it gives a regression sweep with no extra scripting: each cell runs the simulator and checks its headline result against a recorded value.

Risks and mitigations:
- **Combinatorial explosion**: 5 axes of 4 values is 1,024 jobs. Exclude combinations that do not matter; run the full matrix nightly and a small subset per commit.
- **Shared resources**: parallel cells on one machine compete for memory and CPU; benchmarks in the matrix become noisy. Separate correctness cells from timing cells, and cap parallelism.
- **Result aggregation**: collect per-cell results into one report with a stable order, so failures are attributable.
- **Flaky cells**: one nondeterministic cell fails the matrix randomly. Make simulations deterministic and quarantine flaky tests rather than retrying blindly.

**Go deeper on this GitHub:** [SimEng 07, "Matrix Builds: a Parameter Sweep in CI"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-04) · [Glossary: matrix builds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-matrixbuild) · [Glossary: flaky tests](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-flaky)

### Q9. How do you verify a cycle-accurate or RTL-calibrated part of a simulator in CI without slowing everything down?

**Answer:**

- **Split by cost**: fast unit and golden tests on every commit; RTL simulations (Verilator, cocotb) on changes to the RTL or the calibration code, and nightly.
- **Cache compiled models**: Verilator builds are expensive; cache them by a hash of the RTL and flags.
- **Check the fitted cycle model against fresh RTL runs** on a few sizes each night: if the RTL changed and the cycle model did not, the gate fails and the calibration is re-run.
- **Pin toolchain versions** (simulator, cocotb) and record them in results; versions change scheduling and supported features.
- **Bound the test time**: small sizes and short campaigns in CI, with the full campaign recorded separately.

**Go deeper on this GitHub:** [SimEng 05, "Verilator, Icarus and CI for RTL"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-10) · [SimEng 06, "cocotb: Python Testbenches for RTL"](https://brendanjameslynskey.github.io/SimEng_06_Testing_Frameworks/#slide-12) · [Glossary: calibrating a simulator from RTL](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-rtlcalib)
