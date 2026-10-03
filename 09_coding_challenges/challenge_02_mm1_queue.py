"""
=============================================================================
Challenge 02: Simulate an M/M/1 Queue and Check It Against Theory
=============================================================================

PROBLEM STATEMENT
-----------------
Customers arrive as a Poisson process of rate `lam` at a single FIFO server
whose service times are exponential with rate `mu` (lam < mu).

1. Write `waits(lam, mu, n, rng)` returning the waiting time in queue
   (arrival to start of service) of each of `n` customers, starting from an
   empty system.
2. Write `replicate(lam, mu, n, warmup, reps, seed)` that runs `reps`
   independent replications, deletes the first `warmup` customers of each,
   and returns the mean queueing delay with a 95% confidence interval built
   from the replication means (Student t).
3. Show that the analytic mean wait  Wq = rho / (mu - lam),  rho = lam / mu,
   lies inside the interval, and that the interval covers the truth about
   95% of the time over many independent experiments.

EXAMPLE
-------
    lam = 0.8, mu = 1.0  ->  rho = 0.8,  Wq = 0.8 / 0.2 = 4.0
    replicate(0.8, 1.0, n=20_000, warmup=2_000, reps=20, seed=1)
    -> (mean ~ 4.0, half_width ~ 0.1 - 0.2)

CONSTRAINTS
-----------
    0 < lam < mu.  n up to 10^6.  Use the standard library only.

EDGE CASES / PITFALLS TO DISCUSS
--------------------------------
    - Initialisation bias: an empty start makes early customers wait less.
      At rho = 0.9 a short run without warm-up deletion underestimates Wq.
    - Customers within one run are strongly autocorrelated: a CI computed
      from the n individual waits as if independent is far too narrow.
      Use replications (or batch means), one number per replication.
    - Separate random streams for arrivals and service (and per replication)
      so that changing one does not perturb the other: the basis of common
      random numbers.

Go deeper on this GitHub:
    InfSim 02, "Step 2 — A Queue, Checked Against Theory":
      https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-03
    InfSim 06, "Interactive: Replications, Confidence Intervals and Common Random Numbers":
      https://brendanjameslynskey.github.io/InfSim_06_Metrics_Hotspots_Validation/#slide-07
    Glossary, queueing theory checks / warm-up and replications:
      https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-queueing
      https://brendanjameslynskey.github.io/LLM_Hub_Inference_Simulators/#g-warmup
=============================================================================
"""

from __future__ import annotations

import math
import random
import statistics

# Two-sided 95% Student t quantiles t_{0.975, df}. For df > 30 the normal
# value is close enough for an interview answer (and is what we fall back to).
_T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
         8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
         14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
         20: 2.086, 21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
         26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def t975(df: int) -> float:
    return _T975.get(df, 1.96)


def analytic_wq(lam: float, mu: float) -> float:
    if not 0 < lam < mu:
        raise ValueError("need 0 < lam < mu for a stable queue")
    rho = lam / mu
    return rho / (mu - lam)


# =============================================================================
# SOLUTION 1: the Lindley recursion
# =============================================================================
# For a FIFO single-server queue, customer n+1 waits
#     W[n+1] = max(0, W[n] + S[n] - A[n+1])
# where S[n] is customer n's service time and A[n+1] the gap to the next
# arrival. No event list is needed: this is the fastest correct simulator for
# this model, and a useful oracle for a DES implementation (see the tests).
# O(n) time, O(n) memory for the returned list.
# =============================================================================

def waits(lam: float, mu: float, n: int, rng_arrival: random.Random,
          rng_service: random.Random) -> list[float]:
    out = [0.0] * n
    w = 0.0
    s = rng_service.expovariate(mu)
    for i in range(1, n):
        a = rng_arrival.expovariate(lam)
        w = max(0.0, w + s - a)
        out[i] = w
        s = rng_service.expovariate(mu)
    return out


def replicate(lam: float, mu: float, n: int, warmup: int, reps: int,
              seed: int) -> tuple[float, float]:
    """Mean queueing delay and 95% CI half-width from `reps` replications."""
    if reps < 2:
        raise ValueError("need at least two replications for a CI")
    means = []
    for r in range(reps):
        # independent, reproducible streams per replication and per purpose
        ra = random.Random(f"{seed}-arrival-{r}")
        rs = random.Random(f"{seed}-service-{r}")
        w = waits(lam, mu, n, ra, rs)[warmup:]
        means.append(math.fsum(w) / len(w))
    mean = math.fsum(means) / reps
    half = t975(reps - 1) * statistics.stdev(means) / math.sqrt(reps)
    return mean, half


# =============================================================================
# SOLUTION 2 (cross-check): the same queue on an event list
# =============================================================================
# Arrival and departure events on challenge 01's kernel. Given the same
# random draws it must reproduce the Lindley waits (to float rounding, since
# the two compute the same quantity by different sums).
# =============================================================================

def waits_des(lam: float, mu: float, n: int, rng_arrival: random.Random,
              rng_service: random.Random) -> list[float]:
    from challenge_01_des_kernel import Simulator

    sim = Simulator()
    arrival_time: list[float] = []
    out = [0.0] * n
    queue: list[int] = []
    busy = [False]
    service = [rng_service.expovariate(mu) for _ in range(n)]

    def start(i: int) -> None:
        busy[0] = True
        out[i] = sim.now - arrival_time[i]
        sim.schedule(service[i], depart)

    def depart() -> None:
        busy[0] = False
        if queue:
            start(queue.pop(0))

    def arrive(i: int) -> None:
        arrival_time.append(sim.now)
        if i + 1 < n:
            sim.schedule(rng_arrival.expovariate(lam), arrive, i + 1)
        if busy[0]:
            queue.append(i)
        else:
            start(i)

    sim.schedule(0.0, arrive, 0)
    sim.run()
    return out


if __name__ == "__main__":
    m, h = replicate(0.8, 1.0, n=20_000, warmup=2_000, reps=20, seed=1)
    print(f"simulated Wq = {m:.3f} +/- {h:.3f}; analytic = {analytic_wq(0.8, 1.0):.3f}")
