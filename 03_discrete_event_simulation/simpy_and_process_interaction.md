# SimPy and Process-Interaction Modelling — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Processes as generators, resources, stores and containers, modelling hardware in SimPy, common SimPy mistakes
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. What is the process-interaction world view, and how does SimPy implement it?

**Answer:**

There are two classic ways to write a DES:

- **Event scheduling:** you write handlers for each event type ("on arrival: if server free, start service and schedule departure").
- **Process interaction:** you write the life of each entity as a sequential story ("arrive, wait for the server, hold it for the service time, release it, leave"); the framework turns the waits into events.

SimPy implements process interaction with **Python generators**. A process is a generator function; each `yield` hands an event to the environment and suspends the process until that event fires. The environment holds the event list and resumes processes in time order.

```python
import simpy

def customer(env, name, arrival, server, service):
    yield env.timeout(arrival)         # arrive
    arrive = env.now
    with server.request() as req:      # ask for the resource
        yield req                      # wait until granted
        wait = env.now - arrive
        yield env.timeout(service)     # hold it for the service time
    print(f"{name} waited {wait} and left at {env.now}")

env = simpy.Environment()
server = simpy.Resource(env, capacity=1)
for i, t in enumerate([0, 0, 1]):
    env.process(customer(env, f"c{i}", t, server, service=2))
env.run()
# c0 waited 0 and left at 2
# c1 waited 2 and left at 4
# c2 waited 3 and left at 6
```

**Go deeper on this GitHub:** [InfSim 02, "Step 3 — Processes: Generators as Coroutines"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-05) · [Glossary: process interaction and coroutines](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-process) · [Glossary: SimPy](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-simpy)

### Q2. Name SimPy's resource types and what each models.

**Answer:**

| Type | Models | Hardware example |
|---|---|---|
| `Resource(capacity=n)` | n identical servers, FIFO queue | n identical compute units |
| `PriorityResource` | Same, queue ordered by priority | A scheduler favouring latency-critical work |
| `PreemptiveResource` | Higher priority can interrupt the current user | Preemptive scheduling |
| `Container(capacity, init)` | A continuous or countable level (`put`/`get` amounts) | Buffer occupancy, KV-cache memory, energy |
| `Store` | A FIFO queue of Python objects | A hardware FIFO of packets or commands |
| `FilterStore` | A store where `get` takes the first item matching a predicate | Out-of-order completion, tagged responses |
| `PriorityStore` | Items come out in priority order | A priority queue of requests |

Back-pressure falls out naturally: a `Store` with finite capacity makes `put` wait when full, so a fast producer is throttled by a slow consumer.

**Go deeper on this GitHub:** [InfSim 02, "SimPy: The Whole Vocabulary on One Page"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-06) · [Glossary: resources, stores, containers and back-pressure](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-backpressure)

### Q3. What happens if you forget the `yield` in front of `env.timeout(...)`?

**Answer:**

The timeout event is created and scheduled, but **the process does not wait for it**. Execution continues immediately at the same simulated time, so the "delay" silently disappears. If the generator has no other `yield` at all, it is not a generator, and `env.process` raises an error. The silent version is the dangerous one.

```python
import simpy

env = simpy.Environment()
log = []

def worker(env):
    env.timeout(5)            # BUG: no yield, nothing waits
    log.append(env.now)       # still at time 0
    yield env.timeout(1)

env.process(worker(env))
env.run()
assert log == [0]
```

Related mistakes: requesting a resource without releasing it (use the `with` form), and calling a sub-process as a plain function instead of `yield env.process(sub(env))`.

**Go deeper on this GitHub:** [InfSim 02, "Time, Ordering and Determinism Pitfalls"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-10)

---

## Intermediate

### Q4. Does `env.run(until=10)` process an event scheduled at exactly t = 10?

**Answer:**

No. In SimPy 4, `run(until=t)` stops **before** processing events at time t; the clock ends at t and those events remain pending for a later `run`.

```python
import simpy

env = simpy.Environment()
log = []

def p(env, name, d):
    yield env.timeout(d)
    log.append((env.now, name))

env.process(p(env, "at10", 10))
env.process(p(env, "at5", 5))
env.run(until=10)
assert log == [(5, "at5")] and env.now == 10
env.run(until=11)
assert log == [(5, "at5"), (10, "at10")]
```

**Why it matters:** if you collect statistics "up to t = 10" and an event at exactly 10 completes a request, it is not counted. Fence-post issues like this make two implementations of "the same" simulator disagree, so define the convention and test it.

**Go deeper on this GitHub:** [InfSim 02, "SimPy: The Whole Vocabulary on One Page"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-06)

### Q5. How would you model a shared link (or memory channel) in SimPy: hold it, or share it?

**Answer:**

Two common abstractions:

- **FCFS hold:** the link is a `Resource(capacity=1)`; each transfer requests it, holds it for `bytes / bandwidth`, releases. Simple and fast. Transfers are serialised: a small transfer waits behind a large one.
- **Processor sharing:** all active transfers progress simultaneously, each at `bandwidth / n_active`. Closer to how a network or memory system multiplexes many streams. Harder: whenever a transfer starts or ends, the remaining time of every active transfer changes, so pending completion events must be recomputed (or modelled with a fluid approximation).

They agree on total throughput (the link is busy for the same total time) but differ in per-transfer latency: under FCFS a small transfer behind a large one sees the full delay; under sharing it finishes sooner.

**Choose** by the question: if small latency-critical transfers mix with bulk ones, sharing (or a priority policy) matters. If transfers are similar in size, FCFS is fine and much cheaper.

