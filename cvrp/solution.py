from dataclasses import dataclass, field

def route_cost(inst, route):
    if not route:
        return 0.0
    d = inst.dist
    c = d[0][route[0]] + d[route[-1]][0]
    for a, b in zip(route, route[1:]):
        c += d[a][b]
    return c


def route_load(inst, route):
    return sum(inst.demand[c] for c in route)


@dataclass
class Solution:
    routes: list = field(default_factory=list)

    def __post_init__(self):
        self.routes = [r for r in self.routes if r]

    def cost(self, inst):
        return sum(route_cost(inst, r) for r in self.routes)

    def problems(self, inst):
        out = []
        seen = [c for r in self.routes for c in r]
        if sorted(seen) != list(inst.customers):
            out.append("customers not visited exactly once")
        if len(self.routes) > inst.vehicles:
            out.append(f"{len(self.routes)} routes > {inst.vehicles} vehicles")
        for i, r in enumerate(self.routes):
            if route_load(inst, r) > inst.capacity:
                out.append(f"route {i} over capacity")
        return out

    def is_feasible(self, inst):
        return not self.problems(inst)

    def format(self, inst):
        lines = [f"{self.cost(inst):.2f}"]
        for r in self.routes:
            lines.append(" ".join(map(str, [0, *r, 0])))
        return "\n".join(lines)
