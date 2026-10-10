import pytest

from isnad_graph.schema import PROPHET_ID
from isnad_graph.sigha import (
    COMPILER,
    Mention,
    Mode,
    apex_mode,
    borrowed_modes,
    link_modes,
    mode_class,
    read_gap,
    transmission_modes,
)


@pytest.mark.parametrize("gap, mode", [
    (" ، عَنْ ", Mode.AN),
    (" ، قَالَ : حَدَّثَنَا ", Mode.TAHDITH),
    (" ، قال : ثنا ", Mode.TAHDITH),
    (" ، أَنَّهُ سَمِعَ ", Mode.SAMA),
    (" يُحَدِّثُ عَنْ ", Mode.AN),  # rule 1: last formula governs
    (" ، يَقُولُ : سَمِعْتُ ", Mode.SAMA),
    (" ، قَالَ : أَخْبَرَنِي ", Mode.IKHBAR),
    (" ، أنا ", Mode.IKHBAR),
    (" ببغداد انبا ", Mode.IKHBAR),
    (" ، قَالَ : قَرَأْتُ عَلَى ", Mode.QIRAA),
    (" ، قَالَ : كَتَبَ إِلَيَّ ", Mode.KITABA),
    (" ، أَنَّ ", Mode.ANNA),
    (" ، قَالَ : قَالَ ", Mode.QALA),
    (" ، قَالَ : سَأَلْتُ ", Mode.LIQA),
    (" ، وَحَدَّثَنِي ", Mode.TAHDITH),
    (" ، ", Mode.UNREAD),
])
def test_read_gap(gap, mode):
    assert read_gap(gap).mode == mode


def test_gap_structure():
    assert read_gap(" . ح وحَدَّثَنَا ").tahwil and read_gap(" حوحدثنا ").tahwil
    assert read_gap(" وَ ").conjunction and read_gap(" ").conjunction
    assert read_gap(" حَدَّثَهُ أَنَّ ").post == Mode.TAHDITH
    assert not read_gap(" حَدَّثَنَا ").tahwil  # ح inside a word is not taḥwīl


def isnad(*parts):
    """Build text + mentions from alternating gap strings and (id, name) pairs."""
    text, mentions = "", []
    for p in parts:
        if isinstance(p, tuple):
            mentions.append(Mention(p[0], len(text), len(text) + len(p[1])))
            text += p[1]
        else:
            text += p
    return text, mentions


BUKHARI_1 = isnad(  # Ṣaḥīḥ al-Bukhārī 1, verbatim isnad
    "حَدَّثَنَا ", (1, "الْحُمَيْدِيُّ عَبْدُ اللَّهِ بْنُ الزُّبَيْرِ"),
    " ، قَالَ : حَدَّثَنَا ", (2, "سُفْيَانُ"), " ، قَالَ : حَدَّثَنَا ", (3, "يَحْيَى بْنُ سَعِيدٍ"),
    " ، قَالَ : أَخْبَرَنِي ", (4, "مُحَمَّدُ بْنُ إِبْرَاهِيمَ"), " ، أَنَّهُ سَمِعَ ",
    (5, "عَلْقَمَةَ بْنَ وَقَّاصٍ"), " ، يَقُولُ : سَمِعْتُ ", (6, "عُمَرَ بْنَ الْخَطَّابِ"),
    " رَضِيَ اللَّهُ عَنْهُ عَلَى الْمِنْبَرِ، قَالَ : سَمِعْتُ رَسُولَ اللَّهِ ﷺ، يَقُولُ : ")


def test_bukhari_1():
    text, ms = BUKHARI_1
    readings = transmission_modes(text, ms, len(text))
    pairs = readings.pairs
    assert pairs == {(COMPILER, 1): Mode.TAHDITH, (1, 2): Mode.TAHDITH, (2, 3): Mode.TAHDITH,
                     (3, 4): Mode.IKHBAR, (4, 5): Mode.SAMA, (5, 6): Mode.SAMA,
                     (6, PROPHET_ID): Mode.SAMA}
    bukhari = 99
    assert link_modes((PROPHET_ID, 6, 5, 4, 3, 2, 1, bukhari), readings) == (
        Mode.SAMA, Mode.SAMA, Mode.SAMA, Mode.IKHBAR, Mode.TAHDITH, Mode.TAHDITH, Mode.TAHDITH)


@pytest.mark.parametrize("tail, mode", [
    (" ، قَالَ : سَمِعْتُ رَسُولَ اللَّهِ ﷺ يَقُولُ", Mode.SAMA),
    (" ، عَنِ النَّبِيِّ ﷺ ، قَالَ", Mode.AN),
    (" ، أَنَّ رَسُولَ اللَّهِ ﷺ قَالَ", Mode.ANNA),
    (" ، قَالَ : قَالَ رَسُولُ اللَّهِ ﷺ", Mode.QALA),
    (" ، قَالَ : كُنَّا جُلُوسًا", None),
])
def test_apex_mode(tail, mode):
    assert apex_mode(tail) == mode


