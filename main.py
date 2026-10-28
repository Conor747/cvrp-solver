"""Entry point.

Usage:
    python main.py instance.txt                # read from a file
    python main.py < instance.txt              # read from stdin
    python main.py instance.txt --size large   # override: 180s (small=30, medium=60)
    python main.py instance.txt --time 45      # override: explicit limit in seconds
    python main.py instance.txt --debug        # self-check report on stderr

The time limit comes from the size word on the first line of the instance
(small / medium / large, any capitalization). Priority: --time, --size, the
file's word, then 30s (assume small, the safest guess).

Answer goes to stdout; anything diagnostic goes to stderr so it never
pollutes the graded output.
"""

import argparse
import sys

from cvrp import timer                      # import first: starts the clock
from cvrp.instance import read_instance
from cvrp.construct import clarke_wright, first_fit_decreasing
from cvrp.neighbors import neighbor_lists
from cvrp.repair import enforce_vehicle_limit
from cvrp.search import improve

K_NEIGHBORS = 100       # Clarke-Wright uses all 100; repair and search use fewer


def solve(inst, deadline, log=None, seed=0):
    nb = neighbor_lists(inst, K_NEIGHBORS)
    sol = clarke_wright(inst, nb)
    sol = enforce_vehicle_limit(inst, sol, deadline, nb)
    try:
        better = improve(inst, sol, deadline, nb=nb, seed=seed, log=log)
        if better.is_feasible(inst) or not sol.is_feasible(inst):
            sol = better
    except Exception as e:                  # keep the constructed solution
        print(f"search crashed: {e!r}; using constructed solution", file=sys.stderr)
    return sol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--size", type=str.lower, default=None,
                    help="small | medium | large; sets the time limit")
    ap.add_argument("--time", type=float, default=None,
                    help="time limit in seconds (overrides --size)")
    ap.add_argument("--seed", type=int, default=0,
                    help="random seed for the search (for experiments)")
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    inst = read_instance(args.path)       # the clock is already running

    # an unknown size word must not kill the run: no output scores 0
    for source, word in (("--size", args.size), ("file", inst.size)):
        if word is not None and word not in timer.LIMITS:
            print(f"unknown size {word!r} from {source}; ignoring it", file=sys.stderr)
    if args.time is not None:
        limit, source = args.time, "--time"
    elif args.size in timer.LIMITS:
        limit, source = timer.LIMITS[args.size], "--size"
    elif inst.size in timer.LIMITS:
        limit, source = timer.LIMITS[inst.size], f"file says {inst.size}"
    else:
        limit, source = timer.LIMITS[timer.DEFAULT_SIZE], "default: assumed small"
    deadline = timer.Deadline(limit)

    try:
        log = (lambda msg: print(msg, file=sys.stderr)) if args.debug else None
        sol = solve(inst, deadline, log, args.seed)
    except Exception as e:                  # never exit without an answer
        print(f"solver crashed: {e!r}; using fallback", file=sys.stderr)
        sol = first_fit_decreasing(inst)

    print(sol.format(inst))

    if args.debug:
        probs = sol.problems(inst)
        print(f"[debug] limit={limit:g}s ({source})", file=sys.stderr)
        print(f"[debug] n={inst.n} routes={len(sol.routes)}/{inst.vehicles} "
              f"cost={sol.cost(inst):.2f} time={deadline.elapsed():.3f}s "
              f"{'FEASIBLE' if not probs else 'INFEASIBLE: ' + '; '.join(probs)}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
