"""K nearest customers of every customer.

Computed once and shared: Clarke-Wright only scores savings between
neighbours, repair packs customers next to neighbours, and the search only
tries moves between neighbours. This is what keeps every stage close to
O(n*K) instead of O(n^2) after the matrix has been read.
"""

import heapq


def neighbor_lists(inst, k):
    """nb[c] = up to k customers sorted by distance from c (depot excluded)."""
    d = inst.dist
    custs = list(inst.customers)
    k = min(k, len(custs) - 1)
    nb = [[] for _ in range(inst.n)]
    if k <= 0:
        return nb
    for c in custs:
        near = heapq.nsmallest(k + 1, custs, key=d[c].__getitem__)
        nb[c] = [x for x in near if x != c][:k]
    return nb
