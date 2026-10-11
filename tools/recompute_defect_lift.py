"""Recompute only defect comparisons from committed graph, preserving source tables."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from isnad_graph.assess import defect_lift

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/graph"
manifest_path = DATA / "manifest.json"
manifest = json.loads(manifest_path.read_text())
old = manifest["assessment"]["defect_lift"]
hadiths = pd.read_parquet(DATA / "hadiths.parquet")
reports = hadiths.set_index("id")[["best_verdict", "shared_defects"]]
grades = pd.read_parquet(DATA / "external_grades.parquet")
excluded = manifest["assessment"]["defect_lift_excludes"]
new = defect_lift(reports, grades[~grades.collection.isin(excluded)]).to_dict("records")
# Counts, rates and MH estimates must match; inference alone is corrected.
for before, after in zip(old, new, strict=True):
    for key, value in before.items():
        if key != "z":
            assert after[key] == value, (key, before, after)
manifest["assessment"]["defect_lift"] = new
manifest["assessment"]["defect_lift_inference"] = {
    "score": "signed uncorrected CMH, conditional on structural-verdict strata",
    "p_value": "exact conditional, twice smaller inclusive tail",
    "rates": "descriptive marginal rejection proportions",
}
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
audit = {"source": manifest["source"], "excluded_collections": excluded,
         "input_sha256": {name: hashlib.sha256((DATA / name).read_bytes()).hexdigest()
                          for name in ("hadiths.parquet", "external_grades.parquet")},
         "previous": old, "corrected": new}
(ROOT / "docs/defect-inference-audit.json").write_text(
    json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
print(pd.DataFrame(new).drop(columns="strata").to_string(index=False))
