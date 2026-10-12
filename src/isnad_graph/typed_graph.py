"""The isnad graph in the estate's graph contract, checked by vizops' own reader.

math-vizops draws any graph written as ``finite typed relationship graph 1``:
a JSON object that declares its own vocabulary (``provenance_classes`` for
nodes, ``edge_types`` for edges) and classes every node and edge in it. This
module writes one companion bundle of a meaning group in that format, and
reads it back through the vendored ``vizops.adapters.typed_graph`` — the
reader math-vizops runs — then its palette and layout, so an artifact this
repository emits is refused here for every reason it would be refused there.

The vocabulary is declared here, by the repository that owns the data, and
transcribed from the source's own rank scale (Ibn Ḥajar's twelve marātib as
the source encodes them in ``narrators.rank_no``); vizops only ever reads it.
Eight classes, the most vizops' palette colours, so the Prophet ﷺ — the apex
of every bundle and the same for all of them — is not drawn: a bundle starts at
its companion (or, for a mursal bundle, its successor).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from vizops import adapters, layout, palette
from vizops.figure import Figure, FigureError, Provenance
from vizops.outcome import Outcome, Refused, Rendered

from .schema import PROPHET_ID
from .sigha import Mode, mode_class
from .subgraph import group_tree

TYPED_GRAPH_FORMAT = adapters.TYPED_GRAPH_FORMAT
REPO = "larsbx/isnad-graph-lab"
GENERATOR = "isnad_graph.typed_graph"

#: Narrator classes, declared in this order; rank_no → class transcribes the
#: source's own scale and folds nothing across a grade boundary.
GRADE_CLASSES = ("companion", "thiqa", "saduq", "maqbul", "majhul", "daif", "rejected",
                 "ungraded")
_RANK_CLASS = {1: "companion", 2: "thiqa", 3: "thiqa", 4: "saduq", 5: "saduq", 6: "maqbul",
               7: "majhul", 8: "daif", 9: "majhul", 10: "rejected", 11: "rejected",
               12: "rejected"}
#: Edge classes: the transmission-mode class of the link's most frequent mode.
EDGE_TYPES = ("explicit", "ambiguous", "written", "unread")
_STATUS = {"common_link": "common link", "partial": "partial common link"}

REFUSALS = (FigureError, adapters.AdapterError, palette.PaletteError, ValueError, KeyError)


def grade_class(rank_no: int | None) -> str:
    return _RANK_CLASS.get(rank_no, "ungraded") if rank_no is not None else "ungraded"


def typed_graph(g, group_id: int, bundle: int = 0, min_chains: int = 3) -> dict[str, Any]:
    """One companion bundle of a meaning group as ``finite typed relationship graph 1``.

    Only narrators carrying at least ``min_chains`` of the bundle's chains are
    kept — the trunk of the tree; an edge with an endpoint left out is left out
    too. ``bundle`` indexes the bundles largest first, as ``group_tree`` orders them.
    """
    tree = group_tree(g, group_id)
    if not tree["bundles"]:
        raise ValueError(f"group {group_id}: no recorded chains")
    b = tree["bundles"][bundle]
    through = Counter(p for c in b["chains"] for p in set(c["path"]))
    kept = {n["id"]: n for n in b["nodes"]
            if n["id"] != PROPHET_ID and through[n["id"]] >= min_chains}
    name = {i: f"{n['name']} #{i}" for i, n in kept.items()}
    return {
        "format": TYPED_GRAPH_FORMAT,
        "provenance_classes": list(GRADE_CLASSES),
        "edge_types": list(EDGE_TYPES),
        "source": {"repo": REPO, "generator": GENERATOR, "group_id": group_id,
                   "companion": b["companion"], "mursal": b["mursal"],
                   "chains": b["n_chains"], "min_chains": min_chains, "matn": tree["text"]},
        "nodes": [{"id": name[i], "label": _STATUS.get(n["cl"], ""),
                   "provenance": grade_class(n["rank_no"]),
                   "statement": "; ".join(filter(None, (
                       n["full"], n["rank"], n["death"] and f"d. {n['death']} AH",
                       f"{through[i]} of {b['n_chains']} chains"))) or name[i]}
                  for i, n in kept.items()],
        "edges": [{"source": name[e["src"]], "target": name[e["dst"]],
                   "type": mode_class(Mode[e["top"].upper()])}
                  for e in b["edges"] if e["src"] in kept and e["dst"] in kept],
    }


def read_back(raw: bytes, path: str, title: str) -> tuple[Figure, Mapping[str, str],
                                                           Mapping[str, layout.Point]]:
    """Read an emitted artifact exactly as math-vizops would: its adapter, its
    palette by declared position, its column layout. Raises one of ``REFUSALS``."""
    provenance = Provenance(REPO, path, hashlib.sha256(raw).hexdigest(), GENERATOR)
    fig = adapters.typed_graph(raw, provenance, title)
    hues = palette.assign([t.id for t in fig.terms])
    points = layout.columns([t.id for t in fig.populated()], fig.members())
    return fig, hues, points


def write(g, group_id: int, out: Path, bundle: int = 0, min_chains: int = 3) -> Outcome:
    """Emit, read back, and write the artifact — or say why not, as a vizops outcome."""
    scene = f"isnad-g{group_id}-b{bundle}"
    try:
        data = typed_graph(g, group_id, bundle, min_chains)
        raw = (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode()
        read_back(raw, out.as_posix(), f"Isnad trunk of group {group_id}")
    except (*REFUSALS, IndexError) as refusal:
        return Refused(scene, str(refusal) or type(refusal).__name__)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    return Rendered(scene, str(out), hashlib.sha256(raw).hexdigest())
