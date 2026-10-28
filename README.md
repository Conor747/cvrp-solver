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

Open questions for the instructor (marked TODO in code):
- stdin or file input? (both supported)
- output cost precision/rounding (currently 2 decimals)
- how is each instance's time limit passed to our program? (prof: no fixed size
  ranges, each team picks its own sizes, so we cannot infer it from n)
- is numpy allowed? (would make parsing large matrices much faster)
