"""The isnad tree of one report or meaning group, laid out for drawing.

Chains are merged into a DAG (teacher → student), layered by longest path from
the apex, ordered by barycentre sweeps, then placed so each node sits centred
on its students — the shape of the classical isnad diagram, Prophet at the top
(or left) and compilers at the leaves.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from itertools import pairwise
from statistics import mean
from typing import Any

import pandas as pd

from .assess import Defect
from .schema import PROPHET_ID, LinkFlag
from .sigha import Mode, mode_class

ROW = 1.0  # minimum gap between siblings in a layer, in layout units


def layers(edges: Iterable[tuple[int, int]], root: int) -> dict[int, int]:
    """Longest-path layer of every node reachable from ``root``; back edges
    (rare cycles in the source) are ignored."""
    succ: dict[int, list[int]] = defaultdict(list)
    for s, d in edges:
        succ[s].append(d)
    order: list[int] = []
    state: dict[int, int] = {}  # 1 visiting, 2 done
    stack = [(root, iter(succ[root]))]
    state[root] = 1
    while stack:
        node, it = stack[-1]
        nxt = next((d for d in it if state.get(d) != 1), None)
        if nxt is None:
            stack.pop()
            state[node] = 2
            order.append(node)
        elif nxt not in state:
            state[nxt] = 1
            stack.append((nxt, iter(succ[nxt])))
    layer = {root: 0}
    finished = {n: i for i, n in enumerate(order)}  # post-order: descendants first
    for node in reversed(order):  # topological order
        for d in succ[node]:
            if finished[d] < finished[node]:  # skip back edges
                layer[d] = max(layer.get(d, 0), layer[node] + 1)
    return layer


def positions(edges: Sequence[tuple[int, int]], layer: dict[int, int],
              sweeps: int = 6) -> dict[int, float]:
    """Vertical position within each layer: barycentre ordering, then parents
    centred over their children with at least :data:`ROW` between siblings."""
    succ, pred = defaultdict(list), defaultdict(list)
    for s, d in edges:
        if s in layer and d in layer and layer[d] > layer[s]:
            succ[s].append(d)
            pred[d].append(s)
    by_layer: dict[int, list[int]] = defaultdict(list)
    for n, k in sorted(layer.items(), key=lambda x: (x[1], x[0])):
        by_layer[k].append(n)
    depth = max(by_layer)
    rank = {n: i for k in by_layer for i, n in enumerate(by_layer[k])}
    for sweep in range(sweeps):
        down = sweep % 2 == 0
        for k in (range(1, depth + 1) if down else range(depth - 1, -1, -1)):
            near = pred if down else succ
            by_layer[k].sort(key=lambda n: mean(rank[m] for m in near[n]) if near[n]
                             else rank[n])
            rank.update({n: i for i, n in enumerate(by_layer[k])})
    y: dict[int, float] = {}
    for k in range(depth, -1, -1):  # leaves first; parents centred on children
        floor: float | None = None
        for n in by_layer[k]:
            want = (mean(y[c] for c in succ[n]) if succ[n]
                    else 0.0 if floor is None else floor + ROW)
            y[n] = floor = want if floor is None else max(want, floor + ROW)
    return y


def _short(name: str, words: int = 4) -> str:
    """First words of a nasab, never ending on a dangling «بن»."""
    w = str(name).split()[:words]
    while len(w) > 1 and w[-1] in ("بن", "بنت", "ابن"):
        w.pop()
    return " ".join(w)


def _plain(v: Any) -> Any:
    """JSON-ready scalar: NA → None, numpy → Python."""
    if v is None or (not isinstance(v, str | list | dict) and pd.isna(v)):
        return None
    return v.item() if hasattr(v, "item") else v


def _tree(chains: pd.DataFrame, narrators: pd.DataFrame, status: dict[int, str],
          books: pd.Series) -> dict[str, Any]:
    edges: dict[tuple[int, int], dict] = {}
    mudallis = narrators.has_tadlis.fillna(False).astype(bool)
    for row in chains.itertuples():
        path = list(map(int, row.path))
        for (s, d), m, f in zip(pairwise(path), row.modes, row.links, strict=True):
            e = edges.setdefault((s, d), {"src": s, "dst": d, "n": 0, "gap": 0, "tadlis": 0,
                                          "modes": defaultdict(int)})
            mode = Mode(int(m))
            e["n"] += 1
            e["modes"][mode.name.lower()] += 1
            e["gap"] += int(f != 0)
            e["tadlis"] += int(bool(mudallis.get(d, False)) and mode_class(mode) == "ambiguous")
    layer = layers(list(edges), PROPHET_ID)
    y = positions(list(edges), layer)
    col = lambda c, i: _plain(narrators[c].get(i))  # noqa: E731
    return {
        "nodes": [{"id": i, "name": _short(col("name", i) or "?"), "full": col("name", i),
                   "x": layer[i], "y": round(y[i], 3), "rank": col("rank", i),
                   "rank_no": col("rank_no", i), "death": col("death_year", i),
                   "mudallis": bool(mudallis.get(i, False)), "an_share": _plain(
                       None if pd.isna(narrators.an_share.get(i)) else
                       round(float(narrators.an_share.get(i)), 2)),
                   "cl": status.get(i)} for i in sorted(layer)],
        "edges": [{**e, "modes": dict(e["modes"]), "top": max(e["modes"], key=e["modes"].get)}
                  for e in edges.values() if e["src"] in layer and e["dst"] in layer],
        "chains": [{"path": list(map(int, r.path)), "modes": [int(m) for m in r.modes],
                    "book": _plain(books.get(r.book_id)), "verdict": int(r.verdict),
                    "defects": [d.name for d in Defect if d and int(r.defects) & d]}
                   for r in chains.itertuples()],
    }


def group_tree(g, group_id: int) -> dict[str, Any]:
    """A meaning group's recorded isnads as one laid-out tree per companion bundle
    (the narrator below the Prophet), largest bundle first — JSON-ready."""
    c = g.frame("chains")
    c = c[c.group_id.eq(group_id) & c.provenance.eq("recorded") & c.n_links.gt(0)]
    c = c.assign(bundle=c.path.map(lambda p: int(p[1]) if len(p) > 1 else int(p[0])))
    narrators = g.frame("narrators").set_index("id")
    books = g.frame("books").set_index("id").name
    cl = g.frame("common_links")
    cl = cl[cl.group_id.eq(group_id)]
    bundles = []
    for bundle, chains in sorted(c.groupby("bundle"), key=lambda x: -len(x[1])):
        here = cl[cl.bundle.eq(bundle)]
        status = {int(r.rawi_id): "common_link" if r.is_common_link else "partial"
                  for r in here.itertuples()}
        bundles.append({"companion": int(bundle),
                        "name": _short(narrators.name.get(bundle, "?")),
                        "n_chains": len(chains),
                        # the narrator below the Prophet is a successor: a mursal bundle
                        "mursal": bool(chains.links.map(lambda f: int(f[0]) & LinkFlag.IRSAL)
                                       .all()),
                        **_tree(chains, narrators, status, books)})
    return {"group_id": int(group_id),
            "text": str(g.frame("groups").set_index("id").nass.get(group_id, "")),
            "bundles": bundles}
