"""Wall-clock deadline, measured from program start.

The scoring penalty only kicks in after the time limit L, so the solver
should use most of L. The search stops at L - max(MIN_MARGIN, MARGIN * L),
i.e. 28s / 57s / 171s for the three classes.

What the margin has to cover is small and measured: Python startup before
this module is imported, finishing the current iteration, and printing
(0.05-0.4s in total on a laptop). The margin is 5-10x that, for a slower
grading machine. It cannot cover slow setup (parsing, Clarke-Wright): that
runs before the search and is a speed problem, not a margin problem.
"""

import time

START = time.perf_counter()   # set when this module is first imported

MARGIN = 0.05                 # share of the limit kept free
MIN_MARGIN = 2.0              # seconds, at least

# Limits from the spec. The input file does not say which class an instance
# belongs to (each team labels its own), so the grader has to tell us via
# --size or --time. Without that we assume the shortest limit: stopping early
# costs a little solution quality, overrunning 1.5x the limit costs 3/4 of
# the instance's score.
LIMITS = {"small": 30.0, "medium": 60.0, "large": 180.0}
DEFAULT_SIZE = "small"


class Deadline:
    def __init__(self, limit_seconds):
        margin = max(MIN_MARGIN, MARGIN * limit_seconds)
        # very short limits (quick tests): never stop before half the limit
        self.end = START + max(limit_seconds - margin, limit_seconds / 2)

    def elapsed(self):
        return time.perf_counter() - START

    def remaining(self):
        return self.end - time.perf_counter()

    def expired(self):
        return time.perf_counter() >= self.end
