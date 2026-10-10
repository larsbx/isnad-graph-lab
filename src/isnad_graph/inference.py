"""Chains inferred from in-text narrator mentions, for reports the source
records without an explicit sanad (chiefly mawquf and maqtu' reports).

The rule is deliberately conservative — it abstains rather than guesses:

* the matn boundary must be known (mentions inside the matn are not isnad);
* the isnad must be linear (no tahwil «ح» switching between routes);
* every isnad mention must resolve to a known narrator.

Mentions are then read in text order, which is compiler-side first — the same
orientation as a source sanad, which may or may not include its pos-0 compiler
(later compilations tend to name it in the text, earlier ones do not).
"""

from __future__ import annotations

import re
from collections.abc import Container, Sequence
from typing import NamedTuple

_ARABIC = "ء-ٰٟ-ۓ"
TAHWIL = re.compile(rf"(?<![{_ARABIC}])ح(?![{_ARABIC}])")


class Mention(NamedTuple):
    rawi_id: int | None
    start: int
    end: int


def _isnad(mentions: Sequence[Mention], matn_start: int) -> tuple[Mention, ...]:
    return tuple(m for m in sorted(mentions, key=lambda m: m.start) if m.end <= matn_start)


def abstention(
    mentions: Sequence[Mention], matn_start: int | None, text: str, known: Container[int]
) -> str | None:
    """Why the rule abstains, or ``None`` if it can infer a chain."""
    if matn_start is None:
        return "no_matn_boundary"
    if TAHWIL.search(text[:matn_start]):
        return "tahwil"
    if not (isnad := _isnad(mentions, matn_start)):
        return "no_isnad_mentions"
    if any(m.rawi_id is None or m.rawi_id not in known for m in isnad):
        return "unresolved_mention"
    return None


def infer_source_chain(
    mentions: Sequence[Mention], matn_start: int | None, text: str, known: Container[int]
) -> tuple[int, ...] | None:
    """Compiler-first narrator ids of the isnad, or ``None`` to abstain."""
    if abstention(mentions, matn_start, text, known):
        return None
    return tuple(m.rawi_id for m in _isnad(mentions, matn_start))  # type: ignore[arg-type]
