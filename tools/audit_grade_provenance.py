"""Reproduce the committed-bundle provenance audit without downloading source texts."""
import argparse
import json
from itertools import pairwise
from pathlib import Path

import pandas as pd

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", nargs="?", type=Path, default=Path("data/graph"))
args = parser.parse_args()
a = pd.read_parquet(args.directory / "alignments.parquet")
g = pd.read_parquet(args.directory / "external_grades.parquet")
h = pd.read_parquet(args.directory / "hadiths.parquet")
# Never join on hadith_id alone: one source report can represent multiple edition entries.
joined = g.merge(a[["collection", "hadithnumber", "hadith_id", "cross_recension"]],
                 on=["collection", "hadithnumber", "hadith_id"], how="left",
                 validate="many_to_one", suffixes=("_grade", ""), indicator=True)
results = {}
for collection, frame in a.groupby("collection", sort=True):
    ordered = frame.assign(number=pd.to_numeric(frame.hadithnumber)).sort_values("number")
    positions = ordered.merge(h[["id", "no_inbook"]], left_on="hadith_id", right_on="id",
                              how="left", validate="many_to_one").no_inbook.tolist()
    steps = list(pairwise(positions))
    grades = joined[joined.collection.eq(collection)]
    results[collection] = {
        "alignments": len(frame), "distinct_source_reports": frame.hadith_id.nunique(),
        "entries_in_many_to_one": int(frame.hadith_id.duplicated(keep=False).sum()),
        "score_one": int(frame.score.eq(1).sum()),
        "median_score": float(frame.score.median()),
        "equal_source_positions": sum(x == y for x, y in steps),
        "strict_order_share": sum(y > x for x, y in steps) / max(len(steps), 1),
        "non_strict_order_share": sum(y >= x for x, y in steps) / max(len(steps), 1),
        "cross_recension_grade_attributions": int(grades.cross_recension.eq(True).sum()),
        "unmatched_grade_attributions": int(grades._merge.eq("left_only").sum()),
    }
print(json.dumps(results, indent=2))
