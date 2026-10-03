import random

import pytest

from challenge_04_streaming_percentiles import LogHistogram, mean_of_percentiles, percentile


def test_nearest_rank_definition():
    xs = [15, 20, 35, 40, 50]
    assert percentile(xs, 0.05) == 15        # rank ceil(0.25) = 1
    assert percentile(xs, 0.30) == 20        # rank ceil(1.5) = 2
    assert percentile(xs, 0.40) == 20        # rank 2
    assert percentile(xs, 0.50) == 35        # rank ceil(2.5) = 3
    assert percentile(xs, 1.00) == 50


def test_averaging_p99s_is_wrong_and_merging_is_right():
    a = [0.010] * 1000
    b = [0.010] * 980 + [1.0] * 20
    assert percentile(a, 0.99) == 0.010
    assert percentile(b, 0.99) == 1.0
    assert mean_of_percentiles([a, b], 0.99) == pytest.approx(0.505)
    assert percentile(a + b, 0.99) == 0.010            # 20 slow of 2,000 is 1%
    ha, hb = LogHistogram(0.01), LogHistogram(0.01)
    for x in a:
        ha.add(x)
    for x in b:
        hb.add(x)
    assert ha.merge(hb).quantile(0.99) == pytest.approx(0.010, rel=0.01)


def test_mean_of_p99s_can_also_underestimate():
    # one busy shard with a heavy tail, many quiet ones
    busy = [0.01] * 9_000 + [1.0] * 1_000          # p99 = 1 s
    quiet = [[0.01] * 100 for _ in range(9)]        # p99 = 10 ms each
    wrong = mean_of_percentiles([busy] + quiet, 0.99)
    pooled = percentile(busy + sum(quiet, []), 0.99)
    assert pooled == 1.0
    assert wrong == pytest.approx((1.0 + 9 * 0.01) / 10)


@pytest.mark.parametrize("alpha", [0.05, 0.01, 0.001])
def test_relative_error_guarantee(alpha):
    rng = random.Random(42)
    xs = [rng.lognormvariate(-5, 1.5) for _ in range(20_000)]
    h = LogHistogram(alpha)
    for x in xs:
        h.add(x)
    for q in (0.001, 0.25, 0.5, 0.9, 0.99, 0.999, 1.0):
        exact = percentile(xs, q)
        assert abs(h.quantile(q) - exact) / exact <= alpha * (1 + 1e-12)


def test_merge_equals_sketch_of_concatenation():
    rng = random.Random(1)
    shards = [[rng.expovariate(1 / (k + 1)) for _ in range(2_000)] for k in range(5)]
    merged = LogHistogram(0.01)
    for s in shards:
        h = LogHistogram(0.01)
        for x in s:
            h.add(x)
        merged.merge(h)
    whole = LogHistogram(0.01)
    for s in shards:
        for x in s:
            whole.add(x)
    assert merged.buckets == whole.buckets and merged.count == whole.count


def test_memory_grows_with_log_range_not_count():
    h = LogHistogram(0.01)
    rng = random.Random(0)
    for _ in range(100_000):
        h.add(10 ** rng.uniform(-6, 2))    # 1 us .. 100 s
    # log(1e8) / log(1.01/0.99) is about 921 buckets
    assert len(h.buckets) < 1_000


def test_bad_inputs():
    h = LogHistogram()
    with pytest.raises(ValueError):
        h.quantile(0.5)
    with pytest.raises(ValueError):
        h.add(0.0)
    with pytest.raises(ValueError):
        LogHistogram(0.01).merge(LogHistogram(0.02))
    with pytest.raises(ValueError):
        percentile([], 0.5)
