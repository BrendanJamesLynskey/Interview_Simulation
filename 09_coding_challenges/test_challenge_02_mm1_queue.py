import math
import random

import pytest

from challenge_02_mm1_queue import analytic_wq, replicate, waits, waits_des


def test_analytic_value():
    assert analytic_wq(0.8, 1.0) == pytest.approx(4.0)
    assert analytic_wq(0.5, 1.0) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        analytic_wq(1.0, 1.0)


def test_ci_contains_analytic_mean():
    mean, half = replicate(0.8, 1.0, n=20_000, warmup=2_000, reps=20, seed=1)
    assert abs(mean - 4.0) <= half
    assert 0.02 < half < 0.5          # a CI that is informative, not vacuous


def test_ci_coverage_is_about_95_percent():
    # 40 independent experiments; P(Binomial(40, 0.95) < 33) is about 0.002,
    # so a correct method fails this test about once in 500 seeds.
    truth = analytic_wq(0.5, 1.0)
    hits = 0
    for seed in range(40):
        mean, half = replicate(0.5, 1.0, n=4_000, warmup=400, reps=10, seed=1000 + seed)
        hits += abs(mean - truth) <= half
    assert hits >= 33


def test_iid_ci_is_too_narrow():
    # Treating autocorrelated waits within one run as independent samples
    # gives a CI that misses the truth by many of its own half-widths.
    w = waits(0.9, 1.0, 50_000, random.Random("a"), random.Random("s"))[5_000:]
    m = sum(w) / len(w)
    sd = (sum((x - m) ** 2 for x in w) / (len(w) - 1)) ** 0.5
    naive_half = 1.96 * sd / math.sqrt(len(w))
    rep_mean, rep_half = replicate(0.9, 1.0, n=50_000, warmup=5_000, reps=10, seed=7)
    assert rep_half > 5 * naive_half


def test_initialisation_bias_without_warmup():
    # rho = 0.9, Wq = 9. Short runs started empty and kept whole are biased low.
    truth = analytic_wq(0.9, 1.0)
    # The M/M/1 relaxation time is about 1 / (mu (1 - sqrt(rho))^2), roughly
    # 380 mean service times at rho = 0.9: longer than a 200-customer run,
    # so most of each run is still filling up from empty.
    biased, half = replicate(0.9, 1.0, n=200, warmup=0, reps=200, seed=3)
    assert biased + half < 0.8 * truth


def test_des_and_lindley_agree():
    for seed in range(3):
        a = waits(0.7, 1.0, 3_000, random.Random(seed), random.Random(seed + 100))
        b = waits_des(0.7, 1.0, 3_000, random.Random(seed), random.Random(seed + 100))
        assert len(a) == len(b)
        assert max(abs(x - y) for x, y in zip(a, b)) < 1e-9
