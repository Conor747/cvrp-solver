import math
import os
import random
from .neighbors import neighbor_lists
from .solution import Solution

K_NEIGHBORS = 20
EPS = 1e-9

#For ruin & recreate
AVG_REMOVED = 10
MAX_STRING = 10
BLINK_RATE = 0.01

#For simulated annealing
T_START = 1.0
T_END = 0.005

TUNABLE = ("K_NEIGHBORS", "AVG_REMOVED", "MAX_STRING", "BLINK_RATE", "T_START", "T_END")

def _apply_overrides():
    for item in filter(None, os.environ.get("CVRP_PARAMS", "").split(",")):
        name, _, value = item.partition("=")
        name = name.strip()
        if name in TUNABLE:
            try:
                kind = type(globals()[name])
                globals()[name] = kind(float(value)) if kind is int else float(value)
            except ValueError:
                pass

_apply_overrides()


class State:
    def __init__(self, inst, routes, slots):
        self.inst = inst
        self.routes = [list(r) for r in routes] + [[] for _ in range(slots - len(routes))]
        n = inst.n
        self.route_of = [-1] * n
        self.pos = [0] * n
        self.cum = [0.0] * n
        self.load = [0.0] * slots
        self.rcost = [0.0] * slots
        self.cost = 0.0
        for r in range(slots):
            self.refresh(r)

    def refresh(self, r):
        q, d = self.inst.demand, self.inst.dist
        route_of, pos, cum = self.route_of, self.pos, self.cum
        acc, c_cost, prev = 0.0, 0.0, 0
        for i, c in enumerate(self.routes[r]):
            route_of[c] = r
            pos[c] = i
            acc += q[c]
            cum[c] = acc
            c_cost += d[prev][c]
            prev = c
        c_cost += d[prev][0]
        self.load[r] = acc
        self.cost += c_cost - self.rcost[r]
        self.rcost[r] = c_cost

    def copy(self):
        s = State.__new__(State)
        s.inst = self.inst
        s.routes = [r[:] for r in self.routes]
        s.route_of = self.route_of[:]
        s.pos = self.pos[:]
        s.cum = self.cum[:]
        s.load = self.load[:]
        s.rcost = self.rcost[:]
        s.cost = self.cost
        return s

    def snapshot(self):
        return [r[:] for r in self.routes if r]


def descend(st, nb, queue, deadline):
    queue = list(queue)
    queued = set(queue)
    steps = 0
    while queue:
        steps += 1
        if steps & 255 == 0 and deadline.expired():
            return
        u = queue.pop()
        queued.discard(u)
        if st.route_of[u] < 0:
            continue
        touched = _improve_customer(st, nb[u], u)
        if touched:
            for c in touched:
                if c and c not in queued:
                    queue.append(c)
                    queued.add(c)


