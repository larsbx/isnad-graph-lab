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
* ``phases``: ``[birth, death, hearing | null, teaching | null, phases]`` of a
  lifeline in half-years (every estimate is a multiple of ½), each phase
  ``[kind, from, to]``, as ``lives.phases`` computes it; narrators evenly
  spaced by id, plus every one where two of the six bounds coincide.
* ``common_link``: ``[companion, chains, strand, common_link | null]`` of a
  bundle, the chains as narrator ids below the Prophet, as
  ``analysis.strand`` and ``analysis.common_link`` compute them with their
  default ``dominance`` and ``min_chains`` (in ``parameters``); bundles evenly
  spaced in key order, plus every one whose strand meets a share exactly at
  ``dominance`` or a branching node with exactly ``min_chains`` chains.
* ``inference``: ``[mentions, matn_start | null, text, known, abstention | null,
  chain | null]`` as ``inference.abstention`` and ``inference.infer_source_chain``
  compute them, each mention ``[rawi_id | null, start, end]``. The graph keeps no
  raw mentions, so these are drawn from a seeded generator, over an alphabet
  that straddles every bound of the taḥwīl regex, with ties in position.
* ``stratified``: ``[strata, risk_ratio_mh | null, risk_ratio_status, z_cmh | null,
  p_exact | null, n_informative_strata]`` as ``assess.stratified_inference``
  computes them, each stratum ``[a, n1, b, n0]``: every published defect-lift
  comparison, recomputed from the graph, then seeded small tables (with
  empty, degenerate and one-sided strata).

