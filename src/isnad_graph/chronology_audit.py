"""Occurrence-level evidence for the chronology audit of a pinned graph."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from typing import NamedTuple

import numpy as np
import pandas as pd

from .arabic import normalize
from .assess import ACCEPTABLE, Defect, Verdict
from .inference import TAHWIL, Mention
from .schema import LinkFlag
from .sigha import read_gap


class Cause(StrEnum):
    MARKED_SUSPENSION = "source_marked_suspension"
    MARKED_GAP = "source_marked_gap"
    COMPILER_SUSPENSION = "reviewed_compiler_suspension"
    COMPILER_CONTEXT_CUT = "reviewed_compiler_context_cut"
    COMPILER_WRITTEN_CITATION = "reviewed_compiler_written_citation"
    INDIRECT_FORMULA = "explicit_indirect_formula"
    CO_NARRATORS = "inferred_co_narrators"
    INFERRED_SPLICE = "reviewed_inferred_splice"
    RECORDED_SPLICE = "reviewed_recorded_splice"
    IDENTITY_MISMATCH = "reviewed_identity_mismatch"
    DATE_RECORD_DISCREPANCY = "reviewed_date_record_discrepancy"
    DOCUMENTED_CONFLICT = "reviewed_documented_date_conflict"
    IDENTITY_CANDIDATE = "possible_identity_collision"
    COMPILER_CANDIDATE = "suspected_compiler_boundary"
    INFERRED_UNRESOLVED = "inferred_connection_unresolved"
    DIRECT_DATE_CANDIDATE = "direct_wording_dates_disjoint_unverified"
    UNRESOLVED = "unresolved"


COMPILER_REVIEWS = frozenset(
    {
        Cause.COMPILER_SUSPENSION,
        Cause.COMPILER_CONTEXT_CUT,
        Cause.COMPILER_WRITTEN_CITATION,
    }
)
REVIEWABLE = COMPILER_REVIEWS | {
    Cause.INFERRED_SPLICE,
    Cause.RECORDED_SPLICE,
    Cause.IDENTITY_MISMATCH,
    Cause.DATE_RECORD_DISCREPANCY,
    Cause.DOCUMENTED_CONFLICT,
}
QUARANTINED = frozenset(
    {
        Cause.CO_NARRATORS,
        Cause.COMPILER_CONTEXT_CUT,
        Cause.INFERRED_SPLICE,
        Cause.RECORDED_SPLICE,
        Cause.IDENTITY_MISMATCH,
        Cause.DATE_RECORD_DISCREPANCY,
    }
)
MARKED = frozenset({Cause.MARKED_SUSPENSION, Cause.MARKED_GAP})
ADDED_GAPS = {
    Cause.INDIRECT_FORMULA: LinkFlag.INQITA,
    Cause.COMPILER_SUSPENSION: LinkFlag.TALIQ,
}
EXPLAINED = MARKED | ADDED_GAPS.keys() | {Cause.COMPILER_WRITTEN_CITATION}
UNRESOLVED = frozenset(
    {
        Cause.IDENTITY_CANDIDATE,
        Cause.COMPILER_CANDIDATE,
        Cause.INFERRED_UNRESOLVED,
        Cause.DIRECT_DATE_CANDIDATE,
        Cause.UNRESOLVED,
    }
)


@dataclass(frozen=True)
class TextEvidence:
    start: int | None = None
    end: int | None = None
    formula: str = ""
    co_narrators: bool = False
    indirect_formula: bool = False
    explicit_pair: bool = False
    co_narrator_witness: str = ""


# These are whole intervening phrases. In particular, the vocalized passive
# حُدِّثْتُ must be distinguished from حَدَّثْتُ (I narrated).
_RECEIVING = frozenset(
    {
        "حدثنا",
        "حدثني",
        "اخبرنا",
        "اخبرني",
        "انبانا",
        "انباني",
        "ثنا",
        "نا",
        "سمعت",
        "سمعنا",
    }
)
_INDIRECT = frozenset(
    {
        "بلغني ان",
        "قال بلغني ان",
        "بلغنا ان",
        "قال بلغنا ان",
        "انه بلغه ان",
        "انها بلغها ان",
    }
)
_PASSIVE = unicodedata.normalize("NFC", "حُدِّثْتُ")


def source_prefix(
    text: str, boundary: int | None, mentions: Sequence[Mention]
) -> tuple[Mention, ...] | None:
    """Keep unlinked mentions and reject overlapping or uncertain intervals."""
    if boundary is None or not 0 < boundary <= len(text):
        return None
    prefix = tuple(sorted((m for m in mentions if m.start < boundary), key=lambda m: m.start))
    if any(not 0 <= m.start < m.end <= boundary for m in prefix):
        return None
    if any(a.end > b.start for a, b in pairwise(prefix)):
        return None
    return prefix


def adjacent_evidence(
    text: str, mentions: Sequence[Mention], student: int, teacher: int
) -> TextEvidence:
    """Inspect unique named endpoints in this report's own text and text order."""
    students = [i for i, m in enumerate(mentions) if m.rawi_id == student]
    teachers = [i for i, m in enumerate(mentions) if m.rawi_id == teacher]
    if len(students) != 1 or teachers != [students[0] + 1]:
        return TextEvidence()

    def name_only(mention: Mention) -> bool:
        # Some upstream offsets swallow multiple names and receiving clauses.
        # In that case the formulas between spans attach to different subjects.
        tokens = normalize(text[mention.start : mention.end]).split()
        return not any(
            token in _RECEIVING or (token[0] in "وف" and token[1:] in _RECEIVING)
            for token in tokens
        )

    i = students[0]
    if not name_only(mentions[i]) or not name_only(mentions[i + 1]):
        return TextEvidence()
    start, end = mentions[i].end, mentions[i + 1].start
    raw = text[start:end]
    formula = normalize(raw)
    # Keep the literal vocalization for the passive rule, folding punctuation.
    vocalized = re.sub(r"[،,:؛.]", " ", unicodedata.normalize("NFC", raw)).split()
    passive = formula in {"حدثت ان", "قال حدثت ان"} and vocalized[-2:-1] == [_PASSIVE]
    indirect = formula in _INDIRECT or passive

    # A receiving verb introduces the first of two names and a dual verb
    # introduces their common teacher. Mere adjacency or a conjunction is weak.
    before = text[mentions[i - 1].end : mentions[i].start] if i else text[: mentions[i].start]
    after = text[mentions[i + 1].end : mentions[i + 2].start] if i + 2 < len(mentions) else ""
    dual, _, receiving = normalize(after).partition(" ")
    co_narrators = (
        formula in {"", "و"}
        and normalize(before) in _RECEIVING
        and dual == "قالا"
        and receiving in _RECEIVING
        and mentions[i + 2].rawi_id is not None
        and mentions[i + 2].rawi_id not in {teacher, student}
        and name_only(mentions[i + 2])
    )
    witness_start = mentions[i - 1].end if i else 0
    witness = text[witness_start : mentions[i + 2].end] if co_narrators else ""
    return TextEvidence(start, end, raw, co_narrators, indirect, formula in _RECEIVING, witness)


