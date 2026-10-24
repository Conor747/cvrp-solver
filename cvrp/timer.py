"""Wall-clock deadline, measured from program start.

The scoring penalty only kicks in after the time limit L, so the solver
should use most of L. SAFETY leaves room for startup, output, and an
unknown grading machine.
"""

import time

START = time.perf_counter()   # set when this module is first imported

SAFETY = 0.85

# Limits from the spec. The input file does not say which class an instance
# belongs to (each team labels its own), so the grader has to tell us via
# --size or --time. Without that we assume the shortest limit: stopping early
# costs a little solution quality, overrunning 1.5x the limit costs 3/4 of
# the instance's score.
LIMITS = {"small": 30.0, "medium": 60.0, "large": 180.0}
DEFAULT_SIZE = "small"


class Deadline:
    def __init__(self, limit_seconds):
        self.end = START + limit_seconds * SAFETY

    def elapsed(self):
        return time.perf_counter() - START

    def remaining(self):
        return self.end - time.perf_counter()

    def expired(self):
        return time.perf_counter() >= self.end
