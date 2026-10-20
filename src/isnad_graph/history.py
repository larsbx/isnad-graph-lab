"""The graph over time and space: per century of transmission, chain-weighted.

An edge teacher → student is dated by its *terminus ante quem* — the earlier
of the two deaths (``lifespan``), the last year the transmission can have
happened — and counted by the chains it carries.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

VERDICTS = ("consistent", "implausible", "impossible", "conflict", "unknown")


def century(year: pd.Series) -> pd.Series:
    """AH year → century, counted from one (1–100 → 1)."""
    return ((year - 1) // 100 + 1).astype("Int16")


def weighted_median(values: pd.Series, weights: pd.Series) -> float:
    """The lower weighted median of the non-missing values; NaN if there are none."""
    keep = values.notna() & weights.gt(0)
    v, w = values[keep].to_numpy(float), weights[keep].to_numpy(float)
    if not v.size:
        return float("nan")
    order = np.argsort(v, kind="stable")
    cum = np.cumsum(w[order])
    return float(v[order][np.searchsorted(cum, cum[-1] / 2)])


def _dated(edges: pd.DataFrame) -> pd.DataFrame:
    return edges.assign(century=century(edges.ante_quem)).dropna(subset=["century"])


def century_profile(edges: pd.DataFrame) -> pd.DataFrame:
    """Per century: edges, chains, verdict shares, and how local transmission is —
    the share of chains between narrators of one city (where both are placed in
    one), and the chain-weighted median distance between homes."""
    e = _dated(edges)
    w, local = e.n_chains, e.same_city
    by = e.assign(**{f"_{v}": w * e.chronology.eq(v) for v in VERDICTS},
                  _local=w * local.fillna(False), _placed=w * local.notna(),
                  ).groupby("century")
    s = by.agg(n_edges=("src", "size"), n_chains=("n_chains", "sum"),
               _local=("_local", "sum"), _placed=("_placed", "sum"),
               **{f"_{v}": (f"_{v}", "sum") for v in VERDICTS})
    km = by[["distance_km", "n_chains"]].apply(
        lambda d: weighted_median(d.distance_km, d.n_chains))
    return (s.assign(median_km=km, same_city_share=s._local / s._placed,
                     **{f"{v}_share": s[f"_{v}"] / s.n_chains for v in VERDICTS})
            .loc[:, lambda d: ~d.columns.str.startswith("_")].reset_index())


def flows(edges: pd.DataFrame) -> pd.DataFrame:
    """Province → province flows of transmission per century."""
    return (_dated(edges).dropna(subset=["src_region", "dst_region"])
            .groupby(["century", "src_region", "dst_region"])
            .agg(n_edges=("src", "size"), n_chains=("n_chains", "sum")).reset_index())


def hubs(edges: pd.DataFrame, narrators: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """Per century, the ``k`` teacher home cities carrying the most chains."""
    home = narrators.set_index("id")[["home_uri", "home_place"]]
    e = _dated(edges).join(home, on="src").dropna(subset=["home_uri"])
    return (e.groupby(["century", "home_uri", "home_place"]).n_chains.sum().reset_index()
            .sort_values(["century", "n_chains"], ascending=[True, False], kind="stable")
            .groupby("century").head(k).reset_index(drop=True))


def _records(frame: pd.DataFrame) -> list[dict]:
    return [{k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in r.items()}
            for r in frame.astype(object).where(frame.notna(), None).to_dict("records")]


def summary(narrators: pd.DataFrame, edges: pd.DataFrame) -> dict:
    """The manifest's account of the temporal and geographic layer."""
    people = narrators[narrators.kind.eq("narrator")]
    w = people.n_chains
    ages = edges.student_age_at_teacher_death[edges.chronology.eq("consistent")].dropna()
    by_verdict = edges.groupby("chronology").n_chains.sum()
    return {
        "narrators": {
            "death_basis": people.death_basis.value_counts().to_dict(),
            "birth_basis": people.birth_basis.value_counts().to_dict(),
            "bio_conflict": int(people.bio_conflict.sum()),
            "home_level": people.home_level.value_counts().to_dict(),
            "chain_weighted_with_home": round(float(w[people.home_uri.notna()].sum() / w.sum()), 4),
            "chain_weighted_with_recorded_death": round(float(
                w[people.death_basis.eq("recorded")].sum() / w.sum()), 4),
            "place_tokens_unresolved": int(people.n_places_unresolved.sum()),
        },
        "chronology": {
            "edges": edges.chronology.value_counts().to_dict(),
            "chain_share": (by_verdict / by_verdict.sum()).round(4).to_dict(),
        },
        "student_age_at_teacher_death": {
            "n_edges": int(ages.size),
            "quantiles": {f"p{int(q * 100)}": float(ages.quantile(q))
                          for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
            "share_under_10": round(float(ages.lt(10).mean()), 4) if ages.size else None,
        },
        "by_century": _records(century_profile(edges)),
        "hubs": _records(hubs(edges, narrators, k=5)),
    }
