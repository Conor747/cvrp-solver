"""K nearest customers of every customer.

Computed once and shared: Clarke-Wright only scores savings between
neighbours, repair packs customers next to neighbours, and the search only
tries moves between neighbours. This is what keeps every stage close to
O(n*K) instead of O(n^2) after the matrix has been read.
"""

import heapq
import random
import time


def neighbor_lists(inst, k, stop_at=None):
    """nb[c] = up to k customers sorted by distance from c (depot excluded).

    stop_at (a time.perf_counter() value): on huge instances with a short
    time limit, stop early and leave the remaining lists empty. Rows are
    processed in a fixed shuffled order, so the customers that do get a list
    are spread over the whole instance, and the others still appear in their
    neighbours' lists. Every later stage works with partial lists.
    """
    d = inst.dist
    custs = list(inst.customers)
    k = min(k, len(custs) - 1)
    nb = [[] for _ in range(inst.n)]
    if k <= 0:
        return nb
    order = custs
    if stop_at is not None:
        order = custs[:]
        random.Random(0).shuffle(order)
    for i, c in enumerate(order):
        if stop_at is not None and i % 32 == 0 and time.perf_counter() >= stop_at:
            break
        near = heapq.nsmallest(k + 1, custs, key=d[c].__getitem__)
        nb[c] = [x for x in near if x != c][:k]
    return nb