The selection is a pure function of the graph, so the file is reproducible
byte for byte; ``tests/test_formal_vectors.py`` checks that it is current.
"""

from __future__ import annotations

import argparse
import inspect
import json
import random
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd

from isnad_graph.analysis import bundle_nodes, common_link, strand
from isnad_graph.assess import Defect, defect_lift, stratified_inference, structural_verdict
from isnad_graph.build import explode_links
from isnad_graph.graph import IsnadGraph
from isnad_graph.inference import Mention, abstention, infer_source_chain
from isnad_graph.lifespan import estimate
from isnad_graph.lives import link_windows, phases
from isnad_graph.schema import PROPHET_ID, Provenance

PER_VERDICT = 1500
INFERENCE_CASES, SEED = 3000, 0x2A
#: ح, Arabic letters and marks, and the characters just outside each range.
ALPHABET = "\u062d" * 2 + "\u0627\u064b\u0620\u0621\u065f\u0660\u066f\u0670\u06d3\u06d4 x1"
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


def _evenly(n: int, k: int) -> np.ndarray:
    """``k`` positions evenly spaced over ``range(n)``."""
    return np.unique(np.linspace(0, n - 1, min(k, n)).round().astype(int))


def _life(row: pd.Series) -> list:
    return [_int(row.birth_lo), _int(row.death_lo), _int(row.death_hi),
            row.birth_basis in ("recorded", "age"), row.death_basis == "recorded",
            bool(row.bio_conflict)]


def chronology_rows(narrators: pd.DataFrame, edges: pd.DataFrame,
                    per_verdict: int = PER_VERDICT, boundary: int = BOUNDARY) -> list[list]:
    n = narrators.set_index("id")[["birth_lo", "death_lo", "death_hi", "birth_basis",
                                   "death_basis", "bio_conflict"]]
    e = edges.sort_values(["src", "dst"], kind="stable").reset_index(drop=True)
    picks = [_evenly(len(g), per_verdict) for _, g in e.groupby("chronology", sort=True)]
    chosen = pd.concat([e[e.chronology.eq(v)].iloc[p] for (v, _), p in
                        zip(e.groupby("chronology", sort=True), picks, strict=True)])
    t, s = n.reindex(e.src).reset_index(drop=True), n.reindex(e.dst).reset_index(drop=True)
    tie = (s.birth_lo.eq(t.death_hi) | t.birth_lo.eq(s.death_hi)).fillna(False).to_numpy(bool)
    chosen = pd.concat([chosen, e[tie].head(boundary)]).drop_duplicates(["src", "dst"])
    chosen = chosen.sort_values(["src", "dst"], kind="stable")
    return [[_life(n.loc[a]), _life(n.loc[b]), v]
            for a, b, v in zip(chosen.src, chosen.dst, chosen.chronology, strict=True)]


def _half(v: float) -> int:
    if not float(2 * v).is_integer():
        raise ValueError(f"{v!r} is not a multiple of ½: the Lean model counts half-years")
    return int(2 * v)


def phase_rows(narrators: pd.DataFrame, edges: pd.DataFrame,
               per: int = PER_VERDICT, boundary: int = BOUNDARY) -> list[list]:
    n = estimate(narrators).set_index("id")
    placed = link_windows(n, edges).query("start <= end")
    win = lambda end: placed.groupby(end).agg(lo=("start", "min"), hi=("end", "max"))  # noqa: E731
    life = (n[["birth_est", "death_est"]].dropna().sort_index()
            .join(win("dst").add_prefix("h_")).join(win("src").add_prefix("t_")))
    six = np.sort(life.to_numpy(float), axis=1)  # NaN last; NaN never equals
    ties = life.index[(np.diff(six, axis=1) == 0).any(axis=1)][:boundary]
    chosen = life.loc[sorted({*life.index[_evenly(len(life), per)], *ties})]
    pair = lambda lo, hi: None if np.isnan(lo) else (float(lo), float(hi))  # noqa: E731, as lives.span
    half = lambda w: w and [_half(w[0]), _half(w[1])]  # noqa: E731
    return [[_half(b), _half(d), half(h), half(t),
             [[p["kind"], _half(p["from"]), _half(p["to"])] for p in phases(b, d, h, t)]]
            for b, d, h0, h1, t0, t1 in chosen.itertuples(index=False)
            for h, t in [(pair(h0, h1), pair(t0, t1))]]


def _defaults() -> tuple[Fraction, int]:
    p = inspect.signature(common_link).parameters
    return Fraction(str(p["dominance"].default)), p["min_chains"].default


def common_link_rows(chains: pd.DataFrame, per: int = PER_VERDICT,
                     boundary: int = BOUNDARY) -> list[list]:
    dom, min_chains = _defaults()
    rec = chains[chains.group_id.notna() & chains.provenance.eq(Provenance.RECORDED)
                 & chains.path.map(len).ge(2)]
    nodes = bundle_nodes(explode_links(rec))
    step = nodes[["top_share", "n_chains", "top_student", "top_n"]].to_dict("index")
    keys = nodes.index.droplevel("src").unique().sort_values()
    met = lambda g, b: filter(None, (step.get((g, b, x))  # noqa: E731
                                     for x in strand(step, g, b, float(dom))))
    edge = [(g, b) for g, b in keys if any(
        r["top_n"] * dom.denominator == dom.numerator * r["n_chains"] or r["n_chains"] == min_chains
        for r in met(g, b))][:boundary]
    chosen = sorted({*keys[_evenly(len(keys), per)], *edge})
    below = lambda p: [int(x) for x in (p[1:] if p[0] == PROPHET_ID else p)]  # noqa: E731
    paths = rec.assign(bundle=rec.path.str[1]).groupby(["group_id", "bundle"]).path
    return [[int(b), [below(p) for p in paths.get_group((g, b))],
             [int(x) for x in strand(step, g, b, float(dom))],
             None if (cl := common_link(step, g, b, float(dom), min_chains)) is None else int(cl)]
            for g, b in chosen]


def inference_rows(n: int = INFERENCE_CASES, seed: int = SEED) -> list[list]:
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        ms = [Mention(rng.choice([None, *range(1, 7)]), s := rng.randrange(12),
                      s + rng.randrange(1, 4)) for _ in range(rng.randrange(7))]
        matn = None if rng.random() < 0.08 else rng.randrange(16)
        text = "".join(rng.choices(ALPHABET, k=16))
        known = sorted(rng.sample(range(1, 7), rng.randrange(2, 7)))
        chain = infer_source_chain(ms, matn, text, known)
        rows.append([[list(m) for m in ms], matn, text, known, abstention(ms, matn, text, known),
                     None if chain is None else list(chain)])
    return rows


def stratified_rows(g: IsnadGraph, n: int = 400, seed: int = SEED) -> list[list]:
    reports = g.frame("hadiths").set_index("id")[["best_verdict", "shared_defects"]]
    grades = g.frame("external_grades")
    excluded = g.manifest["assessment"]["defect_lift_excludes"]
    published = [[[s["flagged_rejected"], s["flagged_total"], s["clean_rejected"], s["clean_total"]]
                  for s in strata] for strata in
                 defect_lift(reports, grades[~grades.collection.isin(excluded)]).strata]
    rng = random.Random(seed)
    table = lambda: [rng.randint(0, n1 := rng.randint(0, 30)), n1,  # noqa: E731
                     rng.randint(0, n0 := rng.randint(0, 30)), n0]
    seeded = [[table() for _ in range(rng.randint(1, 3))] for _ in range(n)]
    keys = ["risk_ratio_mh", "risk_ratio_status", "z_cmh", "p_exact", "n_informative_strata"]
    plain = lambda v: float(v) if isinstance(v, np.floating) else v  # noqa: E731
    return [[t, *(plain(r[k]) for k in keys)] for t in published + seeded
            for r in [stratified_inference([tuple(x) for x in t])]]


def vectors(g: IsnadGraph) -> dict:
    dom, min_chains = _defaults()
    return {"parameters": {"dominance": [dom.numerator, dom.denominator], "min_chains": min_chains},
            "verdict": verdict_rows(g.frame("chains")),
            "chronology": chronology_rows(g.frame("narrators"), g.frame("transmissions")),
            "phases": phase_rows(g.frame("narrators"), g.frame("transmissions")),
            "common_link": common_link_rows(g.frame("chains")),
            "inference": inference_rows(),
            "stratified": stratified_rows(g)}


def render(data: dict) -> str:
    rows = lambda v: ",\n".join(json.dumps(r, separators=(",", ":")) for r in v)  # noqa: E731
    one = lambda v: f"[\n{rows(v)}\n]" if isinstance(v, list) else json.dumps(v)  # noqa: E731
    return "{\n" + ",\n".join(f'"{k}": {one(v)}' for k, v in data.items()) + "\n}\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--graph", type=Path, default=Path("data/graph"))
    p.add_argument("--out", type=Path, default=OUT)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    data = vectors(IsnadGraph.load(a.graph))
    a.out.write_text(render(data), encoding="utf-8")
    print(f"{a.out}: " + ", ".join(f"{len(v)} {k}" for k, v in data.items() if isinstance(v, list)))


if __name__ == "__main__":
    main()
