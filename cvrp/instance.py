"""Parse a CVRP instance.

Expected format (from the spec):
    line 1        : n demands, depot first (always 0)
    next n lines  : n x n distance matrix
    then          : "Capacity: Q"
    then          : "Vehicles: V"

The parser is deliberately tolerant: extra spaces, blank lines, and the
Capacity/Vehicles lines appearing in either order (or before the matrix)
are all accepted.
"""

import re
import sys
from dataclasses import dataclass


@dataclass
class Instance:
    n: int                     # number of vertices INCLUDING the depot (vertex 0)
    demand: list               # demand[i], demand[0] == 0
    dist: list                 # dist[i][j], list of lists of float
    capacity: float
    vehicles: int

    @property
    def customers(self):
        return range(1, self.n)


_KEY_RE = re.compile(r"(capacity|vehicles)\s*:?\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)


def parse_text(text: str) -> Instance:
    keys = {}
    for m in _KEY_RE.finditer(text):
        keys[m.group(1).lower()] = float(m.group(2))
    if "capacity" not in keys or "vehicles" not in keys:
        raise ValueError("Missing 'Capacity:' or 'Vehicles:' line")
    body = _KEY_RE.sub(" ", text)

    lines = [ln.split() for ln in body.splitlines() if ln.strip()]
    demand = [float(x) for x in lines[0]]
    n = len(demand)

    # Read the matrix from the remaining tokens rather than line-by-line,
    # so a matrix wrapped over odd line breaks still parses.
    tokens = [tok for ln in lines[1:] for tok in ln]
    if len(tokens) < n * n:
        raise ValueError(f"Expected {n * n} matrix entries, found {len(tokens)}")
    flat = list(map(float, tokens[: n * n]))
    dist = [flat[i * n:(i + 1) * n] for i in range(n)]

    return Instance(n=n, demand=demand, dist=dist,
                    capacity=keys["capacity"], vehicles=int(keys["vehicles"]))


def read_instance(path=None) -> Instance:
    """Read from a file path, or from stdin if path is None."""
    if path is None:
        return parse_text(sys.stdin.read())
    with open(path) as f:
        return parse_text(f.read())
