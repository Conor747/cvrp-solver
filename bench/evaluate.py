import argparse
import concurrent.futures as cf
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from array import array

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench")
CACHE = os.path.join(BENCH, "cache")
RESULTS = os.path.join(BENCH, "results")
LIMITS = {"small": 30.0, "medium": 60.0, "large": 180.0}
WEIGHTS = {"small": 0.1, "medium": 0.3, "large": 0.6}

# CVRPLIB instances: vehicles = routes in the best-known solution (tight).
# Generated instances: the exact gen.py arguments, so they can be rebuilt.
SUITE = [
    dict(name="X-n101-k25",  group="core", size="small",  vrp="X-n101-k25",  bks=27591, vehicles=26),
    dict(name="X-n200-k36",  group="core", size="medium", vrp="X-n200-k36",  bks=58578, vehicles=36),
    dict(name="X-n303-k21",  group="core", size="medium", vrp="X-n303-k21",  bks=21736, vehicles=21),
    dict(name="X-n502-k39",  group="core", size="large",  vrp="X-n502-k39",  bks=69226, vehicles=39),
    dict(name="X-n801-k40",  group="core", size="large",  vrp="X-n801-k40",  bks=73311, vehicles=40),
    dict(name="X-n1001-k43", group="core", size="large",  vrp="X-n1001-k43", bks=72355, vehicles=43),
    dict(name="tight-100",   group="core", size="small",
         gen="--n 100 --seed 13 --route-size 10 --slack 0"),
    dict(name="tight-300c",  group="core", size="medium",
         gen="--n 300 --seed 12 --layout clustered --route-size 15 --slack 0"),
    dict(name="gen-2000c",   group="core", size="large",
         gen="--n 2000 --seed 7 --layout clustered --slack 1"),
    dict(name="gen-5000",    group="big",  size="large", gen="--n 5000 --seed 1 --slack 1"),
    dict(name="gen-10000",   group="big",  size="large", gen="--n 10000 --seed 1 --slack 1"),
]

def prepare(entry):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, entry["name"] + ".txt")
    if os.path.exists(path):
        return path
    tmp = f"{path}.{os.getpid()}.part"      # unique: harness runs may build in parallel
    if "vrp" in entry:
        convert_vrp(os.path.join(BENCH, "cvrplib", entry["vrp"] + ".vrp"), tmp,
                    entry["vehicles"], entry["size"])
    else:
        subprocess.run([sys.executable, os.path.join(ROOT, "gen.py"), "--size", entry["size"],
                        *entry["gen"].split(), "-o", tmp], check=True)
    try:
        os.replace(tmp, path)
    except OSError:
        # Windows: another harness run finished the same (identical) file
        # first and has it open. Use theirs.
        os.remove(tmp)
        if not os.path.exists(path):
            raise
    return path


def convert_vrp(src, dst, vehicles, size):
    text = open(src).read()
    capacity = int(re.search(r"CAPACITY\s*:\s*(\d+)", text).group(1))
    coords, demand, section = {}, {}, None
    for line in text.splitlines():
        t = line.split()
        if not t:
            continue
        if t[0].endswith("_SECTION") or t[0] == "EOF":
            section = t[0]
        elif section == "NODE_COORD_SECTION" and len(t) == 3:
            coords[int(t[0])] = (float(t[1]), float(t[2]))
        elif section == "DEMAND_SECTION" and len(t) == 2:
            demand[int(t[0])] = int(t[1])
    ids = sorted(coords)                    # node 1 is the depot in CVRPLIB
    with open(dst, "w", newline="\n") as f:
        f.write(size + "\n")
        f.write(" ".join(str(demand[i]) for i in ids) + "\n")
        for i in ids:
            xi, yi = coords[i]
            f.write(" ".join(str(int(math.hypot(xi - coords[j][0], yi - coords[j][1]) + 0.5))
                             for j in ids) + "\n")
        f.write(f"Capacity: {capacity}\nVehicles: {vehicles}\n")

class Inst:
    """Minimal independent reader (deliberately not cvrp/instance.py)."""
    def __init__(self, path):
        nums, keys = [], {}
        with open(path) as f:
            for line in f:
                m = re.findall(r"(capacity|vehicles)\s*:?\s*([-+]?[\d.]+(?:[eE][-+]?\d+)?)", line, re.I)
                for k, v in m:
                    keys[k.lower()] = float(v)
                if not m and any(ch.isdigit() for ch in line):
                    nums.append(line)
        self.demand = [float(x) for x in nums[0].split()]
        self.n = len(self.demand)
        flat = (float(x) for line in nums[1:] for x in line.split())
        self.dist = [array("d", (next(flat) for _ in range(self.n))) for _ in range(self.n)]
        # a missing line means unlimited (same convention as the solver)
        self.capacity = keys.get("capacity", sum(self.demand))
        self.vehicles = int(keys.get("vehicles", self.n - 1))


