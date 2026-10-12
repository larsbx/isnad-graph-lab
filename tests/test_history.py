import pandas as pd

from isnad_graph.history import century, century_profile, flows, hubs


def test_century_counts_from_one():
    assert century(pd.Series([1, 100, 101, 250, None], dtype="Float64")).tolist()[:4] == [
        1, 1, 2, 3]


E = pd.DataFrame({
    "src": [1, 1, 2, 3], "dst": [2, 3, 4, 4], "n_chains": [10, 2, 5, 1],
    "ante_quem": [90, 95, 180, 150], "chronology": ["consistent"] * 3 + ["impossible"],
    "same_city": pd.array([True, False, None, True], dtype="boolean"),
    "distance_km": pd.array([0.0, 400.0, None, 0.0], dtype="Float64"),
    "src_region": ["Iraq", "Iraq", "Sham", "Iraq"], "dst_region": ["Iraq", "Sham", "Sham", "Sham"],
})
N = pd.DataFrame({"id": [1, 2, 3, 4], "home_uri": ["basra", "dimashq", "kufa", None],
                  "home_place": ["البصرة", "دمشق", "الكوفة", None]})


def test_century_profile_is_chain_weighted():
    p = century_profile(E).set_index("century")
    assert p.loc[1, ["n_edges", "n_chains"]].tolist() == [2, 12]
    assert p.loc[1, "same_city_share"] == 10 / 12
    assert p.loc[2, "same_city_share"] == 1.0  # the unknown edge is not counted
    assert p.loc[2, "impossible_share"] == 1 / 6


def test_flows_between_provinces():
    f = flows(E).set_index(["century", "src_region", "dst_region"])
    assert f.loc[(1, "Iraq", "Sham"), "n_chains"] == 2
    assert f.loc[(2, "Sham", "Sham"), "n_edges"] == 1


def test_hubs_rank_teacher_homes_by_chains_carried():
    h = hubs(E, N, k=2)
    assert h[h.century.eq(1)].home_uri.tolist() == ["basra"]
    assert h[h.century.eq(2)].home_uri.tolist() == ["dimashq", "kufa"]
