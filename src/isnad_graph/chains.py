"""Pure chain algebra: source chains → normalized paths with annotated links.

A source chain lists narrator ids from the compiler (pos 0) up to the apex,
interleaved with *gap markers* (pseudo-narrators such as «موضع إرسال»). A
normalized chain is read in transmission order — apex first, compiler last —
contains only real narrators (plus the synthetic Prophet node for prophetic
reports) and carries one :class:`LinkFlag` per consecutive pair, recording the
markers that stood between them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from functools import reduce

from .schema import PROPHET_ID, LinkFlag


@dataclass(frozen=True, slots=True)
class Chain:
    path: tuple[int, ...]  # apex → compiler
    links: tuple[LinkFlag, ...]  # links[i] annotates path[i] → path[i+1]
    head_gap: LinkFlag = LinkFlag.DIRECT  # markers above the apex (non-prophetic only)
    tail_gap: LinkFlag = LinkFlag.DIRECT  # markers below the compiler
    repeats: int = 0  # consecutive duplicate narrators collapsed

    def __post_init__(self) -> None:
        assert len(self.links) == max(len(self.path) - 1, 0), "one flag per link"

    def edges(self) -> tuple[tuple[int, int, LinkFlag], ...]:
        return tuple(zip(self.path[:-1], self.path[1:], self.links, strict=True))


EMPTY = Chain(path=(), links=())


def _step(markers: Mapping[int, LinkFlag]):
    def step(acc: tuple[Chain, LinkFlag], rid: int) -> tuple[Chain, LinkFlag]:
        chain, pending = acc
        if rid in markers:
            return chain, pending | markers[rid]
        if chain.path and chain.path[-1] == rid and not pending:
            return replace(chain, repeats=chain.repeats + 1), pending
        if not chain.path:
            return replace(chain, path=(rid,), head_gap=pending), LinkFlag.DIRECT
        return (replace(chain, path=(*chain.path, rid), links=(*chain.links, pending)),
                LinkFlag.DIRECT)

    return step


def normalize(
    source_chain: Sequence[int], markers: Mapping[int, LinkFlag], prophetic: bool
) -> Chain:
    """Normalize a compiler-first source chain (pos 0..n).

    For prophetic reports the Prophet is prepended as apex, so a top-level
    «موضع إرسال» becomes an IRSAL-flagged link tabi'i ← Prophet.
    """
    apex_first = ((PROPHET_ID,) if prophetic else ()) + tuple(reversed(source_chain))
    chain, pending = reduce(_step(markers), apex_first, (EMPTY, LinkFlag.DIRECT))
    return replace(chain, tail_gap=pending)

