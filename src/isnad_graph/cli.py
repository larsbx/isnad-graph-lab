"""Command line: fetch → build → verify / stats / export / chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

GRAPH_DIR = Path("data/graph")
EXPORTS = {"graphml": "write_graphml", "gexf": "write_gexf"}


def _load(directory: Path):
    from .graph import IsnadGraph

    return IsnadGraph.load(directory)


def main(argv: list[str] | None = None) -> int:
    from .source import DEFAULT_PATH

    p = argparse.ArgumentParser(prog="isnad-graph", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download and verify the pinned source database")
    b = sub.add_parser("build", help="build the graph from the source database")
    b.add_argument("--db", type=Path, default=DEFAULT_PATH)
    b.add_argument("--no-validate", action="store_true", help="skip inference validation")
    for name, help_ in [("verify", "check structural invariants"), ("stats", "print counts")]:
        sub.add_parser(name, help=help_)
    e = sub.add_parser("export", help="export the narrator transmission graph")
    e.add_argument("out", type=Path)
    e.add_argument("--format", choices=sorted(EXPORTS), default="graphml")
    e.add_argument("--min-chains", type=int, default=1)
    e.add_argument("--recorded-only", action="store_true")
    c = sub.add_parser("chain", help="print the chains of a hadith")
    c.add_argument("hadith_id", type=int)
    p.add_argument("--graph", type=Path, default=GRAPH_DIR, help="graph directory")
    a = p.parse_args(argv)

    if a.cmd == "fetch":
        from .source import fetch

        print(fetch(a.db if "db" in a else DEFAULT_PATH))
    elif a.cmd == "build":
        from .build import build

        g = build(a.db, validate=not a.no_validate)
        print(g.save(a.graph))
        print(json.dumps(g.manifest["invariants"], indent=1))
        return 0 if all(g.manifest["invariants"].values()) else 1
    elif a.cmd == "verify":
        result = _load(a.graph).verify()
        print(json.dumps(result, indent=1))
        return 0 if all(result.values()) else 1
    elif a.cmd == "stats":
        print(json.dumps(_load(a.graph).manifest["counts"], indent=1, ensure_ascii=False))
    elif a.cmd == "export":
        import networkx as nx

        g = _load(a.graph).to_networkx(min_chains=a.min_chains, recorded_only=a.recorded_only)
        getattr(nx, EXPORTS[a.format])(g, a.out)
        print(f"{a.out}: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges")
    elif a.cmd == "chain":
        g = _load(a.graph)
        for row in g.chains_of(a.hadith_id).itertuples():
            print(f"[{row.provenance} chain {row.chain_id}] {g.render_chain(row.chain_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
