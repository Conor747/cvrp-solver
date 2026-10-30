import bisect
import random
import time

from .neighbors import neighbor_lists
from .solution import Solution, route_load

PACK_NEIGHBORS = 30
MERGE_MAX_WORK = 2e7


def enforce_vehicle_limit(inst, sol: Solution, deadline=None, nb=None) -> Solution:
    routes = [list(r) for r in sol.routes if r]
    if len(routes) <= inst.vehicles:
        return Solution(routes)

    excess_work = (len(routes) - inst.vehicles) * inst.n
    if excess_work <= MERGE_MAX_WORK:
        merged = Solution(_merge_routes(inst, routes, deadline))
        if len(merged.routes) <= inst.vehicles:
            return merged
    else:
        merged = Solution(routes)

    if nb is None:
        nb = neighbor_lists(inst, PACK_NEIGHBORS)
    packed = _pack(inst, deadline, nb)
    excess = lambda s: max(0, len(s.routes) - inst.vehicles)
    return min((merged, packed), key=lambda s: (excess(s), s.cost(inst)))

QUICK_EXTRA_SECONDS = 2.0

def quick_solution(inst) -> Solution:
    q = inst.demand
    by_demand = sorted(inst.customers, key=lambda c: -q[c])
    bins = _best_fit(inst, by_demand)
    if len(bins) > inst.vehicles:
        stop = time.perf_counter() + QUICK_EXTRA_SECONDS
        rng = random.Random(0)
        attempt = _pack_once(inst, by_demand, "first", None)
        while True:
            if len(attempt) < len(bins):
                bins = attempt
            if len(bins) <= inst.vehicles or time.perf_counter() >= stop:
                break
            attempt = _best_fit(inst, sorted(inst.customers,
                                             key=lambda c: -q[c] * rng.uniform(0.7, 1.3)))
    return Solution([_order_route(inst.dist, b) for b in bins])


def _best_fit(inst, order):
    q, Q = inst.demand, inst.capacity
    free, ids = [], []
    bins = []
    for c in order:
        i = bisect.bisect_left(free, q[c])
        if i == len(free):
            b, room = len(bins), Q - q[c]
            bins.append([c])
        else:
            b, room = ids[i], free[i] - q[c]
            del free[i], ids[i]
            bins[b].append(c)
        j = bisect.bisect_left(free, room)
        free.insert(j, room)
        ids.insert(j, b)
    return bins

EJECT_CANDIDATES = 3

def _merge_routes(inst, routes, deadline):
    routes = [r[:] for r in routes]
    loads = [route_load(inst, r) for r in routes]
    while len(routes) > inst.vehicles:
        if deadline is not None and deadline.expired():
            break
        order = sorted(range(len(routes)), key=lambda k: (loads[k], len(routes[k])))
        attempts = [(k, False) for k in order] + \
                   [(k, True) for k in order[:EJECT_CANDIDATES]]
        for k, eject in attempts:
            result = _dissolve(inst, routes, loads, k, eject)
            if result is not None:
                routes, loads = result
                break
        else:
            break
    return routes


def _dissolve(inst, routes, loads, k, eject=False):
    q = inst.demand
    rest = [r[:] for i, r in enumerate(routes) if i != k]
    rest_loads = [l for i, l in enumerate(loads) if i != k]

    for c in sorted(routes[k], key=lambda c: -q[c]):
        best = _best_insertion(inst, rest, rest_loads, c)
        if best is not None:
            _, ri, p = best
            rest[ri].insert(p, c)
            rest_loads[ri] += q[c]
        elif not (eject and _eject_insert(inst, rest, rest_loads, c)):
            return None
    return rest, rest_loads

def _best_insertion(inst, routes, loads, c, skip=-1):
    d, Q, qc = inst.dist, inst.capacity, inst.demand[c]
    dc = d[c]
    best = None
    for ri, r in enumerate(routes):
        if ri == skip or loads[ri] + qc > Q:
            continue
        prev = 0
        for p, nxt in enumerate(r + [0]):
            delta = d[prev][c] + dc[nxt] - d[prev][nxt]
            if best is None or delta < best[0]:
                best = (delta, ri, p)
            prev = nxt
    return best


