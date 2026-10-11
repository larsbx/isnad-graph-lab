import pandas as pd
import pytest

from isnad_graph import IsnadGraph, LinkFlag
from isnad_graph.schema import PROPHET_ID
from isnad_graph.sigha import Mode


def edge(g, src, dst):
    e = g.frame("transmissions")
    return e[(e.src == src) & (e.dst == dst)].iloc[0]


def test_all_invariants_hold(mini_graph):
    invariants = mini_graph.manifest["invariants"]
    assert invariants == dict.fromkeys(invariants, True)
    assert all(mini_graph.verify().values())


def test_chain_inventory(mini_graph):
    c = mini_graph.frame("chains")
    assert c.provenance.value_counts().to_dict() == {"recorded": 7, "inferred": 2}
    assert set(c.hadith_id) == {1, 2, 3, 5, 7, 8}  # h4 abstained (tahwil); h6 only a gap marker
    assert c.query("hadith_id == 7").path.map(list).tolist() == [[2]]  # attribution only


def test_mursal_chain_flags_the_link_to_the_prophet(mini_graph):
    (row,) = mini_graph.chains_of(2).itertuples()
    assert list(row.path) == [PROPHET_ID, 3, 4]
    assert list(row.links) == [LinkFlag.IRSAL, LinkFlag.DIRECT]
    assert edge(mini_graph, PROPHET_ID, 3).n_irsal == 1


def test_taliq_is_a_tail_gap(mini_graph):
    (row,) = mini_graph.chains_of(5).itertuples()
    assert list(row.path) == [PROPHET_ID, 1, 2] and row.tail_gap == LinkFlag.TALIQ


def test_inferred_mawquf_chain_has_no_prophet(mini_graph):
    (row,) = mini_graph.chains_of(3).itertuples()
    assert list(row.path) == [1, 3] and row.provenance == "inferred"
    assert edge(mini_graph, 1, 3).n_inferred == 1


def test_edge_multiplicities(mini_graph):
    e = edge(mini_graph, 1, 2)
    assert (e.n_chains, e.n_hadiths, e.n_direct) == (6, 3, 6)
    assert edge(mini_graph, PROPHET_ID, 1).n_chains == 6


def test_chronology(mini_graph):
    assert edge(mini_graph, 2, 5).chronology == "impossible"
    assert edge(mini_graph, 2, 3).chronology == "consistent"
    assert edge(mini_graph, 3, 4).tabaka_delta == 5


def test_narrator_annotations(mini_graph):
    n = mini_graph.frame("narrators").set_index("id")
    assert n.loc[PROPHET_ID, "kind"] == "prophet" and n.loc[30002, "kind"] == "marker"
    assert (n.loc[2, "n_students"], n.loc[2, "n_teachers"]) == (3, 1)
    assert n.loc[4, "n_as_compiler"] == 4 and pd.isna(n.loc[30001, "tabaka"])


def test_common_link(mini_graph):
    cl = mini_graph.frame("common_links").query("group_id == 1").set_index("rawi_id")
    assert cl.index[cl.is_common_link].tolist() == [2]
    assert tuple(cl.loc[2, ["bundle", "fanout", "n_chains", "coverage"]]) == (1, 3, 4, 1.0)
    assert not cl.loc[3, "is_common_link"]  # partial common link: students 4, 5


def test_live_group_statistics(mini_graph):
    g = mini_graph.frame("groups").set_index("id")
    assert (g.loc[1, "n_chains"], g.loc[1, "n_companions"]) == (4, 1)


def test_inference_is_validated_against_recorded_chains(mini_graph):
    v = mini_graph.manifest["inference_validation"]
    assert (v["evaluated"], v["attempted"], v["exact"], v["exact_with_compiler"]) == (3, 3, 2, 1)
    assert v["precision"] == 1.0


def test_inferred_layer_accounting(mini_graph):
    s = mini_graph.manifest["inferred_layer"]
    assert s == {"unrecorded_hadiths": 4, "without_any_mention": 0, "abstained": {"tahwil": 1},
                 "only_gap_markers": 1, "inferred_chains": 2, "single_narrator_chains": 1}


def test_roundtrip(mini_graph, tmp_path):
    back = IsnadGraph.load(mini_graph.save(tmp_path / "g"))
    for name in IsnadGraph.table_names():
        assert getattr(back, name).equals(getattr(mini_graph, name)), name
    assert back.manifest["counts"] == mini_graph.manifest["counts"]