**Go deeper on this GitHub:** [InfSim 02, "Shared Bandwidth: Hold the Link or Share It?"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-08) · [Glossary: FCFS hold versus processor sharing](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-sharing)

### Q6. How do you model a batching server (e.g. an LLM decode engine) in SimPy?

**Answer:**

Not as one process per request each holding a resource, but as **one engine process** that loops over steps:

1. Collect the running batch (new requests join between steps: continuous batching).
2. Ask the cost model for the step time given the batch size and total context.
3. `yield env.timeout(step_time)`.
4. Give every running request one token; requests that finish leave; signal their completion events.
5. If the batch is empty, wait on an event that the admission logic triggers when a request arrives.

Requests are passive: they wait on their own completion event (or a `Store`). This keeps the event count proportional to **steps**, not to tokens × requests, which matters a great deal for speed.

On this GitHub a serving simulator built this way processes one event per batch step: 37,099 batch-step events for a run where per-token events would be 505,895 (14×) and per-layer events 2,967,920 (80×).

**Go deeper on this GitHub:** [InfSim 02, "Modelling Hardware in SimPy"](https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-07) · [InfSim 08, "Fewer Events: Choose the Abstraction"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-03) · [Glossary: event abstraction](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-abstraction)

---

## Advanced

### Q7. What are the main performance limits of SimPy, and how do you work around them?

**Answer:**

SimPy is pure Python: every event allocates objects, goes through a heap, and resumes a generator. Throughput is typically tens to around a hundred thousand events per second (on this GitHub, about 85–100k events per second on an old desktop CPU).

Workarounds, roughly in order of payoff:
1. **Fewer events:** model at a coarser grain (a batch step, not a token; a transfer, not a packet). Usually the biggest win.
2. **Exact macro-stepping:** when nothing can change for k steps (no arrivals, no completions), advance k steps in one event with the same arithmetic. On this GitHub, an exact fast path doubled speed with bit-identical outputs.
3. **Cheaper events:** incremental state (keep running sums instead of recomputing over the batch), avoid probes and per-event logging.
4. **Parallel runs:** independent replications and sweep points in separate processes (SimPy holds the GIL, so threads do not help).
5. **Port the hot core** to a compiled language (Rust or C++) behind a Python interface, with differential tests against the SimPy original. On this GitHub, a Rust port ran 71–74× faster than SimPy.

**Go deeper on this GitHub:** [InfSim 08, "Exact Macro-Stepping"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-05) · [InfSim 08, "Measured: What Each Technique Bought"](https://brendanjameslynskey.github.io/InfSim_08_Accelerating_Simulators/#slide-06) · [the Rust port's speed table](https://github.com/BrendanJamesLynskey/Rust_DES_Kernel/blob/main/examples/results.md)

### Q8. Explain a subtle SimPy ordering behaviour that can make a port disagree with the original.

**Answer:**

Several:

- **Same-time events are processed in scheduling order**, with a small number of internal priority levels (process initialisation and interrupts are "urgent" and go first). A port that orders simultaneous events differently will diverge.
- **Resource grants happen through events.** When a user releases a resource and another is waiting, the grant is an event scheduled at the current time, not an immediate hand-over; code that runs in between (other processes at the same instant) can observe the intermediate state.
- **`Store` puts and gets** are matched when triggered, in the order the requests were made; a get waiting on an empty store is satisfied by the next put, at the same timestamp but one or more events later.

A port that wants bit-exact agreement must reproduce these rules, or both sides must be refactored to make the ordering explicit and model-defined. The FHE simulator on this GitHub keeps a mini-SimPy inside its JavaScript port for exactly this reason.

**Go deeper on this GitHub:** [SimEng 01, "From SimPy Processes to State Machines"](https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-07) · [SimEng 02, "Bit-Exact: The Parity Checklist"](https://brendanjameslynskey.github.io/SimEng_02_Rust_Python_PyO3/#slide-06)

### Q9. System design: model a disaggregated LLM serving cluster in SimPy. What are the components and events?

**Answer (a structured model answer):**

**Components:**
- **Workload generator**: a process producing requests (arrival time, prompt length, output length) from a seeded stream or a recorded trace.
- **Router / admission control**: assigns each request to a prefill instance (least loaded, round robin), and later to a decode instance; rejects or queues when KV memory is full.
- **Prefill instances**: each an engine process that batches waiting prompts and runs one prefill step per batch, cost from a roofline cost model.
- **KV-transfer link**: a resource (FCFS) or shared-bandwidth model; transfer time = KV bytes / link bandwidth + latency.
- **Decode instances**: engine processes running continuous batching; per-step cost depends on batch size and total context; KV memory as a `Container`.
- **Metrics collector**: timestamps per request (arrival, first token, each token, completion), utilisation per resource, power and energy.

**Events:** arrival, prefill batch start and end, KV-transfer start and end, decode-step end, request completion.

**Outputs:** TTFT and TPOT distributions, goodput (requests meeting both SLOs), utilisation, hot-spot attribution, energy per token.

**Validation:** low-load runs against the cost model's step times; an M/D/1-style check of a single queue; capacity against the analytic bound; and conservation (every request completes exactly once).

**Go deeper on this GitHub:** [InfSim 05, "The Simulator: Model and Assumptions"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-05) · [InfSim 05, "Reading the Code"](https://brendanjameslynskey.github.io/InfSim_05_Disaggregated_Inference/#slide-09) · [Disaggregated_Inference_Sim](https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim)
