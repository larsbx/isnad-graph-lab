import json

import pytest

from isnad_graph.basemap import BBOX, basemap, clip_line, clip_ring, compact


def test_clip_ring_keeps_the_inside_of_a_box():
    square = [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]
    clipped = clip_ring(square, (2, -1, 10, 10))
    assert sorted(set(clipped)) == [(2, 0), (2, 4), (4, 0), (4, 4)]
    assert clip_ring(square, (5, 5, 6, 6)) == []


def test_clip_line_splits_at_the_box_and_keeps_one_point_beyond():
    line = [(0, 0), (1, 0), (5, 0), (6, 0), (7, 0), (1, 1), (2, 1)]
    assert clip_line(line, (0, -1, 2, 2)) == [[(0, 0), (1, 0), (5, 0)], [(7, 0), (1, 1), (2, 1)]]


def test_compact_rounds_and_drops_repeats():
    assert compact([(1.004, 2.0), (1.001, 2.001), (1.5, 2.0)], 0.01) == [1.0, 2.0, 1.5, 2.0]


def feature(kind, coords, **props):
    return {"type": "Feature", "properties": props,
            "geometry": {"type": kind, "coordinates": coords}}


@pytest.fixture
def layers(tmp_path):
    lon0, lat0, *_ = BBOX
    inside = [[lon0 + x, lat0 + y] for x, y in ((1, 1), (3, 1), (3, 3), (1, 1))]
    far = [[c[0] - 100, c[1]] for c in inside]
    files = {
        "ne_50m_land.geojson": [feature("MultiPolygon", [[inside], [far]])],
        "ne_50m_lakes.geojson": [feature("Polygon", [inside], name="Lake Van", scalerank=0),
                                 feature("Polygon", [inside], name="Lake Nasser", scalerank=5)],
        "ne_50m_rivers_lake_centerlines.geojson": [
            feature("LineString", inside, name="Euphrates", scalerank=3),
            feature("LineString", inside, name="Suez Canal", scalerank=6)],
        "routes.json": [feature("LineString", inside[:3], Meter=1)],
    }
    for name, feats in files.items():
        (tmp_path / name).write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
    return tmp_path


def test_basemap_keeps_natural_features_inside_the_frame(layers):
    b = basemap(layers)
    assert len(b["land"]) == 1 and len(b["lakes"]) == 1 and len(b["routes"]) == 1
    assert [(r["name"], r["ar"]) for r in b["rivers"]] == [("Euphrates", "الفرات")]  # no canals
    assert all(isinstance(v, float | int) for v in b["land"][0])


def test_missing_basemap_is_empty(tmp_path):
    assert basemap(tmp_path / "absent") == {}
