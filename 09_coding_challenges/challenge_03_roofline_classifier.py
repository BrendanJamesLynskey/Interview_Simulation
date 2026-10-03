"""
=============================================================================
Challenge 03: A Roofline Bound Classifier for an Operator List
=============================================================================

PROBLEM STATEMENT
-----------------
You are given the operators of one forward pass (from a framework trace),
each with its FLOP count and the bytes it moves to and from main memory,
and a device described by its peak FLOP/s and peak memory bandwidth.

Write `classify(ops, device)` that returns, for every operator:
    - arithmetic (operational) intensity  I = flops / bytes
    - its roofline time  t = max(flops / F, bytes / B)
    - its bound: "compute" if flops / F >= bytes / B, else "memory"
and a summary with:
    - the device's ridge point  F / B  (FLOP per byte)
    - the total time (operators run back to back, no overlap between them)
    - the share of the total time spent in compute-bound operators
    - the top-k hot-spot operators by time

Then answer: why is the summed per-operator time an upper bound on what a
fused implementation could achieve, and what is the matching lower bound?

EXAMPLE
-------
    device: F = 1000 GFLOP/s, B = 100 GB/s  -> ridge = 10 FLOP/byte
    ops: matmul  4e9 FLOP, 1e8 B  -> I = 40,  t = 4.0 ms, compute
         softmax 1e7 FLOP, 4e8 B  -> I = 0.025, t = 4.0 ms, memory
         add     1e6 FLOP, 1e8 B  -> I = 0.01, t = 1.0 ms, memory
    total 9.0 ms; compute-bound share 4/9 = 44%

CONSTRAINTS
-----------
    flops >= 0, bytes >= 0, not both zero. Up to 10^5 operators.
    An operator with zero bytes is compute-bound with infinite intensity.

PITFALLS TO DISCUSS
-------------------
    - Using peak rather than achievable F and B (derate with measured
      efficiencies, e.g. MFU and MBU) moves the ridge point.
    - Bytes depend on what is fused and what is a view: the same model gives
      different byte counts through different front ends.
    - The roofline gives a bound per operator, not a schedule: overlap,
      launch overhead and dependency stalls are outside it.

Go deeper on this GitHub:
    InfSim 03, "The Roofline":
      https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-04
    SimEng 10, "Costing the Trace":
      https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-10
    Glossary, roofline and unfused/ideal-fusion bounds:
      https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-roofline
      https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-fusionbound
=============================================================================
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Op:
    name: str
    flops: float
    nbytes: float
    kind: str = "other"      # e.g. "matmul", "elementwise"


@dataclass(frozen=True)
class Device:
    peak_flops: float        # FLOP/s
    peak_bw: float           # bytes/s
    flops_eff: float = 1.0   # achievable fraction of peak (MFU-like)
    bw_eff: float = 1.0      # achievable fraction of peak (MBU-like)

    @property
    def F(self) -> float:
        return self.peak_flops * self.flops_eff

    @property
    def B(self) -> float:
        return self.peak_bw * self.bw_eff

    @property
    def ridge(self) -> float:
        return self.F / self.B


@dataclass(frozen=True)
class OpResult:
    op: Op
    intensity: float
    time: float
    bound: str


# =============================================================================
# SOLUTION
# =============================================================================
# Per operator: two times, take the larger. Ties go to "compute" (the op sits
# exactly on the ridge). Summing assumes the operators do not overlap, which
# is what a stream of dependent kernels on one device does.
#
# Fused lower bound: if a perfect fusion kept every intermediate on chip,
# only some operators would touch memory (e.g. matmuls reading weights).
# Then  t >= max(total_flops / F, essential_bytes / B), one roofline for the
# whole graph. The truth lies between that and the unfused sum.
# O(n log k) for the top-k; O(n) otherwise.
# =============================================================================

def classify_op(op: Op, dev: Device) -> OpResult:
    if op.flops < 0 or op.nbytes < 0 or (op.flops == 0 and op.nbytes == 0):
        raise ValueError(f"bad operator {op}")
    tc, tm = op.flops / dev.F, op.nbytes / dev.B
    intensity = math.inf if op.nbytes == 0 else op.flops / op.nbytes
    return OpResult(op, intensity, max(tc, tm), "compute" if tc >= tm else "memory")


def classify(ops: list[Op], dev: Device, top_k: int = 3) -> dict:
    results = [classify_op(op, dev) for op in ops]
    total = math.fsum(r.time for r in results)
    compute_time = math.fsum(r.time for r in results if r.bound == "compute")
    hot = sorted(results, key=lambda r: (-r.time, r.op.name))[:top_k]
    return {
        "ridge": dev.ridge,
        "results": results,
        "total_time": total,
        "compute_share": compute_time / total if total else 0.0,
        "hotspots": [(r.op.name, r.time, r.bound) for r in hot],
    }


def fused_lower_bound(ops: list[Op], dev: Device,
                      memory_kinds: frozenset[str] = frozenset({"matmul", "gather"})) -> float:
    """One roofline over the whole graph, counting only the bytes that even an
    ideally fused implementation must move (operators of `memory_kinds`)."""
    flops = math.fsum(op.flops for op in ops)
    nbytes = math.fsum(op.nbytes for op in ops if op.kind in memory_kinds)
    return max(flops / dev.F, nbytes / dev.B)


if __name__ == "__main__":
    dev = Device(peak_flops=1e12, peak_bw=1e11)
    ops = [Op("matmul", 4e9, 1e8, "matmul"), Op("softmax", 1e7, 4e8, "softmax"),
           Op("add", 1e6, 1e8, "elementwise")]
    s = classify(ops, dev)
    for r in s["results"]:
        print(f"{r.op.name:8s} I={r.intensity:8.3f}  t={r.time*1e3:.2f} ms  {r.bound}")
    print(f"total {s['total_time']*1e3:.2f} ms, compute share {s['compute_share']:.0%}, "
          f"fused bound {fused_lower_bound(ops, dev)*1e3:.2f} ms")
