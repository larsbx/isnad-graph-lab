"""The Lean conformance vectors are current: regenerated from the committed graph,
they match ``formal/vectors/conformance.json`` byte for byte."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VECTORS = ROOT / "formal" / "vectors" / "conformance.json"


def _exporter():
    spec = importlib.util.spec_from_file_location("export_vectors",
                                                  ROOT / "tools" / "export_vectors.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def committed():
    if not (ROOT / "data" / "graph" / "manifest.json").exists():
        pytest.skip("no committed graph")
    from isnad_graph.graph import IsnadGraph

    return _exporter(), IsnadGraph.load(ROOT / "data" / "graph")


def test_vectors_are_current(committed):
    exporter, g = committed
    assert exporter.render(exporter.vectors(g)) == VECTORS.read_text(encoding="utf-8"), (
        "formal/vectors/conformance.json is stale: run python tools/export_vectors.py")


def test_vectors_cover_every_verdict():
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert {row[2] for row in data["chronology"]} == {
        "unknown", "conflict", "impossible", "implausible", "consistent"}
    assert {(row[0], row[1]) for row in data["verdict"]} >= {
        (r, g) for r in [None, *range(1, 13)] for g in (False, True)}


def test_vectors_cover_every_phase_and_both_common_link_outcomes():
    data = json.loads(VECTORS.read_text(encoding="utf-8"))
    assert {p[0] for row in data["phases"] for p in row[4]} == {
        "quiet", "hearing", "teaching", "both"}
    assert {(row[2] is None, row[3] is None) for row in data["phases"]} == {
        (False, False), (False, True), (True, False), (True, True)}
    assert {row[3] is None for row in data["common_link"]} == {True, False}
    assert max(len(row[2]) for row in data["common_link"]) >= 4  # strands of several links


def test_inference_vectors_cover_every_abstention_and_ordered_successes():
    rows = json.loads(VECTORS.read_text(encoding="utf-8"))["inference"]
    assert {row[4] for row in rows} == {
        None, "no_matn_boundary", "tahwil", "no_isnad_mentions", "unresolved_mention"}
    tied = [row for row in rows if row[5] and len(row[5]) > 1
            and len({m[1] for m in row[0] if m[2] <= row[1]})
            < sum(m[2] <= row[1] for m in row[0])]
    assert len(tied) >= 20  # ties in position check that both sides sort stably


def test_stratified_vectors_cover_the_published_comparisons_and_edge_cases():
    rows = json.loads(VECTORS.read_text(encoding="utf-8"))["stratified"]
    assert {row[2] for row in rows} == {"finite", "infinite", "undefined"}
    assert any(row[4] is None for row in rows) and min(r[4] for r in rows if r[4]) < 1e-60
    assert any(len(row[0]) == 3 for row in rows)  # three strata pool
    assert any(n1 == 0 or n0 == 0 for row in rows for _, n1, _, n0 in row[0])