def alias_index(narrators: pd.DataFrame) -> dict[str, set[int]]:
    """Aliases from the same source, with collisions retained."""
    aliases: dict[str, set[int]] = defaultdict(set)
    for rid, name, nickname in narrators[["id", "name", "nickname"]].itertuples(index=False):
        for spelling in (name, nickname):
            if pd.notna(spelling) and (key := normalize(spelling)):
                aliases[key].add(int(rid))
    return aliases


def compiler_matches(
    books: pd.DataFrame, narrators: pd.DataFrame, aliases: Mapping[str, set[int]]
) -> dict[int, int]:
    """Strict book-author metadata match. The source's author_no is a different ID space."""
    dates = narrators.set_index("id").death_year.dropna().to_dict()
    matched = {}
    for bid, author, death in books[["id", "author_name", "author_death_year"]].itertuples(
        index=False
    ):
        if pd.isna(author) or pd.isna(death):
            continue
        candidates = {rid for rid in aliases.get(normalize(author), ()) if dates.get(rid) == death}
        if len(candidates) == 1:
            (matched[int(bid)],) = candidates
    return matched


def alternate_names(
    text: str, mentions: Sequence[Mention], aliases: Mapping[str, set[int]]
) -> dict[int, set[int]]:
    """Find long, exact alternate aliases for review. Never relink on this test."""
    candidates: dict[int, set[int]] = defaultdict(set)
    for rid, start, end in mentions:
        if rid is None:
            continue
        key = normalize(text[start:end])
        matches = aliases.get(key, set())
        if len(key.split()) >= 4 and rid not in matches:
            candidates[rid].update(matches)
    return candidates


