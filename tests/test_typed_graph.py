import json

import pytest
from vizops.figure import CAVEAT, FigureError
from vizops.outcome import Refused, Rendered
from vizops.palette import RING

from isnad_graph.typed_graph import (
    EDGE_TYPES,
    GRADE_CLASSES,
    TYPED_GRAPH_FORMAT,
    grade_class,
    read_back,
    typed_graph,
    write,
)


def test_vocabulary_fits_the_palette_and_maps_every_rank():
    assert len(GRADE_CLASSES) <= len(RING)
    assert {grade_class(r) for r in range(1, 13)} | {grade_class(None)} == set(GRADE_CLASSES)
    assert (grade_class(1), grade_class(3), grade_class(8), grade_class(12)) == (
        "companion", "thiqa", "daif", "rejected")


def test_emits_the_estate_typed_graph_contract(mini_graph):
    data = typed_graph(mini_graph, group_id=1, bundle=0, min_chains=1)
    assert data["format"] == TYPED_GRAPH_FORMAT
    assert data["provenance_classes"] == list(GRADE_CLASSES)
    assert data["edge_types"] == list(EDGE_TYPES)
    ids = {n["id"] for n in data["nodes"]}
    assert not any("ﷺ" in i or i.endswith("#-1") for i in ids)  # the bundle starts at the companion
    assert all({e["source"], e["target"]} <= ids for e in data["edges"])
    cl = [n for n in data["nodes"] if n["label"] == "common link"]
    assert [n["id"].split("#")[-1] for n in cl] == ["2"]


def test_read_back_through_the_vendored_vizops_adapter(mini_graph):
    raw = json.dumps(typed_graph(mini_graph, 1, 0, 1), ensure_ascii=False).encode()
    fig, hues, points = read_back(raw, "data/graph/typed/g1.json", "test")
    assert fig.caveat == CAVEAT and fig.provenance.repo == "larsbx/isnad-graph-lab"
    assert set(points) == {n.id for n in fig.nodes} and set(hues.values()) <= set(RING)


def test_an_undeclared_class_is_refused():
    bad = {"format": TYPED_GRAPH_FORMAT, "provenance_classes": ["thiqa"],
           "edge_types": ["explicit"], "edges": [],
           "nodes": [{"id": "a", "label": "", "provenance": "invented"}]}
    with pytest.raises(FigureError, match="not one the source declares"):
        read_back(json.dumps(bad).encode(), "x.json", "t")


def test_write_reports_a_vizops_outcome(mini_graph, tmp_path):
    out = write(mini_graph, 1, tmp_path / "g1.json", min_chains=1)
    assert isinstance(out, Rendered) and out.exit_code == 0
    assert (tmp_path / "g1.json").exists()
    refused = write(mini_graph, 999, tmp_path / "none.json")
    assert isinstance(refused, Refused) and not (tmp_path / "none.json").exists()
