"""Isnad assessment: a structural verdict per chain, the defects read from the
texts, and a test of those defects against independent expert gradings.

The **structural verdict** follows the source's own rule — the weakest
narrator's grade (Ibn Ḥajar-style rank 1–12) decides, and any gap makes the
isnad at best ḍaʿīf. It reproduces the source's per-chain verdicts closely,
which validates the graph; it cannot see *how* each link was transmitted.

The **defects** add what the texts say: ʿan (or anna, qāla …) by a known
mudallis, and links the narrators' dates make impossible. Whether a defect
matters is an empirical question, answered per grader by :func:`defect_lift`:
among reports whose structural verdict is acceptable, does "every acceptable
route carries the defect" raise the rate at which the grader rejects them?
"""

from __future__ import annotations

import re
from enum import IntEnum, IntFlag
from typing import NamedTuple

import numpy as np
import pandas as pd

from .sigha import AMBIGUOUS


class Verdict(IntEnum):  # the source's isnad verdict codes (sanads.matn_no)
    SAHIH = 0
    HASAN = 1
    DAIF = 2
    VERY_DAIF = 3  # شديد الضعف
    ACCUSED = 4  # فيه متهم بالوضع
    MAWDU = 5  # موضوع


ACCEPTABLE = frozenset({Verdict.SAHIH, Verdict.HASAN})  # maqbūl


class Defect(IntFlag):
    NONE = 0
    GAP = 1  # irsāl, inqiṭāʿ, taʿlīq or an unnamed narrator
    TADLIS = 2  # ʿan/anna/qāla … by a mudallis graded thiqa (rank ≤ 3)
    TADLIS_WEAK = 4  # … by a mudallis graded ṣadūq or below (rank ≥ 4)
    CHRONOLOGY = 8  # student born after the teacher died


def structural_verdict(worst_rank: float, gap: bool) -> Verdict:
    """Verdict from the weakest narrator's rank (1 companion … 12 fabricator)."""
    v = (Verdict.SAHIH if not worst_rank > 3 else Verdict.HASAN if worst_rank <= 6
         else Verdict.DAIF if worst_rank <= 9 else Verdict.VERY_DAIF if worst_rank == 10
         else Verdict.ACCUSED if worst_rank == 11 else Verdict.MAWDU)
    return max(v, Verdict.DAIF) if gap else v


def assess_chains(chains: pd.DataFrame, links: pd.DataFrame, narrators: pd.DataFrame,
                  edges: pd.DataFrame) -> pd.DataFrame:
    """Per chain: weakest rank on the path, structural verdict and defects."""
    n = narrators.set_index("id")
    rank = n.rank_no.astype("float64")
    mudallis = n.has_tadlis.fillna(False).astype(bool)
    impossible = edges.set_index(["src", "dst"]).chronology.eq("impossible")
    student_rank = links.dst.map(rank)
    by_mudallis = links.dst.map(mudallis).fillna(False).astype(bool) & links["mode"].isin(
        [int(m) for m in AMBIGUOUS])
    flags = (
        np.where(links.flag.ne(0), Defect.GAP, 0)
        | np.where(by_mudallis & student_rank.le(3), Defect.TADLIS, 0)
        | np.where(by_mudallis & student_rank.ge(4), Defect.TADLIS_WEAK, 0)
        | np.where(pd.MultiIndex.from_arrays([links.src, links.dst]).map(impossible)
                   .fillna(False).astype(bool), Defect.CHRONOLOGY, 0)
    )
    link_rank = np.fmax(links.src.map(rank), student_rank)  # both ends: the apex too
    per_chain = (links.assign(defects=flags, rank=link_rank)
                 .groupby("chain_id").agg(defects=("defects", np.bitwise_or.reduce),
                                          worst_rank=("rank", "max")))
    out = chains[["chain_id", "path", "head_gap", "tail_gap"]].join(per_chain, on="chain_id")
    apex_rank = out.path.map(lambda p: rank.get(int(p[0]), np.nan))  # a link-less chain
    worst = out.worst_rank.fillna(apex_rank)
    defects = (out.defects.fillna(0).astype("int64")
               | np.where(out.tail_gap.ne(0) | out.head_gap.ne(0), Defect.GAP, 0))
    verdict = [int(structural_verdict(w, bool(d & Defect.GAP)))
               for w, d in zip(worst, defects, strict=True)]
    return pd.DataFrame({"chain_id": out.chain_id, "worst_rank": worst.astype("Int16"),
                         "verdict": verdict, "defects": defects})


