"""Checks against Disaggregated_Inference_Sim/examples/results.md, section 1
("Cost-model correction (2026-10-03): closed-form steps"), columns
"GB after", "ms after" and "Bound after". The recorded values are rounded to
three decimals, so the comparison allows half a unit in the last place."""

import pytest

from challenge_05_prefill_decode_model import (GB, LLAMA3_8B, LLAMA3_70B, decode, h100,
                                               kv_capacity_tokens, prefill)

# (label, step, recorded GB, recorded ms, recorded bound)
RECORDED = [
    ("8B decode b=1 ctx 2048, 1xH100", lambda: decode(LLAMA3_8B, h100(1), 1, 2048), 15.278, 6.201, "memory"),
    ("8B decode b=64 ctx 2048, 1xH100", lambda: decode(LLAMA3_8B, h100(1), 64, 2048), 32.198, 12.514, "memory"),
    ("70B decode b=16 ctx 2300, 4xH100", lambda: decode(LLAMA3_70B, h100(4), 16, 2300), 151.068, 14.592, "memory"),
    ("70B decode b=1 ctx 2048, 4xH100", lambda: decode(LLAMA3_70B, h100(4), 1, 2048), 139.675, 13.529, "memory"),
    ("70B prefill 2048, 4xH100", lambda: prefill(LLAMA3_70B, h100(4), [2048]), 139.708, 133.867, "compute"),
    ("8B prefill 2048, 1xH100", lambda: prefill(LLAMA3_8B, h100(1), [2048]), 15.295, 59.033, "compute"),
]


@pytest.mark.parametrize("label,step,gb,ms,bound", RECORDED, ids=[r[0] for r in RECORDED])
def test_reproduces_recorded_closed_form(label, step, gb, ms, bound):
    s = step()
    assert s.nbytes / GB == pytest.approx(gb, abs=0.0005)
    assert s.time * 1e3 == pytest.approx(ms, abs=0.0005)
    assert s.bound == bound


def test_decode_flops_added_by_self_attention():
    # results.md: the correction added 524,288 FLOPs to the 8B batch-1 step
    # (4 * 32 layers * 4096 * 1 extra position) and 33,554,432 at batch 64.
    m = LLAMA3_8B
    assert 4 * m.n_layers * m.d_model * 1 == 524_288
    assert 4 * m.n_layers * m.d_model * 64 == 33_554_432


def test_embedding_table_bytes():
    # Charging the whole input embedding every step costs vocab * d * 2 bytes
    # minus the one row actually read: 1,050,664,960 bytes for Llama-3-8B
    # (Torch_Sim_Frontend/examples/results.md, section 4).
    m = LLAMA3_8B
    assert m.vocab * m.d_model * 2 - m.d_model * 2 == 1_050_664_960


def test_decode_intensity_is_about_the_batch_size():
    for b in (1, 8, 64):
        s = decode(LLAMA3_8B, h100(1), b, 2048)
        assert s.bound == "memory"
        assert s.intensity < 2 * b


def test_prefill_is_far_above_the_ridge():
    inst = h100(1)
    s = prefill(LLAMA3_8B, inst, [2048])
    assert s.intensity > 10 * inst.F / inst.B


def test_kv_capacity():
    # 8B on one 80 GB H100 at 90% use: weights ~16.06 GB resident,
    # 128 KiB of KV per token -> roughly 427k tokens.
    cap = kv_capacity_tokens(LLAMA3_8B, h100(1), 80 * GB)
    assert LLAMA3_8B.kv_bytes_per_token == 131_072
    assert 420_000 < cap < 430_000
    with pytest.raises(ValueError):
        kv_capacity_tokens(LLAMA3_70B, h100(1), 80 * GB)
