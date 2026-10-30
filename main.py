import argparse
import sys
import time
from cvrp import timer
from cvrp.instance import read_instance
from cvrp.construct import clarke_wright, first_fit_decreasing
from cvrp.neighbors import neighbor_lists
from cvrp.repair import enforce_vehicle_limit, quick_solution
from cvrp.search import improve

K_NEIGHBORS = 100
NB_SHARE = 0.5

def solve(inst, deadline, log=None, seed=0):
    if deadline.expired():
        if log:
            log(f"[setup] no time left after parsing ({deadline.elapsed():.1f}s): quick packing only")
        return quick_solution(inst)
    
    stop = time.perf_counter() + NB_SHARE * deadline.remaining()
    nb = neighbor_lists(inst, K_NEIGHBORS, stop_at=stop)
    if log:
        done = sum(1 for l in nb if l)
        if done < inst.n - 1:
            log(f"[setup] neighbour lists cut short: {done}/{inst.n - 1} customers")
    if deadline.expired():
        if log:
            log(f"[setup] no time left after neighbour lists ({deadline.elapsed():.1f}s): quick packing only")
        return quick_solution(inst)
    sol = clarke_wright(inst, nb)
    sol = enforce_vehicle_limit(inst, sol, deadline, nb)
    try:
        better = improve(inst, sol, deadline, nb=nb, seed=seed, log=log)
        if better.is_feasible(inst) or not sol.is_feasible(inst):
            sol = better
    except Exception as e:
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

    inst = read_instance(args.path)
    for note in inst.notes or []:
        print(f"warning: {note}", file=sys.stderr)

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
    except Exception as e:
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
