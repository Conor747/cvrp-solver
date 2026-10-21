"""CVRP instance generator.

Points are placed in a square grid; distances are Euclidean, rounded.
The same command + seed always produces the same file (the spec asks us
to submit both with each dataset).

Usage:
    python gen.py --n 100 --seed 1 > small.txt
    python gen.py --n 500 --seed 2 --layout clustered --slack 0 -o medium.txt

Vehicles = (bins needed by first-fit-decreasing) + slack, so every
generated instance is guaranteed feasible. --slack 0 gives the tightest
instances: Clarke-Wright alone will usually need one route too many.
"""

import argparse
import math
import random
import sys


def make_points(rng, n, layout, grid, clusters):
    if layout == "uniform":
        return [(rng.uniform(0, grid), rng.uniform(0, grid)) for _ in range(n)]
    centers = [(rng.uniform(0, grid), rng.uniform(0, grid)) for _ in range(clusters)]
    spread = grid / (4 * math.sqrt(clusters))
    pts = []
    for _ in range(n):
        cx, cy = rng.choice(centers)
        x = min(grid, max(0, rng.gauss(cx, spread)))
        y = min(grid, max(0, rng.gauss(cy, spread)))
        pts.append((x, y))
    return pts


def ffd_bins(demands, capacity):
    loads = []
    for q in sorted(demands, reverse=True):
        for i, load in enumerate(loads):
            if load + q <= capacity:
                loads[i] += q
                break
        else:
            loads.append(q)
    return len(loads)


def generate(args):
    rng = random.Random(args.seed)
    n = args.n

    depot = (args.grid / 2, args.grid / 2) if args.depot == "center" else \
            (rng.uniform(0, args.grid), rng.uniform(0, args.grid))
    pts = [depot] + make_points(rng, n, args.layout, args.grid, args.clusters)

    lo, hi = args.demand
    demand = [0] + [rng.randint(lo, hi) for _ in range(n)]
    capacity = args.capacity or max(hi, round((lo + hi) / 2 * args.route_size))
    vehicles = ffd_bins(demand[1:], capacity) + args.slack

    fmt = f"{{:.{args.decimals}f}}" if args.decimals > 0 else "{:.0f}"
    m = n + 1
    rows = [[0.0] * m for _ in range(m)]
    for i in range(m):
        xi, yi = pts[i]
        for j in range(i + 1, m):
            rows[i][j] = rows[j][i] = math.hypot(xi - pts[j][0], yi - pts[j][1])

    out = [" ".join(map(str, demand))]
    out += [" ".join("0" if i == j else fmt.format(v) for j, v in enumerate(row))
            for i, row in enumerate(rows)]
    out += [f"Capacity: {capacity}", f"Vehicles: {vehicles}"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, required=True, help="number of customers (excl. depot)")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--layout", choices=["uniform", "clustered"], default="uniform")
    ap.add_argument("--clusters", type=int, default=5)
    ap.add_argument("--depot", choices=["random", "center"], default="random")
    ap.add_argument("--grid", type=float, default=1000.0)
    ap.add_argument("--demand", type=int, nargs=2, default=[1, 30], metavar=("MIN", "MAX"))
    ap.add_argument("--capacity", type=int, default=None,
                    help="default: mean demand * --route-size")
    ap.add_argument("--route-size", type=float, default=10.0,
                    help="target customers per route when capacity is derived")
    ap.add_argument("--slack", type=int, default=1,
                    help="extra vehicles on top of the FFD packing (0 = tight)")
    ap.add_argument("--decimals", type=int, default=1)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    text = generate(args)
    if args.out:
        with open(args.out, "w") as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
