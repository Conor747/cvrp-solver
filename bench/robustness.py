import concurrent.futures as cf
import math
import os
import random
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from evaluate import Inst, check

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIMIT = 3.0

def euclid(pts, decimals=1):
    return [[round(math.hypot(a[0] - b[0], a[1] - b[1]), decimals) for b in pts] for a in pts]


def fmt(x):
    return f"{x:.6g}"


def instance(demand, dist, capacity, vehicles, header="small", matrix_fmt=fmt, extra=""):
    lines = [header] if header is not None else []
    lines.append(" ".join(fmt(q) for q in demand))
    lines += [" ".join(matrix_fmt(v) for v in row) for row in dist]
    if capacity is not None:
        lines.append(f"Capacity: {fmt(capacity)}")
    if vehicles is not None:
        lines.append(f"Vehicles: {vehicles}")
    return "\n".join(lines) + "\n" + extra


def random_case(n, seed, qmax=10, capacity=40, vehicles=None, decimals=1, scale=1000.0):
    rng = random.Random(seed)
    pts = [(rng.uniform(0, scale), rng.uniform(0, scale)) for _ in range(n + 1)]
    demand = [0] + [rng.randint(1, qmax) for _ in range(n)]
    if vehicles is None:
        vehicles = n
    return demand, euclid(pts, decimals), capacity, vehicles


def cases():
    """name -> (instance text, feasible?)"""
    c = {}
    d, m, q, v = random_case(30, 1)

    # --- impossible instances: must still print something well formed
    dd = d[:]; dd[5] = 999
    c["infeasible: one demand > capacity"] = (instance(dd, m, q, v), False)
    c["infeasible: too few vehicles"] = (instance(d, m, q, 1), False)
    c["infeasible: zero vehicles"] = (instance(d, m, q, 0), False)

    # --- tiny instances
    c["depot only"] = (instance([0], [[0]], 10, 1), True)
    c["one customer"] = (instance([0, 4], [[0, 7.5], [7.5, 0]], 10, 1), True)
    c["two customers, one vehicle"] = (instance([0, 3, 4], [[0, 1, 2], [1, 0, 1.5], [2, 1.5, 0]], 10, 1), True)

    # --- extreme capacities / fleets
    c["huge capacity: one route"] = (instance(d, m, 10**5, 1), True)
    dd = [0] + [30] * 30
    c["every customer needs its own route"] = (instance(dd, m, 40, 30), True)
    c["more vehicles than customers"] = (instance(d, m, q, 500), True)
    c["all demands zero"] = (instance([0] * 31, m, q, 1), True)
    c["exact fit: total demand = V x Q"] = (instance([0] + [5] * 30, m, 50, 3), True)

    # --- odd distances
    rng = random.Random(7)
    pts = [(rng.choice([0, 100, 200]), rng.choice([0, 100])) for _ in range(31)]
    c["duplicate points (zero distances)"] = (instance(d, euclid(pts), q, v), True)
    flat = [[0 if i == j else 50 for j in range(31)] for i in range(31)]
    c["all distances equal"] = (instance(d, flat, q, v), True)
    c["all distances zero"] = (instance(d, [[0] * 31 for _ in range(31)], q, v), True)
    _, big, _, _ = random_case(30, 1, scale=1e7)
    c["huge distances (1e7, sci notation)"] = (instance(d, big, q, v), True)
    _, tiny, _, _ = random_case(30, 1, scale=0.01, decimals=6)
    c["tiny distances (1e-3)"] = (instance(d, tiny, q, v), True)
    asym = [row[:] for row in m]
    for i in range(31):
        for j in range(31):
            if i != j:
                asym[i][j] = round(asym[i][j] * (1 + 0.01 * ((i * 7 + j) % 3)), 1)
    c["slightly asymmetric matrix"] = (instance(d, asym, q, v), True)
    _, rough, _, _ = random_case(30, 1)
    for i in range(31):
        for j in range(31):
            if i != j and (i + j) % 5 == 0:
                rough[i][j] = rough[j][i] = 9999.0   # breaks the triangle inequality
    c["non-metric distances"] = (instance(d, rough, q, v), True)

    # --- odd numbers and formatting
    df = [0] + [round(x * 0.37, 2) for x in d[1:]]
    c["fractional demands and capacity"] = (instance(df, m, 12.5, v), True)
    c["integer matrix"] = (instance(d, [[round(x) for x in row] for row in m], q, v,
                                    matrix_fmt=lambda x: str(int(x))), True)
    c["depot demand non-zero"] = (instance([7] + d[1:], m, q, v), True)
    txt = instance(d, m, q, v, header="LARGE").replace("\n", "\r\n").replace(" ", " \t ")
    c["CRLF, tabs, LARGE header"] = (txt, True)
    c["no header word"] = (instance(d, m, q, v, header=None), True)
    c["Capacity/Vehicles before demands"] = (
        f"medium\nVehicles: {v}\nCapacity: {q}\n" + instance(d, m, None, None, header=None), True)
    c["trailing junk text"] = (instance(d, m, q, v, extra="EOF\n\n"), True)
    c["missing Vehicles line"] = (instance(d, m, q, None), True)
    c["missing Capacity line"] = (instance(d, m, None, v), True)

    # --- medium-sized, tight
    d2, m2, _, _ = random_case(300, 3, qmax=30)
    total = sum(d2)
    c["300 customers, 99% full"] = (instance(d2, m2, math.ceil(total / 30 / 0.99), 30), None)
    return c


