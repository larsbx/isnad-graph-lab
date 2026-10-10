from isnad_graph.inference import TAHWIL, Mention, infer_source_chain

TEXT = "حَدَّثَنَا زيد عَنْ عمرو عَنْ بكر قَالَ : المتن هنا"
M = [Mention(1, 11, 14), Mention(2, 19, 23), Mention(3, 28, 31)]
MATN = TEXT.index("المتن")
KNOWN = {1, 2, 3}


def test_reads_mentions_in_text_order():
    assert infer_source_chain(list(reversed(M)), MATN, TEXT, KNOWN) == (1, 2, 3)


def test_ignores_mentions_inside_the_matn():
    assert infer_source_chain([*M, Mention(2, MATN + 2, MATN + 5)], MATN, TEXT, KNOWN) == (1, 2, 3)


def test_abstains_without_matn_boundary_or_resolution():
    assert infer_source_chain(M, None, TEXT, KNOWN) is None
    assert infer_source_chain([*M[:2], Mention(None, 28, 31)], MATN, TEXT, KNOWN) is None
    assert infer_source_chain(M, MATN, TEXT, {1, 2}) is None
    assert infer_source_chain([], MATN, TEXT, KNOWN) is None


def test_tahwil_detection_is_word_bounded():
    assert TAHWIL.search("حَدَّثَنَا شُعْبَةُ . ح قَالَ")
    assert TAHWIL.search("عن زيد ح وحدثنا")
    assert not TAHWIL.search("حَدَّثَنَا مُحَمَّدُ بْنُ حَرْبٍ")
    assert not TAHWIL.search("حدثنا صالح")


def test_abstains_on_tahwil():
    text = "حدثنا زيد ح وحدثنا عمرو عن بكر قال المتن"
    assert infer_source_chain(M, text.index("المتن"), text, KNOWN) is None
