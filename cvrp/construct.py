from .solution import Solution

def first_fit_decreasing(inst):
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


def clarke_wright(inst, nb=None):
    d, q, Q = inst.dist, inst.demand, inst.capacity
    custs = list(inst.customers)

    routes = {c: [c] for c in custs}
    load = {c: q[c] for c in custs}
    route_of = {c: c for c in custs}

    d0 = d[0]
    savings = []
    if nb is None:
        for a in range(len(custs)):
            i = custs[a]
            di, d0i = d[i], d0[i]
            for b in range(a + 1, len(custs)):
                j = custs[b]
                s = d0i + d0[j] - di[j]
                if s > 0:
                    savings.append((s, i, j))
    else:
        pairs = {(i, j) if i < j else (j, i) for i in custs for j in nb[i]}
        for i, j in pairs:
            s = d0[i] + d0[j] - d[i][j]
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
            A.reverse()
        if B[0] != j:
            B.reverse()
        merged = A + B

        keep, drop = (ri, rj) if len(A) >= len(B) else (rj, ri)
        for c in routes[drop]:
            route_of[c] = keep
        routes[keep] = merged
        load[keep] = load[ri] + load[rj]
        del routes[drop], load[drop]

    return Solution(list(routes.values()))
