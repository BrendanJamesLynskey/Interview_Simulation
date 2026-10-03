"""
=============================================================================
Challenge 04: Streaming Percentiles, and Why You Must Not Average p99s
=============================================================================

PROBLEM STATEMENT
-----------------
A simulator emits millions of latencies per run, across many runs and many
instances. You must report p50, p99 and p99.9 without storing every sample,
and combine results from shards (instances, runs, workers).

1. Write `percentile(xs, q)` returning the exact nearest-rank q-quantile
   (the value of rank ceil(q * n) in sorted order, 1-based), 0 < q <= 1.
2. Write a mergeable streaming sketch `LogHistogram(alpha)` with
       add(x), merge(other), quantile(q), count
   whose answer for any q is within relative error `alpha` of the exact
   nearest-rank quantile of everything added, for x > 0, using memory that
   grows with log(max/min), not with n.
3. Show with a concrete example that the mean of per-shard p99s is not the
   p99 of the pooled data, while merging sketches gives the right answer.

EXAMPLE
-------
    shard A: 1,000 requests, all 10 ms             -> p99 = 10 ms
    shard B: 1,000 requests, 980 at 10 ms, 20 at 1 s -> p99 = 1 s
    mean of p99s = 505 ms;  pooled p99 (2,000 samples, 20 slow) = 10 ms

CONSTRAINTS
-----------
    Values are positive floats (latencies). alpha in (0, 1), e.g. 0.01.
    O(1) per add; O(buckets) per quantile and per merge.

PITFALLS TO DISCUSS
-------------------
    - Percentiles are not linear: no average of percentiles is a percentile
      of the union. Merge the distributions (histograms or sketches), then
      take the percentile.
    - Different libraries interpolate differently (numpy's default is linear
      between ranks); state the definition when you compare numbers.
    - A p99.9 needs well over 1,000 samples per estimate to mean anything;
      report the sample count with every tail percentile.
    - Sorting once and reading every percentile from the sorted array beats
      sorting once per percentile (a measured 2.25x on one simulator).

Go deeper on this GitHub:
    InfSim 06, "Latency: Distributions, Not Averages":
      https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-02
    SimEng 11, "Closing the Loop: Sort Once":
      https://brendanjameslynskey.github.io/SimEng_11_Performance_Analysis/#slide-09
    Glossary, percentiles and tail-latency CCDFs:
      https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-percentiles
=============================================================================
"""

from __future__ import annotations

import math
from collections import Counter


def percentile(xs: list[float], q: float) -> float:
    """Exact nearest-rank quantile: value of rank ceil(q n) (1-based)."""
    if not xs:
        raise ValueError("no data")
    if not 0 < q <= 1:
        raise ValueError("q must be in (0, 1]")
    s = sorted(xs)
    return s[max(1, math.ceil(q * len(s))) - 1]


# =============================================================================
# SOLUTION: logarithmic buckets with a relative-error guarantee
# =============================================================================
# Choose gamma = (1 + alpha) / (1 - alpha). Bucket i holds values in
# (gamma^(i-1), gamma^i]. Report a bucket by  2 gamma^i / (gamma + 1):
# for any x in the bucket, |estimate - x| / x <= alpha. (This is the idea
# behind DDSketch; HDR histograms use a related log-linear layout.)
#
# The quantile walks buckets in order until the cumulative count reaches
# rank ceil(q n): the bucket that holds the exact nearest-rank value. So the
# guarantee is exact, not probabilistic. Merging adds counts, so a merged
# sketch is identical to a sketch of the concatenated stream: merging is
# associative and commutative, which is what makes shards combinable.
#
# Memory: one counter per occupied bucket, about log(max/min) / log(gamma).
# For 1 us .. 100 s at alpha = 1% that is under 1,000 buckets.
# =============================================================================

class LogHistogram:
    def __init__(self, alpha: float = 0.01) -> None:
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        self.alpha = alpha
        self.gamma = (1 + alpha) / (1 - alpha)
        self._log_gamma = math.log(self.gamma)
        self.buckets: Counter[int] = Counter()
        self.count = 0

    def _index(self, x: float) -> int:
        return math.ceil(math.log(x) / self._log_gamma)

    def add(self, x: float, n: int = 1) -> None:
        if x <= 0:
            raise ValueError("values must be positive")
        i = self._index(x)
        # guard the float edge: make sure gamma^(i-1) < x <= gamma^i
        if x > self.gamma ** i:
            i += 1
        elif x <= self.gamma ** (i - 1):
            i -= 1
        self.buckets[i] += n
        self.count += n

    def merge(self, other: "LogHistogram") -> "LogHistogram":
        if other.alpha != self.alpha:
            raise ValueError("can only merge sketches with the same alpha")
        self.buckets.update(other.buckets)
        self.count += other.count
        return self

    def quantile(self, q: float) -> float:
        if self.count == 0:
            raise ValueError("no data")
        if not 0 < q <= 1:
            raise ValueError("q must be in (0, 1]")
        rank = max(1, math.ceil(q * self.count))
        seen = 0
        for i in sorted(self.buckets):
            seen += self.buckets[i]
            if seen >= rank:
                return 2 * self.gamma ** i / (self.gamma + 1)
        raise AssertionError("unreachable")


def mean_of_percentiles(shards: list[list[float]], q: float) -> float:
    """The WRONG way to combine shards: shown for contrast."""
    return sum(percentile(s, q) for s in shards) / len(shards)


if __name__ == "__main__":
    a = [0.010] * 1000
    b = [0.010] * 980 + [1.0] * 20
    print("mean of p99s:", mean_of_percentiles([a, b], 0.99))
    print("pooled p99:  ", percentile(a + b, 0.99))
    ha, hb = LogHistogram(0.01), LogHistogram(0.01)
    for x in a:
        ha.add(x)
    for x in b:
        hb.add(x)
    print("merged sketch p99:", ha.merge(hb).quantile(0.99))