def check(inst, stdout):
    lines = [l.split() for l in stdout.strip().splitlines() if l.strip()]
    if not lines:
        return None, "no output"
    try:
        printed = float(lines[0][0])
        routes = [[int(x) for x in l] for l in lines[1:]]
    except (ValueError, IndexError):
        return None, "unparsable output"
    if len(routes) > inst.vehicles:
        return None, f"{len(routes)} routes > {inst.vehicles} vehicles"
    seen = []
    cost = 0.0
    d = inst.dist
    for r in routes:
        if len(r) < 2 or r[0] != 0 or r[-1] != 0:
            return None, f"route does not start and end at 0: {r[:5]}..."
        body = r[1:-1]
        if any(c == 0 or not 0 < c < inst.n for c in body):
            return None, "route visits the depot mid-way or an unknown vertex"
        if sum(inst.demand[c] for c in body) > inst.capacity + 1e-9:
            return None, "route over capacity"
        seen += body
        cost += sum(d[a][b] for a, b in zip(r, r[1:]))
    if sorted(seen) != list(range(1, inst.n)):
        return None, "customers not visited exactly once"
    if abs(printed - cost) > 0.01:
        return None, f"printed cost {printed} != route cost {cost:.2f}"
    return cost, None


def score(t, limit, cost, best):
    if cost is None:
        return 0.0
    if t > 1.5 * limit:
        return 0.25
    return 1.0 / (0.5 * (2 ** max(0.0, t / limit - 1) + cost / best))

def run_one(entry, path, limit, seed, params):
    cmd = [sys.executable, os.path.join(ROOT, "main.py"), path,
           "--time", f"{limit:g}", "--seed", str(seed)]
    env = dict(os.environ, CVRP_PARAMS=",".join(params)) if params else None
    t = time.perf_counter()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           timeout=1.5 * limit + 10)
        out, err = p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        out, err = "", "killed after 1.5x limit"
    return dict(instance=entry["name"], seed=seed, limit=limit,
                wall=round(time.perf_counter() - t, 3), stdout=out, stderr=err[-500:])


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def evaluate(args):
    entries = [e for e in SUITE if e["group"] in args.group
               and (not args.only or any(s in e["name"] for s in args.only))]
    if not entries:
        sys.exit("no instances selected")
    scale = 1.0 if args.full else args.scale
    print(f"{len(entries)} instances x {len(args.seeds)} seeds, "
          f"{'full limits' if scale == 1 else f'{scale:.0%} of each limit'}, {args.jobs} parallel"
          f"{', params ' + ' '.join(args.param) if args.param else ''}")

    paths = {e["name"]: prepare(e) for e in entries}
    jobs = [(e, s) for e in entries for s in args.seeds]
    jobs.sort(key=lambda j: -LIMITS[j[0]["size"]])          # long runs first
    raw = []
    with cf.ThreadPoolExecutor(args.jobs) as ex:
        futs = [ex.submit(run_one, e, paths[e["name"]], LIMITS[e["size"]] * scale, s, args.param)
                for e, s in jobs]
        for i, f in enumerate(cf.as_completed(futs), 1):
            r = f.result()
            raw.append(r)
            print(f"  [{i}/{len(futs)}] {r['instance']} seed {r['seed']}: {r['wall']:.1f}s", flush=True)

    runs = []
    for e in entries:
        inst = Inst(paths[e["name"]])
        for r in (r for r in raw if r["instance"] == e["name"]):
            cost, why = check(inst, r["stdout"])
            if why and r["stderr"]:
                why += f" | stderr: {r['stderr'].strip()[-200:]}"
            runs.append(dict(instance=e["name"], size=e["size"], n=inst.n, seed=r["seed"],
                             limit=r["limit"], wall=r["wall"], cost=cost, error=why))
    
    os.makedirs(RESULTS, exist_ok=True)
    best_path = os.path.join(RESULTS, "best_known.json")
    best = load_json(best_path, {})
    for e in entries:
        costs = [r["cost"] for r in runs if r["instance"] == e["name"] and r["cost"] is not None]
        cands = [c for c in [e.get("bks"), best.get(e["name"]), *costs] if c is not None]
        if cands:
            best[e["name"]] = min(cands)
    tmp = f"{best_path}.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(best, f, indent=1, sort_keys=True)
    os.replace(tmp, best_path)
    for r in runs:
        r["score"] = score(r["wall"], r["limit"], r["cost"], best.get(r["instance"], 1.0))

    result = dict(label=args.save, mode="full" if scale == 1 else f"scale {scale}",
                  seeds=args.seeds, jobs=args.jobs, params=args.param or [], runs=runs)
    report(result, best)
    if args.save:
        with open(os.path.join(RESULTS, args.save + ".json"), "w") as f:
            json.dump(result, f, indent=1)
        print(f"\nsaved as bench/results/{args.save}.json")

