"""A narrator's life as a line through time, with the places of transmission on it.

For narrator *x* the line runs from the estimated birth to the estimated death
(``lifespan.estimate``). Every link to or from *x* whose lifespans fit
(``chronology == "consistent"``) has a window in which it can have happened,

    window(t → s) = [max(b(t) + A_TEACH, b(s) + A_HEAR), min(d(t), d(s))],

and a *year*, the window's midpoint. A link whose window the ages leave empty
(say, a teacher who died before *x* was five) is counted, not placed.
Grouped by the other narrator's home, the links become the line's *stops*:
the cities *x* heard in (role ``teacher``) and taught to (role ``student``),
each at the chain-weighted median year of its links, with the earliest and
latest of those years.

The line is coloured by *phase*: *hearing* spans the windows of *x*'s links
from teachers (earliest start to latest end), *teaching* those to students.
Each stretch of the life is ``hearing``, ``both``, ``teaching`` or ``quiet``
(neither). These phases are windows the dates allow, not events attested in a
source.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pandas as pd

from .lifespan import estimate
from .subgraph import _plain, _short

#: The political eras the AH axis is shaded by: [from, to).
ERAS = (
    {"name": "Prophetic", "from": -53, "to": 11},
    {"name": "Rāshidūn", "from": 11, "to": 41},
    {"name": "Umayyad", "from": 41, "to": 132},
    {"name": "ʿAbbāsid", "from": 132, "to": 334},
    {"name": "Buyid and Seljuq ʿAbbāsid", "from": 334, "to": 656},
    {"name": "After Baghdad's fall", "from": 656, "to": 1000},
)
STOPS_PER_ROLE = 8
#: Youngest age to hear: the 5th percentile of the documented ages of students
#: at their teacher's death (``history.summary``) is 5.
A_HEAR = 5
#: Youngest age to transmit, a modelling choice: twenty, the age al-Rāmahurmuzī
#: reports some held sufficient (he himself preferred fifty).
A_TEACH = 20


def era(year: float) -> str | None:
    return next((e["name"] for e in ERAS if e["from"] <= year < e["to"]), None)


def phases(birth: float, death: float, hearing: tuple[float, float] | None,
           teaching: tuple[float, float] | None) -> list[dict]:
    """The life cut by the hearing and teaching windows (clipped to it) into
    maximal stretches of one kind; contiguous, covering ``[birth, death]``."""
    clip = lambda v: min(max(v, birth), death)  # noqa: E731
    spans = {k: w and (clip(w[0]), clip(w[1])) for k, w in (("h", hearing), ("t", teaching))}
    cuts = sorted({birth, death, *(v for w in spans.values() if w for v in w)})
    inside = lambda w, a, b: bool(w) and w[0] <= a and b <= w[1]  # noqa: E731
    kinds = {(True, True): "both", (True, False): "hearing", (False, True): "teaching",
             (False, False): "quiet"}
    merged: list[dict] = []
    for a, b in pairwise(cuts):
        k = kinds[inside(spans["h"], a, b), inside(spans["t"], a, b)]
        if merged and merged[-1]["kind"] == k:
            merged[-1] = {**merged[-1], "to": b}
        else:
            merged.append({"kind": k, "from": a, "to": b})
    return merged


def _wmedian(values: pd.Series, weights: pd.Series) -> float:
    order = np.argsort(values.to_numpy())
    v, w = values.to_numpy()[order], weights.to_numpy()[order]
    return float(v[np.searchsorted(np.cumsum(w), w.sum() / 2)])


def _stops(links: pd.DataFrame, role: str, other: str, names: pd.Series,
           homes: pd.Series, place_names: pd.Series) -> list[dict]:
    placed = links.assign(uri=links[other].map(homes)).dropna(subset=["uri"])
    rows = []
    for uri, grp in placed.groupby("uri"):
        top = grp.sort_values("n_chains", ascending=False)[other].head(2)
        rows.append({"role": role, "uri": uri, "place": place_names.get(uri, uri),
                     "year": round(_wmedian(grp.year, grp.n_chains), 1),
                     "from": round(float(grp.year.min()), 1),
                     "to": round(float(grp.year.max()), 1),
                     "n_chains": int(grp.n_chains.sum()), "n_people": int(grp[other].nunique()),
                     "people": [_short(names.get(i, str(i))) for i in top]})
    return sorted(rows, key=lambda r: -r["n_chains"])[:STOPS_PER_ROLE]


def lifeline(g, narrator_id: int, *, narrators: pd.DataFrame | None = None,
             edges: pd.DataFrame | None = None, places: pd.DataFrame | None = None) -> dict:
    """One narrator's lifeline (see module doc). Frames may be passed in to share
    them across many narrators."""
    n = estimate(narrators if narrators is not None else g.frame("narrators")).set_index("id")
    e = edges if edges is not None else g.frame("transmissions")
    p = places if places is not None else g.frame("places")
    x = n.loc[narrator_id]
    mine = e[e.src.eq(narrator_id) | e.dst.eq(narrator_id)]
    ok = mine[mine.chronology.eq("consistent")]
    t, s = (n.reindex(ok[end].to_numpy()) for end in ("src", "dst"))
    lo = np.maximum(t.birth_est.to_numpy(float) + A_TEACH, s.birth_est.to_numpy(float) + A_HEAR)
    hi = np.minimum(t.death_est.to_numpy(float), s.death_est.to_numpy(float))
    ok = ok.assign(year=(lo + hi) / 2, start=lo, end=hi)
    unplaced = int((lo > hi).sum())
    ok = ok[lo <= hi]
    heard, taught = ok[ok.dst.eq(narrator_id)], ok[ok.src.eq(narrator_id)]
    names, homes = n.name, n.home_uri
    place_names = p.set_index("uri").name
    window = lambda f: (float(f.start.min()), float(f.end.max())) if len(f) else None  # noqa
    b, d = float(x.birth_est), float(x.death_est)
    basis = lambda k: {"lo": _plain(x[f"{k}_lo"]), "hi": _plain(x[f"{k}_hi"]),  # noqa: E731
                       "mid": _plain(x[f"{k}_est"]), "basis": x[f"{k}_basis"]}
    return {
        "id": int(narrator_id), "name": _short(x["name"], 6), "rank": _plain(x["rank"]),
        "known": x.nickname if isinstance(x.nickname, str) and x.nickname.strip() else None,
        "tabaka": None if pd.isna(x.tabaka) else int(x.tabaka),
        "birth": basis("birth"), "death": basis("death"),
        "home": x.home_place if isinstance(x.home_place, str) else None,
        "places": [place_names.get(u, u) for u in x.places],
        "death_place": place_names.get(x.death_uri) if isinstance(x.death_uri, str) else None,
        "phases": phases(b, d, window(heard), window(taught)),
        "stops": [*_stops(heard, "teacher", "src", names, homes, place_names),
                  *_stops(taught, "student", "dst", names, homes, place_names)],
        "n_links": len(mine), "n_unplaced": unplaced, "n_refuted": int(mine.chronology.isin(
            ["impossible", "implausible"]).sum()),
    }
