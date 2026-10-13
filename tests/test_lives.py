from itertools import pairwise

from isnad_graph.lives import ERAS, era, lifeline, phases


def test_phases_partition_the_life():
    assert phases(20, 100, hearing=(25, 57), teaching=(65, 100)) == [
        {"kind": "quiet", "from": 20, "to": 25}, {"kind": "hearing", "from": 25, "to": 57},
        {"kind": "quiet", "from": 57, "to": 65}, {"kind": "teaching", "from": 65, "to": 100}]
    assert phases(20, 100, hearing=(25, 70), teaching=(40, 100)) == [
        {"kind": "quiet", "from": 20, "to": 25}, {"kind": "hearing", "from": 25, "to": 40},
        {"kind": "both", "from": 40, "to": 70}, {"kind": "teaching", "from": 70, "to": 100}]
    assert phases(-53, 11, hearing=None, teaching=(-13, 11)) == [
        {"kind": "quiet", "from": -53, "to": -13}, {"kind": "teaching", "from": -13, "to": 11}]
    assert phases(20, 100, None, None) == [{"kind": "quiet", "from": 20, "to": 100}]
    assert phases(20, 100, hearing=(0, 300), teaching=None) == [
        {"kind": "hearing", "from": 20, "to": 100}]  # clipped to the life


def test_eras_cover_the_period_without_gaps():
    assert all(a["to"] == b["from"] for a, b in pairwise(ERAS))
    assert era(30) == "Rāshidūn" and era(100) == "Umayyad" and era(200) == "ʿAbbāsid"


def test_lifeline_of_a_tabii(mini_graph):
    a = lifeline(mini_graph, 2)  # A: 20–100, Basra; teacher Abu Hurayra; students B, G, D
    assert (a["birth"]["mid"], a["death"]["mid"]) == (20, 100) and a["known"] is None
    # hearing from age A_HEAR; teaching only once teacher is A_TEACH and student A_HEAR
    assert [(p["kind"], p["from"], p["to"]) for p in a["phases"]] == [
        ("quiet", 20, 25), ("hearing", 25, 57), ("quiet", 57, 65), ("teaching", 65, 100)]
    heard = {s["uri"]: s for s in a["stops"] if s["role"] == "teacher"}
    taught = {s["uri"]: s for s in a["stops"] if s["role"] == "student"}
    assert set(heard) == {"madina"} and heard["madina"]["year"] == 41
    assert set(taught) == {"kufa", "basra"}  # D (born after A died) is not a stop
    assert taught["kufa"]["year"] == 82.5 and taught["basra"]["year"] == 87.5
    assert a["n_refuted"] == 1 and a["n_unplaced"] == 0 and a["home"] == "البصرة"


def test_a_window_the_ages_leave_empty_is_counted_not_placed(mini_graph):
    n = mini_graph.frame("narrators")
    n.loc[n.id.eq(1), ["death_lo", "death_hi"]] = 22  # Abu Hurayra dies when A is two
    a = lifeline(mini_graph, 2, narrators=n)
    assert a["n_unplaced"] == 1 and {s["role"] for s in a["stops"]} == {"student"}
