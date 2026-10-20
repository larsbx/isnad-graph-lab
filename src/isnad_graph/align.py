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
          threshold: float = 0.5, max_df: int = 64, *,
          diagnostics: dict[int, dict] | None = None) -> list[Match]:
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

    result = []
    for i, t in left.items():
        s = shingles(t)
        if not s:
            continue
        shared = Counter(j for g in s for j in index.get(g, ()))
        ranked = sorted(shared, key=lambda j: (-shared[j], j))
        if not ranked:
            continue
        j = ranked[0]
        score = shared[j] / len(s)
        if score < threshold:
            continue
        if diagnostics is not None:
            runner_up = shared[ranked[1]] / len(s) if len(ranked) > 1 else 0.0
            diagnostics[i] = {
                "runner_up_score": runner_up,
                "score_margin": score - runner_up,
                "tied_candidates": sum(n == shared[j] for n in shared.values()),
                "text_relation": ("normalized_exact" if normalize(t) == normalize(right[j])
                                  else "textual_correspondence"),
            }
        result.append(Match(i, j, round(score, 4)))
    return sorted(result)


def order_consistency(matches: Sequence[Match], left_rank: Mapping[int, float],
                      right_rank: Mapping[int, float]) -> float:
    """Share of consecutive matches (in left order) whose right order agrees —
    a non-strict order check (equal positions count), not a correctness probability."""
    seq = [right_rank[m.right] for m in sorted(matches, key=lambda m: left_rank[m.left])]
    steps = list(pairwise(seq))
    return sum(b >= a for a, b in steps) / max(len(steps), 1)
