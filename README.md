# CVRP Solver — CS602 Group Project

A heuristic solver for the Capacitated Vehicle Routing Problem (CVRP), a data
generator, and our submitted test datasets.

## Requirements

- Python 3 (tested with 3.13)
- No third-party packages: everything uses the Python standard library, so
  `pip install -r requirements.txt` installs nothing.

## Running the solver

From the repository root:

```
python main.py <instance file>
```

The instance can also be given on stdin: `python main.py < instance.txt`.

The time limit comes from the size word on the first line of the instance
(`small` 30s, `medium` 60s, `large` 180s; any capitalization). The solver
stops its search at L − max(2s, 5% of L) — 28s / 57s / 171s — so it always
finishes inside the limit. If the word is missing or unknown it assumes
`small` (30s).

Optional flags (not needed for grading):

| Flag | Effect |
|---|---|
| `--size small\|medium\|large` | override the size word in the file |
| `--time SECONDS` | override the time limit directly |
| `--seed N` | random seed for the search (default 0) |
| `--debug` | print a feasibility and timing report to stderr |

Example: `python main.py samples/spec_example.txt`

### Input format

```
small
0 2 2 3
0 2.5 5.6 6.0
2.5 0 3.9 6.5
5.6 3.9 0 5.2
6.0 6.5 5.2 0
Capacity: 5
Vehicles: 2
```

1. The size word (`small`, `medium` or `large`).
2. Customer demands, depot first (always 0).
3. The symmetric n × n distance matrix, one row per line; vertex 0 is the depot.
4. `Capacity: Q` and `Vehicles: V`.

The parser is tolerant of extra spaces, blank lines, scientific notation,
the Capacity/Vehicles lines in either order, and matrix rows wrapped over
several lines.

### Output format

Only the answer is written to stdout: the total cost on the first line, then
one route per line, each starting and ending at the depot (0). Warnings and
`--debug` output go to stderr. For the example above:

```
21.80
0 1 0
0 2 3 0
```

The cost is printed to 2 decimal places.

## How the algorithm works

1. **Parse** the instance, storing the matrix as compact arrays.
2. **Neighbour lists:** the 100 nearest customers of each customer, computed
   once and shared by every later stage.
3. **Construct** an initial solution with Clarke-Wright savings, scoring only
   neighbour pairs.
4. **Enforce the vehicle limit:** if there are too many routes, dissolve the
   lightest routes into the others (with one-customer ejection); if that gets
   stuck, use multi-start bin packing with each route ordered by nearest
   neighbour + 2-opt.
5. **Improve until the deadline:** ruin and recreate (remove strings of nearby
   customers, reinsert them greedily), then granular local search (relocate,
   swap, 2-opt, 2-opt* over the 20 nearest neighbours), with simulated-annealing
   acceptance. The best solution found is printed.

Safety nets: on very large inputs the neighbour lists are capped at half the
remaining time, and if setup has used up the limit the solver answers at once
with a quick demand packing. If anything crashes, a first-fit-decreasing
solution is printed instead, so the program always outputs an answer.

## Generating instances

`gen.py` writes one instance. The same command and seed always produce the
same file.

```
python gen.py --size medium --n 500 --seed 2 --layout clustered --slack 0 -o medium.txt
```

Customers are placed on a square grid (`--layout uniform` or `clustered`) and
distances are Euclidean, written with at most 6 significant digits. The number
of vehicles is the first-fit-decreasing bin count plus `--slack`, so every
instance is feasible; `--slack 0` gives the tightest ones. Run
`python gen.py -h` for all options.

## Submitted datasets

One instance per size class. Customers are spread uniformly over the grid, and
the number of vehicles is exactly the bin-packing minimum (no spare vehicle).

| File | Class | Customers | Vehicles | Capacity |
|---|---|---|---|---|
| `small_uniform_5300.txt` | small | 5,300 | 530 | 155 |
| `medium_uniform_7500.txt` | medium | 7,500 | 743 | 155 |
| `large_uniform_12900.txt` | large | 12,900 | 1,284 | 155 |

The exact command, seed and SHA-256 checksum of each file are in
[datasets/MANIFEST.md](datasets/MANIFEST.md). To rebuild them (about 1.4 GB,
written to `datasets/out/`):

```
python datasets/make_datasets.py                # generate missing files + MANIFEST.md
python datasets/make_datasets.py --run          # also run the solver on each
python datasets/make_datasets.py --run --only large
```

`--run` runs `python main.py` on each dataset with its own time limit (30s /
60s / 180s), saves the solver's output to `datasets/out/<name>.out`, and
reports how long each run took.

## Repository layout

```
main.py                    entry point: parse -> construct -> repair -> search -> print
cvrp/instance.py           input parser (file or stdin)
cvrp/timer.py              deadline measured from program start
cvrp/neighbors.py          K nearest customers per customer
cvrp/construct.py          Clarke-Wright savings; first-fit-decreasing fallback
cvrp/repair.py             vehicle-limit repair; emergency quick packing
cvrp/search.py             ruin & recreate + granular local search
cvrp/solution.py           routes, cost, feasibility check, output format
gen.py                     instance generator
datasets/make_datasets.py  builds the submitted datasets and can run the solver on them
datasets/MANIFEST.md       command, seed and checksum of each dataset
samples/                   small example instances
```

## Open questions for the instructor

- Output cost precision: currently 2 decimal places.
