from __future__ import annotations

import pandas as pd
import pytest

from isnad_graph.assess import Defect, Verdict, report_assessment
from isnad_graph.chronology_audit import (
    Cause,
    TextEvidence,
    adjacent_evidence,
    alias_index,
    alternate_names,
    classify,
    compiler_matches,
    replay_assessment,
    report_exposure,
    source_prefix,
    usable_prefix,
)
from isnad_graph.inference import Mention
from isnad_graph.schema import LinkFlag


def spans(text, names):
    """Names are supplied in text order, including unlinked slots."""
    at = 0
    mentions = []
    for rid, name in names:
        start = text.index(name, at)
        at = start + len(name)
        mentions.append(Mention(rid, start, at))
    return mentions


def test_same_endpoints_may_have_a_gap_or_an_unresolved_inference():
    assert classify(LinkFlag.TALIQ | LinkFlag.MUBHAM, False, True, TextEvidence(), False) == (
        Cause.MARKED_SUSPENSION
    )
    assert classify(LinkFlag.IRSAL, False, False, TextEvidence(explicit_pair=True), False) == (
        Cause.MARKED_GAP
    )
    assert classify(0, True, False, TextEvidence(), False) == Cause.INFERRED_UNRESOLVED
    assert classify(0, False, True, TextEvidence(), False) == Cause.COMPILER_CANDIDATE
    assert (
        classify(0, False, False, TextEvidence(explicit_pair=True), False)
        == Cause.DIRECT_DATE_CANDIDATE
    )


@pytest.mark.parametrize(
    ("text", "is_parallel"),
    [
        ("حدثنا خالد وزيد قالا: أخبرنا عمرو", True),
        ("حدثنا خالد وزيد قال: أخبرنا عمرو", False),
        ("قال خالد وزيد قالا: أخبرنا عمرو", False),
        ("حدثنا خالد عن زيد قالا: أخبرنا عمرو", False),
        ("حدثنا خالد وزيد قالا: لم يحدثنا عمرو", False),
    ],
)
def test_co_narrators_require_a_receiving_verb_and_dual_continuation(text, is_parallel):
    mentions = spans(text, [(15, "خالد"), (16, "زيد"), (17, "عمرو")])
    evidence = adjacent_evidence(text, mentions, 15, 16)
    assert evidence.co_narrators is is_parallel
    assert bool(evidence.co_narrator_witness) is is_parallel
    assert classify(0, True, False, evidence, False) == (
        Cause.CO_NARRATORS if is_parallel else Cause.INFERRED_UNRESOLVED
    )
    # The rule stays scoped to inferred sequences. Recorded routes may
    # correspond to a parallel reading that cannot be aligned locally.
    assert classify(0, False, False, evidence, False) == Cause.UNRESOLVED


@pytest.mark.parametrize(
    ("formula", "is_indirect"),
    [
        ("قال: بلغني أن", True),
        ("قَالَ : حُدِّثْتُ ، أَنَّ", True),
        ("قال حدثت أن", False),  # unvocalized ambiguity
        ("قَالَ حَدَّثْتُ أَنَّ", False),  # active voice
        ("قال ألم يبلغني أن", False),
        ("أنه قال", False),
        ("عن أبيه عن", False),
    ],
)
def test_indirect_formula_requires_positive_textual_evidence(formula, is_indirect):
    text = f"عن خالد {formula} زيد"
    mentions = spans(text, [(15, "خالد"), (16, "زيد")])
    evidence = adjacent_evidence(text, mentions, 15, 16)
    assert evidence.indirect_formula is is_indirect
    assert classify(0, True, False, evidence, False) == (
        Cause.INDIRECT_FORMULA if is_indirect else Cause.INFERRED_UNRESOLVED
    )


def test_routes_and_unlinked_intermediaries_prevent_local_claims():
    text = "حدثنا خالد حوحدثنا زيد عن بكر"
    mentions = spans(text, [(15, "خالد"), (16, "زيد"), (17, "بكر")])
    assert usable_prefix(text, len(text), mentions) == ()
    assert source_prefix(text, mentions[1].start + 1, mentions) is None
    assert source_prefix(text, len(text), [Mention(16, 0, 4), Mention(17, 3, 6)]) is None
    nested = "خالد أخبرني رجل عن زيد"
    ms = spans(nested, [(15, "خالد"), (None, "رجل"), (16, "زيد")])
    assert adjacent_evidence(nested, source_prefix(nested, len(nested), ms), 15, 16) == (
        TextEvidence()
    )


@pytest.mark.parametrize("merged_name", ["خالد أخبرنا بكر", "زيد أخبرنا بكر"])
def test_offsets_that_swallow_a_receiving_clause_cannot_support_the_syntax(merged_name):
    first = merged_name if merged_name.startswith("خالد") else "خالد"
    second = merged_name if merged_name.startswith("زيد") else "زيد"
    text = f"حدثنا {first} و {second} قالا حدثنا عمرو"
    ms = spans(text, [(15, first), (16, second), (17, "عمرو")])
    assert adjacent_evidence(text, usable_prefix(text, len(text), ms), 15, 16) == TextEvidence()


