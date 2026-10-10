"""The pinned upstream source: «الجامع» Hadith Knowledge Graph (CC-BY-4.0).

https://huggingface.co/datasets/emadjumaah/hadith-kg — itself a cleaned
relational export of a 2017 dump of the Jami' al-Hadith database.
"""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceSpec:
    repo: str
    filename: str
    revision: str
    sha256: str
    license: str

    @property
    def url(self) -> str:
        return (f"https://huggingface.co/datasets/{self.repo}/resolve/"
                f"{self.revision}/{self.filename}")


HADITH_KG = SourceSpec(
    repo="emadjumaah/hadith-kg",
    filename="hadith-kg.db",
    revision="8ae7e3d5be284a6b32a989cd41866343fc19501c",
    sha256="d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6",
    license="CC-BY-4.0",
)

DEFAULT_PATH = Path("data/source") / HADITH_KG.filename


def sha256(path: Path, chunk: int = 1 << 24) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def fetch(dest: Path = DEFAULT_PATH, spec: SourceSpec = HADITH_KG) -> Path:
    """Download (if absent) and verify the pinned source database."""
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(".part")
        with urllib.request.urlopen(spec.url) as r, part.open("wb") as f:
            shutil.copyfileobj(r, f, 1 << 24)
        part.rename(dest)
    if (digest := sha256(dest)) != spec.sha256:
        raise ValueError(f"{dest}: sha256 {digest} ≠ pinned {spec.sha256}")
    return dest


def connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
