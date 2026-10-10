"""The graph object: an immutable bundle of Arrow tables plus a manifest.

Layers
------
* **narrators** — nodes (people, the synthetic Prophet apex, gap markers), with
  biography, jarh-wa-ta'dil grade, generation and usage statistics.
* **transmissions** — aggregated directed edges teacher → student, annotated
  with multiplicity, gap flags, provenance and chronological consistency.
* **chains** — the hyperedges: every ordered isnad with per-link flags.
* **hadiths / books / groups / topics** — what the chains carry and where.
* **critics / assessments** — the jarh-wa-ta'dil layer: critic → narrator.
* **common_links** — Juynboll-style (partial) common links per meaning group.
* **alignments / external_grades** — reports matched to the public-domain
  hadith-api editions (with English translations in the corpus) and the
  modern gradings attached to them.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any

import networkx as nx
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from .schema import PROPHET_ID, PROPHETIC_TYPES, LinkFlag, NodeKind, Provenance


def _table(x: pa.Table | pd.DataFrame) -> pa.Table:
    return x if isinstance(x, pa.Table) else pa.Table.from_pandas(x, preserve_index=False)


def _attrs(row: Mapping[str, Any]) -> dict[str, Any]:
    """Plain-Python, NA-free attributes (GraphML/GEXF cannot hold NA or numpy scalars)."""
    return {k: v.item() if hasattr(v, "item") else v for k, v in row.items()
            if v is not None and not pd.isna(v)}


@dataclass(frozen=True)
class IsnadGraph:
    narrators: pa.Table
    transmissions: pa.Table
    chains: pa.Table
    hadiths: pa.Table
    books: pa.Table
    groups: pa.Table
    topics: pa.Table
    critics: pa.Table
    assessments: pa.Table
    common_links: pa.Table
    alignments: pa.Table
    external_grades: pa.Table
    manifest: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in self.table_names():
            object.__setattr__(self, name, _table(getattr(self, name)))
        object.__setattr__(self, "manifest", MappingProxyType(dict(self.manifest)))

    @classmethod
    def table_names(cls) -> tuple[str, ...]:
        return tuple(f.name for f in fields(cls) if f.name != "manifest")

    def frame(self, name: str) -> pd.DataFrame:
        return getattr(self, name).to_pandas()

    def with_manifest(self, **entries: Any) -> IsnadGraph:
        return replace(self, manifest={**self.manifest, **entries})

    # ── persistence ─────────────────────────────────────────────────────────
    def save(self, directory: Path | str) -> Path:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        for name in self.table_names():
            pq.write_table(getattr(self, name), d / f"{name}.parquet", compression="zstd",
                           compression_level=19)
        (d / "manifest.json").write_text(
            json.dumps(dict(self.manifest), ensure_ascii=False, indent=2, default=str) + "\n")
        return d

    @classmethod
    def load(cls, directory: Path | str) -> IsnadGraph:
        d = Path(directory)
        return cls(**{n: pq.read_table(d / f"{n}.parquet") for n in cls.table_names()},
                   manifest=json.loads((d / "manifest.json").read_text()))

    # ── queries ─────────────────────────────────────────────────────────────
    def _where(self, name: str, column: str, value: Any) -> pd.DataFrame:
        t = getattr(self, name)
        return t.filter(pc.equal(t[column], value)).to_pandas()

    def narrator(self, rawi_id: int) -> dict[str, Any]:
        rows = self._where("narrators", "id", rawi_id).to_dict("records")
        if not rows:
            raise KeyError(rawi_id)
        return rows[0]

    def teachers(self, rawi_id: int) -> pd.DataFrame:
        return self._where("transmissions", "dst", rawi_id).sort_values("n_chains", ascending=False)

    def students(self, rawi_id: int) -> pd.DataFrame:
        return self._where("transmissions", "src", rawi_id).sort_values("n_chains", ascending=False)

    def chains_of(self, hadith_id: int) -> pd.DataFrame:
        return self._where("chains", "hadith_id", hadith_id)

    def render_chain(self, chain_id: int) -> str:
        """Human-readable chain, apex first; gaps shown on the arrows."""
        row = self._where("chains", "chain_id", chain_id).iloc[0]
        names = self.narrators.select(["id", "name"]).to_pandas().set_index("id").name
        arrows = [" → " if f == 0 else f" ⇢[{LinkFlag(f)!r}] " for f in row.links]
        parts = [names.get(int(p), str(p)) for p in row.path]
        return "".join(a + b for a, b in zip(["", *arrows], parts, strict=True))

    def to_networkx(self, *, min_chains: int = 1, recorded_only: bool = False) -> nx.DiGraph:
        """Narrator transmission digraph (teacher → student) with all annotations."""
        e = self.frame("transmissions")
        weight = e.n_recorded if recorded_only else e.n_chains
        e = e[weight.ge(min_chains)].assign(weight=weight)
        nodes = self.frame("narrators").set_index("id")
        g = nx.DiGraph()
        g.add_nodes_from((i, _attrs(r)) for i, r in
                         nodes[nodes.kind.ne(NodeKind.MARKER)].to_dict("index").items())
        g.add_edges_from((r.pop("src"), r.pop("dst"), _attrs(r)) for r in e.to_dict("records"))
        src = self.manifest.get("source", {})
        g.graph.update(name="isnad transmission graph", builder=self.manifest.get("builder", ""),
                       **{f"source_{k}": src.get(k, "") for k in ("repo", "revision", "license")})
        return g

    # ── accounting ──────────────────────────────────────────────────────────
    def counts(self) -> dict[str, Any]:
        n, c, e = self.frame("narrators"), self.frame("chains"), self.frame("transmissions")
        return {
            "tables": {name: getattr(self, name).num_rows for name in self.table_names()},
            "narrators_by_kind": n.kind.value_counts().to_dict(),
            "chains_by_provenance": c.provenance.value_counts().to_dict(),
            "links": int(c.n_links.sum()),
            "transmission_flags": {col: int(e[col].sum()) for col in e.columns
                                   if col.startswith("n_") and col not in
                                   ("n_chains", "n_hadiths", "n_books")},
            "chronology": e.chronology.value_counts().to_dict(),
            "common_links": int(self.frame("common_links").is_common_link.sum()),
        }

    def verify(self) -> dict[str, bool]:
        """Structural invariants of the graph; all must hold."""
        n, c, e = self.frame("narrators"), self.frame("chains"), self.frame("transmissions")
        h, a = self.frame("hadiths"), self.frame("assessments")
        ids, markers = set(n.id), set(n.id[n.kind.eq(NodeKind.MARKER)])
        on_path = c.path.explode().dropna().astype("int64")
        prophetic = c.hadith_type_no.isin(PROPHETIC_TYPES)
        source_sanads = (self.manifest.get("source", {}).get("meta", {})
                         .get("report.count_sanads"))
        return {
            "edge_endpoints_are_nodes": bool(e.src.isin(ids).all() and e.dst.isin(ids).all()),
            "path_nodes_are_nodes": bool(on_path.isin(ids).all()),
            "no_marker_on_any_path": not bool(on_path.isin(markers).any()),
            "one_flag_per_link": bool((c.links.map(len) == c.path.map(len) - 1).all()),
            "one_mode_per_link": bool((c.modes.map(len) == c.links.map(len)).all()),
            "mode_histogram_partitions_links": bool(
                (e.filter(like="mode_").sum(axis=1) == e.n_links).all()),
            "link_mass_conserved": int(e.n_links.sum()) == int(c.n_links.sum()),
            "provenance_partitions_links": bool((e.n_recorded + e.n_inferred == e.n_links).all()),
            "no_direct_self_loops": not bool((e.src.eq(e.dst) & e.n_direct.gt(0)).any()),
            "prophet_only_as_apex_of_prophetic_chains": bool(
                (c.path.map(lambda p: p[0] == PROPHET_ID) == prophetic).all()
                and not c.path.map(lambda p: PROPHET_ID in p[1:]).any()),
            "chains_reference_hadiths": bool(c.hadith_id.isin(h.id).all()),
            "every_recorded_sanad_present": source_sanads is None or int(source_sanads) == int(
                c.provenance.eq(Provenance.RECORDED).sum()),
            "alignments_reference_hadiths": bool(
                self.frame("alignments").hadith_id.isin(h.id).all()),
            "each_external_entry_aligned_once": not bool(self.frame("alignments")
                .duplicated(["collection", "hadithnumber"]).any()),
            "assessments_reference_nodes": bool(
                a.rawi_id.isin(ids).all() and a.alem_id.isin(self.frame("critics").id).all()),
        }
