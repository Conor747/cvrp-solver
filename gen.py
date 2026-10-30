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


def generate(args, out):
    rng = random.Random(args.seed)
    n = args.n

    depot = (args.grid / 2, args.grid / 2) if args.depot == "center" else \
            (rng.uniform(0, args.grid), rng.uniform(0, args.grid))
    pts = [depot] + make_points(rng, n, args.layout, args.grid, args.clusters)

    lo, hi = args.demand
    demand = [0] + [rng.randint(lo, hi) for _ in range(n)]
    capacity = args.capacity or max(hi, round((lo + hi) / 2 * args.route_size))
    vehicles = ffd_bins(demand[1:], capacity) + args.slack

    dec = args.decimals
    out.write(args.size + "\n")
    out.write(" ".join(map(str, demand)) + "\n")
    for i, (xi, yi) in enumerate(pts):
        out.write(" ".join("0" if i == j else f"{round(math.hypot(xi - x, yi - y), dec):.6g}"
                           for j, (x, y) in enumerate(pts)) + "\n")
    out.write(f"Capacity: {capacity}\nVehicles: {vehicles}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", choices=["small", "medium", "large"], required=True,
                    help="size class written on the first line (sets the time limit)")
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
    ap.add_argument("--decimals", type=int, default=1,
                    help="decimal places for distances (capped at 6 significant digits)")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    if args.out:
        with open(args.out, "w", newline="\n") as f:
            generate(args, f)
    else:
        generate(args, sys.stdout)


if __name__ == "__main__":
    main()