def _improve_customer(st, nbu, u):
    inst = st.inst
    d, q, Q = inst.dist, inst.demand, inst.capacity
    routes, route_of, pos, cum, load = st.routes, st.route_of, st.pos, st.cum, st.load

    ru = route_of[u]
    Ru = routes[ru]
    iu = pos[u]
    pu = Ru[iu - 1] if iu > 0 else 0
    nu = Ru[iu + 1] if iu + 1 < len(Ru) else 0
    du = d[u]
    qu = q[u]
    rem_u = d[pu][nu] - du[pu] - du[nu]

    for v in nbu:
        rv = route_of[v]
        if rv < 0:
            continue
        Rv = routes[rv]
        iv = pos[v]
        pv = Rv[iv - 1] if iv > 0 else 0
        nv = Rv[iv + 1] if iv + 1 < len(Rv) else 0
        dv = d[v]
        duv = du[v]
        same = ru == rv
        fits_u = same or load[rv] + qu <= Q

        if fits_u:
            if v != pu and rem_u + duv + du[nv] - dv[nv] < -EPS:
                _relocate(st, u, v, after=True)
                return (u, v, pu, nu, nv)
            if v != nu and rem_u + du[pv] + duv - d[pv][v] < -EPS:
                _relocate(st, u, v, after=False)
                return (u, v, pu, nu, pv)

        if (v != nu and v != pu) if same else \
                (load[ru] - qu + q[v] <= Q and load[rv] - q[v] + qu <= Q):
            delta = (d[pu][v] + dv[nu] - du[pu] - du[nu]
                     + d[pv][u] + du[nv] - dv[pv] - dv[nv])
            if delta < -EPS:
                Ru[iu], Rv[iv] = v, u
                st.refresh(ru)
                if not same:
                    st.refresh(rv)
                return (u, v, pu, nu, pv, nv)

        if same:
            if iu < iv:
                if v != nu and duv + d[nu][nv] - du[nu] - dv[nv] < -EPS:
                    Ru[iu + 1:iv + 1] = Ru[iu + 1:iv + 1][::-1]
                    st.refresh(ru)
                    return (u, v, nu, nv)
            elif v != pu and duv + d[pv][pu] - du[pu] - dv[pv] < -EPS:
                Ru[iv:iu] = Ru[iv:iu][::-1]
                st.refresh(ru)
                return (u, v, pu, pv)
        else:
            head_v = cum[v] - q[v]
            if (cum[u] + load[rv] - head_v <= Q and head_v + load[ru] - cum[u] <= Q
                    and duv + d[pv][nu] - du[nu] - dv[pv] < -EPS):
                A, B = Ru[:iu + 1] + Rv[iv:], Rv[:iv] + Ru[iu + 1:]
                routes[ru], routes[rv] = A, B
                st.refresh(ru)
                st.refresh(rv)
                return (u, v, nu, pv)
            if (cum[u] + cum[v] <= Q and load[ru] - cum[u] + load[rv] - cum[v] <= Q
                    and duv + d[nu][nv] - du[nu] - dv[nv] < -EPS):
                A = Ru[:iu + 1] + Rv[iv::-1]
                B = Ru[:iu:-1] + Rv[iv + 1:]
                routes[ru], routes[rv] = A, B
                st.refresh(ru)
                st.refresh(rv)
                return (u, v, nu, nv)
    return None


def _relocate(st, u, v, after):
    ru, rv = st.route_of[u], st.route_of[v]
    st.routes[ru].pop(st.pos[u])
    Rv = st.routes[rv]
    i = Rv.index(v)
    Rv.insert(i + 1 if after else i, u)
    st.refresh(ru)
    if rv != ru:
        st.refresh(rv)


def ruin(st, nb, rng):
    routes, route_of, pos = st.routes, st.route_of, st.pos
    used = [r for r in routes if r]
    avg_size = sum(map(len, used)) / len(used)
    lmax = min(MAX_STRING, avg_size)
    ks_max = 4 * AVG_REMOVED / (1 + lmax) - 1
    n_strings = max(1, int(rng.uniform(1, ks_max + 1)))

    seed = rng.randrange(1, st.inst.n)
    removed, ruined = [], set()
    for c in [seed] + nb[seed]:
        if len(ruined) >= n_strings:
            break
        r = route_of[c]
        if r < 0 or r in ruined:
            continue
        R = routes[r]
        length = int(rng.uniform(1, min(len(R), lmax) + 1))
        i = pos[c]
        start = rng.randint(max(0, i - length + 1), min(i, len(R) - length))
        seg = R[start:start + length]
        del R[start:start + length]
        for x in seg:
            route_of[x] = -1
        st.refresh(r)
        ruined.add(r)
        removed.extend(seg)
    return removed


