"""Geographic context for the Chronicle map, clipped to its frame.

* Natural Earth 1:50m (public domain): land, lakes and the great rivers —
  Euphrates, Tigris, Nile, Oxus, Jaxartes, Indus. Reservoirs and canals are
  left out; they post-date the period.
* al-Thurayya's route network (Apache-2.0): the roads of Cornu's atlas
  between the gazetteer's places — the ways a riḥla could take — each
  section (about a day's stage) drawn as the chord between its two places.

Everything is clipped to ``BBOX`` (a margin beyond what the page shows), rounded
to ``PRECISION`` degrees, and flattened to ``[lon, lat, lon, lat, …]``.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from pathlib import Path

from .geo import THURAYYA
from .source import SOURCE_DIR, SourceSpec

BASEMAP_DIR = SOURCE_DIR / "basemap"
NATURAL_EARTH_REVISION = "ca96624a56bd078437bca8184e78163e5039ad19"
_NE = {"ne_50m_land": "e874b27a51d146452be360cafb3cc50c86001074a67d534113e6534682f9826b",
       "ne_50m_lakes": "d350b75978b26fe839b797c2c529b2fb8f47fb3983c03f4964e36d5df9378a52",
       "ne_50m_rivers_lake_centerlines":
           "f286e0ce978fde999ca2d7a78c764be08542e19b63cded52b05c12d5173ccc51"}
BASEMAP_FILES = (
    *(SourceSpec(repo="nvkelso/natural-earth-vector", filename=f"{name}.geojson",
                 revision=NATURAL_EARTH_REVISION, sha256=digest, license="public domain",
                 url=("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
                      f"{NATURAL_EARTH_REVISION}/geojson/{name}.geojson"))
      for name, digest in _NE.items()),
    SourceSpec(repo=THURAYYA.repo, filename="routes.json", revision=THURAYYA.revision,
               sha256="40dd41ec54cb84b643a4206b8275660ac06752d5114b2c1bcec047845eb462b3",
               license=THURAYYA.license,
               url=THURAYYA.url.removesuffix("places.geojson") + "routes.json"),
)
#: lon₀, lat₀, lon₁, lat₁ — beyond the page's frame, so clipped edges stay unseen.
BBOX = (22.0, 6.0, 78.0, 47.0)
PRECISION = 0.02
#: Lakes of scalerank above this are reservoirs at 1:50m.
MAX_LAKE_RANK = 2
#: The seas as the geographers of the period named them, at a label position.
SEAS = (("بحر الروم", "Mediterranean", 31.0, 33.4), ("بحر القلزم", "Red Sea", 38.3, 20.5),
        ("بحر فارس", "Persian Gulf", 51.6, 27.0), ("بحر الخزر", "Caspian", 50.8, 41.6),
        ("بحر الهند", "Arabian Sea", 62.0, 18.0))

#: Natural Earth's river names → the names the period's geographers used.
RIVER_NAMES = {"Euphrates": "الفرات", "Al Furat": "الفرات", "Firat": "الفرات", "Tigris": "دجلة",
               "Dicle": "دجلة", "Nile": "النيل", "Amu  Darya": "جيحون", "Syr Darya": "سيحون",
               "Indus": "مهران"}

Point = tuple[float, float]


def _inside(p: Point, box: Sequence[float]) -> bool:
    return box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]


def clip_ring(ring: Sequence[Point], box: Sequence[float]) -> list[Point]:
    """Sutherland–Hodgman: the part of a polygon ring inside an axis-aligned box."""
    def cut(points: list[Point], axis: int, bound: float, keep_below: bool) -> list[Point]:
        inside = (lambda p: p[axis] <= bound) if keep_below else (lambda p: p[axis] >= bound)
        out: list[Point] = []
        for a, b in zip(points, points[1:] + points[:1], strict=True):
            if inside(b):
                if not inside(a):
                    out.append(_cross(a, b, axis, bound))
                out.append(b)
            elif inside(a):
                out.append(_cross(a, b, axis, bound))
        return out

    pts = [tuple(p) for p in ring]
    for axis, bound, below in ((0, box[0], False), (0, box[2], True),
                               (1, box[1], False), (1, box[3], True)):
        pts = cut(pts, axis, bound, below) if pts else []
    return pts


def _cross(a: Point, b: Point, axis: int, bound: float) -> Point:
    t = (bound - a[axis]) / (b[axis] - a[axis])
    p = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    return (bound, p[1]) if axis == 0 else (p[0], bound)


def clip_line(line: Sequence[Point], box: Sequence[float]) -> list[list[Point]]:
    """The runs of a polyline inside the box, each with one point beyond either
    end so it reaches the edge."""
    pts = [tuple(p) for p in line]
    keep = [any(_inside(q, box) for q in pts[max(i - 1, 0):i + 2]) for i in range(len(pts))]
    runs, run = [], []
    for p, k in zip(pts, keep, strict=True):
        if k:
            run.append(p)
        elif run:
            runs, run = [*runs, run], []
    return [r for r in [*runs, run] if len(r) > 1]


def compact(points: Iterable[Point], precision: float = PRECISION) -> list[float]:
    """Round to ``precision`` degrees, drop repeats, flatten."""
    q = lambda v: round(round(v / precision) * precision, 4)  # noqa: E731
    out: list[Point] = []
    for p in points:
        r = (q(p[0]), q(p[1]))
        if not out or r != out[-1]:
            out.append(r)
    return [v for p in out for v in p]


def _features(path: Path) -> list[dict]:
    return json.loads(path.read_text("utf-8"))["features"]


def _rings(geometry: dict) -> list[list]:
    c = geometry["coordinates"]
    return {"Polygon": lambda: c, "MultiPolygon": lambda: [r for p in c for r in p]}.get(
        geometry["type"], lambda: [])()


def _lines(geometry: dict) -> list[list]:
    c = geometry["coordinates"]
    return {"LineString": lambda: [c], "MultiLineString": lambda: c}.get(
        geometry["type"], lambda: [])()


def basemap(directory: Path = BASEMAP_DIR, box: Sequence[float] = BBOX) -> dict:
    """The clipped layers, or ``{}`` when the files are not fetched."""
    if not all((directory / s.filename).exists() for s in BASEMAP_FILES):
        return {}
    def polys(feats: list[dict]) -> list[list[float]]:
        return [c for f in feats for r in _rings(f["geometry"])
                if len(c := compact(clip_ring(r, box))) >= 6]

    def lines(f: dict) -> list[list[float]]:
        return [c for ln in _lines(f["geometry"]) for run in clip_line(ln, box)
                if len(c := compact(run)) >= 4]

    lakes = [f for f in _features(directory / "ne_50m_lakes.geojson")
             if f["properties"].get("scalerank", 99) <= MAX_LAKE_RANK]
    rivers = [f for f in _features(directory / "ne_50m_rivers_lake_centerlines.geojson")
              if "canal" not in (f["properties"].get("name") or "").lower()]
    return {
        "land": polys(_features(directory / "ne_50m_land.geojson")),
        "lakes": polys(lakes),
        "rivers": [{"name": f["properties"].get("name"),
                    "ar": RIVER_NAMES.get(f["properties"].get("name")), "line": c}
                   for f in rivers for c in lines(f)],
        # a road section is a stage of about a day's travel: drawn as its chord
        "routes": [c for f in _features(directory / "routes.json") for ln in _lines(f["geometry"])
                   if any(_inside(tuple(p), box) for p in (ln[0], ln[-1]))
                   and len(c := compact([ln[0], ln[-1]])) == 4],
        "seas": [{"name": a, "en": e, "lon": lon, "lat": lat} for a, e, lon, lat in SEAS],
    }
