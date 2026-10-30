import time

START = time.perf_counter()

MARGIN = 0.05
MIN_MARGIN = 2.0
LIMITS = {"small": 30.0, "medium": 60.0, "large": 180.0}
DEFAULT_SIZE = "small"


class Deadline:
    def __init__(self, limit_seconds):
        margin = max(MIN_MARGIN, MARGIN * limit_seconds)
        self.end = START + max(limit_seconds - margin, limit_seconds / 2)

    def elapsed(self):
        return time.perf_counter() - START

    def remaining(self):
        return self.end - time.perf_counter()

    def expired(self):
        return time.perf_counter() >= self.end