def _eject_insert(inst, routes, loads, c):
    d, q, Q = inst.dist, inst.demand, inst.capacity
    best = None
    for ri, r in enumerate(routes):
        over = loads[ri] + q[c] - Q
        for xi, x in enumerate(r):
            if q[x] < over:
                continue
            moved = _best_insertion(inst, routes, loads, x, skip=ri)
            if moved is None:
                continue
            prev = r[xi - 1] if xi > 0 else 0
            nxt = r[xi + 1] if xi + 1 < len(r) else 0
            removal = d[prev][nxt] - d[prev][x] - d[x][nxt]
            r_wo = r[:xi] + r[xi + 1:]
            placed = _best_insertion(inst, [r_wo], [loads[ri] - q[x]], c)
            if placed is None:
                continue
            total = removal + placed[0] + moved[0]
            if best is None or total < best[0]:
                best = (total, ri, xi, placed[2], moved[1], moved[2])
    if best is None:
        return False
    _, ri, xi, pc, rj, px = best
    x = routes[ri].pop(xi)
    routes[ri].insert(pc, c)
    loads[ri] += q[c] - q[x]
    routes[rj].insert(px, x)
    loads[rj] += q[x]
    return True


PACK_MODES = ("near", "first", "best")
PACK_BUDGET = 0.05
PACK_MAX_SECONDS = 3.0

def _pack(inst, deadline, nb, max_tries=300):
    q = inst.demand
    by_demand = sorted(inst.customers, key=lambda c: -q[c])
    rng = random.Random(0)
    budget = PACK_MAX_SECONDS
    if deadline is not None:
        budget = min(budget, max(0.0, deadline.remaining()) * PACK_BUDGET)
    stop = time.perf_counter() + budget
    
    best, best_key = None, None
    for t in range(max_tries):
        if t >= 1 and time.perf_counter() >= stop:
            break
        if t < len(PACK_MODES):
            order = by_demand
        else:
            order = sorted(inst.customers, key=lambda c: -q[c] * rng.uniform(0.7, 1.3))
        bins = _pack_once(inst, order, PACK_MODES[t % len(PACK_MODES)], nb)
        excess = max(0, len(bins) - inst.vehicles)
        if best_key is not None and excess > best_key[0]:
            continue
        sol = Solution([_order_route(inst.dist, b) for b in bins])
        key = (excess, sol.cost(inst))
        if best_key is None or key < best_key:
            best, best_key = sol, key
    return best


def _pack_once(inst, order, mode, nb):
    q, Q = inst.demand, inst.capacity
    bins, loads = [], []
    bin_of = {}
    for c in order:
        target = None
        if mode == "near":
            for v in nb[c]:
                b = bin_of.get(v)
                if b is not None and loads[b] + q[c] <= Q:
                    target = b
                    break
        if target is None:
            best = None
            for i, load in enumerate(loads):
                if load + q[c] > Q:
                    continue
                if mode != "best":
                    target = i
                    break
                if best is None or load > best:
                    target, best = i, load
        if target is None:
            target = len(bins)
            bins.append([])
            loads.append(0.0)
        bins[target].append(c)
        loads[target] += q[c]
        bin_of[c] = target
    return bins


def _order_route(d, custs):
    left = set(custs)
    route, cur = [], 0
    while left:
        nxt = min(left, key=lambda c: d[cur][c])
        route.append(nxt)
        left.remove(nxt)
        cur = nxt
    return _two_opt(d, route)


def _two_opt(d, route):
    tour = [0] + route + [0]
    improved = True
    while improved:
        improved = False
        for i in range(1, len(tour) - 2):
            for j in range(i + 1, len(tour) - 1):
                a, b, c, e = tour[i - 1], tour[i], tour[j], tour[j + 1]
                if d[a][c] + d[b][e] < d[a][b] + d[c][e] - 1e-9:
                    tour[i:j + 1] = tour[i:j + 1][::-1]
                    improved = True
    return tour[1:-1]
