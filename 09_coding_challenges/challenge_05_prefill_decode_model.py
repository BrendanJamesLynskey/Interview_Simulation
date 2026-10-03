"""
=============================================================================
Challenge 05: A Prefill and Decode Step-Time Model from Model Dimensions
=============================================================================

PROBLEM STATEMENT
-----------------
A decoder-only transformer is described by
    n_layers, d_model, n_heads, n_kv_heads (grouped-query attention),
    d_ff (SwiGLU MLP: gate, up and down projections), vocab,
    2-byte (BF16) weights and KV cache, an untied embedding and LM head.

Write a roofline cost model for one serving step on an instance of
`n_devices` accelerators (tensor parallel, treated as one big device):

1. parameter counts: per layer, total, and the "matmul" parameters every
   forward pass multiplies by (layers + LM head; the input embedding is a
   lookup, so a step reads only the rows of the tokens it embeds);
2. KV-cache bytes per token;
3. prefill(prompt_lens): FLOPs = 2 * matmul_params * tokens plus causal
   attention (QK^T and AV, each 2 * d_model FLOPs per layer per attended
   position, position c attending to c + 1 positions including itself);
   bytes = weights read + KV written for every token;
4. decode(batch, ctx_per_seq): every sequence emits one token; FLOPs =
   2 * matmul_params * batch + 4 * n_layers * d_model * (total ctx + batch);
   bytes = weights read + KV read for (total ctx + batch) positions;
5. time = max(FLOPs / F, bytes / B) + a fixed 0.5 ms step overhead, with
   F = 55% of peak FLOP/s and B = 80% of peak bandwidth (per device x n).

The model must reproduce the closed-form numbers recorded for
Disaggregated_Inference_Sim (its examples/results.md, section 1), e.g.
Llama-3-8B decode, batch 1, context 2,048 on one H100:
    15.278 GB per step, 6.201 ms (memory-bound).

CONSTRAINTS
-----------
    H100 SXM: 989 TFLOP/s dense BF16, 3.35 TB/s, 80 GB (datasheet peaks).
    Llama-3-8B: 32 layers, d 4096, 32 heads, 8 KV heads, d_ff 14336, vocab 128256.
    Llama-3-70B: 80 layers, d 8192, 64 heads, 8 KV heads, d_ff 28672, vocab 128256.
    Ignore tensor-parallel communication and power limits (the numbers
    reproduced here are not power-limited).

PITFALLS TO DISCUSS
-------------------
    - Charging the whole embedding table every step overstates traffic by
      vocab x d x 2 bytes (1.05 GB for Llama-3-8B): a real error found in the
      reference simulator by an operator trace and corrected.
    - Forgetting that the new token attends to itself (ctx + batch, not ctx).
    - Prefill FLOPs here charge the LM head for every prompt token, as a plain
      forward pass computes; engines that keep only the last position do less.
    - A causal mask halves attention FLOPs only if the kernel skips the masked
      half; a traced unfused kernel computes the full square.

Go deeper on this GitHub:
    InfSim 03, "Counting FLOPs" and "Counting Bytes":
      https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-02
      https://brendanjameslynskey.github.io/InfSim_03_LLM_Inference_Workloads/#slide-03
    SimEng 10, "Checking the Trace Against the Closed Form":
      https://brendanjameslynskey.github.io/SimEng_10_PyTorch_ONNX_Frontends/#slide-09
    Recorded numbers:
      https://github.com/BrendanJamesLynskey/Disaggregated_Inference_Sim/blob/main/examples/results.md
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass

GB, TB = 1e9, 1e12


@dataclass(frozen=True)
class Transformer:
    n_layers: int
    d_model: int
    n_heads: int
    n_kv_heads: int
    d_ff: int
    vocab: int
    wbytes: float = 2.0
    kvbytes: float = 2.0

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    @property
    def params_per_layer(self) -> int:
        d, kv = self.d_model, self.n_kv_heads * self.head_dim
        return 2 * d * d + 2 * d * kv + 3 * d * self.d_ff   # Wq, Wo, Wk, Wv, SwiGLU

    @property
    def params(self) -> int:
        return self.n_layers * self.params_per_layer + 2 * self.vocab * self.d_model

    @property
    def matmul_params(self) -> int:
        return self.n_layers * self.params_per_layer + self.vocab * self.d_model

    def weight_bytes_read(self, tokens: int) -> float:
        return self.matmul_params * self.wbytes + tokens * self.d_model * self.wbytes

    @property
    def kv_bytes_per_token(self) -> float:
        return 2 * self.n_layers * self.n_kv_heads * self.head_dim * self.kvbytes


@dataclass(frozen=True)
class Instance:
    peak_flops: float
    peak_bw: float
    n_devices: int = 1
    flops_eff: float = 0.55
    bw_eff: float = 0.80
    overhead: float = 0.5e-3

    @property
    def F(self) -> float:
        return self.peak_flops * self.flops_eff * self.n_devices

    @property
    def B(self) -> float:
        return self.peak_bw * self.bw_eff * self.n_devices


@dataclass(frozen=True)
class Step:
    flops: float
    nbytes: float
    time: float
    bound: str

    @property
    def intensity(self) -> float:
        return self.flops / self.nbytes


# =============================================================================
# SOLUTION
# =============================================================================
# Decode reads every weight once per step whatever the batch, so its
# intensity is about batch FLOP/byte (2 FLOPs per 2-byte weight per token):
# far below an H100's ridge (~200 FLOP/byte derated). Prefill multiplies each
# weight by thousands of tokens and is compute-bound. Everything else here is
# bookkeeping, which is exactly where real cost models go wrong.
# =============================================================================

def _step(flops: float, nbytes: float, inst: Instance) -> Step:
    tc, tm = flops / inst.F, nbytes / inst.B
    return Step(flops, nbytes, max(tc, tm) + inst.overhead,
                "compute" if tc >= tm else "memory")


def prefill(m: Transformer, inst: Instance, prompt_lens: list[int]) -> Step:
    tokens = sum(prompt_lens)
    flops = 2 * m.matmul_params * tokens
    flops += sum(2 * m.n_layers * m.d_model * s * (s + 1) for s in prompt_lens)
    nbytes = m.weight_bytes_read(tokens) + tokens * m.kv_bytes_per_token
    return _step(flops, nbytes, inst)


def decode(m: Transformer, inst: Instance, batch: int, ctx_per_seq: int) -> Step:
    ctx = batch * ctx_per_seq
    flops = 2 * m.matmul_params * batch + 4 * m.n_layers * m.d_model * (ctx + batch)
    nbytes = m.weight_bytes_read(batch) + (ctx + batch) * m.kv_bytes_per_token
    return _step(flops, nbytes, inst)


def kv_capacity_tokens(m: Transformer, inst: Instance, capacity: float,
                       mem_util: float = 0.9) -> int:
    free = capacity * inst.n_devices * mem_util - m.params * m.wbytes
    if free <= 0:
        raise ValueError("weights do not fit")
    return int(free // m.kv_bytes_per_token)


LLAMA3_8B = Transformer(32, 4096, 32, 8, 14336, 128256)
LLAMA3_70B = Transformer(80, 8192, 64, 8, 28672, 128256)


def h100(n: int = 1) -> Instance:
    return Instance(989 * TB, 3.35 * TB, n_devices=n)


if __name__ == "__main__":
    for label, s in [
        ("8B decode b=1 ctx 2048, 1xH100", decode(LLAMA3_8B, h100(1), 1, 2048)),
        ("8B prefill 2048, 1xH100", prefill(LLAMA3_8B, h100(1), [2048])),
        ("70B decode b=16 ctx 2300, 4xH100", decode(LLAMA3_70B, h100(4), 16, 2300)),
    ]:
        print(f"{label:34s} {s.nbytes/GB:8.3f} GB  {s.time*1e3:8.3f} ms  "
              f"I={s.intensity:7.1f}  {s.bound}")