def summarize(runs, name):
    rs = [r for r in runs if r["instance"] == name]
    ok = [r for r in rs if r["cost"] is not None]
    costs = [r["cost"] for r in ok]
    return dict(rs=rs, ok=ok, costs=costs,
                mean=statistics.mean(costs) if costs else None,
                sd=statistics.stdev(costs) if len(costs) > 1 else 0.0,
                score=statistics.mean(r["score"] for r in rs))


def report(result, best):
    runs = result["runs"]
    names = list(dict.fromkeys(r["instance"] for r in runs))
    print(f"\n{'instance':12} {'n':>6} {'limit':>6} {'ok':>5} {'mean cost':>12} {'sd':>8} "
          f"{'gap':>7} {'max time':>9} {'score':>6}")
    for name in names:
        s = summarize(runs, name)
        r0 = s["rs"][0]
        maxwall = max(r["wall"] for r in s["rs"])
        gap = f"{100 * (s['mean'] / best[name] - 1):6.2f}%" if s["mean"] and name in best else "      -"
        mean = f"{s['mean']:12.1f}" if s["mean"] else f"{'-':>12}"
        print(f"{name:12} {r0['n'] - 1:6} {r0['limit']:5g}s {len(s['ok']):2}/{len(s['rs']):<2} {mean} "
              f"{s['sd']:8.1f} {gap} {maxwall:6.1f}s{' !' if maxwall > r0['limit'] else '  '} {s['score']:6.3f}")
        for r in s["rs"]:
            if r["error"]:
                print(f"    seed {r['seed']}: FAILED - {r['error']}")
    by_size = {}
    for r in runs:
        by_size.setdefault(r["size"], []).append(r["score"])
    parts = {k: statistics.mean(v) for k, v in by_size.items()}
    print("\nscore by class: " + ", ".join(f"{k} {v:.4f}" for k, v in sorted(parts.items())))
    w = sum(WEIGHTS[k] for k in parts)
    print(f"weighted (0.1/0.3/0.6 over classes present): {sum(WEIGHTS[k] * v for k, v in parts.items()) / w:.4f}")
    print("gap = mean cost vs best known; '!' = a run exceeded its limit")


def compare(a_name, b_name):
    a = load_json(os.path.join(RESULTS, a_name + ".json"), None)
    b = load_json(os.path.join(RESULTS, b_name + ".json"), None)
    if not a or not b:
        sys.exit("results not found in bench/results/")
    if (a["mode"], a["seeds"], a["jobs"]) != (b["mode"], b["seeds"], b["jobs"]):
        print(f"WARNING: different settings ({a['mode']}, {a['jobs']} jobs vs "
              f"{b['mode']}, {b['jobs']} jobs); differences may not be meaningful\n")
    for name, res in ((a_name, a), (b_name, b)):
        print(f"{name}: {' '.join(res.get('params') or []) or 'default parameters'}")
    print(f"\n{'instance':12} {a_name:>12} {b_name:>12} {'change':>9} {'noise':>8}")
    for name in dict.fromkeys(r["instance"] for r in a["runs"]):
        sa, sb = summarize(a["runs"], name), summarize(b["runs"], name)
        if not (sa["mean"] and sb["mean"]):
            print(f"{name:12} (failed runs, see the full reports)")
            continue
        diff = 100 * (sb["mean"] / sa["mean"] - 1)
        # standard error of the difference, in % of the mean
        se = 100 * math.sqrt(sa["sd"] ** 2 / len(sa["costs"]) + sb["sd"] ** 2 / len(sb["costs"])) / sa["mean"]
        flag = "  better" if diff < -2 * se else "  worse" if diff > 2 * se else ""
        print(f"{name:12} {sa['mean']:12.1f} {sb['mean']:12.1f} {diff:+8.2f}% {se:7.2f}%{flag}")
    print("\nchange = mean cost difference; 'better'/'worse' only when it exceeds 2x the noise")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="use the real time limits")
    ap.add_argument("--scale", type=float, default=0.25, help="share of each limit in quick mode")
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--jobs", type=int, default=4, help="runs in parallel")
    ap.add_argument("--group", nargs="+", default=["core"], help="core and/or big")
    ap.add_argument("--only", nargs="+", help="instances whose name contains any of these")
    ap.add_argument("--param", nargs="+", metavar="NAME=VALUE",
                    help="override search parameters, e.g. T_START=0.1 (see cvrp/search.py)")
    ap.add_argument("--save", help="store results under this name")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"))
    args = ap.parse_args()
    if args.compare:
        compare(*args.compare)
    else:
        evaluate(args)


if __name__ == "__main__":
    main()
