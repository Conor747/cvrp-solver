# CVRP solver (prototype skeleton)

```
main.py              entry point: parse -> construct -> repair -> search -> print
cvrp/instance.py     tolerant streaming parser (file or stdin), compact array rows
cvrp/solution.py     routes (customers only, no depot), cost, self-check, output
cvrp/timer.py        wall-clock deadline from program start (85% of limit)
cvrp/neighbors.py    K nearest customers per customer, computed once, shared by all stages
cvrp/construct.py    clarke_wright (savings over neighbour pairs), first_fit_decreasing (crash fallback)
cvrp/repair.py       enforce_vehicle_limit: merge (+ejection) -> multi-start packing
cvrp/search.py       improvement until the deadline: ruin & recreate + granular local
                     search (relocate, swap, 2-opt, 2-opt*), simulated-annealing acceptance
gen.py               instance generator (deterministic per --seed)
bench/evaluate.py    evaluation harness: multi-seed runs, independent checker, spec scoring
samples/             spec example, 6-customer example, tight-vehicle edge case
```

Run: `python main.py samples/six_customers.txt --size small --debug`

Time limit: `--size small|medium|large` (30/60/180s) or `--time SECONDS`. With neither,
the solver assumes small (30s): the input file does not say its class, and overrunning
1.5x the limit costs far more than stopping early. The search stops at
L - max(2s, 5% of L): 28s / 57s / 171s. Startup + printing measured at ~0.05-0.4s.

Generate: `python gen.py --n 500 --seed 2 --layout clustered --slack 0 -o medium.txt`
(`python gen.py -h` for all options). Vehicles = FFD bin count + `--slack`, so every
instance is feasible; `--slack 0` gives the tightest ones. Record the exact command
and seed for each submitted dataset.

Evaluate (see `python bench/evaluate.py -h`):
```
python bench/evaluate.py --save before       # quick: 25% of each limit, 3 seeds (~4 min)
# ...change something...
python bench/evaluate.py --save after
python bench/evaluate.py --compare before after
python bench/evaluate.py --full              # real limits (~15 min)
python bench/evaluate.py --group big         # 5000 / 10000 customers
```
Each run is a separate process timed from outside; an independent checker validates
the output and scores it with the spec's formula. Benchmarks: 6 CVRPLIB X instances
(`bench/cvrplib/`, vehicles = routes of the best-known solution) plus generated ones,
rebuilt on demand in `bench/cache/`. Only compare runs made with the same settings.

Open questions for the instructor (marked TODO in code):
- stdin or file input? (both supported)
- output cost precision/rounding (currently 2 decimals)
- how is each instance's time limit passed to our program? (prof: no fixed size
  ranges, each team picks its own sizes, so we cannot infer it from n)
- is numpy allowed? (would make parsing large matrices much faster)
