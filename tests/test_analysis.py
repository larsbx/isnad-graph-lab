from itertools import pairwise

import pandas as pd

from isnad_graph.analysis import bundle_nodes, common_links, strand
from isnad_graph.schema import PROPHET_ID

U, A, M, Y, X = 10, 11, 12, 13, 14  # «إنما الأعمال بالنيات»: ʿUmar → ʿAlqama → al-Taymī → Yaḥyā


def links_of(paths, group_id=1):
    return pd.DataFrame(
        {"chain_id": cid, "hadith_id": cid, "book_id": 1, "group_id": group_id,
         "provenance": "recorded", "src": s, "dst": d, "flag": 0, "depth": i}
        for cid, path in enumerate(paths)
        for i, (s, d) in enumerate(pairwise(path))
    )


def test_single_strand_then_fan_out_finds_the_true_common_link():
    strand = [PROPHET_ID, U, A, M, Y]
    paths = [[*strand, 100 + k % 9, 200 + k] for k in range(40)] + [[PROPHET_ID, U, A, M, X, 300]]
    cl = common_links(links_of(paths)).set_index("rawi_id")
    assert cl.index[cl.is_common_link].tolist() == [Y]
    assert cl.loc[Y, "fanout"] == 9 and cl.loc[Y, "bundle"] == U
    assert M not in cl.index  # 40 of 41 chains go on to Yaḥyā: M is still on the strand


def test_each_companion_bundle_is_analysed_separately():
    paths = ([[PROPHET_ID, U, Y, 100 + k] for k in range(3)]
             + [[PROPHET_ID, A, X, 200 + k] for k in range(4)])
    cl = common_links(links_of(paths))
    assert dict(zip(cl.bundle, cl.rawi_id, strict=True)) == {U: Y, A: X}
    assert cl.is_common_link.all()


def test_a_pure_single_strand_has_no_common_link():
    assert common_links(links_of([[PROPHET_ID, U, A, M]] * 3)).empty


def test_thin_bundles_are_not_called():
    cl = common_links(links_of([[PROPHET_ID, U, Y, 100], [PROPHET_ID, U, Y, 101]]))
    assert not cl.is_common_link.any()  # fan-out at Y, but only 2 chains


def _step(paths):
    return bundle_nodes(links_of(paths))[["top_share", "n_chains", "top_student"]].to_dict("index")


def test_the_strand_runs_from_the_companion_to_the_first_branching():
    paths = [[PROPHET_ID, U, A, M, Y, 100 + k] for k in range(5)]
    assert strand(_step(paths), 1, U, 0.8) == [U, A, M, Y]


def test_the_busiest_student_is_the_smallest_id_among_ties():
    paths = [[PROPHET_ID, U, Y, 100], [PROPHET_ID, U, X, 101], [PROPHET_ID, U, M, 102]]
    assert _step(paths)[(1, U, U)]["top_student"] == M


def test_a_cycle_ends_the_strand():
    assert strand(_step([[PROPHET_ID, U, A, U, A]] * 3), 1, U, 0.8) == [U, A]