def recreate(st, nb, removed, rng):
    inst = st.inst
    d, q, Q = inst.dist, inst.demand, inst.capacity
    routes, route_of, pos, load = st.routes, st.route_of, st.pos, st.load

    how = rng.randrange(4)
    if how == 0:
        rng.shuffle(removed)
    elif how == 1:
        removed.sort(key=lambda c: -q[c])
    elif how == 2:
        removed.sort(key=lambda c: -d[0][c])
    else:
        removed.sort(key=lambda c: d[0][c])

    empty = next((r for r, R in enumerate(routes) if not R), None)
    for c in removed:
        dc, qc = d[c], q[c]
        best, best_r, best_i = None, None, None
        for v in nb[c]:
            r = route_of[v]
            if r < 0 or load[r] + qc > Q:
                continue
            R = routes[r]
            i = pos[v]
            p = R[i - 1] if i > 0 else 0
            n = R[i + 1] if i + 1 < len(R) else 0
            if rng.random() >= BLINK_RATE:
                delta = dc[p] + dc[v] - d[p][v]
                if best is None or delta < best:
                    best, best_r, best_i = delta, r, i
            if rng.random() >= BLINK_RATE:
                delta = dc[v] + dc[n] - d[v][n]
                if best is None or delta < best:
                    best, best_r, best_i = delta, r, i + 1
        if empty is not None and (best is None or 2 * dc[0] < best):
            best, best_r, best_i = 2 * dc[0], empty, 0
        if best is None:
            best_r, best_i = _cheapest_anywhere(st, c)
            if best_r is None:
                return False
        routes[best_r].insert(best_i, c)
        st.refresh(best_r)
        if best_r == empty:
            empty = next((r for r, R in enumerate(routes) if not R), None)
    return True


def _cheapest_anywhere(st, c):
    d, qc, Q = st.inst.dist, st.inst.demand[c], st.inst.capacity
    dc = d[c]
    best, best_r, best_i = None, None, None
    for r, R in enumerate(st.routes):
        if not R or st.load[r] + qc > Q:
            continue
        prev = 0
        for i, nxt in enumerate(R + [0]):
            delta = dc[prev] + dc[nxt] - d[prev][nxt]
            if best is None or delta < best:
                best, best_r, best_i = delta, r, i
            prev = nxt
    return best_r, best_i

def improve(inst, sol, deadline, nb=None, seed=0, log=None):
    if inst.n <= 2 or not sol.routes:
        return sol
    rng = random.Random(seed)
    if nb is None:
        nb = neighbor_lists(inst, K_NEIGHBORS)
    else:
        nb = [l[:K_NEIGHBORS] for l in nb]

    slots = max(inst.vehicles, len(sol.routes))
    cur = State(inst, sol.routes, slots)
    start_cost = cur.cost
    descend(cur, nb, list(inst.customers), deadline)
    best, best_cost = cur.snapshot(), cur.cost
    after_ls = cur.cost

    n_used = sum(1 for r in cur.routes if r)
    avg_edge = cur.cost / (inst.n - 1 + n_used)
    if avg_edge <= 0:
        return Solution(best)
    t0, t1 = T_START * avg_edge, T_END * avg_edge
    begin, span = deadline.elapsed(), max(deadline.remaining(), 1e-9)

    iters = accepted = 0
    while not deadline.expired():
        iters += 1
        cand = cur.copy()
        removed = ruin(cand, nb, rng)
        if not recreate(cand, nb, removed, rng):
            continue
        descend(cand, nb, removed, deadline)

        frac = min(1.0, (deadline.elapsed() - begin) / span)
        temp = t0 * (t1 / t0) ** frac
        if cand.cost < cur.cost - temp * math.log(1.0 - rng.random()):
            cur = cand
            accepted += 1
            if cur.cost < best_cost - EPS:
                best, best_cost = cur.snapshot(), cur.cost

    if log:
        log(f"[search] start={start_cost:.1f} after-LS={after_ls:.1f} "
            f"best={best_cost:.1f} iters={iters} accepted={accepted}")
    return Solution(best)
