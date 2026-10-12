#!/usr/bin/env python3
"""Check vendored packages against the digests pinned in ``vendored.toml``.

A consumer repository copies each upstream package directory byte-for-byte
and records, per package, the upstream repository, the upstream commit, the
local root that acts as the Mojo include path, and the SHA-256 of every
vendored file. This script verifies that every pinned file exists with the
pinned digest and that no unlisted file (bytecode caches aside) sits inside a
vendored package directory, so no local patch can land unnoticed. Protocol:
the README of each consumer repository.

Usage:
    check_vendored_sync.py                 check every package; exit 1 on drift
    check_vendored_sync.py pin NAME COMMIT re-pin NAME's digests from the local
                                           files after replacing the package
                                           directory with a clean copy from
                                           COMMIT (a file upstream removed
                                           drops out; re-derives the
                                           ESTATE.toml pins too)
    check_vendored_sync.py estate          re-derive the ESTATE.toml pins only

A consumer whose ESTATE.toml pins a vendoring source with a [[dep]] gets that
``pin`` checked too: it is the digest the estate audit computes over
vendored.toml (metadata plus file contents), derived and never hand-written.
``check`` fails when it disagrees and ``pin`` / ``estate`` rewrite it. A
consumer without ESTATE.toml has no estate pins to keep.

Manifest shape::

    [[package]]
    name = "finite_exact"
    repository = "larsbx/finite_exact"
    commit = "<40 hex>"
    root = "mojo"                      # local include root; "." for the repo root

    [package.files]
    "finite_exact/__init__.mojo" = "<sha256>"
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

MANIFEST_NAME = "vendored.toml"
ESTATE = "ESTATE.toml"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def repo_root(start: Path | None = None) -> Path:
    """The nearest ancestor of this file holding the manifest.

    The checker is itself vendored, so it cannot assume how deep inside a
    consumer it sits. Searching upward for the manifest makes the depth
    irrelevant; with no manifest anywhere above, the grandparent is returned
    and `check` reports the manifest missing rather than guessing.
    """
    here = (start or Path(__file__)).resolve()
    for parent in here.parents:
        if (parent / MANIFEST_NAME).exists():
            return parent
    return here.parents[1]


def package_files(package_dir: Path) -> list[Path]:
    """Every file of a vendored package directory except Python bytecode caches."""
    return sorted(p for p in package_dir.glob("**/*")
                  if p.is_file() and p.suffix != ".pyc" and "__pycache__" not in p.parts)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(manifest: Path | None = None) -> list[dict]:
    manifest = manifest or repo_root() / MANIFEST_NAME
    return tomllib.loads(manifest.read_text(encoding="utf-8")).get("package", [])


def vendored_directories(root: Path | None = None, manifest: Path | None = None) -> tuple[str, ...]:
    """The package directories the manifest vendors, as sorted repo-relative paths.

    Each is ``root/name`` of a ``[[package]]`` entry (``name`` alone when the
    entry's root is ``.``), with no trailing slash. A consumer that exempts
    vendored files from its own checks reads the boundary here instead of
    re-parsing the manifest. With no manifest, nothing is vendored and the
    answer is empty: the fail-closed direction, since an empty exemption
    exempts nothing. A manifest entry without ``name`` or ``root`` is
    skipped here; ``check`` reports it.
    """
    root = root or repo_root()
    manifest = manifest or root / MANIFEST_NAME
    if not manifest.exists():
        return ()
    return tuple(sorted({
        (PurePosixPath(pkg["root"]) / pkg["name"]).as_posix()
        for pkg in load(manifest) if "root" in pkg and "name" in pkg
    }))


def vendored_files(root: Path | None = None, manifest: Path | None = None) -> tuple[str, ...]:
    """Every file the manifest pins, as sorted repo-relative paths.

    ``root/rel`` for each ``rel`` under an entry's ``[package.files]``. A
    package may pin files beside its directory rather than inside it (a
    specification directly under its root), which ``vendored_directories``
    does not cover; an exemption of vendored files reads both. No manifest
    pins nothing, the fail-closed direction.
    """
    root = root or repo_root()
    manifest = manifest or root / MANIFEST_NAME
    if not manifest.exists():
        return ()
    return tuple(sorted({
        (PurePosixPath(pkg["root"]) / rel).as_posix()
        for pkg in load(manifest) if "root" in pkg
        for rel in pkg.get("files", {})
    }))


def check_package(pkg: dict, root: Path) -> list[str]:
    name = pkg.get("name", "<unnamed>")
    errors: list[str] = []
    for key in ("name", "repository", "commit", "root", "files"):
        if key not in pkg:
            errors.append(f"{name}: manifest entry lacks {key!r}")
    if errors:
        return errors
    if not COMMIT_RE.match(pkg["commit"]):
        errors.append(f"{name}: commit must be a full 40-hex SHA")
    if not pkg["files"]:
        errors.append(f"{name}: no files pinned")
    base = root / pkg["root"]
    for rel, digest in pkg["files"].items():
        path = base / rel
        if not path.exists():
            errors.append(f"{name}: {rel} missing")
        elif sha256(path) != digest:
            errors.append(f"{name}: {rel} differs from {pkg['repository']}@{pkg['commit'][:12]}")
    package_dir = base / name
    listed = set(pkg["files"])
    for path in package_files(package_dir):
        rel = path.relative_to(base).as_posix()
        if rel not in listed:
            errors.append(f"{name}: {rel} is not pinned in vendored.toml")
    return errors


def estate_digest(packages: list[dict], repository: str, root: Path) -> str:
    """The estate audit's vendored digest (estate-governance audit, ``vendored_digest``)."""
    rows = sorted(({
        "name": pkg.get("name"),
        "commit": pkg.get("commit"),
        "root": pkg.get("root"),
        "files": {rel: {"recorded": digest, "actual": sha256(root / pkg["root"] / rel)}
                  for rel, digest in sorted(pkg["files"].items())},
    } for pkg in packages if pkg.get("repository") == repository), key=lambda row: row["name"])
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def estate_pins(root: Path | None = None, manifest: Path | None = None) -> dict[str, str]:
    """dep id -> the pin ESTATE.toml must carry for that vendoring source."""
    root = root or repo_root()
    packages = load(manifest or root / MANIFEST_NAME)
    return {source.split("/")[1]: "sha256:" + estate_digest(packages, source, root)
            for source in sorted({p["repository"] for p in packages})}


def _dep_pin(dep_id: str) -> re.Pattern[str]:
    return re.compile(r'(^\[\[dep\]\][ \t]*(?:#.*)?\nid = "' + re.escape(dep_id) + r'"\n(?:[^\[\n].*\n|\n)*?pin = ")([^"]*)(")', re.M)


def estate_drift(root: Path | None = None, manifest: Path | None = None) -> list[str]:
    root = root or repo_root()
    estate = root / ESTATE
    if not estate.exists():
        return []
    deps = {d.get("id"): d.get("pin") for d in tomllib.loads(estate.read_text(encoding="utf-8")).get("dep", [])}
    return [f"{ESTATE}: no [[dep]] {dep_id!r} for vendored packages" if dep_id not in deps
            else f"{ESTATE}: [[dep]] {dep_id!r} pin {deps[dep_id]} != {want}; run check_vendored_sync.py estate"
            for dep_id, want in estate_pins(root, manifest).items() if deps.get(dep_id) != want]


def write_estate_pins(root: Path | None = None, manifest: Path | None = None) -> list[str]:
    root = root or repo_root()
    estate = root / ESTATE
    if not estate.exists():
        return []
    text = estate.read_text(encoding="utf-8")
    errors = []
    for dep_id, want in estate_pins(root, manifest).items():
        text, n = _dep_pin(dep_id).subn(lambda m: m[1] + want + m[3], text, count=1)
        if n != 1:
            errors.append(f"{ESTATE}: no [[dep]] {dep_id!r} for vendored packages")
    if not errors:
        estate.write_text(text, encoding="utf-8")
    return errors


def check_files(root: Path | None = None, manifest: Path | None = None) -> list[str]:
    root = root or repo_root()
    manifest = manifest or root / MANIFEST_NAME
    if not manifest.exists():
        return [f"missing manifest {manifest.name}"]
    packages = load(manifest)
    if not packages:
        return ["manifest pins no packages"]
    return [e for pkg in packages for e in check_package(pkg, root)]


def check(root: Path | None = None, manifest: Path | None = None) -> list[str]:
    return check_files(root, manifest) or estate_drift(root, manifest)


def render(packages: list[dict]) -> str:
    out = ["# Vendored packages, checked by check_vendored_sync.py; re-pin with", "# `check_vendored_sync.py pin NAME COMMIT` after copying from upstream.", ""]
    for pkg in packages:
        out += ["[[package]]"]
        out += [f'{k} = "{pkg[k]}"' for k in ("name", "repository", "commit", "root")]
        out += ["", "[package.files]"]
        out += [f'"{rel}" = "{digest}"' for rel, digest in sorted(pkg["files"].items())]
        out += [""]
    return "\n".join(out)


def pin(name: str, commit: str, root: Path | None = None, manifest: Path | None = None) -> list[str]:
    root = root or repo_root()
    manifest = manifest or root / MANIFEST_NAME
    if not COMMIT_RE.match(commit):
        return ["commit must be a full 40-hex SHA"]
    packages = load(manifest)
    target = next((p for p in packages if p["name"] == name), None)
    if target is None:
        return [f"no package named {name!r} in {manifest.name}"]
    base = root / target["root"]
    # The pin set is the fresh copy of the package directory, every file it
    # holds: a file upstream removed drops out, one it added or renamed is
    # pinned. A listed file outside that directory (a package pinned as single
    # files under its root) has no fresh copy to compare, so it must still exist.
    inside = f"{name}/"
    outside = sorted(rel for rel in target["files"] if not rel.startswith(inside))
    missing = [rel for rel in outside if not (base / rel).is_file()]
    if missing:
        return [f"{name}: cannot pin missing file {rel}" for rel in missing]
    files = outside + [p.relative_to(base).as_posix() for p in package_files(base / name)]
    if not files:
        return [f"{name}: nothing to pin under {target['root']}/{name}"]
    target["files"] = {rel: sha256(base / rel) for rel in files}
    target["commit"] = commit
    manifest.write_text(render(packages), encoding="utf-8")
    return write_estate_pins(root, manifest)


def main(argv: list[str]) -> int:
    if len(argv) == 4 and argv[1] == "pin":
        errors = pin(argv[2], argv[3])
        print("\n".join(errors) if errors else f"pinned {argv[2]} at {argv[3]}")
        return 1 if errors else 0
    if argv[1:] == ["estate"]:
        errors = check_files() or write_estate_pins()
        print("\n".join(errors) if errors else f"{ESTATE} pins re-derived from vendored.toml")
        return 1 if errors else 0
    if len(argv) != 1:
        print(__doc__)
        return 2
    errors = check()
    if errors:
        print("vendored packages are out of sync with vendored.toml:\n")
        print("\n".join(errors))
        return 1
    names = ", ".join(p["name"] for p in load(repo_root() / MANIFEST_NAME))
    print(f"OK: vendored packages match their pins ({names}).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
