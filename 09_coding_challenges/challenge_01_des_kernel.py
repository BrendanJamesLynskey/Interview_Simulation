"""
=============================================================================
Challenge 01: A Minimal Discrete-Event Kernel with Deterministic Ties
=============================================================================

PROBLEM STATEMENT
-----------------
Write the core of a discrete-event simulator: an event list and a run loop.

    sim = Simulator()
    sim.schedule(delay, callback, *args, priority=0)   # returns an event id
    sim.cancel(event_id)                               # lazily cancel
    sim.run(until=None)                                # returns the final time
    sim.now                                            # current simulated time

Rules:

1. Events fire in order of (time, priority, insertion order). A lower
   priority number fires first. Two events with the same time and priority
   fire in the order they were scheduled (FIFO). This makes every run
   reproducible: the order never depends on the heap's internal layout,
   on dictionary order, or on comparing callbacks.
2. Callbacks may schedule further events, including events at the current
   time (delay 0). Those fire in the same instant, after everything already
   scheduled for that instant at the same priority.
3. `run(until=T)` processes every event with time <= T, then sets `now = T`.
   Without `until` it runs until the list is empty.
4. Scheduling into the past (negative delay) is an error.
5. A cancelled event never fires. Cancellation must be O(1); do not search
   the heap.

EXAMPLE
-------
    log = []
    sim = Simulator()
    sim.schedule(2.0, log.append, "b")
    sim.schedule(1.0, log.append, "a")
    sim.schedule(2.0, log.append, "c")         # same time as "b": after it
    sim.schedule(2.0, log.append, "urgent", priority=-1)
    sim.run()
    log == ["a", "urgent", "b", "c"]

CONSTRAINTS
-----------
    Up to 10^6 events; O(log n) per schedule and per event fired.
    Times are floats >= 0. Callbacks are arbitrary callables (not orderable).

EDGE CASES TO CONSIDER
----------------------
    - Ties in time: the reason `heapq` on (time, callback) crashes or, worse,
      orders by callback identity.
    - A callback that schedules at delay 0 during the same instant.
    - Cancelling an event that has already fired (must be harmless).
    - run(until=T) when the next event is exactly at T (it fires).
    - Float time accumulation: 0.1 + 0.2 != 0.3, so never use time equality
      to decide "same instant" in your own code; the kernel just orders.

Go deeper on this GitHub:
    InfSim 02, "Step 1 — A Kernel in 30 Lines":
      https://brendanjameslynskey.github.io/InfSim_02_Simulator_Development_Tutorial/#slide-02
    SimEng 01, "Ordering Floats, Breaking Ties":
      https://brendanjameslynskey.github.io/SimEng_01_Rust_for_Simulation_Engineers/#slide-03
    Glossary, deterministic tie-breaking:
      https://brendanjameslynskey.github.io/SimEng_Hub_Toolkit/#g-tiebreak
=============================================================================
"""

from __future__ import annotations

import heapq
import itertools
from typing import Any, Callable


# =============================================================================
# SOLUTION
# =============================================================================
# The heap holds tuples (time, priority, seq, event_id). `seq` comes from a
# monotonically increasing counter, so no two keys are ever equal and Python
# never falls through to comparing the payload. Callbacks live in a dict keyed
# by event id; cancelling deletes the dict entry (O(1)) and the heap entry is
# skipped when it surfaces ("lazy deletion").
#
# Complexity: schedule O(log n); each fired or skipped event O(log n).
# Memory: cancelled events stay in the heap until popped. If cancellation is
# very common (timeouts that rarely expire), rebuild the heap when the dead
# fraction passes, say, one half.
# =============================================================================

class Simulator:
    def __init__(self) -> None:
        self.now: float = 0.0
        self._heap: list[tuple[float, int, int, int]] = []
        self._pending: dict[int, tuple[Callable[..., Any], tuple[Any, ...]]] = {}
        self._seq = itertools.count()
        self.events_fired = 0

    def schedule(self, delay: float, callback: Callable[..., Any], *args: Any,
                 priority: int = 0) -> int:
        if delay < 0:
            raise ValueError(f"cannot schedule into the past (delay={delay})")
        seq = next(self._seq)
        event_id = seq                     # the sequence number doubles as the id
        heapq.heappush(self._heap, (self.now + delay, priority, seq, event_id))
        self._pending[event_id] = (callback, args)
        return event_id

    def cancel(self, event_id: int) -> bool:
        """Cancel a pending event. Returns False if it already fired or was cancelled."""
        return self._pending.pop(event_id, None) is not None

    def peek(self) -> float | None:
        """Time of the next live event, or None."""
        while self._heap and self._heap[0][3] not in self._pending:
            heapq.heappop(self._heap)      # discard cancelled entries
        return self._heap[0][0] if self._heap else None

    def run(self, until: float | None = None) -> float:
        while True:
            t = self.peek()
            if t is None or (until is not None and t > until):
                break
            _, _, _, event_id = heapq.heappop(self._heap)
            callback, args = self._pending.pop(event_id)
            self.now = t
            self.events_fired += 1
            callback(*args)
        if until is not None:
            if until < self.now:
                raise ValueError("until is in the past")
            self.now = until
        return self.now


# =============================================================================
# A SMALL MODEL ON TOP: a single server with a FIFO queue and fixed service.
# Used by the tests to check the kernel against hand-computed departures.
# =============================================================================

class FixedServiceQueue:
    def __init__(self, sim: Simulator, service: float) -> None:
        self.sim, self.service = sim, service
        self.queue: list[str] = []
        self.busy = False
        self.departures: list[tuple[float, str]] = []

    def arrive(self, name: str) -> None:
        self.queue.append(name)
        if not self.busy:
            self._start()

    def _start(self) -> None:
        self.busy = True
        name = self.queue.pop(0)
        self.sim.schedule(self.service, self._depart, name)

    def _depart(self, name: str) -> None:
        self.departures.append((self.sim.now, name))
        self.busy = False
        if self.queue:
            self._start()


if __name__ == "__main__":
    log: list[str] = []
    sim = Simulator()
    sim.schedule(2.0, log.append, "b")
    sim.schedule(1.0, log.append, "a")
    sim.schedule(2.0, log.append, "c")
    sim.schedule(2.0, log.append, "urgent", priority=-1)
    sim.run()
    print(log)   # ['a', 'urgent', 'b', 'c']
