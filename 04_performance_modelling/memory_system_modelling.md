# Memory-System Modelling — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** DRAM organisation and timing, row hits and conflicts, FR-FCFS scheduling, address mapping, refresh and tFAW, why "bandwidth × efficiency" fails
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. Describe how a DRAM (or HBM) device is organised, from channel to row.

**Answer:**

From the controller down:

- **Channel**: an independent command/data bus with its own controller. HBM stacks have many channels (and pseudo-channels within them); a DDR DIMM has one or two.
- **Rank**: a set of chips that respond together on a channel.
- **Bank group** (DDR4 and later, HBM): banks grouped to share some internal resources; back-to-back accesses to the *same* bank group must wait longer (tCCD_L) than to *different* groups (tCCD_S).
- **Bank**: an independent array with its own **row buffer** (sense amplifiers).
- **Row** (page): activating a row copies it into the bank's row buffer; columns are then read or written from the buffer.
- **Column / burst**: each read or write transfers a burst (e.g. BL = 8 beats) from the open row.

Parallelism comes from many banks and channels working at once; locality comes from hitting the open row.

**Go deeper on this GitHub:** [SimEng 04, "How DRAM Is Organised"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-02) · [Glossary: channels, ranks, bank groups, banks and rows](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-dramorg)

### Q2. What are row hits, misses and conflicts, and what do they cost?

**Answer:**

For a read to a bank:
- **Row hit**: the requested row is already open. Cost: column read latency, `CL + BL/2` cycles.
- **Row miss (bank closed)**: no row open. Activate first: `tRCD + CL + BL/2`.
- **Row conflict**: a different row is open. Precharge (close) it, activate the new one, read: `tRP + tRCD + CL + BL/2`.

Conflicts are expensive in latency and, worse, in **bandwidth**: while a bank precharges and activates, it transfers nothing. Streaming access patterns get many hits; random patterns get conflicts (open-page policy) or misses (closed-page policy).

On this GitHub's DDR4 model: row hit 26 cycles, closed bank 48, conflict 70, each equal to its closed form.

