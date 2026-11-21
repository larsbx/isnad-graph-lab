from __future__ import annotations

import pandas as pd
import pytest

from isnad_graph.biography_audit import (
    PROVISIONAL,
    city_sets,
    distinctive_key,
    exact_hijri_year,
    make_linkage,
    name_key,
    recorded_point,
    relation_evidence,
    sample_matches,
    score_review,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("53 BH/570 CE (Makkah)", -53),
        ("135 AH (Basra)[ Natural ]", 135),
        ("135 AH / 752 CE (Basra)", 135),
        ("0 AH", None),
        ("NA", None),
        ("~135 AH/752 CE", None),
        ("133–163 AH", None),
        ("133 or 163 AH", None),
        ("133 AH [or 163 AH]", None),
        ("133 AH (approx)", None),
        ("752 CE", None),
    ],
)
def test_hijri_points_preserve_era_and_abstain_on_uncertainty(raw, expected):
    assert exact_hijri_year(raw) == expected


def test_reported_death_and_city_comparisons_keep_missingness():
    assert recorded_point("recorded", 133, 163) is None
    assert recorded_point("tabaqa", 133, 133) is None
    assert recorded_point("recorded", 133, pd.NA) is None
    assert recorded_point("recorded", 133, 133) == 133
    assert city_sets("الحجاز، الكوفة", external=False) == {"الكوفة"}
    assert city_sets("Hijaz, Kufa, Medinah", external=True) == {"الكوفة", "المدينة"}
    assert city_sets("Syria, Hijaz, Egypt", external=True) == set()


def test_keys_handle_presentation_forms_but_do_not_count_tokens_as_lineage():
    assert name_key("Hussain ( حسين بن علي بن أﺑﻲ طالب ( رضي الله عنه") == name_key(
        "حسين ابن علي ابن أبي طالب"
    )
    assert not distinctive_key("عبد الرحمن بن جبير")
    assert distinctive_key("عبد الرحمن بن جبير الحمصي")
    assert distinctive_key("عبد الرحمن بن جبير بن نفير")


def test_reciprocal_names_abstain_on_alias_collisions_and_weak_matches():
    graph = pd.DataFrame(
        [
            (0, "محمد بن عبد الله النجاري", None, "marker", 123),
            (1, "أحمد بن موسى بن عيسى", "خالد بن سعيد الدمشقي", "narrator", 100),
            (2, "عبد الرحمن بن جبير", None, "narrator", 110),
            (3, "حسين بن صالح بن زيد", "خالد بن سعيد الدمشقي", "narrator", 101),
            (4, "محمد بن عبد الله النجاري", None, "narrator", 123),
            (5, "نافع بن زيد البصري", None, "narrator", 111),
        ],
        columns=["id", "name", "nickname", "kind", "death_year"],
    )
    ext = pd.DataFrame(
        [
            (10, "خالد بن سعيد الدمشقي", 100),
            (11, "عبد الرحمن بن جبير", 110),
            (12, "محمد بن عبد الله النجاري", 400),
            (13, "نافع بن زيد البصري", 90),
            (14, "نافع بن زيد البصري", 111),
            (15, "حسين بن صالح بن زيد", 101),
        ],
        columns=["scholar_indx", "name", "death_year"],
    )
    aligned = make_linkage(graph, ext).set_index("rawi_id")
    assert aligned.loc[1, "status"] == "ambiguous_exact_candidates"
    assert aligned.loc[3, "candidate_ids"] == "10,15"
    assert aligned.loc[2, "status"] == "underspecified_exact_candidate"
    assert aligned.loc[4, "status"] == PROVISIONAL
    assert aligned.loc[4, "scholar_indx"] == 12  # dates deliberately disagree
    assert aligned.loc[5, "status"] == "ambiguous_exact_candidates"
    assert pd.isna(aligned.loc[5, "scholar_indx"])  # close dates cannot pick a homonym
    assert 0 not in aligned.index


def test_relation_evidence_requires_a_provable_recorded_direct_occurrence():
    edges = pd.DataFrame(
        [(1, 2, 4, 4), (1, 3, 4, 3), (2, 3, 5, 0), (3, 1, 2, 0)],
        columns=["src", "dst", "n_direct", "n_inferred"],
    )
    matches = pd.DataFrame({"rawi_id": [1, 2, 3], "scholar_indx": [11, 22, 33]})
    external = pd.DataFrame(
        [(11, "NA", "22, 33"), (22, "11", "33"), (33, "11, 22", "NA")],
        columns=["scholar_indx", "teachers_inds", "students_inds"],
    )
    assert relation_evidence(edges, matches, external) == {1: 1, 2: 1, 3: 2}


def test_review_sample_ignores_dates_and_id_order_and_requires_pin_and_witness():
    matches = pd.DataFrame({"rawi_id": range(250), "scholar_indx": range(300, 550)})
    for field in ("kg_name", "kg_nickname", "kg_nisba", "ms_name", "shared_keys"):
        matches[field] = field
    matches["death_abs_difference"] = range(250)
    sample = sample_matches(matches)
    unrelated = matches.iloc[::-1].assign(death_abs_difference=10_000)
    pd.testing.assert_frame_equal(sample, sample_matches(unrelated))
    partial = sample.head(1).assign(decision="same", source_locator="Primary source, p. 20")
    score = score_review(sample, partial)
    assert score["observed_precision"] is None
    assert score["sample_precision_bounds"] == [0.005, 1.0]
    complete = sample.assign(decision="same", source_locator="Per-row locator")
    complete.loc[complete.index[0], "decision"] = "different"
    assert score_review(sample, complete)["observed_precision"] == 199 / 200
    with pytest.raises(ValueError, match="out-of-sample"):
        score_review(sample, partial.assign(rawi_id=-5))
    with pytest.raises(ValueError, match="evidence locator"):
        score_review(sample, partial.assign(source_locator=pd.NA))
    with pytest.raises(ValueError, match="duplicate"):
        score_review(sample, pd.concat([partial, partial]))
