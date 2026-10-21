"""Entry point.

Usage:
    python main.py instance.txt            # read from a file
    python main.py < instance.txt          # read from stdin
    python main.py instance.txt --time 30  # override the time limit
    python main.py instance.txt --debug    # self-check report on stderr

Answer goes to stdout; anything diagnostic goes to stderr so it never
pollutes the graded output.
"""

import argparse
import sys

from cvrp import timer                      # import first: starts the clock
from cvrp.instance import read_instance
from cvrp.construct import clarke_wright, first_fit_decreasing
from cvrp.repair import enforce_vehicle_limit
from cvrp.search import improve


def solve(inst, deadline, log=None):
    sol = clarke_wright(inst)
    sol = enforce_vehicle_limit(inst, sol, deadline)
    try:
        better = improve(inst, sol, deadline, log=log)
        if better.is_feasible(inst) or not sol.is_feasible(inst):
            sol = better
    except Exception as e:                  # keep the constructed solution
        print(f"search crashed: {e!r}; using constructed solution", file=sys.stderr)
    return sol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--time", type=float, default=None)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    inst = read_instance(args.path)
    limit = args.time if args.time is not None else timer.default_limit(inst.n)
    deadline = timer.Deadline(limit)

    try:
        log = (lambda msg: print(msg, file=sys.stderr)) if args.debug else None
        sol = solve(inst, deadline, log)
    except Exception as e:                  # never exit without an answer
        print(f"solver crashed: {e!r}; using fallback", file=sys.stderr)
        sol = first_fit_decreasing(inst)

    print(sol.format(inst))

    if args.debug:
        probs = sol.problems(inst)
        print(f"[debug] n={inst.n} routes={len(sol.routes)}/{inst.vehicles} "
              f"cost={sol.cost(inst):.2f} time={deadline.elapsed():.3f}s "
              f"{'FEASIBLE' if not probs else 'INFEASIBLE: ' + '; '.join(probs)}",
              file=sys.stderr)


if __name__ == "__main__":
    main()
