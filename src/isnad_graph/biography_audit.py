"""Conservative narrator linkage for measuring disagreement between biographies."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

from .arabic import normalize
from .geo import place_key

# The MuslimScholars display strings retain era and uncertainty lost in the
# scraped numeric columns. Only an exact Hijri point enters the agreement test.
_EXACT_YEAR = re.compile(r"^([1-9][0-9]{0,3})\s*(AH|BH)(?:\s*/\s*[0-9]{1,4}\s*CE)?$")
_HIJRI_ERA = re.compile(r"\b(?:AH|BH)\b")
_UNCERTAIN = re.compile(r"\b(?:or|approx(?:imately)?|circa|est(?:imated)?|about)\b|[~?]", re.I)
_HONORIFIC = re.compile(r"\s+(?:رضي الله عنه(?:ما|م|ا)?|رحمه الله|عليه السلام)$")
_LINEAGE = frozenset({"بن", "بنت"})

# Match whole place labels at city level. The source sometimes lists only a
# region, and "places of stay" can list several cities for one narrator.
_CITIES = {
    "المدينة": ("medina", "medinah", "madina", "madinah"),
    "مكة": ("mecca", "makkah", "makka"),
    "الكوفة": ("kufa", "kufah"),
    "البصرة": ("basra", "basrah"),
    "بغداد": ("baghdad",),
    "دمشق": ("damascus", "dimashq"),
    "حمص": ("hims", "homs"),
    "واسط": ("wasit", "waset"),
    "مرو": ("merv", "marw"),
    "همذان": ("hamadan", "hamadhan"),
    "نيسابور": ("nishapur", "naisabur", "neishabur"),
    "أصبهان": ("isfahan", "asbahan", "isbahaan"),
    "الطائف": ("taif",),
    "الري": ("rayy", "ray"),
    "بخارى": ("bukhara",),
    "فسطاط": ("fustat",),
    "حلب": ("aleppo", "halab"),
    "عسقلان": ("asqalan", "ashkelon"),
    "صنعاء": ("sanaa", "sana"),
    "الموصل": ("mosul", "mawsil"),
}
_ARABIC_CITIES = {place_key(name): name for name in _CITIES} | {
    place_key(a): b
    for a, b in (
        ("إصبهان", "أصبهان"),
        ("همدان", "همذان"),
        ("يثرب", "المدينة"),
        ("بخارة", "بخارى"),
    )
}
_LATIN_CITIES = {alias: name for name, aliases in _CITIES.items() for alias in aliases}
PROVISIONAL = "provisional_exact"


def exact_hijri_year(raw: str) -> int | None:
    """Parse one explicitly dated point, with negative integers for BH."""
    body = raw.split("[", 1)[0].strip()
    if _UNCERTAIN.search(raw) or len(_HIJRI_ERA.findall(raw)) != 1:
        return None
    m = _EXACT_YEAR.fullmatch(body.split("(", 1)[0].strip())
    if m is None:
        return None
    return int(m[1]) * (-1 if m[2] == "BH" else 1)


def name_key(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    name = normalize(unicodedata.normalize("NFKC", raw))
    name = _HONORIFIC.sub("", name)
    tokens = ["بن" if t == "ابن" else t for t in name.split()]
    # Keep weak exact name candidates as review leads.
    return " ".join(tokens) if len(tokens) >= 4 else ""


def distinctive_key(key: str) -> bool:
    tokens = key.split()
    # Count Arabic genealogical components, rather than treating e.g.
    # «عبد الرحمن بن جبير» as four independent identifying words.
    lineage = sum(t in _LINEAGE for t in tokens)
    nisba = bool(tokens) and tokens[-1].startswith("ال") and tokens[-1].endswith(("ي", "يه"))
    return lineage >= 2 or (lineage >= 1 and nisba)


def city_sets(raw: object, *, external: bool) -> frozenset[str]:
    if not isinstance(raw, str):
        return frozenset()
    tokens = re.split(r"[،,;؛]", raw)
    if not external:
        return frozenset(_ARABIC_CITIES[k] for t in tokens if (k := place_key(t)) in _ARABIC_CITIES)
    keys = (re.sub(r"[^a-z]", "", t.strip().lower().removeprefix("al-")) for t in tokens)
    return frozenset(_LATIN_CITIES[k] for k in keys if k in _LATIN_CITIES)


def recorded_point(basis: str, lo: object, hi: object) -> int | None:
    if basis == "recorded" and pd.notna(lo) and pd.notna(hi) and lo == hi:
        return int(lo)
    return None


def make_linkage(graph: pd.DataFrame, external: pd.DataFrame) -> pd.DataFrame:
    """Reciprocal unique exact name candidates, with no dates in selection."""
    graph = graph[graph.kind.eq("narrator")]
    if not graph.id.is_unique or not external.scholar_indx.is_unique:
        raise ValueError("source narrator IDs must be unique")
    ext_keys: dict[str, set[int]] = defaultdict(set)
    for rid, name in external[["scholar_indx", "name"]].itertuples(index=False, name=None):
        if key := name_key(name):
            ext_keys[key].add(int(rid))
    proposed: dict[int, dict[int, set[str]]] = {}
    informative = set()
    for gid, name, nickname in graph[["id", "name", "nickname"]].itertuples(index=False, name=None):
        keys = {name_key(name), name_key(nickname)} - {""}
        if keys:
            informative.add(int(gid))
        matches: dict[int, set[str]] = defaultdict(set)
        for key in keys:
            for rid in ext_keys.get(key, ()):
                matches[rid].add(key)
        proposed[int(gid)] = matches
    incoming = Counter(rid for matches in proposed.values() for rid in matches)

    rows = []
    for gid, matches in proposed.items():
        candidate = next(iter(matches)) if len(matches) == 1 else None
        unique = candidate is not None and incoming[candidate] == 1
        strong = unique and any(distinctive_key(key) for key in matches[candidate])
        if strong:
            status = PROVISIONAL
        elif unique:
            status = "underspecified_exact_candidate"
        elif matches:
            status = "ambiguous_exact_candidates"
        else:
            status = "unmatched" if gid in informative else "no_distinctive_name"
        rows.append(
            {
                "rawi_id": gid,
                "status": status,
                "scholar_indx": candidate if strong else None,
                "candidate_ids": ",".join(map(str, sorted(matches))),
                "shared_keys": " | ".join(sorted({k for v in matches.values() for k in v})),
            }
        )
    return pd.DataFrame(rows).astype({"scholar_indx": "Int64"})


def explicit_companion(grade: str) -> bool | None:
    """The two numeric generation schemes have different granularity."""
    if grade.startswith("Comp."):
        return True
    if grade.startswith(("Follower", "Succ.", "3rd Century AH", "4th Century AH")):
        return False
    return None


def agreement_rows(
    linkage: pd.DataFrame, graph: pd.DataFrame, external: pd.DataFrame
) -> pd.DataFrame:
    """Diagnostic values for proposed matches, including possible disagreements."""
    g = graph.set_index("id")
    e = external.set_index("scholar_indx")
    rows = []
    for link in linkage.loc[linkage.status.eq(PROVISIONAL)].itertuples(index=False):
        rawi, scholar = g.loc[link.rawi_id], e.loc[link.scholar_indx]
        local_death = recorded_point(rawi.death_basis, rawi.death_lo, rawi.death_hi)
        other_death = exact_hijri_year(scholar.death_date_place)
        local_birth = recorded_point(rawi.birth_basis, rawi.birth_lo, rawi.birth_hi)
        other_birth = exact_hijri_year(scholar.birth_date_place)
        local_cities = city_sets(rawi.iqama, external=False)
        other_cities = city_sets(scholar.places_of_stay, external=True)
        companion = explicit_companion(scholar.grade)
        rows.append(
            {
                "rawi_id": link.rawi_id,
                "scholar_indx": link.scholar_indx,
                "kg_name": rawi["name"],
                "kg_nickname": rawi.nickname,
                "kg_nisba": rawi.nasab,
                "ms_name": scholar["name"],
                "shared_keys": link.shared_keys,
                "kg_tabaqa": rawi.tabaka,
                "ms_generation": scholar.grade,
                "companion_agrees": (rawi.rank_no == 1) == companion
                if pd.notna(rawi.rank_no) and companion is not None
                else None,
                "kg_death_ah": local_death,
                "ms_death_ah": other_death,
                "ms_death_display": scholar.death_date_place,
                "death_abs_difference": abs(local_death - other_death)
                if local_death is not None and other_death is not None
                else None,
                "kg_birth_ah": local_birth,
                "ms_birth_ah": other_birth,
                "ms_birth_display": scholar.birth_date_place,
                "kg_residence": rawi.iqama,
                "ms_places_of_stay": scholar.places_of_stay,
                "kg_matched_cities": " | ".join(sorted(local_cities)),
                "ms_matched_cities": " | ".join(sorted(other_cities)),
                "city_overlap": bool(local_cities & other_cities)
                if local_cities and other_cities
                else None,
            }
        )
    return pd.DataFrame(rows).astype(
        {
            "kg_death_ah": "Int64",
            "ms_death_ah": "Int64",
            "death_abs_difference": "Int64",
            "kg_birth_ah": "Int64",
            "ms_birth_ah": "Int64",
            "city_overlap": "boolean",
            "companion_agrees": "boolean",
        }
    )


def relation_evidence(
    edges: pd.DataFrame, matches: pd.DataFrame, external: pd.DataFrame
) -> dict[int, int]:
    """Count corroborating named neighbors without using them for linkage."""
    ids = matches.set_index("rawi_id").scholar_indx.to_dict()
    reverse = {sid: gid for gid, sid in ids.items()}
    relations = set()
    for sid, teachers, students in external[
        ["scholar_indx", "teachers_inds", "students_inds"]
    ].itertuples(index=False, name=None):
        if sid not in reverse:
            continue
        relations.update((int(t), sid) for t in teachers.split(",") if t.strip().isdigit())
        relations.update((sid, int(s)) for s in students.split(",") if s.strip().isdigit())
    counts: Counter[int] = Counter()
    # By pigeonhole, more direct links than inferred links proves at least
    # one occurrence is both direct and recorded.
    direct_recorded = edges.n_direct.gt(edges.n_inferred)
    for t, s in edges.loc[direct_recorded, ["src", "dst"]].itertuples(index=False, name=None):
        if (ids.get(t), ids.get(s)) in relations:
            counts.update((int(t), int(s)))
    return dict(counts)


def sample_matches(matches: pd.DataFrame, size: int = 200) -> pd.DataFrame:
    """Order a fixed, outcome-blind sample by hashes of scoped identity pairs."""
    columns = [
        "rawi_id",
        "scholar_indx",
        "kg_name",
        "kg_nickname",
        "kg_nisba",
        "ms_name",
        "shared_keys",
    ]
    sample = matches[columns].copy()
    sample["sample_key"] = [
        hashlib.sha256(f"isnad-biography-review-v1/{gid}/{sid}".encode()).hexdigest()
        for gid, sid in sample[["rawi_id", "scholar_indx"]].itertuples(index=False, name=None)
    ]
    sample = sample.sort_values(["sample_key", "rawi_id"]).head(size)
    return sample.assign(decision="", source_locator="", notes="")


def score_review(sample: pd.DataFrame, review: pd.DataFrame) -> dict:
    """Score only reviews of the frozen sample and surface unadjudicated cases."""
    index = ["sample_key", "rawi_id", "scholar_indx"]
    expected = pd.MultiIndex.from_frame(sample[index])
    actual = pd.MultiIndex.from_frame(review[index])
    if not actual.is_unique or not actual.isin(expected).all():
        raise ValueError("duplicate or out-of-sample review")
    decided = review.decision.isin(["same", "different"])
    if (
        not review.decision.isin(["same", "different", "uncertain", ""]).all()
        or review.loc[decided, "source_locator"].fillna("").str.strip().eq("").any()
    ):
        raise ValueError("each decisive review needs an evidence locator")
    yes = int(review.decision.eq("same").sum())
    no = int(review.decision.eq("different").sum())
    n = len(sample)
    unadjudicated = n - yes - no
    return {
        "sample_size": n,
        "same": yes,
        "different": no,
        "unadjudicated": unadjudicated,
        "observed_precision": yes / n if n >= 200 and unadjudicated == 0 else None,
        "sample_precision_bounds": [yes / n, (yes + unadjudicated) / n] if n else None,
    }


def compare_records(frame: pd.DataFrame) -> dict:
    """Denominators count pairs with comparable observations in both sources."""
    gap = frame.death_abs_difference.dropna()
    cities = frame.city_overlap.dropna()
    generation = frame.companion_agrees.dropna()
    return {
        "pairs": len(frame),
        "death_point_years": {
            "compared": len(gap),
            **{
                label: int(gap.le(tol).sum())
                for label, tol in [("exact", 0), ("within_2", 2), ("within_10", 10)]
            },
        },
        "residence_cities": {"compared": len(cities), "share_at_least_one": int(cities.sum())},
        "companion_status": {"compared": len(generation), "agree": int(generation.sum())},
        "corroborating_graph_neighbours": int(frame.corroborating_neighbours.gt(0).sum()),
    }
