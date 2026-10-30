"""Build (and optionally verify) the datasets we submit.

The spec asks for every dataset to be submitted together with the command
and random seed that generate it. This script is that record: DATASETS
below is the full list, MANIFEST.md (written by this script) shows the exact
gen.py command, seed and SHA-256 of every file, so anyone can regenerate a
byte-identical copy.

Sizes (team decision, Oct 30): small 5,300, medium 7,500, large 12,900
customers, the "moderate" choice: on a grading VM up to 2x slower than our
test laptop, setup (parsing etc.) takes at most about half the time limit.

Usage, from the repo root:
    python datasets/make_datasets.py              # generate missing files + MANIFEST.md
    python datasets/make_datasets.py --verify     # also solve each at HALF its limit
    python datasets/make_datasets.py --verify --only small

--verify simulates a VM twice as slow: our solver must give a feasible answer
(checked by the independent checker in bench/evaluate.py) within half the
time limit. Generated files go to datasets/out/ (ignored by git: ~3 GB).
"""

import argparse
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.join(ROOT, "bench"))
from evaluate import Inst, check  # noqa: E402

LIMITS = {"small": 30.0, "medium": 60.0, "large": 180.0}

# name, size class, gen.py arguments (everything except --size and -o)
DATASETS = [
    ("small_uniform_5300",    "small",  "--n 5300 --seed 101 --slack 0"),
    ("small_clustered_5300",  "small",  "--n 5300 --seed 102 --layout clustered --clusters 8 --depot center --slack 1"),
    ("medium_uniform_7500",   "medium", "--n 7500 --seed 201 --slack 0"),
    ("medium_clustered_7500", "medium", "--n 7500 --seed 202 --layout clustered --clusters 8 --depot center --slack 1"),
    ("large_uniform_12900",   "large",  "--n 12900 --seed 301 --slack 0"),
    ("large_clustered_12900", "large",  "--n 12900 --seed 302 --layout clustered --clusters 8 --depot center --slack 1"),
]


def command(size, args, path="<file>"):
    return f"python gen.py --size {size} {args} -o {path}"


def generate(name, size, args):
    path = os.path.join(OUT, name + ".txt")
    if os.path.exists(path):
        return path, False
    tmp = path + ".part"
    subprocess.run([sys.executable, os.path.join(ROOT, "gen.py"), "--size", size,
                    *args.split(), "-o", tmp], check=True)
    os.replace(tmp, path)
    return path, True


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def summary(path):
    """Customers, capacity, vehicles and how full the fleet is (cheap: header + tail)."""
    with open(path) as f:
        f.readline()                                   # size word
        demand = [float(x) for x in f.readline().split()]
    with open(path, "rb") as f:
        f.seek(max(0, os.path.getsize(path) - 200))
        tail = f.read().decode().split()
    cap = float(tail[tail.index("Capacity:") + 1])
    veh = int(tail[tail.index("Vehicles:") + 1])
    return len(demand) - 1, cap, veh, sum(demand) / (cap * veh)


def verify(name, size, path):
    """Solve at half the limit (a 2x slower VM); check the answer independently."""
    limit = LIMITS[size] / 2
    t = time.perf_counter()
    with open(path + ".out", "w") as fo, open(path + ".err", "w") as fe:
        # output to files: an unread pipe would block the solver on a large answer
        code = subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), path,
                               "--time", f"{limit:g}", "--debug"], stdout=fo, stderr=fe,
                              timeout=limit * 1.5 + 30).returncode
    wall = time.perf_counter() - t
    out = open(path + ".out").read()
    notes = [l for l in open(path + ".err").read().splitlines() if "[setup]" in l]
    cost, why = check(Inst(path), out)
    ok = code == 0 and why is None and wall <= limit
    detail = f"cost {cost:.1f}" if why is None else f"REJECTED: {why}"
    return ok, f"{wall:6.1f}s of {limit:g}s  {detail}" + (f"  ({notes[0]})" if notes else "")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true", help="solve each at half its time limit")
    ap.add_argument("--only", nargs="+", help="datasets whose name contains any of these")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    chosen = [d for d in DATASETS if not args.only or any(s in d[0] for s in args.only)]
    rows = []
    for name, size, gen_args in chosen:
        t = time.perf_counter()
        path, made = generate(name, size, gen_args)
        mb = os.path.getsize(path) / 2**20
        n, cap, veh, fill = summary(path)
        print(f"{name:24} {'generated' if made else 'exists   '} {mb:7.0f} MB"
              f"{f'  ({time.perf_counter() - t:.0f}s)' if made else ''}", flush=True)
        rows.append((name, size, gen_args, n, cap, veh, fill, mb, sha256(path)))

    if not args.only:                                   # manifest always lists everything
        with open(os.path.join(HERE, "MANIFEST.md"), "w", newline="\n") as f:
            f.write("# Submitted datasets\n\n"
                    "Generated by `python datasets/make_datasets.py` (Python 3, standard library only).\n"
                    "Each file can be regenerated byte-for-byte with its command; the SHA-256 lets you check.\n\n"
                    "| File | Class | Customers | Capacity | Vehicles | Fleet fill | Size |\n"
                    "|---|---|---|---|---|---|---|\n")
            for name, size, _, n, cap, veh, fill, mb, _ in rows:
                f.write(f"| {name}.txt | {size} | {n} | {cap:g} | {veh} | {fill:.1%} | {mb:.0f} MB |\n")
            f.write("\n## Commands, seeds and checksums\n\n")
            for name, size, gen_args, *_, digest in rows:
                seed = gen_args.split("--seed")[1].split()[0]
                f.write(f"**{name}.txt** (seed {seed})\n```\n{command(size, gen_args, name + '.txt')}\n```\n"
                        f"SHA-256: `{digest}`\n\n")
        print("wrote datasets/MANIFEST.md")

    if args.verify:
        print("\nverifying at half of each time limit (simulates a 2x slower VM):")
        failed = 0
        for name, size, *_ in rows:
            ok, msg = verify(name, size, os.path.join(OUT, name + ".txt"))
            failed += not ok
            print(f"  {'ok  ' if ok else 'FAIL'} {name:24} {msg}", flush=True)
        print(f"\n{len(rows) - failed}/{len(rows)} passed")
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
