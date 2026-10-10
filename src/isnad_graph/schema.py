"""Vocabulary of the graph: node kinds, link flags, provenance, sentinel ids."""

from __future__ import annotations

from enum import IntFlag, StrEnum
from types import MappingProxyType


class LinkFlag(IntFlag):
    """Annotation on one transmission link teacher → student.

    ``DIRECT`` (0) is an unbroken, named link. Any other value records which
    source gap markers stood between the two named narrators.
    """

    DIRECT = 0
    IRSAL = 1  # موضع إرسال — a narrator skipped at the top (mursal)
    INQITA = 2  # موضع انقطاع — a break inside the chain (munqati')
    TALIQ = 4  # موضع تعليق — the compiler suspends the chain (mu'allaq)
    MUBHAM = 8  # اسم مبهم / غير معرف — an unnamed or unidentified narrator


class NodeKind(StrEnum):
    NARRATOR = "narrator"
    PROPHET = "prophet"  # synthetic apex of marfu' and qudsi chains
    MARKER = "marker"  # source pseudo-narrator encoding a gap; never on a path
    STUB = "stub"  # chain narrator without a source biography


class Provenance(StrEnum):
    RECORDED = "recorded"  # an explicit sanad of the source
    INFERRED = "inferred"  # derived from in-text narrator mentions


class HadithType(StrEnum):
    QUDSI = "قدسي"
    MARFU = "مرفوع"
    MAWQUF = "موقوف"
    MAQTU = "مقطوع"


PROPHETIC_TYPES = frozenset({0, 1})  # hadiths.type_no of qudsi / marfu'

PROPHET_ID = -1
PROPHET_NAME = "محمد رسول الله ﷺ"
PROPHET_DEATH_YEAR = 11  # AH

# Gap markers are identified by name, not id, so a re-cut source still resolves.
MARKER_NAMES = MappingProxyType(
    {
        "موضع إرسال": LinkFlag.IRSAL,
        "موضع انقطاع": LinkFlag.INQITA,
        "موضع تعليق": LinkFlag.TALIQ,
        "اسم مبهم": LinkFlag.MUBHAM,
        "غير معرف": LinkFlag.MUBHAM,
    }
)

FLAG_COLUMNS = MappingProxyType({f: f"n_{f.name.lower()}" for f in LinkFlag if f})
