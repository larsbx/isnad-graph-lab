"""Source database → :class:`IsnadGraph`.

All SQL lives here; everything downstream is a pure function of DataFrames.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from collections.abc import Iterator, Mapping
from contextlib import closing
from datetime import UTC, datetime
from itertools import groupby
from operator import itemgetter
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .analysis import aggregate_transmissions, chronology, common_links
from .chains import Chain, normalize
from .graph import IsnadGraph
from .inference import Mention, abstention, infer_source_chain
from .schema import (
    MARKER_NAMES,
    PROPHET_DEATH_YEAR,
    PROPHET_ID,
    PROPHET_NAME,
    PROPHETIC_TYPES,
    LinkFlag,
    NodeKind,
    Provenance,
)
from .source import HADITH_KG, SourceSpec, connect


def read(con: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, dtype_backend="numpy_nullable")


def marker_flags(rawis: pd.DataFrame) -> Mapping[int, LinkFlag]:
    hits = rawis[rawis.name.isin(MARKER_NAMES)]
    return {int(i): MARKER_NAMES[n] for i, n in zip(hits.id, hits.name, strict=True)}


# ── chains ──────────────────────────────────────────────────────────────────

def _chain_row(chain: Chain, **meta) -> dict:
    return {**meta, "path": list(chain.path), "links": [int(f) for f in chain.links],
            "head_gap": int(chain.head_gap), "tail_gap": int(chain.tail_gap),
            "repeats": chain.repeats, "n_links": len(chain.links)}


def recorded_chains(con: sqlite3.Connection, markers: Mapping[int, LinkFlag]) -> pd.DataFrame:
    rows = con.execute("""
        SELECT s.id, h.type_no, sr.rawi_id FROM sanad_rawis sr
        JOIN sanads s ON s.id = sr.sanad_id JOIN hadiths h ON h.id = s.hadith_id
        ORDER BY sr.sanad_id, sr.pos""")
    chains = pd.DataFrame(
        _chain_row(normalize([r[2] for r in grp], markers, rows_type in PROPHETIC_TYPES),
                   sanad_id=sid)
        for (sid, rows_type), grp in groupby(rows, key=itemgetter(0, 1))
    )
    meta = read(con, """SELECT id AS sanad_id, hadith_id, matn_no AS isnad_hukm_no,
                        matn AS isnad_hukm, hukum AS isnad_verdict, takhrij,
                        max_rank AS source_max_rank FROM sanads""")
    return chains.merge(meta, on="sanad_id", validate="1:1").assign(
        provenance=Provenance.RECORDED.value)


def _mention_groups(con: sqlite3.Connection, where: str) -> Iterator[tuple]:
    rows = con.execute(f"""
        SELECT h.id, h.type_no, h.matn_start, substr(h.nass, 1, coalesce(h.matn_start, 0)),
               hr.rawi_id, hr.start, hr.end
        FROM hadiths h JOIN hadith_rawis hr ON hr.hadith_id = h.id
        WHERE {where} ORDER BY h.id, hr.seq""")
    for (hid, type_no, matn_start, isnad_text), grp in groupby(rows, key=itemgetter(0, 1, 2, 3)):
        yield hid, type_no, matn_start, isnad_text, [Mention(*r[4:]) for r in grp]


UNRECORDED = "h.id NOT IN (SELECT hadith_id FROM sanads)"


def inferred_chains(con, markers, known) -> tuple[pd.DataFrame, dict]:
    """Chains for reports without a recorded sanad (see :mod:`.inference`).

    A single-narrator chain (no link) is kept: it still attributes the report.
    """
    outcomes = [
        (hid, reason, None if reason else normalize(
            infer_source_chain(mentions, ms, text, known), markers, type_no in PROPHETIC_TYPES))
        for hid, type_no, ms, text, mentions in _mention_groups(con, UNRECORDED)
        for reason in (abstention(mentions, ms, text, known),)
    ]
    chains = [(hid, c) for hid, _, c in outcomes if c is not None and c.path]
    total, = con.execute(f"SELECT count(*) FROM hadiths h WHERE {UNRECORDED}").fetchone()
    stats = {
        "unrecorded_hadiths": total,
        "without_any_mention": total - len(outcomes),
        "abstained": dict(Counter(r for _, r, _ in outcomes if r)),
        "only_gap_markers": sum(1 for _, _, c in outcomes if c is not None and not c.path),
        "inferred_chains": len(chains),
        "single_narrator_chains": sum(1 for _, c in chains if not c.links),
    }
    frame = pd.DataFrame(_chain_row(c, hadith_id=h) for h, c in chains)
    return frame.assign(provenance=Provenance.INFERRED.value), stats


def validate_inference(con, markers, known) -> dict:
    """Score the inference rule against hadiths with exactly one recorded sanad.

    An inferred chain is exact if it equals the recorded chain with or without
    its pos-0 compiler (who is named in the text only by some compilations).
    """
    single = "(SELECT hadith_id FROM sanads GROUP BY 1 HAVING count(*) = 1)"
    truth = {h: tuple(r[1] for r in g) for h, g in groupby(con.execute(f"""
        SELECT s.hadith_id, sr.rawi_id FROM sanad_rawis sr JOIN sanads s ON s.id = sr.sanad_id
        WHERE s.hadith_id IN {single} ORDER BY s.hadith_id, sr.pos"""), key=itemgetter(0))}
    path = lambda c: normalize(c, markers, prophetic=False).path  # noqa: E731
    outcomes = Counter(
        "abstained" if src is None
        else "exact" if path(src) == path(truth[hid][1:])
        else "exact_with_compiler" if path(src) == path(truth[hid])
        else "mismatch"
        for hid, _, ms, text, mentions in _mention_groups(con, f"h.id IN {single}")
        for src in (infer_source_chain(mentions, ms, text, known),)
    )
    attempted = outcomes.total() - outcomes["abstained"]
    correct = outcomes["exact"] + outcomes["exact_with_compiler"]
    return {"evaluated": outcomes.total(), "attempted": attempted, **dict(outcomes),
            "precision": correct / max(attempted, 1),
            "coverage": attempted / max(outcomes.total(), 1)}


def explode_links(chains: pd.DataFrame) -> pd.DataFrame:
    cols = ["chain_id", "hadith_id", "book_id", "group_id", "provenance"]
    return pd.DataFrame(
        (*meta, s, d, f, i)
        for *meta, path, links in chains[[*cols, "path", "links"]].itertuples(index=False)
        for i, (s, d, f) in enumerate(zip(path[:-1], path[1:], links, strict=True))
    ).set_axis([*cols, "src", "dst", "flag", "depth"], axis=1)


# ── nodes ───────────────────────────────────────────────────────────────────

def _counts(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Missing count after a left join means zero."""
    return frame.fillna(dict.fromkeys(columns, 0)).astype(dict.fromkeys(columns, "int64"))


