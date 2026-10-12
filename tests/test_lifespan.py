import pandas as pd
import pytest

from isnad_graph.lifespan import L_MAX, MIN_TABAQA_N, feasibility, lifespans, parse_years


@pytest.mark.parametrize("raw, expected", [
    ("250", (250, 250)), ("130 - 121", (121, 130)), ("290 : 281", (281, 290)),
    ("530 - 540", (530, 540)), ("", None), (None, None), ("نحو", None),
])
def test_parse_years(raw, expected):
    assert parse_years(raw) == expected


def bio(**rows):
    cols = ["birth_year", "birth_year_raw", "death_year", "death_year_raw", "age_raw", "tabaka"]
    return pd.DataFrame([{"id": i, **dict(zip(cols, (*r, None)[:6], strict=True))}
                         for i, r in rows.items()]).astype({"id": "int64"})


def test_birth_basis_and_intervals():
    n = bio(**{"1": (60, "60", 150, "150", None),      # recorded birth
               "2": (None, None, 100, "110 - 101", 80),  # age against a death range
               "3": (None, None, 200, "200", None),      # prior only
               "4": (None, None, None, None, None)})     # nothing
    s = lifespans(n).set_index("id")
    assert s.loc[1, ["birth_lo", "birth_hi", "birth_basis"]].tolist() == [60, 60, "recorded"]
    assert s.loc[2, ["death_lo", "death_hi"]].tolist() == [101, 110]
    assert s.loc[2, ["birth_lo", "birth_hi", "birth_basis"]].tolist() == [21, 30, "age"]
    assert s.loc[3, ["birth_lo", "birth_hi", "birth_basis"]].tolist() == [200 - L_MAX, 200,
                                                                          "prior"]
    assert s.loc[4, "birth_basis"] == "none" and pd.isna(s.loc[4, "death_lo"])
    assert not s.bio_conflict.any()


def test_conflicting_biography_is_flagged():
    n = bio(**{"1": (300, "300", 100, "100", None),      # born after death
               "2": (20, "20", 100, "100", 50)})         # life 80, age 50
    assert lifespans(n).bio_conflict.all()


def test_a_recorded_age_beyond_the_cap_is_taken_at_its_word():
    n = bio(**{"1": (None, None, 300, "300", L_MAX + 30)})
    assert lifespans(n).birth_lo.item() == 300 - L_MAX - 30


def edges(*pairs):
    return pd.DataFrame(pairs, columns=["src", "dst"])


def test_feasibility_verdicts():
    n = bio(**{"1": (20, "20", 100, "100", None),      # teacher
               "2": (110, "110", 180, "180", None),    # born after 1 died
               "3": (None, None, 100 + L_MAX + 5, None, None),  # needs a life > L_MAX
               "4": (60, "60", 150, "150", None),      # overlaps
               "5": (None, None, None, None, None),    # unknown
               "6": (300, "300", 100, "100", None)})   # conflict
    f = feasibility(edges((1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (4, 1)), lifespans(n))
    assert f.chronology.tolist() == ["impossible", "implausible", "consistent", "unknown",
                                     "conflict", "consistent"]
    # overlap of documented lifespans, and the student's age when the teacher died
    assert f.overlap.tolist()[2] == 40 and f.student_age_at_teacher_death.tolist()[2] == 40
    assert pd.isna(f.overlap.tolist()[1])  # prior births give no documented overlap
    assert f.ante_quem.tolist()[2] == 100 and pd.isna(f.ante_quem.tolist()[3])


def test_a_student_dead_before_the_teacher_was_born_is_impossible():
    n = bio(**{"1": (200, "200", 280, "280", None), "2": (100, "100", 150, "150", None)})
    assert feasibility(edges((1, 2)), lifespans(n)).chronology.item() == "impossible"


def test_a_missing_death_is_imputed_from_the_tabaqa_and_can_only_be_implausible():
    layer = {str(100 + k): (None, None, 150 + k % 40, None, None, 7) for k in range(MIN_TABAQA_N)}
    n = bio(**layer, **{"1": (0, "0", 20, "20", None),        # teacher, died 20
                        "2": (None, None, None, None, None, 7),  # tabaqa 7, no dates
                        "3": (None, None, None, None, None, 9)})  # too few peers in 9
    s = lifespans(n).set_index("id")
    assert s.loc[2, "death_basis"] == "tabaqa" and 150 <= s.loc[2, "death_lo"] < 160
    assert s.loc[3, "death_basis"] == "none"
    f = feasibility(edges((1, 2), (1, 3)), lifespans(n))
    assert f.chronology.tolist() == ["implausible", "unknown"]
