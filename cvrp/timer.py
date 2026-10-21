"""Wall-clock deadline, measured from program start.

The scoring penalty only kicks in after the time limit L, so the solver
should use most of L. SAFETY leaves room for startup, output, and an
unknown grading machine.
"""

import time

START = time.perf_counter()   # set when this module is first imported

SAFETY = 0.85

# Limits from the spec. TODO: get the n thresholds for small/medium/large
# from the instructor; these cutoffs are placeholders.
LIMITS = [(100, 30.0), (500, 60.0), (float("inf"), 180.0)]


def default_limit(n):
    for max_n, limit in LIMITS:
        if n <= max_n:
            return limit
    return LIMITS[-1][1]


class Deadline:
    def __init__(self, limit_seconds):
        self.end = START + limit_seconds * SAFETY

    def elapsed(self):
        return time.perf_counter() - START

    def remaining(self):
        return self.end - time.perf_counter()

    def expired(self):
        return time.perf_counter() >= self.end