def test_repeated_endpoints_abstain_even_where_one_pair_looks_direct():
    text = "خالد حدثنا زيد وقال خالد بلغني أن زيد"
    mentions = spans(text, [(15, "خالد"), (16, "زيد"), (15, "خالد"), (16, "زيد")])
    assert adjacent_evidence(text, mentions, 15, 16) == TextEvidence()


def test_compiler_ids_are_joined_by_metadata_and_keep_ambiguity():
    narrators = pd.DataFrame(
        [
            (5, "خالد بن زيد المكي", "", 61),
            (6, "خالد بن زيد المكي", "", 67),
            (7, "خالد بن زيد المكي", "", 67),
        ],
        columns=["id", "name", "nickname", "death_year"],
    )
    books = pd.DataFrame(
        [
            (9, "خالد بن زيد المكي", 6, 61),  # author_no points to the wrong rawi namespace
            (10, "خالد بن زيد المكي", 5, 67),  # two distinct matches
            (11, "خالد", 5, 61),  # abbreviated author name
        ],
        columns=["id", "author_name", "author_no", "author_death_year"],
    )
    assert compiler_matches(books, narrators, alias_index(narrators)) == {9: 5}
    text = "عن خالد بن زيد المكي"
    aliases = alias_index(narrators)
    assert alternate_names(text, spans(text, [(5, "خالد بن زيد المكي")]), aliases) == {}
    assert alternate_names(text, spans(text, [(8, "خالد بن زيد المكي")]), aliases) == {
        8: {5, 6, 7},
    }
    assert classify(0, True, True, TextEvidence(), True) == Cause.IDENTITY_CANDIDATE


def test_replay_preserves_unresolved_occurrences_and_unrelated_verdicts():
    # Chains 1 and 2 may share the exact pair, with different evidence below.
    chron, gap, tadlis = int(Defect.CHRONOLOGY), int(Defect.GAP), int(Defect.TADLIS)
    chains = pd.DataFrame(
        [
            (1, 30, Verdict.DAIF, chron | gap, 4),
            (2, 30, Verdict.HASAN, chron | tadlis, 4),
            (3, 31, Verdict.SAHIH, chron, 3),
            (4, 32, Verdict.HASAN, chron, 6),
            (5, 33, Verdict.SAHIH, chron, 3),
            (6, 34, Verdict.HASAN, 0, 9),  # unrelated committed rank/verdict discrepancy
            (7, 35, Verdict.VERY_DAIF, chron, 11),  # adding a gap cannot improve severity
            (8, 36, Verdict.HASAN, chron, 4),
        ],
        columns=["chain_id", "hadith_id", "verdict", "defects", "worst_rank"],
    )
    hits = pd.DataFrame(
        [
            (1, Cause.MARKED_SUSPENSION),
            (2, Cause.INFERRED_UNRESOLVED),
            (3, Cause.COMPILER_SUSPENSION),
            (3, Cause.DOCUMENTED_CONFLICT),
            (4, Cause.INFERRED_SPLICE),
            (5, Cause.DOCUMENTED_CONFLICT),
            (7, Cause.INDIRECT_FORMULA),
            (8, Cause.COMPILER_WRITTEN_CITATION),
        ],
        columns=["chain_id", "cause"],
    )
    replay, excluded, retained, added = replay_assessment(chains, hits)
    assert replay.chain_id.tolist() == [1, 2, 3, 5, 6, 7, 8]
    assert replay.defects.tolist() == [gap, chron | tadlis, chron | gap, chron, 0, gap, 0]
    assert replay.verdict.tolist() == [
        Verdict.DAIF,
        Verdict.HASAN,
        Verdict.DAIF,
        Verdict.SAHIH,
        Verdict.HASAN,
        Verdict.VERY_DAIF,
        Verdict.HASAN,
    ]
    assert excluded.tolist() == [False, False, False, False, True, False, False, False]
    assert retained.tolist() == [False, True, False, True, False, True, False, False]
    assert added.tolist() == [0, 0, LinkFlag.TALIQ, 0, 0, 0, LinkFlag.INQITA, 0]
    assert report_assessment(replay).loc[30, "shared_defects"] == chron | tadlis
    assert report_exposure(replay, {3, 5}).to_dict() == {
        30: "unresolved",
        33: "documented_conflict",
        34: "unflagged_by_screen",
        36: "unflagged_by_screen",
    }
    assert chains.verdict[2] == Verdict.SAHIH and chains.defects[0] == chron | gap


def test_report_tri_state_uses_only_acceptable_routes():
    c = pd.DataFrame(
        [
            (1, 0, 10, 8),  # documented chronology on this route
            (2, 1, 10, 0),  # acceptable route with no flag
            (3, 0, 11, 8),
            (4, 2, 11, 0),  # weak alternative ignored
            (5, 1, 12, 8),
            (6, 0, 12, 8),  # both acceptable, but only one confirmed
        ],
        columns=["chain_id", "verdict", "hadith_id", "defects"],
    )
    assert report_exposure(c, {1, 3, 5}).to_dict() == {
        10: "unflagged_by_screen",
        11: "documented_conflict",
        12: "unresolved",
    }
    with pytest.raises(ValueError, match="present in the replay"):
        report_exposure(c, {2})
