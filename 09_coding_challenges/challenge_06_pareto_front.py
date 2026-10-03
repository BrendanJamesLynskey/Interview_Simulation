"""
=============================================================================
Challenge 06: A Pareto-Front Filter for a Design-Space Sweep
=============================================================================

PROBLEM STATEMENT
-----------------
A design-space sweep produces points with several costs to minimise, for
example (latency, energy per operation, die area). A point A *dominates* B
if A is no worse than B in every objective and strictly better in at least
one. The Pareto front is the set of points no other point dominates.

1. Write `dominates(a, b)`.
2. Write `pareto_front(points)` for any number of objectives, returning the
   indices of the non-dominated points in input order.
3. Write `pareto_front_2d(points)` for two objectives in O(n log n).
4. Use the filter on a real sweep: the scratchpad-size sweep recorded for
   FHE_Accelerator_Sim (examples/results.md, section 22) and reproduce its
   "Pareto" column.

EXAMPLE
-------
    points = [(1, 5), (2, 3), (3, 4), (4, 1), (2, 3)]
    pareto_front(points) -> [0, 1, 3, 4]
    (3, 4) is dominated by (2, 3); the duplicate (2, 3) points do not
    dominate each other, so both stay.

CONSTRAINTS
-----------
    n up to 10^4 for the general filter (O(n^2 k) is acceptable);
    n up to 10^6 for the 2-D filter. All objectives are minimised.

PITFALLS TO DISCUSS
-------------------
    - Equal points: neither dominates the other. Decide whether to keep
      duplicates (here: yes) and say so.
    - A point that is better on one axis by a rounding error is still on the
      front; compare with tolerances when the inputs are noisy simulations.
    - Adding an objective keeps every front point that had no exact tie on
      the old objectives, and can add more: a point dominated in (latency,
      energy) may be optimal once area counts. Exact ties are the exception:
      the 2048 and 4096 MiB points below tie on latency and energy, both are
      on that 2-D front, and area then removes the 4096 MiB one.
    - The front says what is not wasteful; choosing on it needs a weighting,
      a constraint (e.g. "fits the reticle") or a composite metric (EDP,
      perf/mm2).

Go deeper on this GitHub:
    SimEng 13, "Pareto Fronts: Why There Is No Single Best Design":
      https://brendanjameslynskey.github.io/SimEng_13_PPA_Tradeoffs/#slide-08
    FHESim 05, "Sweeps, Pareto Fronts and Simulator Speed":
      https://brendanjameslynskey.github.io/FHESim_05_Results_and_Design_Space/#slide-07
    Glossary, Pareto front and dominance:
      https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-paretofront
=============================================================================
"""

from __future__ import annotations

from typing import Sequence

Point = Sequence[float]


def dominates(a: Point, b: Point) -> bool:
    if len(a) != len(b):
        raise ValueError("points must have the same number of objectives")
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


# =============================================================================
# SOLUTION 1: the general filter, O(n^2 k)
# =============================================================================
# Compare every pair. Simple, obviously correct, and fast enough for the few
# thousand points a simulator sweep produces. It is the oracle for the
# faster 2-D version.
# =============================================================================

def pareto_front(points: list[Point]) -> list[int]:
    return [i for i, p in enumerate(points)
            if not any(dominates(q, p) for j, q in enumerate(points) if j != i)]


# =============================================================================
# SOLUTION 2: two objectives, O(n log n)
# =============================================================================
# Sort by (x, y). Sweep in that order keeping the best y seen at strictly
# smaller x. A point is on the front iff its y is below that best (points
# with equal x are handled as a group so that equal-x points do not
# eliminate each other wrongly: within a group only the minimum y survives,
# together with any exact duplicates of it).
# =============================================================================

def pareto_front_2d(points: list[tuple[float, float]]) -> list[int]:
    order = sorted(range(len(points)), key=lambda i: (points[i][0], points[i][1]))
    keep: list[int] = []
    best_y = float("inf")          # best y among points with strictly smaller x
    k = 0
    while k < len(order):
        x = points[order[k]][0]
        group = []
        while k < len(order) and points[order[k]][0] == x:
            group.append(order[k])
            k += 1
        y_min = points[group[0]][1]           # group is sorted by y
        if y_min < best_y:
            keep.extend(i for i in group if points[i][1] == y_min)
            best_y = y_min
    return sorted(keep)


# =============================================================================
# The recorded sweep: FHE_Accelerator_Sim examples/results.md section 22,
# "Scratchpad size as a three-way trade-off", ARK-class design.
# Columns used: SRAM MiB, bootstrap (ms), mJ, die mm2, and the Pareto mark.
# =============================================================================

SWEEP_BASELINE = [  # (SRAM MiB, ms, mJ, mm2, recorded "yes")
    (128, 26.98, 2084, 253.5, True),
    (256, 17.10, 1383, 324.8, True),
    (384, 14.57, 1193, 392.3, True),
    (512, 13.94, 1139, 457.9, True),
    (768, 13.33, 1096, 581.1, True),
    (1024, 11.69, 984, 695.2, True),
    (2048, 11.41, 966, 1182.3, True),
    (4096, 11.41, 966, 2180.5, False),
]

SWEEP_ALL_TECHNIQUES = [  # Min-KS + seeded keys + OTF plaintexts
    (128, 21.22, 1691, 253.5, True),
    (256, 8.71, 774, 324.8, True),
    (384, 7.56, 646, 392.3, True),
    (512, 7.19, 607, 457.9, True),
    (768, 7.19, 607, 581.1, False),
    (1024, 7.19, 607, 695.2, False),
    (2048, 7.19, 607, 1182.3, False),
    (4096, 7.19, 607, 2180.5, False),
]


if __name__ == "__main__":
    for name, rows in [("baseline", SWEEP_BASELINE), ("all techniques", SWEEP_ALL_TECHNIQUES)]:
        front = set(pareto_front([r[1:4] for r in rows]))
        print(name, [r[0] for i, r in enumerate(rows) if i in front], "MiB on the front")
