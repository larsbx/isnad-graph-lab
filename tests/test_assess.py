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
    (3, True, Verdict.DAIF), (10, True, Verdict.VERY_DAIF),
    # an unranked narrator is majhul (rank 9): never sahih (formal/lean: unknown_not_sahih)
    (float("nan"), False, Verdict.DAIF), (float("nan"), True, Verdict.DAIF),
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
    assert row.z_cmh == pytest.approx(1.5811)
    assert row.p_exact == pytest.approx(0.4)


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


def test_an_unranked_narrator_is_majhul():
    from isnad_graph.assess import assess_chains
    from isnad_graph.schema import PROPHET_ID

    chains = pd.DataFrame({"chain_id": [0], "path": [[PROPHET_ID, 10, 11, 12]], "head_gap": [0],
                           "tail_gap": [0]})
    links = pd.DataFrame({"chain_id": [0] * 3, "src": [PROPHET_ID, 10, 11], "dst": [10, 11, 12],
                          "flag": [0] * 3, "mode": [2] * 3})
    narrators = pd.DataFrame({"id": [PROPHET_ID, 10, 11, 12], "rank_no": [None, 1, None, 3],
                              "has_tadlis": [False] * 4})
    edges = pd.DataFrame({"src": [PROPHET_ID, 10, 11], "dst": [10, 11, 12],
                          "chronology": ["unknown"] * 3})
    (row,) = assess_chains(chains, links, narrators, edges).itertuples()
    assert (row.worst_rank, row.verdict) == (9, Verdict.DAIF)  # the Prophet is not ranked


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


def test_confounding_does_not_create_adjusted_significance():
    # Identical within-stratum risks; very different exposure compositions.
    from isnad_graph.assess import stratified_inference

    tables = [(72, 90, 8, 10), (1, 10, 9, 90)]
    result = stratified_inference(tables)
    assert result["risk_ratio_mh"] == 1
    assert result["z_cmh"] == 0
    assert result["p_exact"] > 0.9
    marginal_z = (0.73 - 0.17) / ((0.45 * 0.55 * 0.02) ** 0.5)
    assert marginal_z > 3


@pytest.mark.parametrize("tables, ratio, status, informative", [
    ([(8, 10, 4, 10), (2, 100, 1, 100)], 2, "finite", 2),  # unequal sizes
    ([(0, 10, 5, 10)], 0, "finite", 1),  # zero event cell
    ([(5, 10, 0, 10)], None, "infinite", 1),
    ([(0, 10, 0, 20)], None, "undefined", 0),
    ([(1, 1, 0, 0)], None, "undefined", 0),  # no clean group / singleton
    ([(0, 0, 0, 0)], None, "undefined", 0),
])
def test_stratified_boundaries(tables, ratio, status, informative):
    from isnad_graph.assess import stratified_inference

    result = stratified_inference(tables)
    assert result["risk_ratio_mh"] == ratio
    assert result["risk_ratio_status"] == status
    assert result["n_informative_strata"] == informative
    if not informative:
        assert result["z_cmh"] is None
        assert result["p_exact"] is None


def test_exact_sparse_test_against_exhaustive_conditional_enumeration():
    from fractions import Fraction
    from itertools import product
    from math import comb

    from isnad_graph.assess import stratified_inference

    tables = [(2, 2, 0, 3), (1, 2, 0, 2)]
    # Enumerate independently using exact combinatorial probabilities.
    distributions = []
    for a, n1, b, n0 in tables:
        t, r = n1 + n0, a + b
        distributions.append([(x, Fraction(comb(r, x) * comb(t - r, n1 - x), comb(t, n1)))
                              for x in range(max(0, r - n0), min(n1, r) + 1)])
    observed = 3
    lower = upper = Fraction(0)
    for outcomes in product(*distributions):
        total = sum(x for x, _ in outcomes)
        probability = outcomes[0][1] * outcomes[1][1]
        lower += probability if total <= observed else 0
        upper += probability if total >= observed else 0
    assert stratified_inference(tables)["p_exact"] == pytest.approx(
        float(min(1, 2 * min(lower, upper))))


def test_genuine_effect_and_exposure_reversal():
    from isnad_graph.assess import stratified_inference

    tables = [(40, 50, 10, 50), (80, 100, 20, 100)]
    result = stratified_inference(tables)
    reverse = stratified_inference([(b, n0, a, n1) for a, n1, b, n0 in tables])
    assert result["risk_ratio_mh"] == 4
    assert result["z_cmh"] > 5
    assert result["p_exact"] < 0.001
    assert reverse["z_cmh"] == -result["z_cmh"]
    assert reverse["p_exact"] == pytest.approx(result["p_exact"])
