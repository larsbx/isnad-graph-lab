"""The text corpus and what is extracted from it beyond the isnad.

Corpus (``data/corpus/``, rebuilt locally, not committed):

* ``texts.parquet`` — every source report's full Arabic text with its isnad /
  matn offsets (715,790 reports, ≈ 410 M characters);
* ``translations.parquet`` — English translations of the seven canonical
  collections from hadith-api, keyed by source ``hadith_id`` where aligned.

Extracted into the graph (``data/graph/``, committed):

* ``alignments`` — external entry ↔ source report, with containment score;
* ``external_grades`` — modern gradings (al-Albānī, al-Arnaʾūṭ, Zubair ʿAlī
  Zaʾī, Aḥmad Shākir …) attached to source reports.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .align import align, order_consistency
from .source import HADITH_API_REVISION, HADITH_KG


class Edition(NamedTuple):
    book_id: int  # the source book it is aligned to
    cross_recension: bool = False  # different recension of the same work
    external_work: str | None = None
    source_work: str | None = None


EDITIONS = {
    "bukhari": Edition(1), "muslim": Edition(2), "tirmidhi": Edition(3),
    "abudawud": Edition(4), "ibnmajah": Edition(6), "malik": Edition(8),
    # hadith-api has al-Sunan al-Ṣughrā (al-Mujtabā); the source has al-Sunan al-Kubrā.
    "nasai": Edition(17, True, "al-Sunan al-Sughra (al-Mujtaba)", "al-Sunan al-Kubra"),
}


def load_edition(directory: Path, collection: str) -> pd.DataFrame:
    """One row per entry, Arabic and English side by side (the files are index-aligned)."""
    ara, eng = (json.loads((directory / f"{lang}-{collection}.json").read_text())["hadiths"]
                for lang in ("ara", "eng"))
    assert [a["hadithnumber"] for a in ara] == [e["hadithnumber"] for e in eng]
    return pd.DataFrame({
        "collection": collection,
        "entry": range(len(ara)),
        "hadithnumber": [str(e["hadithnumber"]) for e in eng],
        "arabicnumber": [None if (n := e.get("arabicnumber")) is None else str(n) for e in eng],
        "chapter": [e["reference"]["book"] for e in eng],
        "chapter_hadith": [e["reference"]["hadith"] for e in eng],
        "arabic": [a["text"] for a in ara],
        "english": [e["text"] for e in eng],
        "grades": [e["grades"] for e in eng],
    })


def align_editions(con: sqlite3.Connection, directory: Path,
                   editions: Mapping[str, Edition] = EDITIONS) -> tuple[pd.DataFrame, dict]:
    """All entries of all editions, with the aligned source ``hadith_id`` (or NA)."""
    frames, stats = [], {}
    for collection, ed in editions.items():
        entries = load_edition(directory, collection)
        rows = con.execute("SELECT id, nass, no_inbook FROM hadiths WHERE book_id = ?",
                           (ed.book_id,)).fetchall()
        diagnostics = {}
        matches = align({e: t for e, t in zip(entries.entry, entries.arabic, strict=True)
                         if t.strip()}, {i: t for i, t, _ in rows}, diagnostics=diagnostics)
        hit = pd.DataFrame(matches, columns=["entry", "hadith_id", "score"])
        hit = hit.join(pd.DataFrame.from_dict(diagnostics, orient="index"), on="entry")
        for col in ("runner_up_score", "score_margin", "tied_candidates", "text_relation"):
            if col not in hit:
                hit[col] = pd.Series(dtype=object)
        multiplicity = hit.groupby("hadith_id").entry.transform("size")
        hit["source_entry_count"] = multiplicity
        hit["alignment_status"] = "plausible"
        hit.loc[hit.tied_candidates.gt(1), "alignment_status"] = "ambiguous"
        qualified = entries.merge(hit, on="entry", how="left").assign(
            cross_recension=ed.cross_recension, source_book_id=ed.book_id,
            external_work=ed.external_work, source_work=ed.source_work,
            source_revision=HADITH_KG.revision,
            edition_id=f"fawazahmed0/hadith-api:eng-{collection}@{HADITH_API_REVISION}",
            arabic_edition_id=f"fawazahmed0/hadith-api:ara-{collection}@{HADITH_API_REVISION}",
            independently_verified=False)
        qualified["alignment_status"] = qualified.alignment_status.fillna("unmatched")
        frames.append(qualified)
        source_positions = {i: n for i, _, n in rows}
        positions = [source_positions[m.right] for m in matches]
        stats[collection] = {
            "book_id": ed.book_id, "entries": len(entries), "aligned": len(matches),
            "reports_covered": hit.hadith_id.nunique(), "reports_in_book": len(rows),
            "median_score": float(hit.score.median()) if len(hit) else None,
            "order_consistency": round(order_consistency(
                matches, dict(zip(entries.entry, entries.entry, strict=True)),
                {i: n for i, _, n in rows}), 4),
            "cross_recension": ed.cross_recension,
            "ambiguous": int(hit.tied_candidates.gt(1).sum()),
            "many_to_one_entries": int(multiplicity.gt(1).sum()),
            "equal_successive_positions": sum(
                a == b for a, b in pairwise(positions)),
        }
    return pd.concat(frames, ignore_index=True).astype({"hadith_id": "Int64"}), stats


PROVENANCE_COLUMNS = [
    "entry", "score", "cross_recension", "source_book_id", "source_revision",
    "external_work", "source_work",
    "edition_id", "arabic_edition_id", "alignment_status", "runner_up_score",
    "score_margin", "tied_candidates", "text_relation", "source_entry_count",
    "independently_verified",
]


def alignment_table(entries: pd.DataFrame) -> pd.DataFrame:
    columns = ["hadith_id", "collection", "hadithnumber", "arabicnumber", "chapter",
               "chapter_hadith", *PROVENANCE_COLUMNS]
    return entries.loc[entries.hadith_id.notna()].reindex(columns=columns).reset_index(drop=True)


def grade_table(entries: pd.DataFrame) -> pd.DataFrame:
    """Preserve each attribution, including unmatched and cross-recension entries."""
    columns = ["hadith_id", "collection", "hadithnumber", "grader", "grade",
               *PROVENANCE_COLUMNS]
    rows = []
    for record in entries.to_dict("records"):
        for grade in record["grades"]:
            rows.append({**{k: record.get(k) for k in columns},
                         "grader": grade["name"], "grade": grade["grade"]})
    return pd.DataFrame(rows, columns=columns).astype({"hadith_id": "Int64"})


def export_corpus(con: sqlite3.Connection, entries: pd.DataFrame, out: Path) -> Path:
    """Write the text corpus (Arabic source texts, English translations) as Parquet."""
    out.mkdir(parents=True, exist_ok=True)
    texts = pd.read_sql_query(
        """SELECT h.id AS hadith_id, h.book_id, b.name AS book, h.no_inbook, h.type,
                  h.matn AS hukm, h.nass AS text, h.matn_start AS isnad_end,
                  h.matn_end, h.taraf_nass AS taraf
           FROM hadiths h JOIN books b ON b.id = h.book_id ORDER BY h.id""",
        con, dtype_backend="numpy_nullable")
    pq.write_table(pa.Table.from_pandas(texts, preserve_index=False), out / "texts.parquet",
                   compression="zstd", compression_level=9, row_group_size=50_000)
    translations = entries[["hadith_id", "collection", "hadithnumber", "chapter", "english",
                            "arabic", *PROVENANCE_COLUMNS]].rename(columns={"english": "text_en",
                                                               "arabic": "text_ar_edition"})
    pq.write_table(pa.Table.from_pandas(translations, preserve_index=False),
                   out / "translations.parquet", compression="zstd", compression_level=19)
    return out
