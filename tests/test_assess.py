import pandas as pd
import pytest

from isnad_graph.assess import (
    Defect,
    Verdict,
    defect_lift,
    parse_grade,
    report_assessment,
    structural_verdict,
)


@pytest.mark.parametrize("rank, gap, verdict", [
    (1, False, Verdict.SAHIH), (3, False, Verdict.SAHIH), (4, False, Verdict.HASAN),
    (6, False, Verdict.HASAN), (7, False, Verdict.DAIF), (10, False, Verdict.VERY_DAIF),
    (11, False, Verdict.ACCUSED), (12, False, Verdict.MAWDU),
    (3, True, Verdict.DAIF), (10, True, Verdict.VERY_DAIF), (float("nan"), False, Verdict.SAHIH),
])
def test_structural_verdict(rank, gap, verdict):
    assert structural_verdict(rank, gap) == verdict


@pytest.mark.parametrize("text, verdict, scope", [
    ("Isnaad Hasan", Verdict.HASAN, "isnad"), ("Sahih", Verdict.SAHIH, "hadith"),
    ("Hasan Sahih", Verdict.SAHIH, "hadith"), ("Daif Isnaad", Verdict.DAIF, "isnad"),
    ("Very Daif", Verdict.VERY_DAIF, "hadith"), ("Sahih Lighairihi", Verdict.SAHIH, "corroborated"),
    ("Sahih - Agreed Upon", Verdict.SAHIH, "corroborated"), ("Mawdu", Verdict.MAWDU, "hadith"),
    ("Munkar", Verdict.DAIF, "hadith"), ("Sanad Daif", Verdict.DAIF, "isnad"),
    ("Mauquf", None, "hadith"),
])
def test_parse_grade(text, verdict, scope):
    assert parse_grade(text) == (verdict, scope)


def test_report_defects_count_only_if_every_acceptable_route_has_them():
    chains = pd.DataFrame({"hadith_id": [1, 1, 2, 2, 3], "verdict": [0, 1, 1, 2, 2],
                           "defects": [Defect.TADLIS, Defect.NONE, Defect.TADLIS,
                                       Defect.GAP, Defect.GAP]})
    r = report_assessment(chains)
    assert r.loc[1].tolist() == [0, 0]  # a clean ḥasan route rescues it
    assert r.loc[2].tolist() == [1, Defect.TADLIS]
    assert r.loc[3].tolist() == [2, 0]  # nothing acceptable: no shared defect


def test_defect_lift_is_stratified():
    # within ḥasan, flagged reports are rejected 2/2 vs clean 1/4; ṣaḥīḥ has no flagged ones
    reports = pd.DataFrame({"best_verdict": [1] * 6 + [0] * 4,
                            "shared_defects": [Defect.TADLIS_WEAK] * 2 + [0] * 8},
                           index=pd.Index(range(10), name="hadith_id"))
    grades = pd.DataFrame({"hadith_id": range(10), "grader": "G", "scope": "hadith",
                           "verdict": [2, 2, 2, 0, 0, 0, 0, 0, 0, 0]})
    lift = defect_lift(reports, grades, min_flagged=1, defects=(Defect.TADLIS_WEAK,))
    (row,) = lift.itertuples()
    assert (row.n_flagged, row.reject_flagged, row.n_clean) == (2, 1.0, 8)
    assert row.risk_ratio_mh == pytest.approx(4.0)  # MH within the ḥasan stratum: 1 / (1/4)


def test_apex_rank_counts_toward_the_weakest_narrator():
    # inferred mawquf chain: a majhul (rank 7) apex, then two thiqat — ḍaʿīf, not ṣaḥīḥ
    from isnad_graph.assess import assess_chains

    chains = pd.DataFrame({"chain_id": [0], "path": [[10, 11, 12]], "head_gap": [0],
                           "tail_gap": [0]})
    links = pd.DataFrame({"chain_id": [0, 0], "src": [10, 11], "dst": [11, 12], "flag": [0, 0],
                          "mode": [2, 2]})
    narrators = pd.DataFrame({"id": [10, 11, 12], "rank_no": [7, 3, 3],
                              "has_tadlis": [False] * 3})
    edges = pd.DataFrame({"src": [10, 11], "dst": [11, 12], "chronology": ["unknown"] * 2})
    (row,) = assess_chains(chains, links, narrators, edges).itertuples()
    assert (row.worst_rank, row.verdict) == (7, Verdict.DAIF)


def test_each_report_counts_once_per_grader():
    # report 0 is graded twice by G through two parallel edition entries; report 1 is
    # graded inconsistently (accept + reject) and is dropped, not double-counted
    reports = pd.DataFrame({"best_verdict": [1, 1, 1, 1], "shared_defects": [
        Defect.TADLIS_WEAK, Defect.TADLIS_WEAK, 0, 0]}, index=pd.Index(range(4), name="hadith_id"))
    grades = pd.DataFrame({"hadith_id": [0, 0, 1, 1, 2, 3], "grader": "G", "scope": "hadith",
                           "verdict": [2, 2, 0, 2, 0, 2]})
    (row,) = defect_lift(reports, grades, min_flagged=1,
                         defects=(Defect.TADLIS_WEAK,)).itertuples()
    assert (row.n_flagged, row.reject_flagged, row.n_clean, row.n_conflicting) == (1, 1.0, 2, 1)
