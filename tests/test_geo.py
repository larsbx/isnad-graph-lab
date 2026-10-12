import pandas as pd
import pytest

from conftest import make_gazetteer
from isnad_graph.geo import geo_edges, geocode, haversine_km, load_gazetteer, place_key, resolve


@pytest.fixture(scope="module")
def gaz(tmp_path_factory):
    return load_gazetteer(make_gazetteer(tmp_path_factory.mktemp("gaz") / "places.geojson"))


def test_place_key_drops_article_and_normalizes():
    assert place_key("البصرة") == place_key("بصره") and place_key("أصبهان") == place_key("إصبهان")


def test_homonyms_go_to_the_higher_settlement_type(gaz):
    (p,) = resolve(["البصرة"], gaz)
    assert (p.uri, p.level) == ("basra", "city")


def test_aliases_and_regions(gaz):
    bukhara, sham = resolve(["بخارى", "الشام"], gaz)
    assert bukhara.uri == "bukhara"
    assert (sham.uri, sham.name, sham.level, sham.region) == ("region:Sham", "الشام", "region",
                                                              "Sham")
    assert sham.lat == pytest.approx((33.5 + 34.7 + 33.9) / 3)  # settlements of the region


def test_context_breaks_a_tie_between_regions(gaz):
    assert resolve(["الشام", "بيروت"], gaz)[1].uri == "bayrut"


def test_a_tie_without_context_is_left_unresolved_unless_a_prior_breaks_it(gaz):
    assert resolve(["بيروت"], gaz) == [None]
    assert resolve(["بيروت"], gaz, {"Sham": 5, "Khuzistan": 1})[0].uri == "bayrut"


def test_quarters_resolve_to_their_city(gaz):
    assert resolve(["الصالحية"], gaz)[0].uri == "dimashq"


def test_unknown_token_is_none(gaz):
    assert resolve(["واق الواق"], gaz) == [None]


def test_geocode_picks_the_first_city_as_home(gaz):
    n = pd.DataFrame({"id": [1, 2, 3], "iqama": ["الشام ، دمشق", "العراق", None],
                      "death_place": ["حمص", None, "الكوفة"]})
    g = geocode(n, gaz).set_index("id")
    assert g.loc[1, ["home_uri", "home_level", "death_uri"]].tolist() == ["dimashq", "city",
                                                                         "hims"]
    assert g.loc[2, ["home_uri", "home_level"]].tolist() == ["region:Iraq", "region"]
    assert pd.isna(g.loc[3, "home_uri"]) and g.loc[3, "death_uri"] == "kufa"
    assert g.loc[1, "places"] == ["region:Sham", "dimashq", "hims"]


def test_geo_edges(gaz):
    n = pd.DataFrame({"id": [1, 2, 3], "iqama": ["البصرة", "الكوفة", "البصرة"],
                      "death_place": [None] * 3})
    e = geo_edges(pd.DataFrame({"src": [1, 1, 1], "dst": [2, 3, 9]}), geocode(n, gaz))
    assert e.distance_km.iloc[0] == pytest.approx(haversine_km(30.4, 47.7, 32.0, 44.4), abs=0.05)
    assert e.distance_km.iloc[1] == 0 and pd.isna(e.distance_km.iloc[2])
    assert e.same_city.iloc[:2].tolist() == [False, True] and pd.isna(e.same_city.iloc[2])
    assert e.src_region.iloc[0] == "Iraq" and e.dst_region.iloc[0] == "Iraq"


def test_haversine_known_distance():
    assert haversine_km(0, 0, 0, 1) == pytest.approx(111.19, abs=0.01)


def test_geocode_breaks_ties_by_the_corpus_prior(gaz):
    n = pd.DataFrame({"id": [1, 2, 3], "iqama": ["دمشق", "حمص", "بيروت"],
                      "death_place": [None] * 3})
    assert geocode(n, gaz).home_uri.tolist() == ["dimashq", "hims", "bayrut"]
