# Deriving Workloads from Model Graphs — Interview Questions

**Subject:** Simulation and Performance Modelling
**Topic:** Counting FLOPs and bytes, PyTorch and ONNX front ends (dispatch tracing, torch.export, torch.compile backends, ONNX shape inference), the meta device, operator coverage
**Difficulty tiers:** Fundamentals / Intermediate / Advanced

---

## Fundamentals

### Q1. How do you count the FLOPs of a matrix multiplication and of a transformer forward pass?

**Answer:**

A matrix multiply of an (m × k) by a (k × n) matrix does m·n dot products of length k: **2mkn FLOPs** (one multiply and one add per term).

For a decoder-only transformer, each token multiplies every matmul weight once, so the weight matmuls cost about **2 × (matmul parameters) FLOPs per token**. Attention adds the score and value products, QKᵀ and AV: about 4 × d_model FLOPs per layer per attended position (2·d for each), so their cost grows with context length.

Rules of thumb: prefill of T tokens ≈ 2·P·T + attention; one decode step at batch b ≈ 2·P·b + attention over the cached context.

**Common mistakes:** counting a multiply-add as one FLOP (some vendors do, so state your convention); forgetting the LM head (vocab × d_model, large for big vocabularies); counting the input embedding as a matmul (it is a lookup).

**Go deeper on this GitHub:** [InfSim 03, "Counting FLOPs"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-02) · [Glossary: FLOP and byte counting](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-flops)

### Q2. How do you count the bytes a step moves, and why is that harder than counting FLOPs?

**Answer:**

FLOPs are a property of the math. **Bytes depend on the implementation**: what is fused, what stays on chip, what is a view versus a copy, where precision is converted.

A useful hierarchy:
- **Essential bytes**: weights read once per step, the KV cache read (decode) or written (prefill), inputs and outputs. A lower bound for any implementation.
- **Unfused bytes**: every operator reads its inputs from memory and writes its outputs. An upper bound for a naive implementation.

On this GitHub, the same Llama-3-8B prefill captured through four front ends agreed exactly on matmul FLOPs (32,938,104,455,168, apart from one constant-folded 262,144-FLOP matmul in ONNX) but reported between 169.10 and 333.97 GB of unfused traffic. The arithmetic is a property of the model; the memory traffic is a property of the decomposition.

