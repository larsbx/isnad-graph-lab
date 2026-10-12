"""Artifact bytes in, `Figure` out. One adapter per artifact format.

An adapter transcribes; it does not compute. Every class, label, statement and
edge on a frame is lifted verbatim from a field of the artifact, and where the
artifact declares its own vocabulary -- `provenance_classes` and `edge_types`
in the typed graph, `[[taxonomy]]` in the catalogue -- that declaration is the
figure's vocabulary. Nothing is inferred from a value the file does not carry,
because the repository that owns the artifact already answered that question
and a second answer here could only ever disagree with it.

Each adapter refuses an artifact whose declared format is not the one it knows.
A file that changed shape is not a file to guess at.
"""

from __future__ import annotations

import json
import tomllib
from typing import Callable, Mapping

from .figure import Edge, Figure, Node, Provenance, Term

Adapter = Callable[[bytes, Provenance, str], Figure]

TYPED_GRAPH_FORMAT = "finite typed relationship graph 1"
CATALOGUE_SCHEMA = 1
RELATED = "related"


class AdapterError(ValueError):
    """The artifact is not the format this adapter reads."""


def _require(what: str, data: Mapping, keys: tuple[str, ...]) -> None:
    missing = [k for k in keys if k not in data]
    if missing:
        raise AdapterError(f"{what}: lacks {', '.join(missing)}")


def typed_graph(raw: bytes, provenance: Provenance, title: str) -> Figure:
    """`finite typed relationship graph 1` -- the claim graph that
    `proof_records/generate_ledgers.py` writes beside a proof-record ledger.

    Nodes are classed by the graph's own `provenance` field and badged with its
    own status label. The `status` a ledger record carries is derived upstream
    from the record's kind, its override tag and the completeness of its
    closure; that derivation stays there.
    """
    data = json.loads(raw.decode("utf-8"))
    if data.get("format") != TYPED_GRAPH_FORMAT:
        raise AdapterError(f"format is {data.get('format')!r}, expected {TYPED_GRAPH_FORMAT!r}")
    _require("typed graph", data, ("provenance_classes", "edge_types", "nodes", "edges"))
    for i, n in enumerate(data["nodes"]):
        _require(f"node {i}", n, ("id", "label", "provenance"))
    for i, e in enumerate(data["edges"]):
        _require(f"edge {i}", e, ("source", "target", "type"))
    return Figure(
        title=title,
        provenance=provenance,
        terms=tuple(Term(id=c, name=c) for c in data["provenance_classes"]),
        kinds=tuple(data["edge_types"]),
        nodes=tuple(
            Node(id=n["id"], label=n["id"], term=n["provenance"], badge=n["label"], note=n.get("statement", ""))
            for n in data["nodes"]
        ),
        edges=tuple(Edge(source=e["source"], target=e["target"], kind=e["type"]) for e in data["edges"]),
    )


def object_catalogue(raw: bytes, provenance: Provenance, title: str) -> Figure:
    """The PSC mathematical-object catalogue.

    Classed by the catalogue's `[[taxonomy]]` blocks, badged with each object's
    own `status` word -- which is shown, not interpreted. Edges are the
    `related` field, so the edge kind is the field's name.
    """
    data = tomllib.loads(raw.decode("utf-8"))
    if data.get("schema_version") != CATALOGUE_SCHEMA:
        raise AdapterError(f"schema_version is {data.get('schema_version')!r}, expected {CATALOGUE_SCHEMA}")
    _require("catalogue", data, ("taxonomy", "object"))
    for i, o in enumerate(data["object"]):
        _require(f"object {i}", o, ("id", "name", "taxonomy"))
    return Figure(
        title=data.get("title") or title,
        provenance=provenance,
        terms=tuple(Term(id=t["id"], name=t["name"], description=t.get("description", "")) for t in data["taxonomy"]),
        kinds=(RELATED,),
        nodes=tuple(
            Node(id=o["id"], label=o["name"], term=o["taxonomy"], badge=o.get("status", ""), note=o.get("scope", ""))
            for o in data["object"]
        ),
        edges=_related(data["object"]),
    )


def _related(objects: list[Mapping]) -> tuple[Edge, ...]:
    """Each `related` pair once, whichever side declared it.

    The catalogue states the relation on both objects where both know about
    it, so the pairs are deduplicated unordered -- but a pair only one side
    states is still an edge. Dropping it would be this module deciding the
    catalogue meant something other than what it says.
    """
    pairs = {frozenset((o["id"], r)) for o in objects for r in o.get(RELATED, ()) if r != o["id"]}
    return tuple(Edge(source=a, target=b, kind=RELATED) for a, b in sorted(tuple(sorted(p)) for p in pairs))


ADAPTERS: Mapping[str, Adapter] = {"typed_graph": typed_graph, "object_catalogue": object_catalogue}