**Go deeper on this GitHub:** [SimEng 04, "Row Hits, Misses and Conflicts"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-04) · [Glossary: row hits, misses and conflicts](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-rowhit) · [the recorded checks (section 2)](https://github.com/BrendanJamesLynskey/Memory_System_Sim/blob/main/examples/results.md)

### Q3. What does a memory controller's scheduler do, and what is FR-FCFS?

**Answer:**

The controller holds a queue of pending requests and decides which DRAM command to issue each cycle, subject to every timing constraint.

- **FCFS**: serve requests strictly in arrival order. Simple, fair, but one row conflict at the head blocks hits behind it.
- **FR-FCFS (first-ready, first-come first-served)**: among commands that can issue now, prefer **row hits** (column commands to open rows), then the oldest request. This reorders requests to exploit the open rows and greatly raises bandwidth for mixed streams.

Trade-offs: FR-FCFS can starve requests to rows that are never "ready" (a stream of hits keeps winning), so real controllers add age caps or fairness rules. Write handling (batching writes to reduce read/write turnarounds) and the **page policy** (leave rows open, or close after each access) interact with it.

On this GitHub's HBM model, one pseudo-channel streaming with 1 in 3 writes reaches 0.147 of peak under FCFS but 0.804 under FR-FCFS (open page).

**Go deeper on this GitHub:** [SimEng 04, "Scheduling and Page Policy"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-05) · [Glossary: FCFS and FR-FCFS scheduling](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-frfcfs) · [Glossary: open and closed page policy](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-pagepolicy)

---

## Intermediate

### Q4. Why does "bandwidth × efficiency" fail as a memory model?

**Answer:**

A flat derating (say, 80% of peak) assumes the achieved fraction of bandwidth is a property of the memory. It is a property of the memory **and** the traffic **and** the controller:

- **Access pattern**: streaming vs random vs strided changes the row-hit rate and bank parallelism.
- **Read/write mix**: bus turnarounds cost cycles.
- **Address mapping**: which address bits select channel, bank and row decides whether strides spread across banks or pile onto one.
- **Scheduler and page policy**.
- **Load**: queueing latency grows sharply near saturation.
- **Refresh** and the **four-activate window**.

Measured on this GitHub's HBM model (one pseudo-channel, FR-FCFS, open page), achieved efficiency ranged from **0.10 to 0.93** across six access patterns. A single derating factor is right for at most one traffic mix, one mapping and one load.

And it matters for conclusions: in the FHE accelerator model, a flat 0.7 derating predicted a bootstrap at 19.26 ms where the command-level model gave 15.31 ms (and an FCFS controller 23.70 ms).

**Go deeper on this GitHub:** [SimEng 04, "Why "Bandwidth × Efficiency" Fails"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-01) · [Glossary: bandwidth × efficiency](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-beff) · [FHE results (section 20)](https://github.com/BrendanJamesLynskey/FHE_Accelerator_Sim/blob/main/examples/results.md)

### Q5. Explain address mapping and why XOR bank hashing helps.

**Answer:**

The controller maps each physical address to (channel, rank, bank group, bank, row, column) by slicing bits. Different orders suit different patterns:

- putting **column bits low** keeps sequential addresses in one open row (good locality for streams);
- putting **channel and bank bits low** spreads consecutive blocks over banks (good parallelism);
- a **power-of-two stride** (e.g. one row, or 8 KiB) can map every access to the same bank, serialising on row conflicts.

**XOR hashing** computes the bank index as the XOR of the normal bank bits with some row bits. Accesses that would collide in one bank (same bank bits, different rows) get spread across banks, while sequential streams keep their behaviour.

On this GitHub's DDR4 channel, a stride of exactly one row achieved 0.054 of peak under a plain mapping and 0.456 with XOR hashing; streaming was unaffected (0.998 vs 0.996).

**Go deeper on this GitHub:** [SimEng 04, "Address Mapping"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-06) · [Glossary: address mapping and XOR bank hashing](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-addrmap)

### Q6. What are refresh and tFAW, and how much do they cost?

**Answer:**

- **Refresh**: DRAM cells leak, so every row must be refreshed periodically. The controller issues a refresh command every **tREFI**; each takes **tRFC** during which the rank (or bank) is unavailable. The bandwidth lost is roughly **tRFC / tREFI**. On this GitHub's HBM model, refresh cost a long stream about 9.1% (with tRFC/tREFI = 9.0%).
- **tFAW (four-activate window)**: at most four row activations may occur in any tFAW window (a power-delivery limit). Random traffic with closed pages needs an activate per access, so its bandwidth is capped near **4 × (BL/2) / tFAW**. On this GitHub's models that bound is 0.471 (DDR4) and 0.308 (HBM) of peak, and the simulated random closed-page reads reached 0.457 and 0.304.

Both are invisible to a flat bandwidth model, and both matter most for exactly the random, bank-hopping traffic that accelerators with large lookup tables generate.

**Go deeper on this GitHub:** [SimEng 04, "Refresh and the Four-Activate Window"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-07) · [Glossary: refresh](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-refresh) · [Glossary: the four-activate window](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-tfaw)

---

## Advanced

### Q7. How would you validate a new DRAM model?

**Answer:**

1. **Closed-form latency checks**: hit, miss and conflict latencies equal their formulas exactly.
2. **Throughput bounds**: streaming near peak minus refresh; same-bank-next-row at `(BL/2)/tRC`; random closed-page under the tFAW bound.
3. **An independent protocol checker**: replay the model's command trace through a separate checker that enforces every timing constraint. It catches illegal command sequences the model itself would not notice. (On this GitHub, property-based tests with such a checker as the oracle found a real bug: the write-to-read turnaround was tracked only for the most recent write.)
4. **Cross-check against an established simulator** (DRAMsim3, Ramulator) with identical traces, timing and mapping. Expect close agreement on simple patterns and investigate large differences on complex ones (scheduler details).
5. **Load–latency curves**: latency flat at low load, rising sharply near saturation, as queueing theory predicts.

On this GitHub's cross-check against DRAMsim3, 9 of 14 pattern-and-mapping cases agreed within 3%; streams with writes and interleaved streams differed by 8–16%, and four interleaved streams by 54% under one mapping. Those are scheduler-policy differences, documented rather than hidden.

**Go deeper on this GitHub:** [SimEng 04, "How We Know the Model Is Right"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-10) · [SimEng 04, "Cross-Checked Against DRAMsim3"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-11) · [Glossary: independent protocol checker](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-protocheck)

### Q8. An accelerator streams 4 MiB chunks of keys from HBM. How would you model the memory without a full command-level simulator in the loop?

**Answer:**

Use the command-level model **offline** to calibrate a cheap per-chunk model:

1. Run the command-level simulator for the access patterns the accelerator generates (chunk size, read after read, write after read, read after write), with the real mapping and scheduler.
2. Tabulate the achieved efficiency per pattern and chunk size.
3. In the system simulator, cost each chunk as `bytes / (peak bandwidth × efficiency(pattern, size))`.

On this GitHub, the HBM model gives 0.902 efficiency for a 4 MiB read after a read and 0.883 for 1 MiB with the default mapping and FR-FCFS, but around 0.54 with a mapping that keeps a row's bursts in one bank group, and 0.56 with FCFS. Plugged into the FHE simulator this way, a bootstrap took 15.31 ms, against 13.94 ms at peak bandwidth. A flat 0.9 derating happened to land close for that configuration (15.33 ms), but nothing in a flat factor predicts the FCFS controller (23.70 ms) or the bank-group-unfriendly mapping (24.43 ms).

The table must be **regenerated** when the mapping, scheduler or traffic pattern changes.

**Go deeper on this GitHub:** [SimEng 04, "Plugging It Into the FHE Simulator"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-12) · [memory results (section 8)](https://github.com/BrendanJamesLynskey/Memory_System_Sim/blob/main/examples/results.md)

### Q9. Load–latency: sketch and explain the curve for streaming and random traffic on one HBM pseudo-channel.

**Answer:**

Latency against offered load (as a fraction of peak) is flat at low load (just the access latency), then rises steeply as the channel approaches its **saturation throughput** for that pattern, like any queue.

The key point is that **saturation is pattern-dependent**:
- **Streaming** saturates near the top (around 0.9 of peak). On this GitHub's model, mean latency was 37 ns at 10% load and 247 ns at 90%, with the p99 rising from 365 ns to 557 ns.
- **Random** traffic saturates near 0.27 of peak (row conflicts, tFAW), so at only 30% offered load its mean latency had already reached 1,250 ns.

So "this memory supports 800 GB/s" is meaningless without the pattern: random traffic at 30% of nominal bandwidth can already be past saturation.

**Go deeper on this GitHub:** [SimEng 04, "Load and Latency"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-09) · [SimEng 04, "Interactive: Patterns, Policies and Load"](https://brendanjameslynskey.github.io/SimEng_04_Memory_Systems_DRAM_HBM/#slide-08) · [memory results (section 5)](https://github.com/BrendanJamesLynskey/Memory_System_Sim/blob/main/examples/results.md)
