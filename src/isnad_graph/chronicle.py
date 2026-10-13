"""The Isnad Chronicle page: where and when transmission happened, by century.

    isnad-graph chronicle out/isnad-chronicle.html

It embeds:

* per century of transmission (``history``): the chains carried by teachers at
  home in each place, the busiest flows between two different homes, the
  century profile;
* the age-structure histogram of students at their teacher's death;
* the lifelines of the most-cited narrators (``lives``);
* the map's context: coast, rivers, lakes, roads (``basemap``).

It is stamped and reported like the Atlas (``atlas.stamp_page``).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from vizops.outcome import Outcome, Refused

from .atlas import stamp_page
from .basemap import BASEMAP_DIR, basemap
from .history import _records, century, century_profile
from .lives import A_HEAR, A_TEACH, ERAS, lifeline

TEMPLATE = Path(__file__).resolve().parent / "templates" / "chronicle.html"
PAGE = "isnad-chronicle"
#: Centuries carrying fewer chains than this are left off the slider.
MIN_CENTURY_CHAINS = 1000
TOP_FLOWS = 60
AGE_BINS = np.arange(0, 125, 5)
#: Lifelines embedded: the narrators on the most chains, with a death to anchor them.
LIVES = 300


def lives(g, k: int = LIVES) -> list[dict]:
    """Lifelines of the ``k`` narrators on the most chains whose death is known."""
    n, e, p = g.frame("narrators"), g.frame("transmissions"), g.frame("places")
    top = n[n.kind.eq("narrator") & n.death_basis.ne("none")].nlargest(k, "n_chains")
    return [{**lifeline(g, i, narrators=n, edges=e, places=p), "n_chains": int(c)}
            for i, c in zip(top.id, top.n_chains, strict=True)]


def payload(g, top_flows: int = TOP_FLOWS, min_chains: int = MIN_CENTURY_CHAINS,
            basemap_dir: Path = BASEMAP_DIR, k_lives: int = LIVES) -> dict:
    n = g.frame("narrators").set_index("id")
    e = g.frame("transmissions").assign(
        century=lambda d: century(d.ante_quem),
        src_home=lambda d: d.src.map(n.home_uri), dst_home=lambda d: d.dst.map(n.home_uri))
    profile = century_profile(e)
    centuries = profile.century[profile.n_chains.ge(min_chains)].astype(int).tolist()
    e = e[e.century.isin(centuries)]
    homes = (e.dropna(subset=["src_home"]).groupby(["century", "src_home"]).n_chains.sum())
    moves = (e.dropna(subset=["src_home", "dst_home"]).query("src_home != dst_home")
             .groupby(["century", "src_home", "dst_home"]).n_chains.sum().reset_index()
             .sort_values(["century", "n_chains"], ascending=[True, False], kind="stable")
             .groupby("century").head(top_flows))
    ok = e.chronology.eq("consistent")
    ages = e.student_age_at_teacher_death[ok].dropna()
    counts, _ = np.histogram(ages.clip(AGE_BINS[0], AGE_BINS[-1] - 1), AGE_BINS)
    places = g.frame("places")
    return {
        "centuries": centuries,
        "places": _records(places[["uri", "name", "translit", "lat", "lon", "region", "type",
                                   "n_home"]]),
        "homes": {int(c): {u: int(v) for u, v in s.droplevel(0).items()}
                  for c, s in homes.groupby(level=0)},
        "flows": {int(c): f[["src_home", "dst_home", "n_chains"]].values.tolist()
                  for c, f in moves.groupby("century")},
        "profile": _records(profile[profile.century.isin(centuries)]),
        "ages": {"bins": AGE_BINS.tolist(), "counts": counts.tolist(), "n": int(ages.size),
                 "median": float(ages.median()) if ages.size else None},
        "chronology": g.manifest.get("timeline_geography", {}).get("chronology", {}),
        "coverage": g.manifest.get("timeline_geography", {}).get("narrators", {}),
        "basemap": basemap(basemap_dir),
        "lives": lives(g, k_lives),
        "eras": list(ERAS),
        "ages_assumed": {"hear": A_HEAR, "teach": A_TEACH},
    }


def build(g, out: Path, min_chains: int = MIN_CENTURY_CHAINS,
          basemap_dir: Path = BASEMAP_DIR) -> Outcome:
    """Write the page — with the map's geographic context when the basemap files
    are fetched, without it otherwise — or say why not."""
    data = payload(g, min_chains=min_chains, basemap_dir=basemap_dir)
    if not data["centuries"] or g.places.num_rows == 0:
        return Refused(PAGE, "no geocoded, dated transmission to draw")
    return stamp_page(TEMPLATE, PAGE, data, "isnad_graph.chronicle.payload", out,
                      f"{len(data['centuries'])} centuries")