def test_networkx_view(mini_graph):
    g = mini_graph.to_networkx()
    assert 30002 not in g and g.has_edge(PROPHET_ID, 1)
    assert g.edges[2, 5]["chronology"] == "impossible"
    assert g.nodes[1]["name"] == "أبو هريرة"
    assert set(mini_graph.to_networkx(recorded_only=True).successors(1)) == {2}


def test_render_chain(mini_graph):
    (cid,) = mini_graph.chains_of(2).chain_id
    assert mini_graph.render_chain(cid).startswith("محمد رسول الله ﷺ ⇢[")


def test_graph_is_immutable(mini_graph):
    with pytest.raises(AttributeError):
        mini_graph.chains = None
    with pytest.raises(TypeError):
        mini_graph.manifest["x"] = 1


def test_transmission_modes_are_read_per_link(mini_graph):
    c = mini_graph.frame("chains").set_index("sanad_id")
    # s1 = Prophet → 1 → 2 → 3 → 4, text «حدثنا باء عن ألف عن أبي هريرة قال : متن»
    assert list(c.loc[1, "modes"]) == [Mode.UNREAD, Mode.AN, Mode.AN, Mode.TAHDITH]
    assert all(len(m) == n for m, n in zip(c.modes, c.n_links, strict=True))


def test_edge_mode_histogram(mini_graph):
    e = edge(mini_graph, 3, 4)
    assert (e.mode_tahdith, e.top_mode) == (2, "tahdith")
    assert edge(mini_graph, 1, 2).mode_an == 6


def test_tadlis_risk_flags_an_of_a_mudallis(mini_graph):
    c = mini_graph.frame("chains").set_index("sanad_id")
    assert c.loc[1, "n_tadlis_risk"] == 1  # A (mudallis) ← Abū Hurayra by ʿan
    assert mini_graph.manifest["transmission_modes"]["chains_with_tadlis_risk"] == 6  # s1–s3, s5–s7


def test_hearing_profile(mini_graph):
    n = mini_graph.frame("narrators").set_index("id")
    assert (n.loc[2, "an_share"], n.loc[2, "explicit_share"]) == (1.0, 0.0)
    assert n.loc[4, "n_links_read"] == 3


def test_external_edition_is_aligned_by_text(mini_graph):
    a = mini_graph.frame("alignments")
    assert dict(zip(a.hadithnumber, a.hadith_id, strict=True)) == {"10": 1, "11": 2}
    stats = mini_graph.manifest["external_editions"]["alignment"]["mini"]
    assert (stats["entries"], stats["aligned"], stats["order_consistency"]) == (3, 2, 1.0)


def test_external_grades_attach_to_source_reports(mini_graph):
    (row,) = mini_graph.frame("external_grades").itertuples()
    assert (row.hadith_id, row.grader, row.grade) == (2, "Al-Albani", "Sahih")


def test_structural_verdicts_and_defects(mini_graph):
    from isnad_graph.assess import Defect, Verdict

    c = mini_graph.frame("chains").set_index("sanad_id")
    # s1: Prophet → Abū Hurayra → A (thiqa mudallis, by ʿan) → B → C; all rank ≤ 3,
    # and C (b. 194) cannot have heard B (d. 150)
    assert (c.loc[1, "verdict"], c.loc[1, "defects"]) == (
        Verdict.SAHIH, Defect.TADLIS | Defect.CHRONOLOGY)
    assert c.loc[4, "verdict"] == Verdict.DAIF and c.loc[4, "defects"] & Defect.GAP  # mursal
    assert c.loc[6, "defects"] & Defect.CHRONOLOGY  # D born after A died
    assert c.loc[2, "verdict"] == Verdict.SAHIH


def test_report_level_assessment(mini_graph):
    h = mini_graph.frame("hadiths").set_index("id")
    assert h.loc[2, "best_verdict"] == 2  # only route is mursal
    assert h.loc[1, "shared_defects"] & 2  # every acceptable route of h1 has A's ʿan


def test_grades_are_parsed(mini_graph):
    (row,) = mini_graph.frame("external_grades").itertuples()
    assert (row.verdict, row.scope) == (0, "hadith")


def test_reproduction_is_reported(mini_graph):
    r = mini_graph.manifest["assessment"]["reproduction_of_source_verdicts"]
    assert r["chains"] == 7 and 0 <= r["exact"] <= 1