def classify(
    flag: int,
    inferred: bool,
    at_author_boundary: bool,
    text: TextEvidence,
    identity_candidate: bool,
    reviewed: Cause | None = None,
) -> Cause:
    if flag & LinkFlag.TALIQ:
        return Cause.MARKED_SUSPENSION
    if flag:
        return Cause.MARKED_GAP
    if reviewed is not None:
        return reviewed
    if inferred and text.co_narrators:
        return Cause.CO_NARRATORS
    if inferred and text.indirect_formula:
        return Cause.INDIRECT_FORMULA
    if identity_candidate:
        return Cause.IDENTITY_CANDIDATE
    if at_author_boundary:
        return Cause.COMPILER_CANDIDATE
    if inferred:
        return Cause.INFERRED_UNRESOLVED
    return Cause.DIRECT_DATE_CANDIDATE if text.explicit_pair else Cause.UNRESOLVED


def usable_prefix(
    text: str, boundary: int | None, mentions: Sequence[Mention]
) -> tuple[Mention, ...]:
    prefix = source_prefix(text, boundary, mentions)
    if prefix is None or TAHWIL.search(text[:boundary]):
        return ()
    # The formula parser also recognizes glued route switches such as حوحدثنا.
    gaps = (text[a.end : b.start] for a, b in pairwise((Mention(None, 0, 0), *prefix)))
    return () if any(read_gap(gap).tahwil for gap in gaps) else prefix


def report_exposure(chains: pd.DataFrame, confirmed_ids: set[int]) -> pd.Series:
    """Exposure across acceptable routes, under the audit's direct-link screen."""
    acceptable = chains[chains.verdict.isin(ACCEPTABLE)]
    confirmed = acceptable.chain_id.isin(confirmed_ids)
    possible = (acceptable.defects & int(Defect.CHRONOLOGY)).ne(0)
    if (confirmed & ~possible).any():
        raise ValueError("confirmed chronology must also be present in the replay")
    by_report = acceptable.assign(confirmed=confirmed, possible=possible).groupby("hadith_id")
    shared = by_report[["confirmed", "possible"]].all()
    result = pd.Series("unflagged_by_screen", index=shared.index, name="chronology_exposure")
    result.loc[shared.possible] = "unresolved"
    result.loc[shared.confirmed] = "documented_conflict"
    return result


class Replay(NamedTuple):
    chains: pd.DataFrame
    excluded: pd.Series
    retained: pd.Series
    new_gap: pd.Series


def replay_assessment(chains: pd.DataFrame, hits: pd.DataFrame) -> Replay:
    """Change chronology and add documented gaps using committed ranks and verdicts."""
    quarantined = hits.loc[hits.cause.isin(QUARANTINED), "chain_id"]
    excluded = hits.chain_id.isin(quarantined)
    retained = ~excluded & ~hits.cause.isin(EXPLAINED)
    new_gap = hits.cause.map(ADDED_GAPS).where(~excluded).fillna(0).astype(int)
    out = chains.loc[~chains.chain_id.isin(quarantined)].copy()
    adds_gap = out.chain_id.isin(hits.loc[new_gap.ne(0), "chain_id"])
    still_flagged = out.chain_id.isin(hits.loc[retained, "chain_id"])
    out["defects"] = (
        (out.defects & ~int(Defect.CHRONOLOGY))
        | np.where(still_flagged, int(Defect.CHRONOLOGY), 0)
        | np.where(adds_gap, int(Defect.GAP), 0)
    )
    # A documented gap caps an otherwise acceptable verdict (assess.structural_verdict).
    out.loc[adds_gap, "verdict"] = out.loc[adds_gap, "verdict"].clip(lower=int(Verdict.DAIF))
    return Replay(out, excluded, retained, new_gap)
