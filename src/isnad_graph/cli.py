"""Command line: fetch → build → verify / stats / export / chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

GRAPH_DIR = Path("data/graph")
CORPUS_DIR = Path("data/corpus")
EXPORTS = {"graphml": "write_graphml", "gexf": "write_gexf"}


def _load(directory: Path):
    from .graph import IsnadGraph

    return IsnadGraph.load(directory)


def main(argv: list[str] | None = None) -> int:
    from .source import DEFAULT_PATH

    p = argparse.ArgumentParser(prog="isnad-graph", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch", help="download and verify the pinned sources")
    sub.add_parser("corpus", help="write the text corpus (Arabic texts, English translations)")
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
    t = sub.add_parser("tree", help="export laid-out isnad trees of meaning groups as JSON")
    t.add_argument("out", type=Path)
    t.add_argument("group_ids", type=int, nargs="+")
    c = sub.add_parser("chain", help="print the chains of a hadith")
    c.add_argument("hadith_id", type=int)
    p.add_argument("--graph", type=Path, default=GRAPH_DIR, help="graph directory")
    a = p.parse_args(argv)

    if a.cmd == "fetch":
        from .source import fetch, fetch_editions

        print(fetch(dest=DEFAULT_PATH), fetch_editions(), sep="\n")
    elif a.cmd == "corpus":
        from .corpus import align_editions, export_corpus
        from .source import EDITIONS_DIR, connect

        con = connect(DEFAULT_PATH)
        print(export_corpus(con, align_editions(con, EDITIONS_DIR)[0], CORPUS_DIR))
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
    elif a.cmd == "tree":
        from .subgraph import group_tree

        g = _load(a.graph)
        trees = [group_tree(g, gid) for gid in a.group_ids]
        a.out.write_text(json.dumps(trees, ensure_ascii=False, separators=(",", ":")))
        print(f"{a.out}: {len(trees)} groups, {sum(len(t['bundles']) for t in trees)} bundles")
    elif a.cmd == "chain":
        g = _load(a.graph)
        for row in g.chains_of(a.hadith_id).itertuples():
            print(f"[{row.provenance} chain {row.chain_id}] {g.render_chain(row.chain_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
