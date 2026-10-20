"""Lifespans as intervals, and whether two lifespans let a transmission happen.

Every narrator gets a death interval ``[death_lo, death_hi]`` (AH) and a birth
interval, each with a *basis* saying where it comes from. Death:

* ``recorded`` — the source's range (``"130 - 121"``) or year;
* ``tabaqa``   — none recorded: the central ``TABAQA_COVERAGE`` of the
  recorded death years of the narrator's tabaqa (the source's 38 layers, about
  25 years apart from the seventh on), if that tabaqa has ``MIN_TABAQA_N``;
* ``none``     — neither.

Birth:

* ``recorded`` — the source's birth year (or range);
* ``age``      — the source's age at death, subtracted from a recorded death;
* ``prior``    — otherwise ``[death_lo − L_MAX, death_hi]``, the assumption
  that nobody lived longer than ``L_MAX`` years;
* ``none``     — no death interval either.

Births by ``recorded``/``age`` and deaths by ``recorded`` are *documented*.

A transmission teacher → student needs the two lifespans to overlap:
``birth(student) ≤ death(teacher)`` and ``birth(teacher) ≤ death(student)``.
With intervals, a lifespan pair is *refuted* when even the most generous
bounds miss — ``birth_lo(s) > death_hi(t)`` or ``birth_lo(t) > death_hi(s)``.
The verdict on an edge is the first that applies of

    unknown      either death year is missing
    conflict     either biography contradicts itself (born after death, or an
                 age at death off by more than ``AGE_TOL`` from death − birth)
    impossible   refuted by documented dates alone
    implausible  refuted only once the ``L_MAX`` prior or the tabaqa is used
    consistent   not refuted

``consistent`` claims only that the dates do not rule the link out.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

#: Longest life assumed when the source records neither birth nor age; 99.8%
#: of the source's recorded ages at death are ≤ 120.
L_MAX = 120
#: Tolerance between a recorded age and death − birth (lunar-year rounding).
AGE_TOL = 2
#: Median of the source's recorded ages at death: the point estimate of a birth
#: known only through the prior (``estimate``).
TYPICAL_LIFE = 80
TABAQA_COVERAGE = 0.95
MIN_TABAQA_N = 30
_YEARS = re.compile(r"^\s*(\d{1,4})\s*(?:[-:]\s*(\d{1,4})\s*)?$")
VERDICTS = ("unknown", "conflict", "impossible", "implausible", "consistent")


def parse_years(raw: object) -> tuple[int, int] | None:
    """``"250"`` → (250, 250); ``"130 - 121"`` → (121, 130); anything else → None."""
    m = _YEARS.match(raw) if isinstance(raw, str) else None
    if not m:
        return None
    a, b = int(m[1]), int(m[2] or m[1])
    return min(a, b), max(a, b)


def _interval(raw: pd.Series, year: pd.Series) -> pd.DataFrame:
    parsed = raw.map(parse_years)
    lo = parsed.map(lambda p: p and p[0]).astype("Float64").fillna(year.astype("Float64"))
    hi = parsed.map(lambda p: p and p[1]).astype("Float64").fillna(year.astype("Float64"))
    return pd.DataFrame({"lo": lo, "hi": hi})


def tabaqa_deaths(tabaka: pd.Series, death: pd.Series) -> pd.DataFrame:
    """Per tabaqa with ≥ ``MIN_TABAQA_N`` recorded deaths: the central
    ``TABAQA_COVERAGE`` interval of those deaths, floored and ceiled to years."""
    tail = (1 - TABAQA_COVERAGE) / 2
    by = pd.DataFrame({"t": tabaka, "d": death.astype("float64")}).dropna().groupby("t").d
    q = by.quantile([tail, 1 - tail]).unstack().reindex(columns=[tail, 1 - tail])
    q = q[by.size().reindex(q.index) >= MIN_TABAQA_N]
    return pd.DataFrame({"lo": np.floor(q[tail]), "hi": np.ceil(q[1 - tail])})


def lifespans(narrators: pd.DataFrame) -> pd.DataFrame:
    """Birth and death intervals, their bases and self-contradiction, per narrator."""
    rec = _interval(narrators.death_year_raw, narrators.death_year)
    layer = tabaqa_deaths(narrators.tabaka, rec.lo).reindex(narrators.tabaka.to_numpy())
    d = rec.fillna(layer.set_axis(rec.index).astype("Float64"))
    b = _interval(narrators.birth_year_raw, narrators.birth_year)
    age = pd.to_numeric(narrators.age_raw, errors="coerce").astype("Float64")
    recorded, aged = b.lo.notna(), age.notna() & rec.lo.notna()
    birth_lo = b.lo.fillna((rec.lo - age).where(aged)).fillna(d.lo - L_MAX)
    birth_hi = b.hi.fillna((rec.hi - age).where(aged)).fillna(d.hi)
    life = (rec.lo + rec.hi) / 2 - (b.lo + b.hi) / 2
    conflict = (b.lo > rec.hi).fillna(False) | ((life - age).abs() > AGE_TOL).fillna(False)
    return pd.DataFrame({
        "id": narrators.id.to_numpy(),
        "birth_lo": birth_lo, "birth_hi": birth_hi, "death_lo": d.lo, "death_hi": d.hi,
        "birth_basis": np.select([recorded, aged, d.lo.notna()], ["recorded", "age", "prior"],
                                 "none"),
        "death_basis": np.select([rec.lo.notna(), d.lo.notna()], ["recorded", "tabaqa"], "none"),
        "bio_conflict": conflict.astype(bool),
    })


def feasibility(edges: pd.DataFrame, spans: pd.DataFrame) -> pd.DataFrame:
    """Edges with ``chronology`` (see module doc), ``overlap`` of the documented
    lifespans and ``student_age_at_teacher_death`` (years; NA unless every date
    they use is documented: births by record or age, deaths by record), and
    ``ante_quem``, the earlier death: the last year the transmission can be from."""
    s = spans.set_index("id")
    t, u = (s.reindex(edges[end].to_numpy()).reset_index(drop=True) for end in ("src", "dst"))
    documented = lambda x: x.birth_basis.isin(["recorded", "age"])  # noqa: E731

    def refuted(strict: bool) -> pd.Series:
        def bounds(x: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
            return ((x.birth_lo.where(documented(x)), x.death_hi.where(
                x.death_basis.eq("recorded"))) if strict else (x.birth_lo, x.death_hi))
        (bt, dt), (bu, du) = bounds(t), bounds(u)
        return ((bu > dt) | (bt > du)).fillna(False)

    mid = lambda x, k: (x[f"{k}_lo"] + x[f"{k}_hi"]) / 2  # noqa: E731
    bt, bu = (mid(x, "birth").where(documented(x)) for x in (t, u))
    dt, du = (mid(x, "death").where(x.death_basis.eq("recorded")) for x in (t, u))
    verdict = np.select(
        [t.death_lo.isna() | u.death_lo.isna(),
         t.bio_conflict.fillna(False) | u.bio_conflict.fillna(False),
         refuted(True), refuted(False)],
        list(VERDICTS[:4]), VERDICTS[4])
    keep = lambda v: pd.Series(v.to_numpy(), index=edges.index)  # noqa: E731
    return edges.assign(
        chronology=verdict,
        overlap=keep(np.minimum(dt, du) - np.maximum(bt, bu)),
        student_age_at_teacher_death=keep(dt - bu),
        ante_quem=keep(np.minimum(t.death_hi, u.death_hi)),
    )


def estimate(spans: pd.DataFrame) -> pd.DataFrame:
    """Point estimates: ``birth_est`` (the documented birth's midpoint, else death
    − ``TYPICAL_LIFE``) and ``death_est`` (the death interval's midpoint)."""
    death = (spans.death_lo + spans.death_hi) / 2
    documented = spans.birth_basis.isin(["recorded", "age"])
    birth = ((spans.birth_lo + spans.birth_hi) / 2).where(documented, death - TYPICAL_LIFE)
    return spans.assign(birth_est=birth, death_est=death)
