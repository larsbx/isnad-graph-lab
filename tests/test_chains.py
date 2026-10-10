from hypothesis import assume, given
from hypothesis import strategies as st

from isnad_graph.chains import normalize
from isnad_graph.schema import PROPHET_ID, LinkFlag

IRSAL, INQITA, TALIQ, MUBHAM = 9001, 9002, 9003, 9004
MARKERS = {IRSAL: LinkFlag.IRSAL, INQITA: LinkFlag.INQITA, TALIQ: LinkFlag.TALIQ,
           MUBHAM: LinkFlag.MUBHAM}

narrator = st.integers(1, 40)
token = st.one_of(narrator, st.sampled_from(sorted(MARKERS)))
source_chain = st.lists(token, max_size=12)


def test_plain_chain_is_reversed_into_transmission_order():
    c = normalize([10, 20, 30], MARKERS, prophetic=False)
    assert c.path == (30, 20, 10)
    assert c.links == (LinkFlag.DIRECT,) * 2
    assert c.edges() == ((30, 20, 0), (20, 10, 0))


def test_prophetic_chain_gets_prophet_apex():
    assert normalize([10, 20], MARKERS, prophetic=True).path == (PROPHET_ID, 20, 10)


def test_top_irsal_becomes_flagged_link_to_prophet():
    c = normalize([10, 20, IRSAL], MARKERS, prophetic=True)
    assert c.path == (PROPHET_ID, 20, 10)
    assert c.links == (LinkFlag.IRSAL, LinkFlag.DIRECT)
    assert c.head_gap == c.tail_gap == LinkFlag.DIRECT


def test_top_marker_without_prophet_is_a_head_gap():
    c = normalize([10, 20, MUBHAM], MARKERS, prophetic=False)
    assert c.path == (20, 10) and c.head_gap == LinkFlag.MUBHAM


def test_taliq_at_compiler_end_is_a_tail_gap():
    c = normalize([TALIQ, 20, 30], MARKERS, prophetic=False)
    assert c.path == (30, 20) and c.tail_gap == LinkFlag.TALIQ


def test_consecutive_inner_markers_combine():
    c = normalize([10, INQITA, MUBHAM, 20], MARKERS, prophetic=False)
    assert c.links == (LinkFlag.INQITA | LinkFlag.MUBHAM,)


def test_adjacent_duplicates_collapse_but_gapped_ones_do_not():
    assert normalize([10, 10, 20], MARKERS, False).path == (20, 10)
    assert normalize([10, 10, 20], MARKERS, False).repeats == 1
    c = normalize([10, MUBHAM, 10], MARKERS, False)
    assert c.path == (10, 10) and c.links == (LinkFlag.MUBHAM,)


@given(source_chain, st.booleans())
def test_no_marker_survives_on_a_path(raw, prophetic):
    assert not set(normalize(raw, MARKERS, prophetic).path) & set(MARKERS)


@given(source_chain, st.booleans())
def test_narrators_are_conserved(raw, prophetic):
    c = normalize(raw, MARKERS, prophetic)
    real = [r for r in raw if r not in MARKERS]
    assert set(c.path) - {PROPHET_ID} == set(real)
    assert len(c.path) + c.repeats == len(real) + prophetic


@given(source_chain, st.booleans())
def test_every_marker_is_accounted_for_exactly_once(raw, prophetic):
    c = normalize(raw, MARKERS, prophetic)
    seen = LinkFlag.DIRECT
    for f in (c.head_gap, *c.links, c.tail_gap):
        seen |= f
    assert seen == LinkFlag(sum({MARKERS[r] for r in raw if r in MARKERS}))


@given(source_chain, st.booleans())
def test_normalization_is_idempotent_on_clean_paths(raw, prophetic):
    c = normalize(raw, MARKERS, prophetic)
    # a gapped self-link (X ⇢ X) would re-collapse, so exclude it
    assume(all(a != b for a, b in zip(c.path, c.path[1:], strict=False)))
    body = [r for r in c.path if r != PROPHET_ID]
    again = normalize(list(reversed(body)), MARKERS, prophetic)
    assert again.path == c.path
