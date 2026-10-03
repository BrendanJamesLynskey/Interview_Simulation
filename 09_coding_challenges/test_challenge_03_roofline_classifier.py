import math

import pytest

from challenge_03_roofline_classifier import Device, Op, classify, classify_op, fused_lower_bound

DEV = Device(peak_flops=1e12, peak_bw=1e11)
OPS = [Op("matmul", 4e9, 1e8, "matmul"), Op("softmax", 1e7, 4e8, "softmax"),
       Op("add", 1e6, 1e8, "elementwise")]


def test_example():
    s = classify(OPS, DEV)
    assert s["ridge"] == pytest.approx(10.0)
    r = {x.op.name: x for x in s["results"]}
    assert r["matmul"].intensity == pytest.approx(40.0)
    assert r["matmul"].time == pytest.approx(4e-3) and r["matmul"].bound == "compute"
    assert r["softmax"].time == pytest.approx(4e-3) and r["softmax"].bound == "memory"
    assert r["add"].time == pytest.approx(1e-3) and r["add"].bound == "memory"
    assert s["total_time"] == pytest.approx(9e-3)
    assert s["compute_share"] == pytest.approx(4 / 9)
    # tie on time between matmul and softmax is broken by name, deterministically
    assert [h[0] for h in s["hotspots"]] == ["matmul", "softmax", "add"]


def test_ridge_point_classification():
    # exactly on the ridge counts as compute-bound; just below is memory-bound
    assert classify_op(Op("on", 10.0, 1.0), DEV).bound == "compute"
    assert classify_op(Op("below", 9.99, 1.0), DEV).bound == "memory"


def test_zero_bytes_is_compute_bound():
    r = classify_op(Op("regs", 1e6, 0.0), DEV)
    assert r.bound == "compute" and math.isinf(r.intensity)


def test_bad_ops_rejected():
    with pytest.raises(ValueError):
        classify_op(Op("empty", 0.0, 0.0), DEV)
    with pytest.raises(ValueError):
        classify_op(Op("neg", -1.0, 1.0), DEV)


def test_derating_moves_the_ridge():
    # Achievable 55% of FLOP/s and 80% of bandwidth: ridge = 10 * 0.55 / 0.8
    d = Device(1e12, 1e11, flops_eff=0.55, bw_eff=0.8)
    assert d.ridge == pytest.approx(6.875)
    # an op at intensity 8 is memory-bound at peak, compute-bound when derated
    op = Op("mid", 8e9, 1e9)
    assert classify_op(op, DEV).bound == "memory"
    assert classify_op(op, d).bound == "compute"


def test_fused_bound_is_below_unfused_sum():
    s = classify(OPS, DEV)
    lb = fused_lower_bound(OPS, DEV)
    # only the matmul's 1e8 bytes remain; flops 4.011e9 -> 4.011 ms
    assert lb == pytest.approx(4.011e-3)
    assert lb <= s["total_time"]


def test_h100_decode_gemv_is_memory_bound_and_prefill_gemm_compute_bound():
    # H100 SXM datasheet peaks used by Disaggregated_Inference_Sim:
    # 989 TFLOP/s dense BF16, 3.35 TB/s.
    h100 = Device(989e12, 3.35e12)
    d = 4096
    # batch-1 GEMV with a d x d BF16 weight: 2 d^2 FLOPs, 2 d^2 bytes of weight
    gemv = Op("gemv", 2 * d * d, 2 * d * d)
    # 2048-token GEMM with the same weight: weight read once, activations in/out
    t = 2048
    gemm = Op("gemm", 2 * t * d * d, 2 * d * d + 2 * 2 * t * d)
    assert classify_op(gemv, h100).bound == "memory"       # intensity 1
    assert classify_op(gemm, h100).bound == "compute"      # intensity ~ 1000
