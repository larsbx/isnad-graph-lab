"""A miniature source database with the verbatim upstream schema.

Narrators: 1 Abu Hurayra (companion), 2 A, 3 B, 7 G (tabi'un and later),
4 C and 5 D (compilers; D born after A died), markers 30001 ta'liq, 30002 irsal.
A is a mudallis. Isnad texts read «حدثنا X عن Y عن Z قال : متن».

    h1 marfu', group 1:  s1 [4,3,2,1]  s2 [5,3,2,1]  s3 [4,7,2,1]  s6 [5,2,1]
    h2 marfu' (mursal):  s4 [4,3,30002]
    h5 marfu':           s5 [30001,2,1]
    h3 mawquf, no sanad: text mentions B ← Abu Hurayra       → inferred 1 → 3
    h4 maqtu', no sanad: tahwil in the isnad                 → abstain
    h6 mawquf, no sanad: isnad mentions only a gap marker     → no narrator, dropped
    h7 maqtu', no sanad: names one narrator                   → attribution-only chain [2]
    h8 marfu':           s7 [4,7,2,1], and its text also names the compiler 4
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

SCHEMA = Path(__file__).parent / "fixtures" / "schema.sql"

RAWIS = {  # id: (name, rank_no, tabaka, birth, death)
    1: ("أبو هريرة", 1, 1, None, 57), 2: ("ألف", 3, 3, 20, 100), 3: ("باء", 3, 5, 60, 150),
    7: ("جيم", 4, 5, 70, 160), 4: ("دال", 2, 10, 194, 256), 5: ("هاء", 2, 10, 200, 261),
    30001: ("موضع تعليق", 12, 0, None, None), 30002: ("موضع إرسال", 12, 0, None, None),
}
MUDALLIS = {2}  # A narrates with tadlis

SANADS = {1: (1, [4, 3, 2, 1]), 2: (1, [5, 3, 2, 1]), 3: (1, [4, 7, 2, 1]),
          4: (2, [4, 3, 30002]), 5: (5, [30001, 2, 1]), 6: (1, [5, 2, 1]), 7: (8, [4, 7, 2, 1])}
HADITHS = {  # id: (type_no, group_id, isnad mention ids, tahwil?)
    1: (1, 1, [3, 2, 1], False), 2: (1, 2, [3], False), 5: (1, 3, [2, 1], False),
    3: (2, None, [3, 1], False), 4: (3, None, [7, 2], True), 6: (2, None, [30002], False),
    7: (3, None, [2], False), 8: (1, 4, [4, 7, 2, 1], False),
}


def isnad_text(mention_ids, tahwil):
    text, spans = "", []
    for k, rid in enumerate(mention_ids):
        text += "حدثنا " if k == 0 else (" ح وحدثنا " if tahwil and k == 1 else " عن ")
        spans.append((rid, len(text), len(text) + len(RAWIS[rid][0])))
        text += RAWIS[rid][0]
    text += " قال : "
    return text + "متن", spans, len(text)


def make_db(path: Path) -> Path:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA.read_text())
    ins = lambda t, rows: con.executemany(  # noqa: E731
        f"INSERT INTO {t} VALUES ({','.join('?' * len(rows[0]))})", rows)
    ins("rawis", [(i, n, "", r, None, t, 0, 0, 0, int(i in MUDALLIS), 0, b, None, d, None,
                   None, None, None, None, None, 0) for i, (n, r, t, b, d) in RAWIS.items()])
    ins("books", [(1, "كتاب", 1, "مصنف", 256, None, None, None, 1, "صحاح", 5)])
    rows, mentions = [], []
    for hid, (type_no, gid, ids, tahwil) in HADITHS.items():
        text, spans, ms = isnad_text(ids, tahwil)
        rows.append((hid, 1, hid, 1, type_no, "t", 0, "صحيح", gid, None, "طرف", text, ms,
                     len(text)))
        mentions += [(hid, k, rid, s, e) for k, (rid, s, e) in enumerate(spans)]
    ins("hadiths", rows)
    ins("hadith_rawis", mentions)
    ins("sanads", [(s, h, 0, "صحيح", "إسناده متصل", HADITHS[h][1], None, 3, len(c))
                   for s, (h, c) in SANADS.items()])
    ins("sanad_rawis", [(s, p, r) for s, (_, c) in SANADS.items() for p, r in enumerate(c)])
    ins("meaning_groups", [(g, None, 0, 0, 1, 1, "نص") for g in (1, 2, 3, 4)])
    ins("topics", [(1, "باب", None, 0, 1, 2, 1, 1)])
    ins("alems", [(1, "ناقد", None, "ناقد", None, 9, 300, 1, None, 1, None)])
    ins("aqwal", [(1, 1, 3, "ثقة")])
    ins("meta", [("report.count_sanads", str(len(SANADS)))])
    con.commit()
    con.close()
    return path


def make_editions(directory: Path) -> Path:
    """A miniature external edition of book 1 with its own numbering: entry 10 is
    h1's text, entry 11 h2's with honorifics spelled out, entry 12 matches nothing."""
    con = sqlite3.connect(directory.parent / "mini.db")
    text = dict(con.execute("SELECT id, nass FROM hadiths"))
    con.close()
    ara = [text[1], text[2].replace("قال", "رضي الله عنه قال"), "نص لا يوجد في المصدر اصلا"]
    grades = [[], [{"name": "Al-Albani", "grade": "Sahih"}], []]
    directory.mkdir(exist_ok=True)
    for lang, texts in [("ara", ara), ("eng", ["Narrated A", "Narrated B", "Other"])]:
        (directory / f"{lang}-mini.json").write_text(json.dumps({"hadiths": [
            {"hadithnumber": n, "arabicnumber": n, "text": t, "grades": g,
             "reference": {"book": 1, "hadith": n - 9}}
            for n, t, g in zip((10, 11, 12), texts, grades, strict=True)]}))
    return directory


@pytest.fixture(scope="session")
def mini_db(tmp_path_factory) -> Path:
    return make_db(tmp_path_factory.mktemp("src") / "mini.db")


@pytest.fixture(scope="session")
def mini_graph(mini_db):
    from isnad_graph.build import build
    from isnad_graph.corpus import Edition

    return build(mini_db, editions_dir=make_editions(mini_db.parent / "editions"),
                 editions={"mini": Edition(1)})
