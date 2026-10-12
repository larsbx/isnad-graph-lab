"""Places of the narrators, geocoded against the al-Thurayya gazetteer.

al-Thurayya (Seydi & Romanov; Apache-2.0) is the geospatial model of the early
Islamic world built on Georgette Cornu's *Atlas du monde arabo-islamique*:
2,518 toponyms with Arabic names, coordinates, settlement type and province.
The source's ``iqama`` (places of residence, «الشام ، دمشق») and
``death_place`` are split into tokens and each token is resolved to one place:

1. a province named outright (``REGIONS``) → that province, drawn at the
   centroid of its settlements, ``level = "region"``;
2. otherwise the gazetteer entries whose name (or variant) has the token's
   key — after ``ALIASES`` maps the source's spelling to the gazetteer's —
   ranked by agreement with the provinces of the narrator's other tokens,
   then by settlement type (``TYPE_RANK``), then by how many narrators the
   corpus places in each province; a tie that survives all three between
   different provinces is left unresolved, never guessed.

A narrator's *home* is the first residence token resolved to a city, else the
first resolved to a province.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import NamedTuple

import numpy as np
import pandas as pd

from .arabic import normalize
from .source import SOURCE_DIR, SourceSpec

THURAYYA = SourceSpec(
    repo="althurayya/althurayya.github.io",
    filename="places.geojson",
    revision=(rev := "f244e65ddf782baef08e410870c61c8096ff9f90"),
    sha256="9ceef49582106441fc63fc230a17045fdb6f5ef778f77d8c63eebbea2e2137d3",
    license="Apache-2.0",
    url=f"https://raw.githubusercontent.com/althurayya/althurayya.github.io/{rev}/master/places.geojson",
)
GAZETTEER_PATH = SOURCE_DIR / "althurayya" / THURAYYA.filename

TYPE_RANK = MappingProxyType({t: r for r, t in enumerate((
    "metropoles", "capitals", "towns", "quarters", "villages", "waystations", "xroads",
    "sites", "regions", "waters"))})
SETTLEMENTS = frozenset({"metropoles", "capitals", "towns"})
_SEP = re.compile(r"\s*[،,]\s*")


def place_key(name: str) -> str:
    """Matching key: normalized, without the article or a leading «بلاد»."""
    return re.sub(r"^(?:بلاد\s+)?ال", "", normalize(name).removeprefix("بلاد "))


#: The source's spelling → the gazetteer's; quarters and suburbs → their city.
ALIASES = MappingProxyType({place_key(a): place_key(b) for a, b in {
    "بخارى": "بخارة", "أنطاكيا": "أنطاكية", "صيدا": "صيداء", "سر من رأى": "سامراء",
    "قرقيسيا": "قرقيسية", "إسفرايين": "أسفراين", "يثرب": "المدينة", "المدائن": "المدائين",
    "ترمذ": "الترميذ",
    **dict.fromkeys(("الحربية", "الزعفرانية", "المخرم", "باب حرب", "باب الشعير",
                     "قنطرة الأشنان", "دار القطن", "باب الأزج", "باب البصرة"), "بغداد"),
    **dict.fromkeys(("الصالحية", "قاسيون", "بيت لهيا"), "دمشق"),
}.items()})
#: Provinces named in the source → al-Thurayya's region codes.
PROVINCES = MappingProxyType({
    "الشام": "Sham", "فلسطين": "Sham", "العراق": "Iraq", "مصر": "Egypt", "خراسان": "Khurasan",
    "اليمن": "Yemen", "الحجاز": "Jazirat al-Arab", "الأندلس": "Andalus", "فارس": "Faris",
    "إفريقية": "Maghrib", "المغرب": "Maghrib", "كرمان": "Kirman", "سجستان": "Sijistan",
    "الجزيرة": "Aqur", "الجبال": "Jibal", "السند": "Sind", "خوزستان": "Khuzistan",
    "برقة": "Barqa", "صقلية": "Sicile", "الديلم": "Daylam", "ما وراء النهر": "Transoxiana",
})
REGIONS = MappingProxyType({place_key(a): b for a, b in PROVINCES.items()})
#: A province's display name: the first of the source's names for it.
PROVINCE_NAMES = MappingProxyType({c: a for a, c in reversed(PROVINCES.items())})


class Place(NamedTuple):
    uri: str
    name: str
    lat: float
    lon: float
    region: str
    level: str  # "city" | "region"
    rank: int


@dataclass(frozen=True)
class Gazetteer:
    places: pd.DataFrame
    index: Mapping[str, tuple[Place, ...]]
    regions: Mapping[str, Place]


def load_gazetteer(path: Path = GAZETTEER_PATH) -> Gazetteer:
    rows = [f["properties"]["cornuData"] for f in json.loads(path.read_text("utf-8"))["features"]]
    places = pd.DataFrame({
        "uri": [r["cornu_URI"] for r in rows], "name": [r["toponym_arabic"] for r in rows],
        "translit": [r.get("toponym_translit", "") for r in rows],
        "lat": [float(r["coord_lat"]) for r in rows], "lon": [float(r["coord_lon"]) for r in rows],
        "region": [r["region_code"] for r in rows], "type": [r["top_type_hom"] for r in rows],
        "variants": [{r["toponym_arabic"], *_SEP.split(r.get("toponym_arabic_other", ""))}
                     for r in rows]})
    index: dict[str, list[Place]] = {}
    for r in places.itertuples():
        p = Place(r.uri, r.name, r.lat, r.lon, r.region, "city", TYPE_RANK.get(r.type, 99))
        for key in {place_key(v) for v in r.variants if v.strip()}:
            index.setdefault(key, []).append(p)
    towns = places[places.type.isin(SETTLEMENTS)].groupby("region")[["lat", "lon"]].mean()
    regions = {code: Place(f"region:{code}", PROVINCE_NAMES[code], towns.lat[code],
                           towns.lon[code], code, "region", -1)
               for code in set(REGIONS.values()) if code in towns.index}
    return Gazetteer(places.drop(columns="variants"),
                     MappingProxyType({k: tuple(sorted(v, key=lambda p: p.rank))
                                       for k, v in index.items()}),
                     MappingProxyType(regions))


EMPTY_GAZETTEER = Gazetteer(
    pd.DataFrame(columns=["uri", "name", "translit", "lat", "lon", "region", "type"]),
    MappingProxyType({}), MappingProxyType({}))


def _candidates(token: str, gaz: Gazetteer) -> tuple[Place, ...]:
    key = place_key(token)
    if key in REGIONS:
        region = gaz.regions.get(REGIONS[key])
        return (region,) if region else ()
    return gaz.index.get(ALIASES.get(key, key), ())


def resolve(tokens: Sequence[str], gaz: Gazetteer,
            prior: Mapping[str, int] = MappingProxyType({})) -> list[Place | None]:
    """Resolve each token in the context of the others (see module doc); ``prior``
    (narrators per province) breaks what context and settlement type leave tied."""
    found = [_candidates(t, gaz) for t in tokens]
    context = {c[0].region for c in found if c and len({p.region for p in c}) == 1}

    def pick(cands: tuple[Place, ...]) -> Place | None:
        if not cands:
            return None
        score = lambda p: (p.region not in context, p.rank, -prior.get(p.region, 0))  # noqa
        best = min(map(score, cands))
        top = {p.region: p for p in cands if score(p) == best}
        return next(iter(top.values())) if len(top) == 1 else None

    return [pick(c) for c in found]


def _tokens(raw: object) -> list[str]:
    return [t for t in _SEP.split(raw.strip()) if t] if isinstance(raw, str) else []


def geocode(narrators: pd.DataFrame, gaz: Gazetteer) -> pd.DataFrame:
    """Per narrator: home and death place (uri, lat, lon, region, level) and all places.

    Two passes: the first, without a prior, counts the narrators placed in each
    province; the second uses those counts to break the ties the first left."""
    pairs = list(zip(narrators.iqama, narrators.death_place, strict=True))
    first = (resolve([*_tokens(i), *_tokens(d)], gaz) for i, d in pairs)
    prior = MappingProxyType(Counter(r for ps in first for r in {p.region for p in ps if p}))

    def one(iqama: object, death: object) -> dict:
        res, dth = _tokens(iqama), _tokens(death)
        places = resolve([*res, *dth], gaz, prior)
        here = [p for p in places[:len(res)] if p]
        home = next((p for p in here if p.level == "city"), here[0] if here else None)
        died = next((p for p in places[len(res):] if p), None)
        return {"home_place": home and home.name, "home_uri": home and home.uri,
                "home_lat": home and home.lat, "home_lon": home and home.lon,
                "home_region": home and home.region, "home_level": home and home.level,
                "death_uri": died and died.uri, "death_lat": died and died.lat,
                "death_lon": died and died.lon,
                "places": list(dict.fromkeys(p.uri for p in places if p)),
                "n_places_unresolved": sum(p is None for p in places)}

    rows = [one(i, d) for i, d in pairs]
    return pd.DataFrame(rows, index=narrators.index).assign(id=narrators.id.to_numpy()).astype(
        {"home_lat": "Float64", "home_lon": "Float64", "death_lat": "Float64",
         "death_lon": "Float64"})[["id", *rows[0]]] if rows else pd.DataFrame()


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance on a sphere of radius 6371 km; vectorised."""
    p1, p2, l1, l2 = (np.radians(np.asarray(x, dtype=float)) for x in (lat1, lat2, lon1, lon2))
    dl = l2 - l1
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(a))


