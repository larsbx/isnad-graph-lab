"""Conformance vectors for the Lean model, from the committed graph.

    python tools/export_vectors.py [--graph data/graph] [--out formal/vectors/conformance.json]

* ``verdict``: ``[worst_rank | null, gap, code]`` for the whole domain
  (rank unknown or 1–12, with and without a gap) as
  ``assess.structural_verdict`` computes it, and every combination stored on a
  chain of the graph.
* ``chronology``: ``[teacher, student, verdict]`` with each end as
  ``[birth_lo, death_lo, death_hi, birth_documented, death_recorded, conflict]``.
  For each verdict, links are taken evenly spaced over the edges in key order,
  plus every boundary link where a bound comparison is an equality.

The selection is a pure function of the graph, so the file is reproducible
byte for byte; ``tests/test_formal_vectors.py`` checks that it is current.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from isnad_graph.assess import Defect, structural_verdict
from isnad_graph.graph import IsnadGraph

PER_VERDICT = 1500
BOUNDARY = 1500
OUT = Path("formal/vectors/conformance.json")


def _int(v: object) -> int | None:
    if pd.isna(v):
        return None
    if not float(v).is_integer():
        raise ValueError(f"non-integral year {v!r}: the Lean model is over Int")
    return int(v)


def verdict_rows(chains: pd.DataFrame) -> list[list]:
    domain = [[r, g, int(structural_verdict(np.nan if r is None else r, g))]
              for r in [None, *range(1, 13)] for g in (False, True)]
    stored = (chains.assign(gap=(chains.defects.astype("int64") & int(Defect.GAP)).ne(0))
              [["worst_rank", "gap", "verdict"]].drop_duplicates()
              .sort_values(["worst_rank", "gap", "verdict"], na_position="first"))
    return domain + [[_int(w), bool(g), int(v)] for w, g, v in stored.itertuples(index=False)]


def _life(row: pd.Series) -> list:
    return [_int(row.birth_lo), _int(row.death_lo), _int(row.death_hi),
            row.birth_basis in ("recorded", "age"), row.death_basis == "recorded",
            bool(row.bio_conflict)]


def chronology_rows(narrators: pd.DataFrame, edges: pd.DataFrame,
                    per_verdict: int = PER_VERDICT, boundary: int = BOUNDARY) -> list[list]:
    n = narrators.set_index("id")[["birth_lo", "death_lo", "death_hi", "birth_basis",
                                   "death_basis", "bio_conflict"]]
    e = edges.sort_values(["src", "dst"], kind="stable").reset_index(drop=True)
    picks = [np.unique(np.linspace(0, len(g) - 1, min(per_verdict, len(g))).round().astype(int))
             for _, g in e.groupby("chronology", sort=True)]
    chosen = pd.concat([e[e.chronology.eq(v)].iloc[p] for (v, _), p in
                        zip(e.groupby("chronology", sort=True), picks, strict=True)])
    t, s = n.reindex(e.src).reset_index(drop=True), n.reindex(e.dst).reset_index(drop=True)
    tie = (s.birth_lo.eq(t.death_hi) | t.birth_lo.eq(s.death_hi)).fillna(False).to_numpy(bool)
    chosen = pd.concat([chosen, e[tie].head(boundary)]).drop_duplicates(["src", "dst"])
    chosen = chosen.sort_values(["src", "dst"], kind="stable")
    return [[_life(n.loc[a]), _life(n.loc[b]), v]
            for a, b, v in zip(chosen.src, chosen.dst, chosen.chronology, strict=True)]


def vectors(g: IsnadGraph) -> dict:
    return {"verdict": verdict_rows(g.frame("chains")),
            "chronology": chronology_rows(g.frame("narrators"), g.frame("transmissions"))}


def render(data: dict) -> str:
    rows = lambda k: ",\n".join(json.dumps(r, separators=(",", ":")) for r in data[k])  # noqa: E731
    return "{\n" + ",\n".join(f'"{k}": [\n{rows(k)}\n]' for k in data) + "\n}\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--graph", type=Path, default=Path("data/graph"))
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    data = vectors(IsnadGraph.load(a.graph))
    a.out.write_text(render(data), encoding="utf-8")
    print(f"{a.out}: {len(data['verdict'])} verdict, {len(data['chronology'])} chronology rows")


if __name__ == "__main__":
    main()
