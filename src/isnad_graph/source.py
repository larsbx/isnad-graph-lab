"""Pinned upstream sources, each verified by sha256.

* «الجامع» Hadith Knowledge Graph (CC-BY-4.0) — the reports, chains and
  narrators: https://huggingface.co/datasets/emadjumaah/hadith-kg
* hadith-api (public domain, Unlicense) — Arabic and English editions of the
  canonical collections with modern gradings:
  https://github.com/fawazahmed0/hadith-api
* al-Thurayya gazetteer (Apache-2.0) — places and coordinates of the early
  Islamic world (``geo.THURAYYA``): https://github.com/althurayya/althurayya.github.io
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

SOURCE_DIR = Path("data/source")


@dataclass(frozen=True)
class SourceSpec:
    repo: str
    filename: str
    revision: str
    sha256: str
    license: str
    url: str


HADITH_KG = SourceSpec(
    repo="emadjumaah/hadith-kg",
    filename="hadith-kg.db",
    revision=(rev := "8ae7e3d5be284a6b32a989cd41866343fc19501c"),
    sha256="d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6",
    license="CC-BY-4.0",
    url=f"https://huggingface.co/datasets/emadjumaah/hadith-kg/resolve/{rev}/hadith-kg.db",
)
DEFAULT_PATH = SOURCE_DIR / HADITH_KG.filename

HADITH_API_REVISION = "df57907be35291c91ad6a6691180e22ca9920784"
EDITIONS_DIR = SOURCE_DIR / "hadith-api"
_EDITION_SHA256 = MappingProxyType({
    "ara-abudawud": "216139c5f40a8147e700d62ffa3b5b2fe45d0e034f86941a193c598c10056189",
    "ara-bukhari": "e34a3402889ca378871da3c5984b7875c680920e93f1c8738ac7afe502179562",
    "ara-ibnmajah": "b406e6be81588ab0ec1ddbed32f5fd95bbcdda242c460d88331e82eb5c2bc0aa",
    "ara-malik": "088b1f354e110211da006d47e37dd8f8837368f318ed683271f0fdb0f09a3ab5",
    "ara-muslim": "194073b24090c5368e4d14a3f55c9e0ef144c7437bd7e5aa83aa4d2bc54a8ea0",
    "ara-nasai": "c705983c19bb089c87cd6531aff609bd94d862183ed0859115b0ff991826a956",
    "ara-tirmidhi": "408028cd56329ed78edbe3ad443beb96b58e16c3e5bd49f9bc7b0eac77c8820f",
    "eng-abudawud": "f6bcf73ad96d2f28296232e201e12963e7b3dd5325572fb88365edbbfb0ecd40",
    "eng-bukhari": "b3a10b8d50949e86cec82b0d323ce0eae3e2f713fa2f3daa5361638feb795988",
    "eng-ibnmajah": "5e9479efd403e935ddcf746a709b2727d535a41fe1f496deadc8a43f1d103cd7",
    "eng-malik": "fb02a0ae16ebba1a658b107da3b93e72ecb59c2acd871819e2b1f3bd2e90d27b",
    "eng-muslim": "2ef51a2a1980fb91e395fbf1580cc9c9413297f54bb8cad271e1499417299488",
    "eng-nasai": "4f2aaca4229b96210fdaa887915c69ba99dda8726816856cc8660e996b6b3a1f",
    "eng-tirmidhi": "f64f1a5e6f2614e164e3b10138412af322d3959011bf84d67f428f79b3858afb",
})
EDITION_FILES = tuple(
    SourceSpec(
        repo="fawazahmed0/hadith-api", filename=f"{name}.json", revision=HADITH_API_REVISION,
        sha256=digest, license="Unlicense (public domain)",
        url=(f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@{HADITH_API_REVISION}"
             f"/editions/{name}.json"),
    )
    for name, digest in _EDITION_SHA256.items()
)


def sha256(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def fetch(spec: SourceSpec = HADITH_KG, dest: Path | None = None) -> Path:
    """Download (if absent) and verify one pinned source file."""
    dest = dest or SOURCE_DIR / spec.filename
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(".part")
        with urllib.request.urlopen(spec.url) as r, part.open("wb") as f:
            shutil.copyfileobj(r, f, 1 << 24)
        part.rename(dest)
    if (digest := sha256(dest)) != spec.sha256:
        raise ValueError(f"{dest}: sha256 {digest} ≠ pinned {spec.sha256}")
    return dest


def fetch_editions(directory: Path = EDITIONS_DIR) -> Path:
    for spec in EDITION_FILES:
        fetch(spec, directory / spec.filename)
    return directory


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
