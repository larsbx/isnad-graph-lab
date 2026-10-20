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
