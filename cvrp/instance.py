import re
import sys
from array import array
from dataclasses import dataclass


@dataclass
class Instance:
    n: int
    demand: list
    dist: list
    capacity: float
    vehicles: int
    size: str = None
    notes: list = None

    @property
    def customers(self):
        return range(1, self.n)


_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_KEY_RE = re.compile(rf"(capacity|vehicles)\s*:?\s*({_NUM})", re.IGNORECASE)
_SHORT = 256


def parse_lines(lines) -> Instance:
    keys = {}
    size = None
    demand = None
    dist = []
    pending = []
    n = 0

    for line in lines:
        if demand is None and len(line) < _SHORT:
            text = line.strip().lstrip("﻿")
            if text and not any(ch.isdigit() for ch in text):
                if size is None:
                    size = text.split()[0].lower()
                continue
        
        if len(line) < _SHORT or _KEY_RE.search(line, 0, _SHORT):
            found = _KEY_RE.findall(line)
            if found:
                for k, v in found:
                    keys[k.lower()] = float(v)
                line = _KEY_RE.sub(" ", line)
        if len(dist) == n and demand is not None:
            continue
        toks = line.split()
        if not toks:
            continue
        if demand is None:
            demand = [float(x) for x in toks]
            n = len(demand)
            continue
        if not pending and len(toks) == n:
            dist.append(array("d", map(float, toks)))
            continue
        pending.extend(toks)
        while len(pending) >= n and len(dist) < n:
            dist.append(array("d", map(float, pending[:n])))
            del pending[:n]

    if demand is None:
        raise ValueError("Empty input: no demand line")
    if len(dist) < n:
        raise ValueError(f"Expected {n} matrix rows, found {len(dist)}")


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