def narrator_table(rawis: pd.DataFrame, markers: Mapping[int, LinkFlag],
                   chains: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    prophet = pd.DataFrame([{"id": PROPHET_ID, "name": PROPHET_NAME, "nickname": "",
                             "death_year": PROPHET_DEATH_YEAR, "is_stub": 0}])
    nodes = pd.concat([prophet, rawis], ignore_index=True)
    kind = np.select(
        [nodes.id.eq(PROPHET_ID), nodes.id.isin(list(markers)), nodes.is_stub.eq(1)],
        [NodeKind.PROPHET.value, NodeKind.MARKER.value, NodeKind.STUB.value],
        NodeKind.NARRATOR.value)
    on_path = (chains[["chain_id", "hadith_id", "path"]].explode("path")
               .rename(columns={"path": "id"}))
    per_node = on_path.groupby("id").agg(n_chains=("chain_id", "nunique"),
                                         n_hadiths=("hadith_id", "nunique"))
    ends = chains.path.map(lambda p: (p[0], p[-1]))
    return (
        nodes.drop(columns="is_stub")
        .assign(kind=kind,
                tabaka=nodes.tabaka.mask(nodes.tabaka.eq(0)).astype("Int16"),
                rank_no=nodes.rank_no.mask(nodes.rank_no.eq(0)).astype("Int16"))
        .join(per_node, on="id")
        .join(edges.groupby("dst").src.nunique().rename("n_teachers"), on="id")
        .join(edges.groupby("src").dst.nunique().rename("n_students"), on="id")
        .join(ends.str[0].value_counts().rename("n_as_apex"), on="id")
        .join(ends.str[-1].value_counts().rename("n_as_compiler"), on="id")
        .pipe(_counts, ["n_chains", "n_hadiths", "n_teachers", "n_students",
                        "n_as_apex", "n_as_compiler"])
        .astype(dict.fromkeys(["is_bukhari", "is_muslim", "has_ikhtilat", "has_tadlis"], "boolean"))
    )


def build(db: Path, spec: SourceSpec = HADITH_KG, validate: bool = True) -> IsnadGraph:
    with closing(connect(db)) as con:
        rawis = read(con, "SELECT * FROM rawis")
        markers = marker_flags(rawis)
        known = frozenset(rawis.id.tolist())
        hadiths = read(con, """SELECT id, book_id, no_inbook, page_no, type_no, type,
                               matn_no AS hukm_no, matn AS hukm, group_id, takhrij,
                               matn_start, matn_end FROM hadiths""")
        inferred, inference_stats = inferred_chains(con, markers, known)
        chains = (
            pd.concat([recorded_chains(con, markers), inferred], ignore_index=True)
            .merge(hadiths[["id", "book_id", "group_id", "type_no"]]
                   .rename(columns={"id": "hadith_id", "type_no": "hadith_type_no"}),
                   on="hadith_id", how="left", validate="m:1")
            .sort_values(["hadith_id", "sanad_id"], na_position="last", kind="stable")
            .reset_index(drop=True)
        )
        chains.insert(0, "chain_id", range(len(chains)))
        chains = chains.astype({"sanad_id": "Int64", "group_id": "Int64", "takhrij": "Int64"})
        links = explode_links(chains)
        edges = aggregate_transmissions(links)
        narrators = narrator_table(rawis, markers, chains, edges)
        per_hadith = chains.pivot_table(index="hadith_id", columns="provenance",
                                        values="chain_id", aggfunc="size", fill_value=0)
        counts = [f"n_chains_{p}" for p in Provenance]
        hadiths = (hadiths.join(per_hadith.add_prefix("n_chains_"), on="id")
                   .reindex(columns=[*hadiths.columns, *counts]).pipe(_counts, counts))
        live = links[links.provenance.eq(Provenance.RECORDED) & links.src.eq(PROPHET_ID)]
        groups = (read(con, "SELECT * FROM meaning_groups")
                  .join(hadiths.groupby("group_id").agg(n_hadiths=("id", "size"),
                                                        n_books=("book_id", "nunique")), on="id")
                  .join(chains.groupby("group_id").chain_id.size().rename("n_chains"), on="id")
                  .join(live.groupby("group_id").dst.nunique().rename("n_companions"), on="id")
                  .pipe(_counts, ["n_hadiths", "n_books", "n_chains", "n_companions"]))
        graph = IsnadGraph(
            narrators=narrators,
            transmissions=chronology(edges, narrators),
            chains=chains,
            hadiths=hadiths,
            books=read(con, "SELECT * FROM books"),
            groups=groups,
            topics=read(con, "SELECT * FROM topics"),
            critics=read(con, "SELECT * FROM alems"),
            assessments=read(con, "SELECT * FROM aqwal"),
            common_links=common_links(links),
            manifest={
                "builder": f"isnad_graph {__version__}",
                "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "source": {"repo": spec.repo, "file": spec.filename,
                           "revision": spec.revision, "sha256": spec.sha256,
                           "license": spec.license,
                           "meta": dict(con.execute("SELECT key, value FROM meta"))},
                "markers": {str(k): v.name for k, v in sorted(markers.items())},
                "inferred_layer": inference_stats,
                "inference_validation": validate_inference(con, markers, known) if validate
                else None,
            },
        )
    return graph.with_manifest(counts=graph.counts(), invariants=graph.verify())
