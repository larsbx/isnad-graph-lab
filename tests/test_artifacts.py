"""Regression tests on the committed graph in data/graph (skipped if absent)."""

from pathlib import Path

import pytest

from isnad_graph import IsnadGraph
from isnad_graph.schema import PROPHET_ID

GRAPH = Path(__file__).parents[1] / "data" / "graph"
pytestmark = pytest.mark.skipif(not (GRAPH / "manifest.json").exists(), reason="no built graph")

YAHYA_AL_ANSARI, UMAR = 8272, 5913


@pytest.fixture(scope="module")
def g() -> IsnadGraph:
    return IsnadGraph.load(GRAPH)


def test_invariants_hold(g):
    assert all(g.verify().values())
    assert g.manifest["invariants"] == g.verify()


def test_inventory_matches_manifest_and_source(g):
    counts = g.manifest["counts"]
    assert counts == g.counts()
    meta = g.manifest["source"]["meta"]
    for table, key in [("hadiths", "count_hadiths"), ("books", "count_books"),
                       ("critics", "count_alems"), ("assessments", "count_aqwal"),
                       ("groups", "count_meaning_groups"), ("topics", "count_topics")]:
        assert counts["tables"][table] == int(meta[f"report.{key}"]), table
    assert counts["chains_by_provenance"]["recorded"] == int(meta["report.count_sanads"])


def test_inference_precision_floor(g):
    assert g.manifest["inference_validation"]["precision"] > 0.95


def test_innama_al_amal_common_link_is_yahya_b_said(g):
    groups = g.frame("groups")
    gid = int(groups[groups.nass.str.startswith("إنما الأعمال بالنيات")]
              .sort_values("n_chains").id.iloc[-1])
    cl = g.frame("common_links")
    cl = cl[cl.group_id.eq(gid) & cl.bundle.eq(UMAR)]
    assert cl[cl.is_common_link].rawi_id.tolist() == [YAHYA_AL_ANSARI]


def test_abu_hurayra_is_the_busiest_companion(g):
    top = g.students(PROPHET_ID).iloc[0]
    assert g.narrator(int(top.dst))["name"] == "عبد الرحمن بن صخر"  # Abū Hurayra


def test_bukhari_1_transmission_modes(g):
    from isnad_graph.sigha import Mode

    (modes,) = g.chains_of(1).modes  # Prophet → ʿUmar → ʿAlqama → al-Taymī → Yaḥyā → Sufyān …
    assert [Mode(m) for m in modes] == [Mode.SAMA] * 3 + [Mode.IKHBAR] + [Mode.TAHDITH] * 3


def test_unread_share_ceiling(g):
    by_class = g.manifest["transmission_modes"]["links_by_class"]
    assert by_class["unread"] / sum(by_class.values()) < 0.09


def test_archetypal_mudallis_narrates_by_an(g):
    al_amash = g.narrator(3629)  # سليمان بن مهران الأعمش
    assert al_amash["has_tadlis"] and al_amash["an_share"] > 0.9


def test_editions_align_with_preserved_order(g):
    stats = g.manifest["external_editions"]["alignment"]
    for collection, s in stats.items():
        floor = 0.85 if s["cross_recension"] else 0.99
        assert s["order_consistency"] > floor, collection
        assert s["aligned"] / s["entries"] > (0.7 if s["cross_recension"] else 0.9), collection
    a = g.frame("alignments")
    assert a[a.hadith_id.eq(1)].hadithnumber.tolist() == ["1"]  # Bukhārī 1 ↔ hadith-api 1


def test_structural_verdict_reproduces_source_verdicts(g):
    r = g.manifest["assessment"]["reproduction_of_source_verdicts"]
    assert r["exact"] > 0.9 and r["acceptable_vs_rejected"] > 0.94


def _lift(g, grader, defect):
    (row,) = [r for r in g.manifest["assessment"]["defect_lift"]
              if r["grader"] == grader and r["defect"] == defect]
    return row


def test_an_of_a_weaker_mudallis_predicts_rejection_for_major_graders(g):
    for grader in ["Al-Albani", "Shuaib Al Arnaut", "Zubair Ali Zai", "Ahmad Muhammad Shakir"]:
        row = _lift(g, grader, "TADLIS_WEAK")
        assert row["z"] > 4 and row["risk_ratio_mh"] > 1.2, grader


def test_zubair_ali_zai_alone_rejects_an_of_thiqa_mudallisun(g):
    assert _lift(g, "Zubair Ali Zai", "TADLIS")["z"] > 10
    for lenient in ["Al-Albani", "Shuaib Al Arnaut", "Ahmad Muhammad Shakir"]:
        assert _lift(g, lenient, "TADLIS")["z"] < 3, lenient
