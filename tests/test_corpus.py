import json
import sqlite3
from dataclasses import replace

import pandas as pd
import pytest

from isnad_graph.align import align
from isnad_graph.corpus import Edition, align_editions, export_corpus, grade_table

TEXT = "حدثنا مالك عن عائشة قالت كان رسول الله يقول الاعمال بالنيات"


def entries(tmp_path, cross=True):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE hadiths(id, nass, no_inbook, book_id)")
    con.executemany("INSERT INTO hadiths VALUES (?, ?, ?, ?)",
                    [(20, TEXT, 1, 17), (21, TEXT, 2, 17)])
    for lang in ("ara", "eng"):
        records = [{"hadithnumber": n, "arabicnumber": n,
                    "reference": {"book": 1, "hadith": n}, "text": t,
                    "grades": [{"name": "Original critic", "grade": "Original verdict"}]}
                   for n, t in enumerate([TEXT, TEXT, "نص منفصل بلا ارتباط بالمصدر ابدا"])]
        (tmp_path / f"{lang}-nasai.json").write_text(json.dumps({"hadiths": records}))
    return align_editions(con, tmp_path, {"nasai": Edition(17, cross)})


def test_cross_recension_many_to_one_and_unmatched_attributions(tmp_path):
    frame, stats = entries(tmp_path)
    grades = grade_table(frame)
    assert grades.hadith_id.tolist()[:2] == [20, 20]
    assert pd.isna(grades.hadith_id.iloc[2])
    assert grades.cross_recension.all()
    assert grades.alignment_status.tolist() == ["ambiguous", "ambiguous", "unmatched"]
    assert grades.source_entry_count.tolist()[:2] == [2, 2]
    assert grades.tied_candidates.tolist()[:2] == [2, 2]
    assert grades.grader.tolist() == ["Original critic"] * 3
    assert grades.grade.tolist() == ["Original verdict"] * 3
    assert grades.edition_id.str.contains("eng-nasai").all()
    assert grades.source_book_id.eq(17).all()
    assert stats["nasai"]["equal_successive_positions"] == 1
    assert stats["nasai"]["order_consistency"] == 1


def test_guarded_queries_and_legacy_bundle(tmp_path, mini_graph):
    frame, _ = entries(tmp_path)
    graph = replace(mini_graph, external_grades=grade_table(frame))
    assert graph.grades_of(20).empty
    assert graph.grades_of(20, include_cross_recension=True).empty
    included = graph.grades_of(20, include_cross_recension=True, include_ambiguous=True)
    assert included.entry.tolist() == [0, 1]  # no collapsing distinct edition entries
    assert graph.grades_of(20, include_cross_recension=True, include_ambiguous=True,
                           min_score_margin=0.01).empty
    legacy = replace(graph, external_grades=grade_table(frame)[
        ["hadith_id", "collection", "hadithnumber", "grader", "grade"]])
    with pytest.raises(ValueError, match="Legacy"):
        legacy.grades_of(20)
    with pytest.raises(ValueError, match="between"):
        graph.grades_of(20, min_score_margin=-1)


def test_exact_text_is_not_independent_verification():
    diagnostics = {}
    assert align({0: TEXT}, {20: TEXT, 21: TEXT}, diagnostics=diagnostics)[0].right == 20
    assert diagnostics[0]["text_relation"] == "normalized_exact"
    assert diagnostics[0]["tied_candidates"] == 2


def test_translation_export_carries_provenance(tmp_path, mini_db):
    from conftest import make_editions

    directory = make_editions(mini_db.parent / "editions")
    with sqlite3.connect(mini_db) as con:
        frame, _ = align_editions(con, directory, {"mini": Edition(1, True)})
        export_corpus(con, frame, tmp_path / "corpus")
    translations = pd.read_parquet(tmp_path / "corpus/translations.parquet")
    assert translations.cross_recension.all()
    assert translations.alignment_status.iloc[-1] == "unmatched"
    assert "edition_id" in translations


def test_no_matches_and_no_editions_preserve_schema(tmp_path, mini_db):
    from isnad_graph.build import build

    frame, _ = entries(tmp_path)
    empty = grade_table(frame.iloc[:0])
    assert "cross_recension" in empty
    graph = build(mini_db, editions_dir=None)
    assert graph.grades_of(1).empty
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE hadiths(id, nass, no_inbook, book_id)")
    unmatched, _ = align_editions(con, tmp_path, {"nasai": Edition(17, True)})
    assert grade_table(unmatched).alignment_status.eq("unmatched").all()


def test_ordinary_grade_survives_save_load_and_opt_in_preserves_rows(tmp_path, mini_graph):
    from isnad_graph.graph import IsnadGraph

    before = mini_graph.grades_of(2)
    assert before.grader.tolist() == ["Al-Albani"]
    assert before.cross_recension.eq(False).all()
    reloaded = IsnadGraph.load(mini_graph.save(tmp_path / "bundle"))
    pd.testing.assert_frame_equal(before, reloaded.grades_of(2))


def test_multiple_critics_retain_attribution_and_entry_identity(tmp_path):
    frame, _ = entries(tmp_path)
    frame.at[0, "grades"] = [{"name": "A", "grade": "One"},
                              {"name": "B", "grade": "Two"}]
    grades = grade_table(frame)
    assert grades[grades.entry.eq(0)][["grader", "grade"]].values.tolist() == [
        ["A", "One"], ["B", "Two"]]
    assert grades[grades.entry.eq(0)].cross_recension.all()