def geo_edges(edges: pd.DataFrame, geo: pd.DataFrame) -> pd.DataFrame:
    """Edges with the distance between homes, whether they share a city, and
    the provinces of either end."""
    g = geo.set_index("id")
    t, s = (g.reindex(edges[end].to_numpy()).reset_index(drop=True) for end in ("src", "dst"))
    city = lambda x: x.home_uri.where(x.home_level.eq("city"))  # noqa: E731
    keep = lambda v, dtype: pd.Series(v, index=edges.index).astype(dtype)  # noqa: E731
    return edges.assign(
        distance_km=keep(np.round(haversine_km(*(x[c].astype("float64") for x in (t, s)
                                                  for c in ("home_lat", "home_lon"))), 1),
                         "Float64"),
        same_city=keep(city(t).eq(city(s)).where(city(t).notna() & city(s).notna())
                       .to_numpy(), "boolean"),
        src_region=keep(t.home_region.to_numpy(), "string"),
        dst_region=keep(s.home_region.to_numpy(), "string"),
    )


def used_places(geo: pd.DataFrame, gaz: Gazetteer) -> pd.DataFrame:
    """The gazetteer entries (and province centroids) the graph refers to, with counts."""
    regions = pd.DataFrame([{"uri": p.uri, "name": p.name, "translit": p.region, "lat": p.lat,
                             "lon": p.lon, "region": p.region, "type": "province"}
                            for p in gaz.regions.values()])
    homes = geo.home_uri.value_counts().rename("n_home")
    anywhere = geo.places.explode().value_counts().rename("n_narrators")
    return (pd.concat([gaz.places.drop_duplicates("uri"), regions], ignore_index=True)
            .join(anywhere, on="uri", how="inner").join(homes, on="uri")
            .fillna({"n_home": 0}).astype({"n_home": "int64", "n_narrators": "int64"})
            .sort_values("n_narrators", ascending=False, kind="stable").reset_index(drop=True))
