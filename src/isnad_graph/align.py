"""Text alignment of an external edition to the source's reports.

Numbering systems differ between editions (Bukhārī: 7,031 source reports vs
7,589 numbered entries), and some editions number each parallel route of a
report separately where the source merges them into one report with several
sanads (Muslim). So each external entry is mapped to the source report that
best *contains* it: the share of the entry's normalized word trigrams found in
the report, through an inverted index. The result is a function entry → report
(many-to-one), kept where containment ≥ threshold.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import NamedTuple

from .arabic import normalize

K = 3
# Phrases editions spell, abbreviate (ﷺ) or omit at will; inline Qurʾān references.
NOISE = re.compile(r"صلي الله عليه وسلم|رضي الله (?:تعالي )?عن(?:هما|ها|هم|ه)|عليه السلام"
                   r"|عز وجل|سوره \S+ ايه")


class Match(NamedTuple):
    left: int
    right: int
    score: float


def shingles(text: str, k: int = K) -> frozenset[str]:
    t = NOISE.sub(" ", normalize(text.replace("ﷺ", " صلى الله عليه وسلم "))).split()
    return frozenset(" ".join(t[i:i + k]) for i in range(len(t) - k + 1))


def align(left: Mapping[int, str], right: Mapping[int, str],
          threshold: float = 0.5, max_df: int = 64) -> list[Match]:
    """Map each left text to the right text containing the largest share of its
    trigrams (ties: lowest id), if that share ≥ ``threshold``.

    Trigrams occurring in more than ``max_df`` right texts (formulaic isnad
    phrases) do not propose candidates but still count in the denominator.
    """
    rs = {j: shingles(t) for j, t in right.items()}
    postings: dict[str, list[int]] = defaultdict(list)
    for j, s in rs.items():
        for g in s:
            postings[g].append(j)
    index = {g: ids for g, ids in postings.items() if len(ids) <= max_df}

    def best(s: frozenset[str]) -> tuple[int, float] | None:
        shared = Counter(j for g in s for j in index.get(g, ()))
        j, n = max(shared.items(), key=lambda x: (x[1], -x[0]), default=(None, 0))
        return None if j is None else (j, n / len(s))

    return sorted(
        Match(i, j, round(score, 4))
        for i, t in left.items() if (s := shingles(t))
        for j, score in [best(s) or (None, 0.0)]
        if j is not None and score >= threshold
    )


def order_consistency(matches: Sequence[Match], left_rank: Mapping[int, float],
                      right_rank: Mapping[int, float]) -> float:
    """Share of consecutive matches (in left order) whose right order agrees —
    an independent check, since alignment never looks at numbering."""
    seq = [right_rank[m.right] for m in sorted(matches, key=lambda m: left_rank[m.left])]
    steps = list(pairwise(seq))
    return sum(b >= a for a, b in steps) / max(len(steps), 1)
