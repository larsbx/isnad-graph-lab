"""The vendored packages are upstream's bytes, every file pinned (vendored.toml)."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "check_vendored_sync", ROOT / "vendor/python/vendoring/check_vendored_sync.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_every_vendored_file_matches_its_pin():
    assert checker.check(ROOT) == []


def test_vizops_is_imported_from_the_pinned_copy():
    import vizops.figure

    pinned = ROOT / "vendor/python/vizops/figure.py"
    assert Path(vizops.figure.__file__).resolve() == pinned.resolve()


def test_a_patched_vendored_file_is_caught(tmp_path):
    import shutil

    shutil.copy(ROOT / "vendored.toml", tmp_path / "vendored.toml")
    shutil.copytree(ROOT / "vendor", tmp_path / "vendor")
    target = tmp_path / "vendor/python/vizops/palette.py"
    target.write_text(target.read_text() + "\n# a local patch\n")
    assert any("palette.py differs" in e for e in checker.check(tmp_path))
