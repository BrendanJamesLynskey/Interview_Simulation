# Quiz — Discrete-Event Simulation and Performance Modelling

**Subject:** Simulation and Performance Modelling
**Topics covered:** Event lists and determinism, SimPy, queueing checks, parallel DES, the roofline, TLM, memory systems, LLM and FHE workloads, model front ends
**Format:** Multiple-choice and short-answer questions. Answers at the end.

---

### Q1. A DES kernel stores `(time, callback)` tuples in Python's `heapq`. What goes wrong when two events share a time, and how do you fix it?

---

### Q2. Which key gives a fully deterministic event order?

a) (time)
b) (time, priority)
c) (time, priority, insertion sequence number)
d) (time, id(callback))

---

### Q3. In SimPy 4, does `env.run(until=10)` process an event scheduled at exactly t = 10?

---

### Q4. A SimPy process contains `env.timeout(5)` without `yield` (and other `yield` statements elsewhere). What happens?

a) A `TypeError` is raised
b) The process waits 5 time units
c) The timeout is scheduled but the process does not wait for it
d) The simulation deadlocks

---

### Q5. State Little's law and one way to use it to check a simulator.

---

### Q6. For an M/M/1 queue with ρ = 0.9 and μ = 1, the mean wait in queue is:

a) 0.9
b) 1
c) 9
d) 10

---

### Q7. Deterministic service (M/D/1) instead of exponential (M/M/1), at the same ρ, changes the mean queueing delay by:

a) No change
b) Halves it
c) Doubles it
d) Removes it entirely

---

### Q8. In conservative parallel DES, what is "lookahead", and why does small lookahead hurt?

---

### Q9. A device has 1,000 TFLOP/s and 4 TB/s. What is its ridge point, and is an operator with 50 FLOP/byte compute- or memory-bound on it?

---

### Q10. In SystemC TLM-2.0, which interface and protocol does an approximately timed model use?

a) `b_transport` with a delay argument
b) `nb_transport_fw/bw` with the four-phase base protocol
c) The debug transport interface
d) DMI only

---

### Q11. Increasing the global quantum in a loosely timed model generally:

a) Slows it down and improves accuracy
b) Speeds it up and may reduce timing accuracy of interactions
c) Has no effect on speed
d) Makes it cycle-accurate

---

### Q12. Give the DRAM read latency, in timing parameters, for a row hit, a closed bank and a row conflict.

---

### Q13. Why is "bandwidth × efficiency" an unreliable memory model?

---

### Q14. LLM decode at batch size 1 in BF16 has arithmetic intensity of roughly:

a) 0.1 FLOP/byte
b) 1 FLOP/byte
c) 100 FLOP/byte
d) 2,000 FLOP/byte

---

### Q15. Compute the KV-cache bytes per token for a model with 32 layers, 8 KV heads, head dimension 128, in BF16.

---

### Q16. On a memory-bound FHE accelerator, which change is most likely to reduce bootstrap latency?

a) Doubling the NTT units
b) Reducing key traffic (e.g. Min-KS, seeded keys)
c) Raising the compute clock
d) Adding MAC lanes

---

### Q17. Two PyTorch front ends agree exactly on a model's matmul FLOPs but differ by 2× in bytes moved. Is one of them wrong?

---

## Answers

**A1.** On equal times `heapq` compares the second element, the callbacks. Functions are not orderable, so it raises `TypeError`; if the payload were orderable, ties would be broken by an arbitrary property of the payload. Fix: key on `(time, priority, seq)` with a global insertion counter, and keep the payload out of the comparison.

**A2.** (c). Only a unique sequence number makes the key a total order independent of payloads and heap layout.

**A3.** No. `run(until=t)` stops before processing events at t; they remain pending for a later run.

**A4.** (c). The timeout event is created and scheduled, but nothing waits on it, so the delay silently disappears.

**A5.** L = λW: mean number in the system equals throughput times mean time in the system. Measure all three independently at a boundary (queue, engine, whole system) and check they agree within statistical error; a mismatch signals double-counting, lost requests or wrong timestamps.

**A6.** (c). W_q = ρ / (μ − λ) = 0.9 / 0.1 = 9.

**A7.** (b). By Pollaczek–Khinchine, W_q ∝ (1 + C_s²); C_s² is 1 for exponential and 0 for deterministic service.

**A8.** A guaranteed minimum delay before a logical process can affect another. It lets neighbours safely advance up to that horizon. With small lookahead, processes synchronise (null messages) almost every step, and the synchronisation overhead can exceed the useful work.

**A9.** Ridge = 1,000e12 / 4e12 = 250 FLOP/byte. At 50 FLOP/byte the operator is memory-bound (attainable 4e12 × 50 = 200 TFLOP/s).

**A10.** (b). LT models use `b_transport`.

**A11.** (b). Fewer synchronisations, so faster; interactions between initiators can be seen late or out of order. On this GitHub's model, a quantum up to 1 µs kept the end time exact; 10 µs to 1 ms made it 0.8–3.6% late.

**A12.** Hit: CL + BL/2. Closed bank: tRCD + CL + BL/2. Conflict: tRP + tRCD + CL + BL/2.

**A13.** The achieved fraction of peak bandwidth depends on access pattern, read/write mix, address mapping, scheduler, page policy, load, refresh and tFAW. On this GitHub's HBM model it ranged from 0.10 to 0.93 across six patterns with one controller.

**A14.** (b). Each 2-byte weight is read once and used for 2 FLOPs per token, so intensity ≈ batch size (about 1.1 including KV traffic in this GitHub's recorded example).

**A15.** 2 (K and V) × 32 × 8 × 128 × 2 bytes = 131,072 bytes (128 KiB) per token.

**A16.** (b). When HBM is the bottleneck, reducing traffic helps; extra compute sits idle. (On a compute-starved design, the same techniques can make things slower because they add compute.)

**A17.** Not necessarily. FLOPs are a property of the math; bytes depend on the decomposition (fusion, which ops are views versus copies, where precision is converted) and on the code path traced (e.g. a math attention path versus a fused one). Name the code path, and separate essential from incidental traffic.
