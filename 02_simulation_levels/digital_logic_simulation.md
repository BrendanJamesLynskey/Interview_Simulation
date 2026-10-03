# Digital Logic Simulation — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Event-driven and cycle-based RTL simulation, delta cycles, gate-level simulation, emulation and FPGA prototyping
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What is the difference between event-driven and cycle-based RTL simulation?

**Answer:**

**Event-driven** simulation keeps a time-ordered queue (a "time wheel") of signal changes. When a signal changes, only the processes sensitive to it are re-evaluated, possibly scheduling more changes. It supports four-state values (0, 1, X, Z), arbitrary `#` delays and every testbench construct. Icarus Verilog, GHDL and the commercial simulators work this way.

**Cycle-based** simulation evaluates the whole design once per clock edge as compiled code. It assumes synchronous logic, usually two-state values and no timing inside a cycle. Verilator compiles SystemVerilog into a C++ model this way (and since version 5 also accepts timing constructs with `--timing`).

Trade-offs:

| | Event-driven | Cycle-based |
|---|---|---|
| Speed on large synchronous designs | Lower | Much higher |
| X-propagation, delays, full testbench language | Yes | Limited |
| Start-up cost | Low (interpret or quick compile) | Compile to C++ and then to machine code |

Measured on this GitHub, same NTT core: Icarus 6,416 cycles per second (0.03 s compile), Verilator 837,883 cycles per second (4.38 s compile): **131×** faster once compiled.

**Go deeper on this GitHub:** [Introduction to Simulation, "Level 3: Digital Logic, Event-Driven and Cycle-Based"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/10) · [Glossary: Verilator and Icarus Verilog](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-verilator)

### Q2. What is a delta cycle, and why does it exist?

**Answer:**

A delta cycle is a zero-duration simulation step. Within one simulated time instant, the kernel repeats:

1. **evaluate** every process that is ready to run (they read current signal values and schedule updates);
2. **update** signals with the scheduled values;
3. any process sensitive to a changed signal becomes ready, and another delta cycle begins,

until nothing changes. Only then does simulated time advance.

It exists to make concurrent hardware deterministic on a sequential computer. Without it, the result of `a <= b; b <= a;` (a swap in one clock) would depend on which process the simulator ran first. With separate evaluate and update phases, every process sees the *old* values in the evaluate phase, as real flip-flops sampling on the same edge do.

VHDL and SystemC use delta cycles explicitly; SystemVerilog's scheduling regions (active, inactive, non-blocking assignment, and so on) serve the same purpose.

**Common mistake:** using blocking assignments (`=`) for sequential logic in Verilog, which writes during the evaluate phase and creates order-dependent races between `always` blocks.

