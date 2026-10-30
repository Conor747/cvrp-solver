"""Parse a CVRP instance.

Expected format (from the spec and the instructor's announcement):
    line 1        : small | medium | large   (any capitalization)
    line 2        : n demands, depot first (always 0)
    next n lines  : n x n distance matrix
    then          : "Capacity: Q"
    then          : "Vehicles: V"

The parser is deliberately tolerant: a missing or unknown size word, extra
spaces, blank lines, scientific notation (1.5e+03), the Capacity/Vehicles
lines appearing in either order (or before the matrix), and matrix rows
wrapped over odd line breaks are all accepted.

It streams the input line by line and stores each matrix row as a compact
array of doubles (8 bytes per entry instead of ~32 for a list of floats),
so a 5000-customer instance needs ~0.2 GB instead of ~3 GB.
"""

import re
import sys
from array import array
from dataclasses import dataclass


@dataclass
class Instance:
    n: int                     # number of vertices INCLUDING the depot (vertex 0)
    demand: list               # demand[i], demand[0] == 0
    dist: list                 # dist[i][j]; each row is an array('d')
    capacity: float
    vehicles: int
    size: str = None           # word on the first line, lowercased; None if absent
    notes: list = None         # parser warnings (e.g. a missing line), for stderr

    @property
    def customers(self):
        return range(1, self.n)


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_KEY_RE = re.compile(rf"(capacity|vehicles)\s*:?\s*({_NUM})", re.IGNORECASE)
_SHORT = 256                   # keyword lines are short; matrix rows usually aren't


def parse_lines(lines) -> Instance:
    keys = {}
    size = None
    demand = None
    dist = []
    pending = []               # tokens of a matrix row split over several lines
    n = 0

    for line in lines:
        if demand is None and len(line) < _SHORT:
            # header: the size word on the first line ("small", "LARGE", ...).
            # Any short line without digits before the demands is skipped
            # rather than crashing on it; its first word is taken as the size.
            text = line.strip().lstrip("﻿")
            if text and not any(ch.isdigit() for ch in text):
                if size is None:
                    size = text.split()[0].lower()
                continue
        # Only short lines (or the start of long ones) can hold a keyword.
        if len(line) < _SHORT or _KEY_RE.search(line, 0, _SHORT):
            found = _KEY_RE.findall(line)
            if found:
                for k, v in found:
                    keys[k.lower()] = float(v)
                line = _KEY_RE.sub(" ", line)
        if len(dist) == n and demand is not None:
            continue           # matrix complete: only keywords matter now
        toks = line.split()
        if not toks:
            continue
        if demand is None:
            demand = [float(x) for x in toks]
            n = len(demand)
            continue
        if not pending and len(toks) == n:
            dist.append(array("d", map(float, toks)))          # fast path
            continue
        pending.extend(toks)
        while len(pending) >= n and len(dist) < n:
            dist.append(array("d", map(float, pending[:n])))
            del pending[:n]

    if demand is None:
        raise ValueError("Empty input: no demand line")
    if len(dist) < n:
        raise ValueError(f"Expected {n} matrix rows, found {len(dist)}")
    # A missing Capacity/Vehicles line must not cost a whole instance:
    # treat the missing constraint as unlimited and say so on stderr.
    notes = []
    if "capacity" not in keys:
        keys["capacity"] = sum(demand)
        notes.append("no 'Capacity:' line; assuming unlimited capacity")
    if "vehicles" not in keys:
        keys["vehicles"] = n - 1
        notes.append("no 'Vehicles:' line; assuming one vehicle per customer")
    return Instance(n=n, demand=demand, dist=dist, capacity=keys["capacity"],
                    vehicles=int(round(keys["vehicles"])), size=size, notes=notes)


def parse_text(text: str) -> Instance:
    return parse_lines(text.splitlines())


def read_instance(path=None) -> Instance:
    """Read from a file path, or from stdin if path is None."""
    if path is None:
        return parse_lines(sys.stdin)
    with open(path) as f:
        return parse_lines(f)
