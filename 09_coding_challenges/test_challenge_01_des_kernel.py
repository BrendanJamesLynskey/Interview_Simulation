import random

import pytest

from challenge_01_des_kernel import FixedServiceQueue, Simulator


def test_example_order():
    log = []
    sim = Simulator()
    sim.schedule(2.0, log.append, "b")
    sim.schedule(1.0, log.append, "a")
    sim.schedule(2.0, log.append, "c")
    sim.schedule(2.0, log.append, "urgent", priority=-1)
    assert sim.run() == 2.0
    assert log == ["a", "urgent", "b", "c"]


def test_uncomparable_callbacks_with_equal_keys():
    # Two different lambdas at the same (time, priority): plain heapq on
    # (time, priority, callback) would raise TypeError here.
    log = []
    sim = Simulator()
    sim.schedule(1.0, lambda: log.append(1))
    sim.schedule(1.0, lambda: log.append(2))
    sim.run()
    assert log == [1, 2]


def test_zero_delay_from_inside_an_instant_runs_last_in_that_instant():
    log = []
    sim = Simulator()

    def first():
        log.append("first")
        sim.schedule(0.0, log.append, "spawned")

    sim.schedule(1.0, first)
    sim.schedule(1.0, log.append, "second")
    sim.schedule(1.5, log.append, "later")
    sim.run()
    assert log == ["first", "second", "spawned", "later"]


def test_cancel():
    log = []
    sim = Simulator()
    a = sim.schedule(1.0, log.append, "a")
    sim.schedule(2.0, log.append, "b")
    assert sim.cancel(a) is True
    assert sim.cancel(a) is False          # second cancel is harmless
    sim.run()
    assert log == ["b"]
    assert sim.events_fired == 1


def test_cancel_after_fire_is_harmless():
    sim = Simulator()
    e = sim.schedule(1.0, lambda: None)
    sim.run()
    assert sim.cancel(e) is False


def test_run_until_is_inclusive_and_advances_clock():
    log = []
    sim = Simulator()
    sim.schedule(1.0, log.append, 1)
    sim.schedule(2.0, log.append, 2)
    sim.schedule(3.0, log.append, 3)
    assert sim.run(until=2.0) == 2.0
    assert log == [1, 2]
    assert sim.run(until=10.0) == 10.0
    assert log == [1, 2, 3]


def test_negative_delay_rejected():
    with pytest.raises(ValueError):
        Simulator().schedule(-1e-9, lambda: None)


def test_fixed_service_queue_matches_hand_computation():
    # Arrivals at 0, 1, 1, 5 with service 2: departures at 2, 4, 6, 8
    # (D arrives at 5 while C is in service until 6).
    sim = Simulator()
    q = FixedServiceQueue(sim, service=2.0)
    for t, name in [(0, "A"), (1, "B"), (1, "C"), (5, "D")]:
        sim.schedule(t, q.arrive, name)
    sim.run()
    assert q.departures == [(2.0, "A"), (4.0, "B"), (6.0, "C"), (8.0, "D")]


def test_determinism_independent_of_insertion_shuffle_within_distinct_keys():
    # Events with distinct (time, priority) fire in the same order however
    # they were inserted; equal keys fire in insertion order.
    keys = [(random.Random(s).randint(0, 20) / 4, random.Random(s + 99).randint(-1, 1))
            for s in range(200)]
    def order(seed):
        rng = random.Random(seed)
        idx = list(range(len(keys)))
        rng.shuffle(idx)
        sim, log = Simulator(), []
        for i in idx:
            t, p = keys[i]
            sim.schedule(t, log.append, i, priority=p)
        sim.run()
        return log, idx
    for seed in range(5):
        log, idx = order(seed)
        fired_keys = [keys[i] for i in log]
        assert fired_keys == sorted(fired_keys)
        # within equal keys, insertion order is preserved
        pos = {i: n for n, i in enumerate(idx)}
        for a, b in zip(log, log[1:]):
            if keys[a] == keys[b]:
                assert pos[a] < pos[b]