**Go deeper on this GitHub:** [InfSim 03, "Counting Bytes"](https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-03) · [SimEng 10, "Four Front Ends, One Answer"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-08) · [the recorded comparison (section 3)](https://github.com/BrendanJamesLynskey/Torch_Sim_Frontend/blob/main/examples/results.md)

### Q3. What is a simulator "front end", and why does a simulator need one?

**Answer:**

A front end turns a real model (a PyTorch module, an ONNX file, a compiler's IR) into the simulator's workload format: an **operator trace** with shapes, FLOPs, bytes and dependencies.

Without one, workloads are hand-written closed forms. Those are fine for a few well-known models, but they drift from reality (new architectures, framework changes) and hide bookkeeping errors. A front end gives:
- **real models**, including ones nobody has hand-modelled;
- **cross-checks** on the closed forms (on this GitHub, an operator trace found two errors in a hand-written cost model, which were then fixed);
- **operator coverage**: which operators the target hardware supports natively and which fall back to a host.

**Go deeper on this GitHub:** [SimEng 10, "Why a Simulator Needs a Front End"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-01) · [InfSim 09, "Why Integration Is Half the Job"](https://brendanjameslynskey.github.io/InfSim_09_Framework_Integration/#slide-01) · [Glossary: operator trace](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-optrace)

---

## Intermediate

### Q4. Compare four ways to capture a PyTorch model's operators.

**Answer:**

| Route | How | Strengths | Caveats |
|---|---|---|---|
| **Dispatch interception** | A `TorchDispatchMode` sees every ATen operator as it runs | Exact, sees what actually executes, simple | Runs the model (eagerly), one path through control flow |
| **torch.export** | Captures a full graph (FX, Core ATen IR) ahead of time | Whole graph with shapes; standard IR | Decompositions can differ from eager; export may need code changes |
| **torch.compile backend** | A custom backend receives the FX graph(s) Dynamo captures | Fits the compile flow; graph breaks are visible | May split into several graphs |
| **ONNX export + shape inference** | Export the model; walk the ONNX graph with inferred shapes | Framework-neutral, standard operator set | Export coverage; some ops become several (Transpose, Expand materialise) |

All can run on the **meta device** (or fake tensors), which carry shapes and dtypes but no data, so a model of tens of billions of parameters can be traced on a laptop without loading weights.

**Go deeper on this GitHub:** [SimEng 10, "One Trace Format, Four Front Ends"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-02) · [InfSim 09, "Three Ways to Drive a Simulator"](https://brendanjameslynskey.github.io/InfSim_09_Framework_Integration/#slide-02) · [Glossary: torch.export and FX graphs](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-export) · [Glossary: dispatch interception and the meta device](https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-dispatch)

### Q5. What is the meta device, and what can go wrong when you trace with it?

**Answer:**

The meta device holds tensors with shape, dtype and stride but **no storage**. Operators on meta tensors compute output metadata only. Tracing a model on it is fast and needs no memory for weights.

What can go wrong:
- **Code paths differ by device.** Libraries choose kernels by device: on this GitHub, a model traced on meta took a "math" attention path that materialised the full score matrix, while fake CPU tensors took the fused attention path. Unfused prefill traffic was 214.35 GB on meta versus 70.09 GB on fake CPU tensors, for the same model.
- **Data-dependent control flow** cannot be evaluated (no values), so it fails or takes a default branch.
- **Some operators lack meta implementations**.

**Fake tensors** (fake tensors pretending to live on a real device) are a middle ground: still no data, but the same dispatch decisions as the real device. Decide which device's code path you want to model, and record it with the trace.

**Go deeper on this GitHub:** [SimEng 10, "Meta or Fake Tensors: What the Trace Means"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-05) · [SimEng 10, "Real Models, No Weights: the Meta Device"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-03) · [Glossary: fake tensors and traced code paths](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-faketensor)

### Q6. How would you check that a front end's FLOP count is right?

**Answer:**

Three independent references:

1. **The closed form**: 2 × matmul parameters × tokens plus attention; compare term by term.
2. **Another front end**: four routes should agree exactly on matmul FLOPs (they compute the same math).
3. **PyTorch's own counter** (`FlopCounterMode`), with its conventions understood (which operators it counts, e.g. it counts matmul-like operators and attention, not element-wise operations).

Any difference must be **explained**, not tolerated. On this GitHub, the trace and the closed form differed in decode matmul FLOPs by 128 (a rotary-frequency matmul the closed form did not model) and in decode weight bytes by 532,480 (the RMSNorm weights), both documented. Earlier, the same comparison exposed two real closed-form errors: the whole input embedding table charged every step (1.05 GB too much for Llama-3-8B), and a missing attention-to-self term.

**Go deeper on this GitHub:** [SimEng 10, "Checking the Trace Against the Closed Form"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-09) · [Glossary: PyTorch's FLOP counter](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-flopcounter) · [the recorded cross-check (section 4)](https://github.com/BrendanJamesLynskey/Torch_Sim_Frontend/blob/main/examples/results.md)

---

## Advanced

### Q7. What is operator coverage, and why is it an engineering metric for novel hardware?

**Answer:**

Operator coverage is the fraction of a model's work that the target hardware (or its compiler) supports natively. Measure it three ways, because they tell different stories:
- by **operator count** (how many distinct ops must be implemented),
- by **operator instances** (how many calls),
- by **FLOPs or time** (how much of the work).

A matmul engine may cover over 99% of FLOPs but a small fraction of operator types: softmax, norms, rotary embeddings, gathers and reshapes fall back to a host processor. If the fallback ops are cheap in FLOPs but expensive in **data movement** to and from the host, they dominate the step time.

So coverage belongs in the simulator's outputs: which operators fall back, what the round trips cost, and which few operators to implement next for the biggest gain.

**Go deeper on this GitHub:** [SimEng 10, "Operator Coverage as an Engineering Metric"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-12) · [SimEng 10, "Interactive: Operator Coverage, Counted Three Ways"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-11) · [Glossary: operator coverage](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-opcoverage)

### Q8. How would you integrate a performance simulator with a compiler stack such as MLIR, or an FHE compiler such as HEIR?

**Answer:**

Pick the **lowest level that still has the information the simulator needs**, and read it directly:

- For ML: a dialect after fusion and tiling decisions (so the trace reflects what the hardware will run), but before lowering to instructions loses the operator structure.
- For FHE: HEIR lowers programs to a CKKS dialect where each homomorphic operation, its level and its key are explicit. A front end can walk that IR and emit the simulator's kernel trace. On this GitHub, a HEIR front end reproduced HEIR's own OpenFHE run of a small network exactly in rotations (55), keys (41) and relinearisations (2).

Then use the simulator **as a cost model inside the compiler**: the compiler queries it (or a fast surrogate fitted to it) to choose between transformations. Keep the trace format stable and versioned; it is the contract between the two teams.

**Go deeper on this GitHub:** [InfSim 09, "MLIR in One Slide"](https://brendanjameslynskey.github.io/InfSim_09_Framework_Integration/#slide-08) · [InfSim 09, "HEIR: An MLIR Compiler for FHE"](https://brendanjameslynskey.github.io/InfSim_09_Framework_Integration/#slide-10) · [FHESim 03, "A HEIR Front End: Real Programs"](https://brendanjameslynskey.github.io/FHESim_03_Simulating_an_FHE_Accelerator/#slide-12) · [Glossary: HEIR](https://brendanjameslynskey.github.io/FHE_Hub_Accelerator_Simulators/#g-heir)

### Q9. A colleague's trace of a model shows 4.3 GB per decode step in `clone` operations. Is the model inefficient, the hardware, or the trace?

**Answer:**

Probably the **framework code path captured by the trace**, not the model or the hardware.

On this GitHub, exactly this appeared in a meta-device trace of Llama-3-8B: `aten.clone` moved 4.30 GB per decode step because the attention implementation's `repeat_kv` materialised the 8 KV heads as 32 to feed a non-GQA math attention path. The fused attention path (seen with fake CPU tensors) reads the cache once through native grouped-query attention, and the clone disappears: 15.84 GB per step against 25.02 GB.

The lesson for simulation:
- **Name the code path** a trace represents (device, attention backend, framework version).
- **Separate essential from incidental traffic** before drawing hardware conclusions.
- If the deployment will use a fused kernel, model that, and keep the unfused trace as an upper bound.

**Go deeper on this GitHub:** [SimEng 10, "Costing the Trace"](https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-10) · [Glossary: unfused and ideal-fusion bounds](https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-fusionbound) · [the recorded traffic table (section 5)](https://github.com/BrendanJamesLynskey/Torch_Sim_Frontend/blob/main/examples/results.md)
