"""The Isnad Atlas page: laid-out isnad trees, stamped the way vizops stamps.

    isnad-graph page out/isnad-atlas.html [GROUP ...]

The page embeds ``subgraph.group_tree`` for each meaning group and draws it in
the browser; it computes nothing the graph does not already hold. Like every
math-vizops page it carries a ``Provenance`` — repository, path, and the sha256
of the exact bytes it draws (the embedded tree payload) — beside the vizops
caveat, and a build reports a vizops ``Outcome``: ``Rendered`` with the page's
digest, or ``Refused`` with the reason.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from vizops.figure import CAVEAT, Provenance
from vizops.outcome import Outcome, Refused, Rendered

from .subgraph import group_tree

TEMPLATE = Path(__file__).resolve().parent / "templates" / "atlas.html"
PAGE = "isnad-atlas"
REPO = "larsbx/isnad-graph-lab"
#: «إنما الأعمال بالنيات», «الدين النصيحة», «الحلال بين», «لا يؤمن أحدكم»,
#: «بني الإسلام على خمس», «من حسن إسلام المرء».
GROUPS = (319, 397, 444, 690, 523, 595)


def build(g, out: Path, groups: Sequence[int] = GROUPS) -> Outcome:
    """Lay out every group's trees and write the page — or say why not."""
    trees = [group_tree(g, gid) for gid in groups]
    empty = [t["group_id"] for t in trees if not t["bundles"]]
    if not groups or empty:
        return Refused(PAGE, f"no recorded chains for group(s) {empty}" if empty
                       else "no groups asked for")
    payload = json.dumps(trees, ensure_ascii=False, separators=(",", ":"))
    provenance = Provenance(REPO, "data/graph", hashlib.sha256(payload.encode()).hexdigest(),
                            "isnad_graph.subgraph.group_tree")
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__STAMP__", f"{provenance.stamp} · {CAVEAT}")
            .replace("__DATA__", payload.replace("</", "<\\/")))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return Rendered(PAGE, str(out), hashlib.sha256(out.read_bytes()).hexdigest())
