import random

import pytest

from challenge_06_pareto_front import (SWEEP_ALL_TECHNIQUES, SWEEP_BASELINE, dominates,
                                       pareto_front, pareto_front_2d)


def test_example():
    pts = [(1, 5), (2, 3), (3, 4), (4, 1), (2, 3)]
    assert pareto_front(pts) == [0, 1, 3, 4]
    assert pareto_front_2d(pts) == [0, 1, 3, 4]


def test_dominates():
    assert dominates((1, 1), (1, 2))
    assert not dominates((1, 2), (1, 2))          # equal: no domination
    assert not dominates((1, 3), (2, 2))          # a trade-off
    with pytest.raises(ValueError):
        dominates((1,), (1, 2))


@pytest.mark.parametrize("rows", [SWEEP_BASELINE, SWEEP_ALL_TECHNIQUES],
                         ids=["baseline", "all-techniques"])
def test_reproduces_recorded_pareto_column(rows):
    front = set(pareto_front([r[1:4] for r in rows]))
    assert [i in front for i in range(len(rows))] == [r[4] for r in rows]


def test_adding_area_changes_the_front():
    # In (latency, energy) alone, the 2048 and 4096 MiB baseline points tie
    # and dominate everything slower. With area, the cheaper designs return
    # and the tie is broken against the larger die.
    two = set(pareto_front([r[1:3] for r in SWEEP_BASELINE]))
    three = set(pareto_front([r[1:4] for r in SWEEP_BASELINE]))
    assert two == {6, 7}
    assert three == {0, 1, 2, 3, 4, 5, 6}
    # every 2-D front point without an exact 2-D tie stays on the 3-D front
    for i in two:
        tied = [j for j in two if j != i and SWEEP_BASELINE[j][1:3] == SWEEP_BASELINE[i][1:3]]
        if not tied:
            assert i in three


def test_front_is_non_dominated_and_covers_the_rest():
    rng = random.Random(3)
    pts = [tuple(rng.randint(0, 20) for _ in range(3)) for _ in range(300)]
    front = pareto_front(pts)
    fs = set(front)
    for i in front:
        assert not any(dominates(pts[j], pts[i]) for j in range(len(pts)))
    for i in range(len(pts)):
        if i not in fs:
            assert any(dominates(pts[j], pts[i]) for j in front)


def test_2d_matches_general_filter_on_random_inputs_with_ties():
    for seed in range(50):
        rng = random.Random(seed)
        pts = [(rng.randint(0, 15), rng.randint(0, 15)) for _ in range(rng.randint(1, 120))]
        assert pareto_front_2d(pts) == pareto_front(pts)


def test_empty_and_single():
    assert pareto_front([]) == [] and pareto_front_2d([]) == []
    assert pareto_front([(1.0, 2.0)]) == [0] and pareto_front_2d([(1.0, 2.0)]) == [0]
