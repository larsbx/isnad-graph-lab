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
