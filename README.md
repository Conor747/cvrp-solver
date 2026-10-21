# CVRP solver (prototype skeleton)

```
main.py              entry point: parse -> construct -> repair -> search -> print
cvrp/instance.py     tolerant parser (file or stdin)
cvrp/solution.py     routes (customers only, no depot), cost, self-check, output
cvrp/timer.py        wall-clock deadline from program start (85% of limit)
cvrp/construct.py    clarke_wright (savings), first_fit_decreasing (crash fallback)
cvrp/repair.py       enforce_vehicle_limit: merge (+ejection) -> multi-start packing
cvrp/search.py       improvement until the deadline: ruin & recreate + granular local
                     search (relocate, swap, 2-opt, 2-opt*), simulated-annealing acceptance
gen.py               instance generator (deterministic per --seed)
samples/             spec example, 6-customer example, tight-vehicle edge case
```

Run: `python main.py samples/six_customers.txt --debug`

Generate: `python gen.py --n 500 --seed 2 --layout clustered --slack 0 -o medium.txt`
(`python gen.py -h` for all options). Vehicles = FFD bin count + `--slack`, so every
instance is feasible; `--slack 0` gives the tightest ones. Record the exact command
and seed for each submitted dataset.

Open questions for the instructor (marked TODO in code):
- stdin or file input? (both supported)
- output cost precision/rounding (currently 2 decimals)
- n thresholds for small / medium / large (timer.py placeholders)
- is numpy allowed? (would make parsing large matrices much faster)
