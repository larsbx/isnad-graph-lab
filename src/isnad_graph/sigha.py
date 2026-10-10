"""Modes of transmission (صيغ الأداء) read from the isnad text.

Between two narrator mentions «… S ‹gap› T …» the gap holds the formula by
which the student S received from the teacher T. Four rules, each mined from
the corpus:

1. **Last formula governs** — the formula adjacent to T's name is the one that
   counts: «يحدث عن T» is ʿan, «قال: حدثنا T» is taḥdīth.
2. **Post-posed verbs** — «عن S أن T حدثه أن …»: the verb after T's name
   (حدثه, أخبره) upgrades the preceding *anna* link S ← T to an explicit one.
3. **Co-narrators** — «حدثنا A و B قالا حدثنا C»: a gap that is only a
   conjunction groups A and B; the next formula applies to each of them.
4. **Taḥwīl** — a «ح» in the gap restarts the route, at the compiler or at the
   isnad's first narrator («وبالإسناد إلى الطبراني … ح قال ونا»); both are
   offered, and only pairs that are real chain links are ever looked up.

Two more recover links whose endpoints are not adjacent in the text:

5. **Gap markers** — «عن S عن ‹شيخ› عن T»: the chain bridges T → S over the
   anonymous narrator; the link takes S's formula.
6. **Unnamed kin** — «S عن أبيه عن T»: the chain holds the father H; the kin
   word splits the gap into the formulas of S ← H and H ← T.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Container, Mapping, Sequence
from enum import IntEnum
from itertools import pairwise
from types import MappingProxyType
from typing import NamedTuple

from .arabic import normalize
from .schema import PROPHET_ID

COMPILER = -2  # sentinel student: the (usually unnamed) compiler of the book


class Mode(IntEnum):
    UNREAD = 0  # no formula recognised (or conflicting readings)
    SAMA = 1  # سمعت، سمع، إملاء
    TAHDITH = 2  # حدثنا، حدثني، ثنا، نا
    IKHBAR = 3  # أخبرنا، أنا، أنبأنا، نبأنا
    QIRAA = 4  # قرأت على، قرئ على، بقراءتي
    LIQA = 5  # سألت، رأيت، دخلت على، أتيت — explicit encounter
    KITABA = 6  # كتب إلي
    IJAZA = 7  # أجاز لي
    WIJADA = 8  # وجدت (في كتاب)
    AN = 9  # عن
    ANNA = 10  # أن، أنه
    QALA = 11  # قال، قالت، قالا، قالوا
    DHAKARA = 12  # ذكر
    RAWA = 13  # روى، يروي


EXPLICIT = frozenset({Mode.SAMA, Mode.TAHDITH, Mode.IKHBAR, Mode.QIRAA, Mode.LIQA})
WRITTEN = frozenset({Mode.KITABA, Mode.IJAZA, Mode.WIJADA})
AMBIGUOUS = frozenset({Mode.AN, Mode.ANNA, Mode.QALA, Mode.DHAKARA, Mode.RAWA})


def mode_class(mode: Mode) -> str:
    return ("explicit" if mode in EXPLICIT else "written" if mode in WRITTEN
            else "ambiguous" if mode in AMBIGUOUS else "unread")


def _lexicon(**groups: str) -> Mapping[str, Mode]:
    return MappingProxyType({w: Mode[m] for m, words in groups.items() for w in words.split()})


WORDS = _lexicon(  # normalized forms (see arabic.normalize)
    SAMA="سمعت سمع سمعنا سمعته سمعا املاء املي",
    TAHDITH="حدثنا حدثني حدثتني حدثتنا حدثناه حدثنيه ثنا نا ثني قثنا حدثهم حدث يحدثنا",
    IKHBAR="اخبرنا اخبرني اخبرتني اخبرتنا اخبرناه انا ابنا انبا انبانا انباني نبانا نبا اخبرهم",
    LIQA="سالت رايت اتيت شهدت لقيت",
    IJAZA="اجاز اجازه",
    WIJADA="وجدت",
    AN="عن",
    ANNA="ان انه انها انهم انهما",
    QALA="قال قالت قالا قالوا يقول تقول",
    DHAKARA="ذكر يذكر ذكره",
    RAWA="روي يروي رواه يرويه",
)
PHRASES = MappingProxyType({
    ("قرات", "علي"): Mode.QIRAA, ("قرئ", "علي"): Mode.QIRAA, ("قراءه", "عليه"): Mode.QIRAA,
    ("بقراءتي", "عليه"): Mode.QIRAA, ("دخلت", "علي"): Mode.LIQA,
    ("كتب", "الي"): Mode.KITABA, ("كتب", "الينا"): Mode.KITABA, ("كتب", "اليه"): Mode.KITABA,
})
POST_VERBS = MappingProxyType({  # verb right after T's name, about T's own hearing
    "حدثه": Mode.TAHDITH, "حدثها": Mode.TAHDITH, "حدثهم": Mode.TAHDITH,
    "اخبره": Mode.IKHBAR, "اخبرها": Mode.IKHBAR, "اخبرهم": Mode.IKHBAR,
    "اخبرتهم": Mode.IKHBAR, "انباه": Mode.IKHBAR,
})
CONJUNCTIONS = frozenset({"", "و", "او"})
KIN = frozenset({
    "ابيه", "ابيها", "جده", "جدته", "جدها", "عمه", "عمته",
    "اخيه", "اخته", "امه", "امها", "خاله", "مولاه",
})
TAHWIL = "ح"


def _lookup(token: str) -> Mode | None:
    if (m := WORDS.get(token)) is not None:
        return m
    if token[:1] in "وف" and len(token) > 2:  # proclitic wa-/fa-
        return WORDS.get(token[1:])
    return None


class Gap(NamedTuple):
    mode: Mode  # the formula governing the following name
    post: Mode | None  # a post-posed verb about the preceding name
    tahwil: bool
    conjunction: bool
    kin: tuple[Mode, Mode] | None  # (S ← kin, kin ← T) when an unnamed relative intervenes


def _last_formula(tokens: Sequence[str]) -> Mode:
    return next(
        (m for i in range(len(tokens) - 1, -1, -1)
         if (m := PHRASES.get(tuple(tokens[i:i + 2])) or _lookup(tokens[i])) is not None),
        Mode.UNREAD,
    )


def read_gap(raw: str) -> Gap:
    tokens = normalize(raw).split()
    text = " ".join(tokens)
    tahwil = TAHWIL in tokens or any(t.startswith("حو") and _lookup(t[1:]) for t in tokens)
    tokens = [t[1:] if t.startswith("حو") else t for t in tokens]
    k = next((i for i, t in enumerate(tokens) if t in KIN), None)
    kin = None if k is None else (_last_formula(tokens[:k]), _last_formula(tokens[k + 1:]))
    post = POST_VERBS.get(tokens[0]) if tokens else None
    return Gap(_last_formula(tokens), post, tahwil, text in CONJUNCTIONS, kin)


class Mention(NamedTuple):
    rawi_id: int
    start: int
    end: int


APEX_WINDOW = 12  # tokens after the last isnad mention; the source's matn often starts
# before «قال رسول الله ﷺ», so the Prophet may be named just inside it


def apex_mode(tail: str) -> Mode | None:
    """Mode of the link to the Prophet ﷺ from the text after the last isnad
    mention («… قال: سمعت رسول الله ﷺ يقول»), if he is named within the window."""
    tokens = normalize(tail.replace("ﷺ", " النبي ")).split()[:APEX_WINDOW]
    def named(i, t):
        return (t in ("النبي", "للنبي")
                 or (t in ("رسول", "لرسول") and tokens[i + 1:i + 2] == ["الله"]))
    at = next((i for i, t in enumerate(tokens) if named(i, t)), None)
    return None if at is None else read_gap(" ".join(tokens[:at])).mode


class Readings(NamedTuple):
    pairs: dict[tuple[int, int], Mode]  # (student, teacher) → mode
    hops: dict[tuple[int, int], tuple[Mode, Mode]]  # (student, teacher) over unnamed kin


def transmission_modes(
    text: str, mentions: Sequence[Mention], isnad_end: int,
    markers: Container[int] = frozenset(),
) -> Readings:
    """Modes of every adjacent pair in one isnad (rules 1–6).

    ``text`` may run past ``isnad_end`` (for the apex link). The compiler
    appears as student :data:`COMPILER`, the Prophet as teacher
    :data:`PROPHET_ID`. Pairs read with conflicting modes map to ``Mode.UNREAD``.
    """
    ms = sorted((m for m in mentions if m.end <= isnad_end), key=lambda m: m.start)
    gaps = [read_gap(text[a.end:b.start]) for a, b in zip([None, *ms], ms, strict=False)
            for a in ([a] if a else [Mention(COMPILER, 0, 0)])]
    readings: dict[tuple[int, int], set[Mode]] = defaultdict(set)
    hops: dict[tuple[int, int], tuple[Mode, Mode]] = {}
    students: tuple[int, ...] = ()
    group: tuple[int, ...] = (COMPILER,)
    last: list[tuple[int, int]] = []
    for m, gap in zip(ms, gaps, strict=True):
        if gap.post and last:  # rule 2: upgrade the preceding anna/ʿan link
            for key in last:
                if readings[key] <= {Mode.ANNA, Mode.AN}:
                    readings[key] = {gap.post}
        if gap.conjunction and students:  # rule 3: co-narrator of the current group
            group = (*group, m.rawi_id)
            last = [(s, m.rawi_id) for s in students]
            for key in last:
                readings[key] |= readings[(students[0], group[0])]
            continue
        students = (COMPILER, ms[0].rawi_id) if gap.tahwil else group  # rule 4
        last = [(s, m.rawi_id) for s in students]
        for key in last:
            readings[key].add(gap.mode)
            if gap.kin:  # rule 6
                hops[key] = gap.kin
        group = (m.rawi_id,)
    if ms and (apex := apex_mode(text[ms[-1].end:])) is not None:
        for s in group:
            readings[(s, PROPHET_ID)].add(apex)
    for (s, gap_marker), modes in list(readings.items()):  # rule 5
        if gap_marker in markers:
            for (s2, t), _ in list(readings.items()):
                if s2 == gap_marker and (s, t) not in readings:
                    readings[(s, t)] = set(modes)
    pairs = {k: next(iter(v)) if len(v) == 1 else Mode.UNREAD for k, v in readings.items()}
    return Readings(pairs, hops)


def link_modes(path: Sequence[int], readings: Readings) -> tuple[Mode, ...]:
    """Mode of each link teacher → student of a normalized chain (apex → compiler)."""
    compiler = path[-1] if len(path) else None

    def lookup(s: int, t: int) -> Mode | None:
        found = readings.pairs.get((s, t))
        return readings.pairs.get((COMPILER, t)) if found is None and s == compiler else found

    direct = [lookup(s, t) for t, s in pairwise(path)]
    modes = list(direct)
    for j in range(1, len(direct)):  # rule 6: path[j-1] → hidden path[j] → path[j+1]
        hop = readings.hops.get((path[j + 1], path[j - 1]))
        if hop and direct[j] is None and direct[j - 1] is None:
            modes[j], modes[j - 1] = hop
    return tuple(Mode.UNREAD if m is None else m for m in modes)


def borrowed_modes(
    path: Sequence[int], own: Readings, neighbours: Sequence[Readings]
) -> tuple[tuple[Mode, ...], int]:
    """Link modes read from the report itself, then — for links its text does not
    contain — from preceding reports of the same book, following the «بهذا
    الإسناد» convention. Returns the modes and how many were borrowed."""
    modes = link_modes(path, own)
    filled = modes
    for r in neighbours:
        other = link_modes(path, r)
        filled = tuple(o if m == Mode.UNREAD else m for m, o in zip(filled, other, strict=True))
    return filled, sum(a != b for a, b in zip(modes, filled, strict=True))
