from hypothesis import given
from hypothesis import strategies as st

from isnad_graph.align import Match, align, order_consistency, shingles

A = ("حَدَّثَنَا الْحُمَيْدِيُّ قَالَ حَدَّثَنَا سُفْيَانُ قَالَ إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ"
     " وَإِنَّمَا لِكُلِّ امْرِئٍ مَا نَوَى")
B = ("حدثنا عبد الله بن يوسف قال أخبرنا مالك عن هشام عن أبيه عن عائشة أن الحارث سأل"
     " رسول الله كيف يأتيك الوحي")
C = ("حدثنا يحيى بن بكير قال حدثنا الليث عن عقيل عن ابن شهاب عن عروة عن عائشة أول ما بدئ"
     " به رسول الله الرؤيا")


def test_shingles_ignore_diacritics_punctuation_and_honorifics():
    assert shingles("حَدَّثَنَا ، سُفْيَانُ : قَالَ") == shingles("حدثنا سفيان قال")
    assert shingles("قال رسول الله ﷺ إنما الأعمال") == shingles(
        "قال رسول الله صلى الله عليه وسلم إنما الأعمال")
    assert shingles("عن عائشة رضي الله عنها قالت كان") == shingles("عن عائشة قالت كان")


def test_aligns_by_text_despite_different_numbering():
    left = {1: A, 2: B, 3: C}
    right = {101: C + " .", 205: "حَدَّثَنَا " + B, 300: A}
    assert align(left, right) == [Match(1, 300, 1.0), Match(2, 205, 1.0), Match(3, 101, 1.0)]


def test_dissimilar_texts_are_left_out():
    assert align({1: A, 2: "نص آخر لا علاقة له بشيء مما سبق ابدا"}, {9: A}) == [Match(1, 9, 1.0)]


def test_parallel_routes_map_to_one_merged_report():
    merged = A + " ح وحدثنا " + B
    assert [(m.left, m.right) for m in align({1: A, 2: B}, {50: merged, 60: C})] == [
        (1, 50), (2, 50)]


words = st.sampled_from(
    ["حدثنا", "عن", "قال", "سفيان", "مالك", "عائشة", "رسول", "الله", "النبي", "الوحي"])
texts = st.lists(words, min_size=4, max_size=12).map(" ".join)


@given(st.dictionaries(st.integers(0, 50), texts, max_size=8),
       st.dictionaries(st.integers(0, 50), texts, max_size=8))
def test_alignment_is_a_partial_function_above_threshold(left, right):
    m = align(left, right)
    assert len({x.left for x in m}) == len(m)
    assert all(0.5 <= x.score <= 1 and x.left in left and x.right in right for x in m)


def test_order_consistency():
    m = [Match(1, 10, 1), Match(2, 20, 1), Match(3, 15, 1)]
    assert order_consistency(m, {1: 1, 2: 2, 3: 3}, {10: 10, 15: 15, 20: 20}) == 0.5