def report_assessment(chains: pd.DataFrame) -> pd.DataFrame:
    """Per report: best structural verdict, and the defects shared by *every*
    acceptable route (a defect matters only if no clean acceptable route exists)."""
    best = chains.groupby("hadith_id").verdict.min().rename("best_verdict")
    ok = chains[chains.verdict.isin([int(v) for v in ACCEPTABLE])]
    shared = ok.groupby("hadith_id").defects.agg(np.bitwise_and.reduce).rename("shared_defects")
    return pd.concat([best, shared], axis=1).fillna({"shared_defects": 0}).astype("int64")


class Grade(NamedTuple):
    verdict: Verdict | None
    scope: str  # isnad | hadith | corroborated


_G = [(r"mawdu|batil|fabricat", Verdict.MAWDU), (r"very da", Verdict.VERY_DAIF),
      (r"da'?if|daeef|munkar|shadh", Verdict.DAIF), (r"sahih", Verdict.SAHIH),
      (r"hasan", Verdict.HASAN)]


def parse_grade(text: str) -> Grade:
    """Parse an English grade («Isnaad Hasan», «Sahih Lighairihi», «Daif» …)."""
    t = text.lower()
    verdict = next((v for pattern, v in _G if re.search(pattern, t)), None)
    scope = ("corroborated" if re.search(r"lighairihi|agreed|bukhari|muslim|mutawatir", t)
             else "isnad" if re.search(r"isnaad|sanad", t) else "hadith")
    return Grade(verdict, scope)


def defect_lift(reports: pd.DataFrame, grades: pd.DataFrame, min_flagged: int = 20,
                defects: tuple[Defect, ...] = (Defect.TADLIS, Defect.TADLIS_WEAK,
                                               Defect.CHRONOLOGY)) -> pd.DataFrame:
    """Rejection rate of each grader on structurally acceptable reports, with vs
    without a defect on every acceptable route — within each verdict stratum
    (ṣaḥīḥ, ḥasan), pooled by Mantel–Haenszel. Uncorroborated grades only, one
    observation per (grader, report); ``n_conflicting`` counts reports a grader
    graded both ways through parallel entries (excluded)."""
    g = grades[grades.verdict.notna() & grades.scope.ne("corroborated")]
    # one observation per (grader, report): parallel edition entries aligned to one
    # report would otherwise count as independent; inconsistent ones are dropped
    share = (g.assign(reject=g.verdict.gt(Verdict.HASAN))
             .groupby(["grader", "hadith_id"]).reject.mean().reset_index())
    conflicting = share[share.reject.between(0, 1, inclusive="neither")]
    g = (share.drop(conflicting.index).assign(reject=lambda d: d.reject.eq(1))
         .join(reports, on="hadith_id", how="inner"))
    g = g[g.best_verdict.isin([int(v) for v in ACCEPTABLE])]
    n_conflicting = conflicting.groupby("grader").size()
    rows = []
    for (grader, d), defect in ((x, f) for x in g.groupby("grader") for f in defects):
        flagged = (d.shared_defects & int(defect)).ne(0)  # Flag is iterable
        if flagged.sum() < min_flagged:
            continue
        num = den = 0.0
        for _, s in d.groupby("best_verdict"):
            f = (s.shared_defects & int(defect)).ne(0)
            a, b = s.reject[f].sum(), s.reject[~f].sum()
            n1, n0, t = f.sum(), (~f).sum(), len(s)
            num, den = num + a * n0 / t, den + b * n1 / t
        p1, p0 = d.reject[flagged].mean(), d.reject[~flagged].mean()
        p = d.reject.mean()
        se = np.sqrt(p * (1 - p) * (1 / flagged.sum() + 1 / (~flagged).sum()))
        rows.append({"grader": grader, "defect": defect.name, "n_flagged": int(flagged.sum()),
                     "reject_flagged": round(p1, 4), "n_clean": int((~flagged).sum()),
                     "n_conflicting": int(n_conflicting.get(grader, 0)),
                     "reject_clean": round(p0, 4), "risk_ratio_mh": round(num / den, 3)
                     if den else None, "z": round((p1 - p0) / se, 2) if se else None})
    return pd.DataFrame(rows)
