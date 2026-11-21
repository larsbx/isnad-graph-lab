"""Compare the committed biographies to the pinned MuslimScholars CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from isnad_graph.biography_audit import (
    PROVISIONAL,
    agreement_rows,
    compare_records,
    make_linkage,
    relation_evidence,
    sample_matches,
    score_review,
)
from isnad_graph.source import sha256

SOURCE_REVISION = "1"
SOURCE_URL = (
    "https://api.kaggle.com/v1/datasets/download/"
    f"fahd09/hadith-narrators?datasetVersionNumber={SOURCE_REVISION}"
)
SOURCE_SHA256 = "d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11"
GRAPH = Path(__file__).resolve().parents[1] / "data" / "graph"


def edge_evidence(
    edges: pd.DataFrame, links: pd.DataFrame, comparisons: pd.DataFrame
) -> pd.DataFrame:
    annotated = edges.loc[
        edges.chronology.eq("impossible"), ["src", "dst", "n_links", "n_recorded", "n_inferred"]
    ].copy()
    endpoints = links.set_index("rawi_id")[["status", "scholar_indx", "candidate_ids"]].join(
        comparisons.set_index("rawi_id")[
            ["death_abs_difference", "city_overlap", "companion_agrees", "corroborating_neighbours"]
        ]
    )
    for side in ("src", "dst"):
        annotated = annotated.join(endpoints.add_prefix(side + "_"), on=side, validate="m:1")
    review_statuses = {"ambiguous_exact_candidates", "underspecified_exact_candidate"}
    annotated["context_for_review"] = (
        annotated.src_status.isin(review_statuses)
        | annotated.dst_status.isin(review_statuses)
        | annotated.src_death_abs_difference.gt(10).fillna(False)
        | annotated.dst_death_abs_difference.gt(10).fillna(False)
        | annotated.src_companion_agrees.eq(False).fillna(False)
        | annotated.dst_companion_agrees.eq(False).fillna(False)
    )
    return annotated


def run(source_csv: Path, graph: Path, out: Path, review_path: Path | None = None) -> dict:
    if sha256(source_csv) != SOURCE_SHA256:
        raise ValueError("MuslimScholars CSV differs from the pinned Kaggle version")
    inputs = {name: graph / f"{name}.parquet" for name in ("narrators", "transmissions")}
    narrators, edges = (pd.read_parquet(path) for path in inputs.values())
    external = pd.read_csv(source_csv, keep_default_na=False, dtype={"scholar_indx": "int64"})
    linkage = make_linkage(narrators, external)
    comparisons = agreement_rows(linkage, narrators, external)
    comparisons["corroborating_neighbours"] = (
        comparisons.rawi_id.map(relation_evidence(edges, comparisons, external))
        .fillna(0)
        .astype(int)
    )
    impossible = edge_evidence(edges, linkage, comparisons)
    endpoint_ids = set(impossible.src) | set(impossible.dst)
    endpoint_comparisons = comparisons[comparisons.rawi_id.isin(endpoint_ids)]
    sample = sample_matches(comparisons)
    review = pd.read_csv(review_path, keep_default_na=False) if review_path else sample.iloc[:0]
    receipt = {
        "schema_version": 1,
        "source": {
            "dataset": "fahd09/hadith-narrators",
            "revision": SOURCE_REVISION,
            "filename": "all_rawis.csv",
            "url": SOURCE_URL,
            "license_label": "CC0 on Kaggle",
            "sha256": SOURCE_SHA256,
            "rows": len(external),
        },
        "graph_sha256": {path.name: sha256(path) for path in inputs.values()},
        "linkage": linkage.status.value_counts().sort_index().to_dict(),
        "provisional_pairs": compare_records(comparisons),
        "impossible_edge_endpoint_pairs": compare_records(endpoint_comparisons),
        "impossible_edges": {
            "count": len(impossible),
            "unique_endpoints": len(endpoint_ids),
            "both_provisional": int(
                (
                    impossible.src_status.eq(PROVISIONAL) & impossible.dst_status.eq(PROVISIONAL)
                ).sum()
            ),
            "any_provisional": int(
                (
                    impossible.src_status.eq(PROVISIONAL) | impossible.dst_status.eq(PROVISIONAL)
                ).sum()
            ),
            "with_biography_review_lead": int(impossible.context_for_review.sum()),
        },
        "review_sample": score_review(sample, review),
        "review_sha256": sha256(review_path) if review_path else None,
    }

    out.mkdir(parents=True, exist_ok=True)
    linkage.to_csv(out / "narrator_linkage.csv", index=False)
    comparisons.to_csv(out / "provisional_comparisons.csv", index=False)
    impossible.to_csv(out / "impossible_edge_biographies.csv", index=False)
    sample.to_csv(out / "identity_review_sample.csv", index=False)
    (out / "biography_manifest.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--review-csv", type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.is_relative_to(args.graph.resolve()):
        parser.error("--out must be outside the committed graph directory")
    print(json.dumps(run(args.source_csv, args.graph, out, args.review_csv), indent=2))


if __name__ == "__main__":
    main()
