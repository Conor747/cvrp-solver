import heapq
import random
import time


def neighbor_lists(inst, k, stop_at=None):
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