**Go deeper on this GitHub:** [SimEng 03, "The SystemC Kernel: Processes, Events, Delta Cycles"](https://brendanjameslynskey.github.io/SimEng_03_SystemC_TLM_Models/#slide-03) · [Glossary: the SystemC kernel and delta cycles](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-sckernel)

### Q3. What is gate-level simulation for, if RTL simulation already passes?

**Answer:**

Gate-level simulation runs the synthesised (and possibly placed-and-routed) netlist, optionally with timing back-annotated from static timing analysis (an SDF file). It catches things RTL simulation cannot:

- **synthesis/RTL mismatches**: `full_case`/`parallel_case` pragmas, incomplete sensitivity lists, X-optimism in RTL `if` statements that synthesis resolves differently;
- **reset and initialisation problems**: X-propagation from uninitialised flops that RTL hid;
- **timing-related issues** in specific paths, multicycle and false-path constraints that are wrong, and asynchronous interfaces (with SDF timing);
- **power-aware behaviour** of the actual cells, and switching activity for power analysis.

It is much slower than RTL simulation, so it is run on targeted tests, not the full regression. Static timing analysis and formal equivalence checking do most of the timing and equivalence work.

**Go deeper on this GitHub:** [Introduction to Simulation, "Gate Level, Emulation and FPGA Prototypes"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/11)

---

## Intermediate

### Q4. Compare RTL simulation, emulation and FPGA prototyping.

**Answer:**

| | RTL simulation | Emulation | FPGA prototype |
|---|---|---|---|
| Speed (indicative) | Hz–kHz on a full SoC | Around MHz | Tens of MHz |
| Visibility | Every signal, any time | Very good (built-in trace) | Limited (embedded logic analysers) |
| Bring-up effort | Low | Medium (compile to the emulator) | High (partitioning, clocking, memories) |
| Change turnaround | Minutes | Hours | Hours to a day |
| Typical use | Block and subsystem verification | Full-chip verification, firmware, OS boot | Software development, real interfaces, long runs |

**Rule of thumb:** move up when the test needs more cycles than the lower platform can deliver in a day (booting an OS is billions of cycles), and stay down when you need visibility and quick turnaround.

**Go deeper on this GitHub:** [Introduction to Simulation, "Gate Level, Emulation and FPGA Prototypes"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/11) · [InfSim 08, "Accelerating the RTL End"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-13)

### Q5. Your RTL regression takes 14 hours. How do you speed it up?

**Answer:**

1. **Measure first:** which tests take the time, and is it compile, elaboration, simulation or the testbench (Python cocotb or class-based testbenches can dominate)?
2. **Switch simulator class where possible:** a compiled cycle-based simulator (Verilator) for synchronous designs, keeping an event-driven simulator for tests that need four-state or timing.
3. **Parallelise across tests and seeds**: tests are independent; CI matrix builds or a farm.
4. **Compile once, run many**: reuse the compiled model across tests via plusargs or parameters.
5. **Trim the tests**: remove redundant tests found by coverage ranking; shorten long tests that only re-check what earlier cycles covered.
6. **Lower the testbench cost**: fewer Python round-trips per cycle (transaction-level driving), avoid printing.
7. **Waveform dumping off by default**, on only for failing reruns.
8. **Move very long tests to emulation**.

**Go deeper on this GitHub:** [SimEng 05, "Verilator, Icarus and CI for RTL"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-10) · [SimEng 07, "Matrix Builds: a Parameter Sweep in CI"](https://brendanjameslynskey.github.io/SimEng_07_Jenkins_for_Simulation_Teams/#slide-04)

### Q6. What is X-propagation, and why do cycle-based simulators struggle with it?

**Answer:**

X means "unknown". In four-state simulation, an uninitialised flop, a bus with conflicting drivers or an out-of-range array read produces X, and X spreads through logic that depends on it. This exposes reset bugs and uninitialised state.

The subtlety is **X-optimism**: an RTL `if (sel)` with `sel = X` takes the `else` branch in Verilog semantics, hiding the unknown; real hardware might take either branch. Gate-level simulation can be pessimistic in the opposite direction.

Two-state cycle-based simulators represent each bit as 0 or 1, so X cannot exist. They typically initialise state to zero or to random values. Randomised initialisation across seeds is a practical substitute: if results depend on the initial values, there is a reset bug.

**Go deeper on this GitHub:** [Introduction to Simulation, "Level 3: Digital Logic, Event-Driven and Cycle-Based"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/10)

---

## Advanced

### Q7. How would you verify a datapath block (for example a modular multiplier) against a software golden model?

**Answer:**

1. **Bit-accurate golden model** in Python or C++: same widths, same algorithm (e.g. Barrett reduction with the same correction steps), so outputs can be compared exactly, not just mathematically.
2. **Testbench with transactors**: a driver that turns transactions into pin activity (ready/valid), and a monitor that turns pin activity back into transactions.
3. **Scoreboard**: compares each output transaction against the golden model's prediction.
4. **Stimulus**: directed corner cases (zero, maximum, the modulus minus one) plus **constrained-random** stimulus biased towards the corners that matter.
5. **Functional coverage with crosses**: not just "did input X occur" but "did the second correction step occur *and* was its effect observable at the output". A wrong correction can be masked downstream.
6. **Seeded bugs**: deliberately break the RTL and confirm the testbench catches it.

On this GitHub, a dropped Barrett correction step escaped a uniform-random campaign (4,000 transactions, 53% functional coverage) and was caught by a constrained-random campaign that closed the observability crosses. Line and toggle coverage were no help: uniform stimulus already reached 100% of lines and branches.

**Go deeper on this GitHub:** [SimEng 05, "A Seeded Bug: Caught or Escaped"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-09) · [SimEng 05, "Functional Coverage, and the Crosses That Matter"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-07) · [Glossary: coverage crosses and observability](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-crosscov)

### Q8. Why might Verilator and an event-driven simulator give different results for the same RTL, and what do you do?

**Answer:**

Legitimate causes:
- **Races** in the RTL or testbench: order-dependent code (blocking assignments across `always` blocks, reading and writing the same variable in one time step). The language allows different orders; different simulators pick different ones.
- **Four-state vs two-state**: X in one becomes 0 or random in the other.
- **Timing constructs**: delays inside a cycle, `#0`, or event controls that a cycle-based simulator handles differently.
- **Unsupported or differently-supported features**, especially in the testbench.

What to do: treat a difference as a bug report against the RTL first. Lint (Verilator's lint is strict and useful), remove races, make reset explicit, and only then blame a simulator. Running two simulators in CI is itself a cheap race detector.

**Go deeper on this GitHub:** [SimEng 05, "Verilator, Icarus and CI for RTL"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-10) · [Introduction to Simulation, "Level 3: Digital Logic, Event-Driven and Cycle-Based"](https://brendanjameslynskey.github.io/Introduction_to_Simulation/#/10)

### Q9. How do you turn RTL simulation into input for a faster performance model?

**Answer:**

- **Cycle counts:** run the RTL on representative sizes and fit a cycle model (often closed form). On this GitHub an NTT core's measured compute cycles fit `log2(n) (n/2P + 6)` exactly at every measured size and lane count; the system simulator then uses that as the efficiency of a core of P lanes.
- **Switching activity:** toggle counts per operation as a power proxy, data-dependent (on this GitHub, small operands toggled 0.74× as many register bits as uniform random ones).
- **Latency and throughput limits** of interfaces: back-pressure behaviour, pipeline depth.

Then **close the loop**: when the RTL changes, re-run the extraction and the system model's results. A model calibrated from last quarter's RTL can silently diverge from this quarter's design.

**Go deeper on this GitHub:** [SimEng 05, "RTL Cycle Counts and a Cycle Model"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-11) · [SimEng 05, "Switching Activity as a Power Proxy"](https://brendanjameslynskey.github.io/SimEng_05_Verification_Bridge_cocotb/#slide-13) · [the recorded RTL results](https://github.com/BrendanJamesLynskey/RTL_CoSim_NTT/blob/main/examples/results.md)
