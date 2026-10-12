"""The thing a scene draws, and every reason it can be refused.

A `Figure` is the whole interface between the estate's artifacts and the
animation. Nothing downstream of here reads a repository, and nothing upstream
of here knows what manim is.

Two rules are carried by the type rather than by discipline:

*   **A figure cannot exist without provenance.** `Provenance` is a required
    field, its digest is the sha256 of the exact bytes the figure was built
    from, and every scene stamps it on the frame. A frame that names no source
    is unrepresentable rather than merely discouraged.

*   **The vocabulary belongs to the source.** `terms` are the classes the
    source file itself declares, in the order it declares them, and a node
    whose term is not among them is refused. vizops never invents a class,
    never maps one repository's word onto another's, and never promotes a
    term: the words on the frame are the words in the file.

`FigureError` names every problem at once, so a malformed artifact takes one
run to diagnose rather than one run per defect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

DIGEST = re.compile(r"^[0-9a-f]{64}$")

#: Stamped on every frame. A rendered animation is a derived surface: it is
#: evidence of what an artifact said at one digest, and of nothing else.
CAVEAT = "derived surface — depicts the source at this digest; authorizes nothing"


class FigureError(ValueError):
    """The figure is malformed; the message names every reason."""


@dataclass(frozen=True, slots=True)
class Provenance:
    repo: str
    path: str
    digest: str
    generator: str = ""

    def __post_init__(self) -> None:
        problems = [f"provenance: {f} is empty" for f in ("repo", "path") if not getattr(self, f)]
        if not DIGEST.fullmatch(self.digest):
            problems.append(f"provenance: {self.digest!r} is not a sha256 hex digest")
        if problems:
            raise FigureError("\n  ".join(("provenance refused:", *problems)))

    @property
    def stamp(self) -> str:
        return f"{self.repo}/{self.path} @ sha256:{self.digest[:12]}"


@dataclass(frozen=True, slots=True)
class Term:
    """One class the source declares, in the source's own words."""

    id: str
    name: str
    description: str = ""


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    label: str
    term: str
    badge: str = ""
    note: str = ""


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: str


@dataclass(frozen=True, slots=True)
class Figure:
    title: str
    provenance: Provenance
    terms: tuple[Term, ...]
    kinds: tuple[str, ...]
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...] = ()

    def __post_init__(self) -> None:
        problems: list[str] = []
        if not self.title.strip():
            problems.append("figure: no title")
        problems += _duplicates("term", (t.id for t in self.terms))
        problems += _duplicates("edge kind", self.kinds)
        problems += _duplicates("node", (n.id for n in self.nodes))
        if not self.terms:
            problems.append("figure: no terms; the source declares the vocabulary and this one declared none")
        if not self.nodes:
            problems.append("figure: no nodes; an empty frame depicts nothing and is not a render")
        terms, ids = {t.id for t in self.terms}, {n.id for n in self.nodes}
        problems += [f"node {n.id}: term {n.term!r} is not one the source declares" for n in self.nodes if n.term not in terms]
        problems += [f"node {n.id}: no label" for n in self.nodes if not n.label.strip()]
        for e in self.edges:
            where = f"edge {e.source}->{e.target}"
            problems += [f"{where}: {end!r} is not a node in this figure" for end in (e.source, e.target) if end not in ids]
            if e.kind not in self.kinds:
                problems.append(f"{where}: kind {e.kind!r} is not one the source declares")
            if e.source == e.target:
                problems.append(f"{where}: an edge from a node to itself")
        if problems:
            raise FigureError("\n  ".join((f"figure refused: {self.title}", *problems)))

    @property
    def caveat(self) -> str:
        return CAVEAT

    def populated(self) -> tuple[Term, ...]:
        """The declared terms that this figure actually has nodes for, in
        declared order. A class with no members keeps its colour and leaves
        the frame, rather than shifting the colours of the ones that stayed."""
        present = {n.term for n in self.nodes}
        return tuple(t for t in self.terms if t.id in present)

    def used_kinds(self) -> tuple[str, ...]:
        """The declared edge kinds this figure actually draws, in declared
        order. A vocabulary can declare nine kinds and a figure use two; a key
        that lists the other seven tells a reader nothing about the frame."""
        present = {e.kind for e in self.edges}
        return tuple(k for k in self.kinds if k in present)

    def members(self) -> Mapping[str, tuple[str, ...]]:
        """Node ids per term, in figure order."""
        return {t.id: tuple(n.id for n in self.nodes if n.term == t.id) for t in self.populated()}

    def node(self, node_id: str) -> Node:
        return next(n for n in self.nodes if n.id == node_id)


def _duplicates(what: str, ids: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    return [f"{what} {i!r}: declared twice" for i in ids if i in seen or seen.add(i)]  # type: ignore[func-returns-value]
