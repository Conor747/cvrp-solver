"""Build an initial solution."""

from .solution import Solution


def first_fit_decreasing(inst):
    """Safety-net constructor: bin-pack customers by demand.

    Ignores distance entirely, so it's poor on cost, but it finds a
    capacity-feasible packing with few routes. Used as the fallback
    when Clarke-Wright needs too many vehicles.
    """
    order = sorted(inst.customers, key=lambda c: -inst.demand[c])
    routes, loads = [], []
    for c in order:
        q = inst.demand[c]
        for i, load in enumerate(loads):
            if load + q <= inst.capacity:
                routes[i].append(c)
                loads[i] += q
                break
        else:
            routes.append([c])
            loads.append(q)
    return Solution(routes)


def clarke_wright(inst):
    """Clarke-Wright savings (parallel version).

    1. One route per customer: 0 -> c -> 0.
    2. saving s(i, j) = d[0][i] + d[0][j] - d[i][j] for every pair i < j.
    3. Scan pairs from largest saving to smallest. Merge the routes of
       i and j when:
         - they are on different routes,
         - i and j are both at an END of their route,
         - the combined load fits the capacity,
         - the saving is positive (otherwise stop: the rest are worse).
    4. Orient the routes so i is the tail of A and j the head of B,
       then join: A + B.

    Optimizes distance only; the vehicle limit is handled afterwards
    by repair.enforce_vehicle_limit().
    """
    d, q, Q = inst.dist, inst.demand, inst.capacity
    custs = list(inst.customers)

    routes = {c: [c] for c in custs}      # route id -> list of customers
    load = {c: q[c] for c in custs}       # route id -> total demand
    route_of = {c: c for c in custs}      # customer -> route id

    d0 = d[0]
    savings = []
    for a in range(len(custs)):
        i = custs[a]
        di, d0i = d[i], d0[i]
        for b in range(a + 1, len(custs)):
            j = custs[b]
            s = d0i + d0[j] - di[j]
            if s > 0:
                savings.append((s, i, j))
    savings.sort(reverse=True)

    for s, i, j in savings:
        ri, rj = route_of[i], route_of[j]
        if ri == rj:
            continue
        A, B = routes[ri], routes[rj]
        if i != A[0] and i != A[-1]:
            continue
        if j != B[0] and j != B[-1]:
            continue
        if load[ri] + load[rj] > Q:
            continue

        if A[-1] != i:
            A.reverse()                   # now ... -> i
        if B[0] != j:
            B.reverse()                   # now j -> ...
        merged = A + B

        # keep the larger route's id so we relabel fewer customers
        keep, drop = (ri, rj) if len(A) >= len(B) else (rj, ri)
        for c in routes[drop]:
            route_of[c] = keep
        routes[keep] = merged
        load[keep] = load[ri] + load[rj]
        del routes[drop], load[drop]

    return Solution(list(routes.values()))
