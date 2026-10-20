"""Derived annotations over links and chains (pure DataFrame → DataFrame)."""

from __future__ import annotations

import pandas as pd

from .lifespan import feasibility
from .schema import FLAG_COLUMNS, PROPHET_ID, Provenance
from .sigha import AMBIGUOUS, EXPLICIT, Mode

MODE_COLUMNS = {m: f"mode_{m.name.lower()}" for m in Mode}


def aggregate_transmissions(links: pd.DataFrame) -> pd.DataFrame:
    """Collapse per-chain links into one annotated edge per (teacher, student)."""
    flagged = links.assign(
        recorded=links.provenance.eq(Provenance.RECORDED),
        n_direct=links.flag.eq(0),
        **{col: (links.flag & int(f)).ne(0) for f, col in FLAG_COLUMNS.items()},  # Flag is iterable
    )
    counts = ["recorded", "n_direct", *FLAG_COLUMNS.values()]
    modes = (pd.crosstab([links.src, links.dst], links["mode"])
             .reindex(columns=[int(m) for m in Mode], fill_value=0)
             .rename(columns={int(m): c for m, c in MODE_COLUMNS.items()}))
    read = modes.drop(columns=MODE_COLUMNS[Mode.UNREAD])
    top = read.idxmax(axis=1).str.removeprefix("mode_").where(read.sum(axis=1).gt(0))
    return (
        flagged.groupby(["src", "dst"], sort=True)
        .agg(
            n_links=("chain_id", "size"),
            n_chains=("chain_id", "nunique"),
            n_hadiths=("hadith_id", "nunique"),
            n_books=("book_id", "nunique"),
            **{c: (c, "sum") for c in counts},
        )
        .rename(columns={"recorded": "n_recorded"})
        .assign(n_inferred=lambda d: d.n_links - d.n_recorded)
        .join(modes).assign(top_mode=top)
        .reset_index()
    )


def tadlis_risk(links: pd.DataFrame, narrators: pd.DataFrame) -> pd.Series:
    """Per chain: links where the student is a known mudallis and the formula is
    ambiguous (ʿan, anna, qāla …) — the classical ʿanʿana-of-a-mudallis defect."""
    mudallis = set(narrators.id[narrators.has_tadlis.fillna(False).astype(bool)])
    risky = links.dst.isin(mudallis) & links["mode"].isin([int(m) for m in AMBIGUOUS])
    return risky.groupby(links.chain_id).sum()


def hearing_profile(links: pd.DataFrame) -> pd.DataFrame:
    """Per narrator as student: share of read links with explicit hearing, and with ʿan."""
    read = links[links["mode"].ne(Mode.UNREAD)]
    flags = read.assign(explicit=read["mode"].isin([int(x) for x in EXPLICIT]),
                        an=read["mode"].eq(Mode.AN))
    return (flags.groupby("dst")
            .agg(n_links_read=("mode", "size"), explicit_share=("explicit", "mean"),
                 an_share=("an", "mean"))
            .rename_axis("id"))


def chronology(edges: pd.DataFrame, narrators: pd.DataFrame) -> pd.DataFrame:
    """Annotate edges with generation gap, death gap and lifespan feasibility
    (``lifespan.feasibility``; ``narrators`` carries ``lifespan.lifespans``)."""
    bio = narrators.set_index("id")[["tabaka", "death_year"]].astype("Float64")
    t, s = (bio.reindex(edges[end].to_numpy()).reset_index(drop=True) for end in ("src", "dst"))
    return feasibility(edges.assign(
        tabaka_delta=(s.tabaka - t.tabaka).astype("Int16").set_axis(edges.index),
        death_gap=(s.death_year - t.death_year).astype("Int32").set_axis(edges.index),
    ), narrators)


def common_links(links: pd.DataFrame, dominance: float = 0.8, min_chains: int = 3) -> pd.DataFrame:
    """Juynboll-style common links of each meaning group, per companion bundle.

    Chains of a group are bundled by their companion (the first narrator below
    the Prophet). Within a bundle a node's *top share* is the fraction of its
    chains carried on by its busiest student. Starting at the companion, the
    single strand is followed while the top share is ≥ ``dominance``; the first
    node where it is not is the bundle's *common link* (if it carries ≥
    ``min_chains`` chains). Every other node with ≥ 2 students and no dominant
    one is a *partial* common link. Returns one row per (partial) common link.
    """
    rec = links[links.group_id.notna() & links.provenance.eq(Provenance.RECORDED)]
    rec = rec.assign(bundle=rec.chain_id.map(
        rec[rec.depth.eq(0)].set_index("chain_id").dst)).dropna(subset=["bundle"])
    rec = rec[rec.src.ne(PROPHET_ID)]
    keys = ["group_id", "bundle", "src"]
    flows = rec.groupby([*keys, "dst"]).chain_id.nunique().rename("n").reset_index()
    best = flows.sort_values("n", ascending=False).drop_duplicates(keys).set_index(keys)
    nodes = (
        rec.groupby(keys)
        .agg(n_chains=("chain_id", "nunique"), fanout=("dst", "nunique"), depth=("depth", "median"))
        .join(best.rename(columns={"dst": "top_student", "n": "top_n"}))
        .assign(top_share=lambda d: d.top_n / d.n_chains)
    )
    bundle_size = rec.groupby(["group_id", "bundle"]).chain_id.nunique().rename("bundle_chains")
    nodes = nodes.join(bundle_size).assign(coverage=lambda d: d.n_chains / d.bundle_chains)

    step = nodes[["top_share", "n_chains", "top_student"]].to_dict("index")

    def descend(group_id, bundle) -> int | None:
        node, seen = bundle, set()
        while (row := step.get((group_id, bundle, node))) and node not in seen:
            seen.add(node)
            if row["top_share"] < dominance:
                return node if row["n_chains"] >= min_chains else None
            node = row["top_student"]
        return None

    cl = {(g, b, n) for g, b in bundle_size.index if (n := descend(g, b)) is not None}
    branching = nodes[nodes.fanout.ge(2) & nodes.top_share.lt(dominance)]
    return (
        branching.assign(is_common_link=[k in cl for k in branching.index])
        .reset_index().rename(columns={"src": "rawi_id"})
        .astype({"bundle": "int64", "rawi_id": "int64", "top_student": "int64"})
        .sort_values(["group_id", "bundle", "is_common_link", "n_chains"],
                     ascending=[True, True, False, False], ignore_index=True)
        .drop(columns="top_n")
    )