def test_post_posed_verb_upgrades_anna():
    text, ms = isnad("حدثنا ", (1, "مالك"), " عن ", (2, "ابن شهاب"), " أن ", (3, "عروة"),
                     " حدثه أن ", (4, "عائشة"), " قالت")
    pairs = transmission_modes(text, ms, len(text)).pairs
    assert pairs[(2, 3)] == Mode.TAHDITH and pairs[(3, 4)] == Mode.ANNA


def test_co_narrators_share_the_formula():
    text, ms = isnad("حدثنا ", (1, "أبو بكر"), " و ", (2, "عثمان"), " قالا حدثنا ", (3, "جرير"),
                     " عن ", (4, "منصور"))
    pairs = transmission_modes(text, ms, len(text)).pairs
    assert pairs[(1, 3)] == pairs[(2, 3)] == Mode.TAHDITH
    assert pairs[(COMPILER, 2)] == Mode.TAHDITH and pairs[(3, 4)] == Mode.AN


def test_tahwil_restarts_at_the_compiler():
    text, ms = isnad("حدثنا ", (1, "أبو الوليد"), " حدثنا ", (2, "شعبة"), " ح وحدثني ",
                     (3, "بشر"), " حدثنا ", (4, "محمد"), " عن ", (2, "شعبة"))
    pairs = transmission_modes(text, ms, len(text)).pairs
    assert pairs[(COMPILER, 3)] == Mode.TAHDITH and (2, 3) not in pairs
    assert pairs[(4, 2)] == Mode.AN and pairs[(1, 2)] == Mode.TAHDITH


def test_conflicting_readings_are_unread():
    text, ms = isnad("حدثنا ", (1, "أ"), " عن ", (2, "ب"), " ح وحدثنا ", (1, "أ"), " حدثنا ",
                     (2, "ب"))
    assert transmission_modes(text, ms, len(text)).pairs[(1, 2)] == Mode.UNREAD


def test_mentions_past_the_isnad_are_ignored():
    text, ms = isnad("حدثنا ", (1, "أ"), " عن ", (2, "ب"), " قال: رأيت ", (3, "ج"))
    assert (2, 3) not in transmission_modes(text, ms, ms[2].start - 1).pairs


def test_classes_partition_the_modes():
    assert {mode_class(m) for m in Mode} == {"explicit", "written", "ambiguous", "unread"}
    assert mode_class(Mode.AN) == "ambiguous" and mode_class(Mode.SAMA) == "explicit"


def test_tahwil_may_restart_at_the_first_narrator():
    text, ms = isnad("وبالإسناد إلى ", (1, "الطبراني"), " قال نا ", (2, "أحمد"), " . ح قال ونا ",
                     (3, "ابن يزداد"))
    pairs = transmission_modes(text, ms, len(text)).pairs
    assert pairs[(1, 3)] == pairs[(COMPILER, 3)] == Mode.TAHDITH


def test_gap_marker_is_bridged_with_the_students_formula():
    mubham = 1131
    text, ms = isnad("حدثني ", (1, "عبد الملك"), " عن ", (2, "نصر"), " ، حدثني ", (mubham, "شيخ"),
                     " من بني سليم عن ", (3, "عتبة"))
    readings = transmission_modes(text, ms, len(text), markers={mubham})
    assert readings.pairs[(2, 3)] == Mode.TAHDITH
    assert link_modes((3, 2, 1), readings) == (Mode.TAHDITH, Mode.AN)


def test_unnamed_kin_splits_the_gap_over_two_hops():
    text, ms = isnad("حدثنا ", (1, "يحيى"), " عن ", (2, "هشام بن عروة"), " قال أخبرني أبيه عن ",
                     (3, "عائشة"))
    readings = transmission_modes(text, ms, len(text))
    urwa = 7
    assert link_modes((3, urwa, 2, 1), readings) == (Mode.AN, Mode.IKHBAR, Mode.AN)
    assert link_modes((3, 2, 1), readings) == (Mode.AN, Mode.AN)  # no hidden hop in this chain


def test_links_missing_from_a_text_are_borrowed_from_preceding_reports():
    prev_text, prev = isnad("حدثنا ", (1, "علي بن حجر"), " حدثنا ", (2, "علي بن مسهر"))
    text, ms = isnad("وحدثنا ", (3, "ابن نمير"), " عن ", (2, "علي بن مسهر"))
    own = transmission_modes(text, ms, len(text))
    nbr = transmission_modes(prev_text, prev, len(prev_text))
    muslim = 9
    assert borrowed_modes((2, 1, muslim), own, [nbr]) == ((Mode.TAHDITH, Mode.TAHDITH), 2)
    assert borrowed_modes((2, 3, muslim), own, [nbr]) == ((Mode.AN, Mode.TAHDITH), 0)
