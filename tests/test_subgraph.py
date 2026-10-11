from itertools import pairwise

from hypothesis import given
from hypothesis import strategies as st

from isnad_graph.subgraph import ROW, layers, positions


def test_longest_path_layering():
    edges = [(0, 1), (1, 2), (0, 2), (2, 3)]
    assert layers(edges, 0) == {0: 0, 1: 1, 2: 2, 3: 3}


def test_cycles_do_not_hang_and_unreachable_nodes_are_dropped():
    assert set(layers([(0, 1), (1, 2), (2, 1), (5, 6)], 0)) == {0, 1, 2}


dags = st.lists(st.tuples(st.integers(0, 12), st.integers(0, 12)), max_size=30).map(
    lambda es: [(0, 1), *[(min(a, b), max(a, b)) for a, b in es if a != b]])


@given(dags)
def test_layers_strictly_increase_along_edges(edges):
    layer = layers(edges, 0)
    assert all(layer[d] > layer[s] for s, d in edges if s in layer)


@given(dags)
def test_siblings_never_overlap(edges):
    layer = layers(edges, 0)
    y = positions(edges, layer)
    assert set(y) == set(layer)
    for k in set(layer.values()):
        ys = sorted(y[n] for n in layer if layer[n] == k)
        assert all(b - a >= ROW - 1e-9 for a, b in pairwise(ys))


def test_group_tree_is_per_companion_bundle(mini_graph):
    import json

    from isnad_graph.subgraph import group_tree

    tree = group_tree(mini_graph, 1)
    (bundle,) = tree["bundles"]  # all of group 1 goes through Abū Hurayra
    assert (bundle["companion"], bundle["n_chains"], bundle["mursal"]) == (1, 4, False)
    status = {n["id"]: n["cl"] for n in bundle["nodes"]}
    assert status[2] == "common_link" and status[3] == "partial"
    assert {n["x"] for n in bundle["nodes"] if n["id"] == -1} == {0}
    json.dumps(tree)  # JSON-ready, no NA


def test_mursal_bundle(mini_graph):
    from isnad_graph.subgraph import group_tree

    (bundle,) = group_tree(mini_graph, 2)["bundles"]
    assert bundle["mursal"] and bundle["companion"] == 3


def test_short_names_do_not_end_on_ibn():
    from isnad_graph.subgraph import _short

    assert _short("يحيى بن سعيد بن قيس بن عمرو") == "يحيى بن سعيد"
    assert _short("سليمان بن مهران") == "سليمان بن مهران"