def run_case(name, text, feasible, tmpdir):
    path = os.path.join(tmpdir, f"{abs(hash(name))}.txt")
    with open(path, "w", newline="") as f:
        f.write(text)
    t = time.perf_counter()
    try:
        p = subprocess.run([sys.executable, os.path.join(ROOT, "main.py"), path, "--time", str(LIMIT)],
                           capture_output=True, text=True, timeout=LIMIT * 1.5 + 10)
        out, err, code = p.stdout, p.stderr, p.returncode
    except subprocess.TimeoutExpired:
        out, err, code = "", "timed out", None
    wall = time.perf_counter() - t

    problems = []
    if code != 0:
        problems.append(f"exit code {code}")
    if not out.strip():
        problems.append("no output")
    if wall > LIMIT:
        problems.append(f"took {wall:.1f}s > {LIMIT:g}s")
    if "crashed" in err:
        problems.append("internal crash (caught by a fallback)")
    verdict = ""
    if out.strip():
        try:
            inst = Inst(path)
            cost, why = check(inst, out)
        except Exception as e:
            cost, why = None, f"checker could not read instance ({e!r})"
        if feasible is True and why:
            problems.append(f"answer rejected: {why}")
        verdict = f"cost {cost:.1f}" if why is None else f"checker: {why}"
        lines = out.strip().splitlines()
        try:
            float(lines[0])
            for l in lines[1:]:
                r = [int(x) for x in l.split()]
                assert r[0] == 0 and r[-1] == 0
        except Exception:
            problems.append("output not well formed")
    return name, problems, verdict, wall, err.strip().splitlines()[-1:] if err.strip() else []


def main():
    filters = sys.argv[1:]
    selected = {k: v for k, v in cases().items() if not filters or any(f in k for f in filters)}
    with tempfile.TemporaryDirectory() as tmp, cf.ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda kv: run_case(kv[0], *kv[1], tmp), selected.items()))
    failed = 0
    for name, problems, verdict, wall, err in results:
        status = "FAIL" if problems else "ok  "
        failed += bool(problems)
        print(f"{status} {name:40} {wall:4.1f}s  {verdict}")
        for p in problems:
            print(f"       - {p}")
        if problems and err:
            print(f"       stderr: {err[0][:150]}")
    print(f"\n{len(results) - failed}/{len(results)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
