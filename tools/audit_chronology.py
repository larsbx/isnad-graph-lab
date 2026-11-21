"""Audit impossible edge occurrences against the pinned source, with read-only replays.

Run from the repository root after installing the project in editable mode.
"""

from __future__ import annotations

import argparse
import json
import platform
import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import asdict
from math import isclose
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow
import scipy

from isnad_graph.assess import ACCEPTABLE, Defect, assess_chains, defect_lift, report_assessment
from isnad_graph.build import explode_links, marker_flags, reproduction
from isnad_graph.chains import Chain, normalize
from isnad_graph.chronology_audit import (
    COMPILER_REVIEWS,
    REVIEWABLE,
    UNRESOLVED,
    Cause,
    adjacent_evidence,
    alias_index,
    alternate_names,
    classify,
    compiler_matches,
    replay_assessment,
    report_exposure,
    source_prefix,
    usable_prefix,
)
from isnad_graph.inference import Mention, infer_source_chain
from isnad_graph.lifespan import feasibility, lifespans
from isnad_graph.schema import PROPHETIC_TYPES, Provenance
from isnad_graph.sigha import Mode
from isnad_graph.source import DEFAULT_PATH, HADITH_KG, connect, sha256

CHRONOLOGY = int(Defect.CHRONOLOGY)
KEY = ["src", "dst"]
REVIEW_KEY = ["hadith_id", "sanad_id", "depth", *KEY]
ROOT = Path(__file__).resolve().parents[1]
TABLES = ("transmissions", "chains", "narrators", "books", "hadiths", "external_grades")
BASE = "21f5fcc77c1f4e5f44ca9cc9fc28ef981dc3b8bb"
BASE_MANIFEST = "fa748593e8e3b7f2b25ff243253aaafec6d342fea7fe835c61a90a42aa5b2303"


def reviewed_cases(path: Path | None) -> dict:
    if path is None:
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw["source_sha256"] != HADITH_KG.sha256:
        raise ValueError("reviewed cases are pinned to a different source")
    indexed = {}
    for row in raw["cases"]:
        key = tuple(row[k] for k in REVIEW_KEY)
        if (
            key in indexed
            or Cause(row["cause"]) not in REVIEWABLE
            or not row["anchor"].strip()
            or not row["note"].strip()
            or not row["sources"]
        ):
            raise ValueError(f"invalid or duplicate review {key}")
        indexed[key] = row
    return indexed


def source_occurrences(
    con: sqlite3.Connection,
    hits: pd.DataFrame,
    chains: pd.DataFrame,
    narrators: pd.DataFrame,
    books: pd.DataFrame,
    cases: dict,
) -> Iterator[dict]:
    aliases = alias_index(narrators)
    compiler_ids = compiler_matches(books, narrators, aliases)
    markers = marker_flags(narrators)
    known = frozenset(narrators.id)
    chain_rows = chains.set_index("chain_id")
    used_cases = set()

    for hid, per_report in hits.groupby("hadith_id", sort=True):
        book, number, page, type_no, text, boundary = con.execute(
            "SELECT book_id,no_inbook,page_no,type_no,nass,matn_start FROM hadiths WHERE id=?",
            (int(hid),),
        ).fetchone()
        mentions = [
            Mention(*x)
            for x in con.execute(
                "SELECT rawi_id,start,end FROM hadith_rawis WHERE hadith_id=? ORDER BY seq",
                (int(hid),),
            )
        ]
        prefix = source_prefix(text, boundary, mentions)
        safe_prefix = usable_prefix(text, boundary, mentions)
        alternatives = alternate_names(text, prefix or (), aliases)
        for cid, per_chain in per_report.groupby("chain_id", sort=True):
            chain = chain_rows.loc[cid]
            inferred = chain.provenance == Provenance.INFERRED
            sanad = None if inferred else int(chain.sanad_id)
            if inferred:
                if (
                    pd.notna(chain.sanad_id)
                    or con.execute(
                        "SELECT 1 FROM sanads WHERE hadith_id=? LIMIT 1", (int(hid),)
                    ).fetchone()
                ):
                    raise ValueError(f"inferred chain {cid} has a source sanad")
                raw = infer_source_chain(mentions, boundary, text, known)
                pos0 = None
            else:
                recorded = con.execute(
                    """SELECT pos,rawi_id FROM sanad_rawis JOIN sanads ON id=sanad_id
                       WHERE sanad_id=? AND hadith_id=? ORDER BY pos""",
                    (sanad, int(hid)),
                ).fetchall()
                raw = tuple(rid for _, rid in recorded)
                pos0 = recorded[0][1] if recorded and recorded[0][0] == 0 else None
            normalized = normalize(raw, markers, type_no in PROPHETIC_TYPES) if raw else None
            stored = Chain(
                tuple(chain.path), tuple(chain.links), chain.head_gap, chain.tail_gap, chain.repeats
            )
            if normalized != stored or chain.book_id != book:
                raise ValueError(f"source replay differs on chain {cid}")
            for row in per_chain.itertuples(index=False):
                terminal = row.depth == len(stored.links) - 1
                raw_boundary = terminal and pos0 == row.dst
                author_boundary = terminal and compiler_ids.get(book) == row.dst
                evidence = adjacent_evidence(text, safe_prefix, row.dst, row.src)
                alt_src = sorted(alternatives.get(row.src, ()))
                alt_dst = sorted(alternatives.get(row.dst, ()))
                key = (hid, sanad, row.depth, row.src, row.dst)
                review = cases.get(key)
                reviewed = Cause(review["cause"]) if review else None
                if review:
                    acceptable_location = (
                        (reviewed not in COMPILER_REVIEWS or (raw_boundary and author_boundary))
                        and (reviewed != Cause.INFERRED_SPLICE or inferred)
                        and (
                            reviewed not in {Cause.DOCUMENTED_CONFLICT, Cause.RECORDED_SPLICE}
                            or not inferred
                        )
                    )
                    if row.flag or not acceptable_location or review["anchor"] not in text:
                        raise ValueError(f"review evidence no longer applies at {key}")
                    used_cases.add(key)
                cause = classify(
                    row.flag,
                    inferred,
                    author_boundary,
                    evidence,
                    bool(alt_src or alt_dst),
                    reviewed,
                )
                # Flagged pairs can still have names in the text. The proof of
                # a gap is the raw marker/normalized flag, even if it has a mode.
                yield {
                    "link_index": row.link_index,
                    "sanad_id": sanad,
                    "book_number": number,
                    "source_page": page,
                    "is_terminal": terminal,
                    "source_pos0_id": pos0,
                    "student_is_source_pos0": raw_boundary,
                    "book_author_match_id": compiler_ids.get(book),
                    "student_matches_book_author": author_boundary,
                    "matn_start": boundary,
                    "linear_spans_usable": bool(safe_prefix),
                    **asdict(evidence),
                    "alternate_src_ids": ";".join(map(str, alt_src)),
                    "alternate_dst_ids": ";".join(map(str, alt_dst)),
                    "cause": cause.value,
                    "review_anchor": review["anchor"] if review else "",
                    "review_note": review["note"] if review else "",
                }
    if used_cases != cases.keys():
        raise ValueError(
            f"review keys missing from the impossible population: "
            f"{sorted(cases.keys() - used_cases, key=repr)}"
        )


def chronology_links(links: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    impossible = edges[edges.chronology.eq("impossible")].copy()
    pairs = pd.MultiIndex.from_frame(links[KEY])
    hits = links.loc[pairs.isin(pd.MultiIndex.from_frame(impossible[KEY]))]
    hits = hits.rename_axis("link_index").reset_index()
    counts = hits.groupby(KEY).agg(
        n_links=("chain_id", "size"),
        n_chains=("chain_id", "nunique"),
        n_hadiths=("hadith_id", "nunique"),
        n_books=("book_id", "nunique"),
        n_recorded=("provenance", lambda x: x.eq(Provenance.RECORDED).sum()),
        n_inferred=("provenance", lambda x: x.eq(Provenance.INFERRED).sum()),
    )
    pd.testing.assert_frame_equal(
        counts, impossible.set_index(KEY)[list(counts)].sort_index(), check_dtype=False
    )
    return hits, impossible


def report_outputs(chains: pd.DataFrame, hadiths: pd.DataFrame) -> pd.DataFrame:
    return (
        hadiths[["id"]]
        .set_index("id")
        .join(report_assessment(chains))
        .rename_axis("hadith_id")
        .astype({"best_verdict": "Int8", "shared_defects": "Int16"})
    )


def records(frame: pd.DataFrame) -> list[dict]:
    return frame.astype(object).where(frame.notna(), None).to_dict("records")


def stats(
    chains: pd.DataFrame,
    reports: pd.DataFrame,
    grades: pd.DataFrame,
    hits: pd.DataFrame,
    mask: pd.Series,
) -> dict:
    flagged = hits[hits.link_index.map(mask)]
    chronology_rows = defect_lift(reports, grades, min_flagged=0, defects=(Defect.CHRONOLOGY,))
    expert = chronology_rows.assign(meets_original_threshold=chronology_rows.n_flagged.ge(20))
    return {
        "assessed_chains": len(chains),
        "recorded_assessed_chains": int(chains.provenance.eq(Provenance.RECORDED).sum()),
        "reports_with_chains": int(reports.best_verdict.notna().sum()),
        "structurally_acceptable_reports": int(reports.best_verdict.isin(ACCEPTABLE).sum()),
        "report_best_verdict": {
            str(int(k)): int(v) for k, v in reports.best_verdict.value_counts().sort_index().items()
        },
        "chronology_flagged_occurrences": len(flagged),
        "chronology_flagged_edges_with_any_occurrence": flagged.groupby(KEY).ngroups,
        "chronology_flagged_chains": int((chains.defects & CHRONOLOGY).ne(0).sum()),
        "reports_with_a_chronology_flagged_chain": int(flagged.hadith_id.nunique()),
        "reports_with_shared_chronology": int(
            (reports.shared_defects.fillna(0).astype(int) & CHRONOLOGY).ne(0).sum()
        ),
        "flags_by_provenance": flagged.provenance.value_counts().sort_index().to_dict(),
        "reproduction_of_source_verdicts": reproduction(chains),
        "expert_chronology_lift_all_sample_sizes": records(expert),
        "expert_other_defect_lift_original_threshold": records(
            defect_lift(reports, grades, defects=(Defect.TADLIS, Defect.TADLIS_WEAK))
        ),
    }


def chain_assessment_differences(chains, links, narrators, edges) -> pd.DataFrame:
    columns = ["worst_rank", "verdict", "defects"]
    recomputed = assess_chains(chains, links, narrators, edges).set_index("chain_id")[columns]
    committed = chains.set_index("chain_id")
    changes = committed[columns].fillna(-1).ne(recomputed.fillna(-1))
    if changes.defects.any():
        raise ValueError("current assessment code changes the committed defect flags")
    return (
        committed.loc[changes.any(axis=1), ["hadith_id", "sanad_id", "provenance", *columns]]
        .rename(columns={key: f"original_{key}" for key in columns})
        .join(recomputed.add_prefix("recomputed_"))
    )


def check_baseline(reports, hadiths, stats, manifest) -> None:
    saved = hadiths.set_index("id")[["best_verdict", "shared_defects"]].rename_axis("hadith_id")
    pd.testing.assert_frame_equal(reports, saved, check_dtype=False)
    if stats["reproduction_of_source_verdicts"] != manifest["reproduction_of_source_verdicts"]:
        raise ValueError("reproduction of source verdicts does not match the committed manifest")
    expected = {(r["grader"], r["defect"]): r for r in manifest["defect_lift"]}
    actual = {
        (r["grader"], r["defect"]): {k: v for k, v in r.items() if k != "meets_original_threshold"}
        for r in (
            stats["expert_chronology_lift_all_sample_sizes"]
            + stats["expert_other_defect_lift_original_threshold"]
        )
        if r.get("meets_original_threshold", True)
    }
    if expected.keys() != actual.keys():
        raise ValueError("defect lift did not reproduce the committed baseline cohort")
    for key, row in expected.items():
        for k, value in row.items():
            same = (
                isclose(value, actual[key][k], rel_tol=1e-12)
                if k == "p_exact" and value is not None
                else value == actual[key][k]
            )
            if not same:
                raise ValueError(f"defect lift mismatch on {key} {k}")


def write_outputs(out: Path, hits, edges, baseline, replay, exposure, drift, summary) -> None:
    out.mkdir(parents=True, exist_ok=True)
    hits.to_csv(out / "occurrences.csv", index=False)
    edges.to_csv(out / "edges.csv", index=False)
    drift.to_csv(out / "baseline_assessment_differences.csv")
    comparison = baseline.add_prefix("original_").join(replay.add_prefix("replay_")).join(exposure)
    comparison = comparison[
        comparison.original_best_verdict.ne(comparison.replay_best_verdict).where(
            comparison.original_best_verdict.notna(), comparison.replay_best_verdict.notna()
        )
        | comparison.original_shared_defects.fillna(-1).ne(
            comparison.replay_shared_defects.fillna(-1)
        )
        | comparison.chronology_exposure.isin(["documented_conflict", "unresolved"])
    ]
    comparison.to_csv(out / "affected_reports.csv")
    (out / "audit_manifest.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8"
    )


def load_reviews(review_file: Path | None, supplements: tuple[Path, ...]) -> dict:
    cases = reviewed_cases(review_file)
    for path in supplements:
        added = reviewed_cases(path)
        if cases.keys() & added.keys():
            raise ValueError(f"duplicate occurrence across review files: {path}")
        cases.update(added)
    return cases


def run(
    graph: Path,
    db: Path,
    review_file: Path | None,
    out: Path,
    *,
    supplements: tuple[Path, ...] = (),
) -> dict:
    manifest_path = graph / "manifest.json"
    manifest_digest = sha256(manifest_path)
    original = json.loads(manifest_path.read_text(encoding="utf-8"))
    if original["source"]["sha256"] != HADITH_KG.sha256 or sha256(db) != HADITH_KG.sha256:
        raise ValueError("source database digest does not match the committed graph")
    cases = load_reviews(review_file, supplements)
    edges, chains, narrators, books, hadiths, grades = (
        pd.read_parquet(graph / f"{name}.parquet") for name in TABLES
    )
    spans = lifespans(narrators)
    pd.testing.assert_frame_equal(narrators[list(spans)], spans, check_dtype=False)
    feasibility_result = feasibility(edges, spans)
    pd.testing.assert_series_equal(
        feasibility_result.chronology, edges.chronology, check_dtype=False
    )
    # All descriptions of date conflicts below use the existing interval rule.
    links = explode_links(chains)
    hits, impossible = chronology_links(links, edges)
    with closing(connect(db)) as con:
        evidence = pd.DataFrame(source_occurrences(con, hits, chains, narrators, books, cases))
    for key in ("sanad_id", "source_pos0_id", "book_author_match_id", "matn_start", "start", "end"):
        evidence[key] = evidence[key].astype("Int64")
    hits = hits.merge(evidence, on="link_index", validate="1:1")
    hits["mode_name"] = hits["mode"].map(lambda x: Mode(int(x)).name)
    by_cause = hits.groupby([*KEY, "cause"]).size().unstack(fill_value=0)
    by_cause = by_cause.rename(columns=lambda x: f"occurrences_{x}")
    edge_cause = by_cause.gt(0).apply(
        lambda row: (
            row.index[row][0].removeprefix("occurrences_")
            if row.sum() == 1
            else "mixed_occurrence_causes"
        ),
        axis=1,
    )
    edge_rows = impossible.join(by_cause.assign(edge_cause=edge_cause), on=KEY, validate="1:1")
    spans = narrators.set_index("id")
    columns = [
        "name",
        "nickname",
        "birth_year_raw",
        "death_year_raw",
        "age_raw",
        "birth_lo",
        "birth_hi",
        "death_lo",
        "death_hi",
        "birth_basis",
        "death_basis",
    ]
    for end in KEY:
        edge_rows = edge_rows.join(spans[columns].add_prefix(f"{end}_"), on=end)
    edge_rows["student_ever_chain_end"] = edge_rows.dst.map(spans.n_as_compiler).gt(0)
    edge_rows["ever_inferred"] = edge_rows.n_inferred.gt(0)
    edge_rows["only_one_chain"] = edge_rows.n_chains.eq(1)
    for key in ("is_terminal", "student_is_source_pos0", "student_matches_book_author"):
        seen = hits.groupby(KEY)[key].any()
        edge_rows = edge_rows.join(seen.rename(f"any_{key}"), on=KEY)
    edge_rows["student_born_after_teacher_death"] = (
        edge_rows.dst_birth_basis.isin(["recorded", "age"])
        & edge_rows.src_death_basis.eq("recorded")
        & edge_rows.dst_birth_lo.gt(edge_rows.src_death_hi)
    ).fillna(False)
    edge_rows["teacher_born_after_student_death"] = (
        edge_rows.src_birth_basis.isin(["recorded", "age"])
        & edge_rows.dst_death_basis.eq("recorded")
        & edge_rows.src_birth_lo.gt(edge_rows.dst_death_hi)
    ).fillna(False)
    if not (
        edge_rows.student_born_after_teacher_death | edge_rows.teacher_born_after_student_death
    ).all():
        raise ValueError("impossible edge has no documented strict inequality")

    grades = grades[~grades.collection.isin(original["assessment"]["defect_lift_excludes"])]
    drift = chain_assessment_differences(chains, links, narrators, edges)
    original_reports = report_outputs(chains, hadiths)
    base_mask = links.index.to_series().isin(hits.link_index)
    original_stats = stats(chains, original_reports, grades, hits, base_mask)
    check_baseline(original_reports, hadiths, original_stats, original["assessment"])

    replay, excluded, retained, added_gap = replay_assessment(chains, hits)
    hits["chain_excluded_from_replay"] = excluded
    hits["chronology_in_replay"] = retained
    hits["gap_flag_added_in_replay"] = added_gap
    mask = links.index.to_series().isin(hits.loc[retained, "link_index"])
    after = report_outputs(replay, hadiths)
    replay_stats = stats(replay, after, grades, hits, mask)

    confirmed = set(hits.loc[retained & hits.cause.eq(Cause.DOCUMENTED_CONFLICT), "chain_id"])
    exposure = report_exposure(replay, confirmed)
    complete = after.loc[exposure[exposure.ne("unresolved")].index].copy()
    # Here the comparison retains only adjudicated positives and reports with
    # some acceptable route clear of this screen, omitting unresolved exposures.
    confirmed_lift = defect_lift(complete, grades, min_flagged=0, defects=(Defect.CHRONOLOGY,))
    recorded = replay[replay.provenance.eq(Provenance.RECORDED)]
    recorded_mask = mask & links.provenance.eq(Provenance.RECORDED)
    recorded_stats = stats(recorded, report_outputs(recorded, hadiths), grades, hits, recorded_mask)

    categories = ["student_ever_chain_end", "ever_inferred", "only_one_chain"]
    intersections = (
        edge_rows.groupby(categories, observed=True).size().rename("edges").reset_index()
    )
    cause_counts = (
        hits.groupby("cause")
        .agg(
            occurrences=("link_index", "size"),
            chains=("chain_id", "nunique"),
            reports=("hadith_id", "nunique"),
            retained_chronology=("chronology_in_replay", "sum"),
        )
        .join(hits.groupby("cause")[KEY].apply(lambda x: len(x.drop_duplicates())).rename("edges"))
    )
    cause_by_provenance = pd.crosstab(hits.cause, hits.provenance).reset_index()
    crossed = (
        hits.groupby(["student_matches_book_author", "provenance"])
        .size()
        .rename("occurrences")
        .reset_index()
    )
    summary = {
        "schema_version": 1,
        "graph_base_revision": BASE if manifest_digest == BASE_MANIFEST else None,
        "input_sha256": {f"{name}.parquet": sha256(graph / f"{name}.parquet") for name in TABLES}
        | {
            "manifest.json": manifest_digest,
            "reviewed_cases": sha256(review_file) if review_file else None,
        },
        "runtime": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "pyarrow": pyarrow.__version__,
            "scipy": scipy.__version__,
        },
        "source": {k: original["source"][k] for k in ("repo", "revision", "sha256", "license")},
        "source_checks": {
            "replayed_chains": int(hits.chain_id.nunique()),
            "exact_recomputed_defect_masks": len(chains),
            "recomputed_rank_or_verdict_differences": len(drift),
            "recomputed_verdict_differences": int(
                drift.original_verdict.ne(drift.recomputed_verdict).sum()
            ),
            "rank_or_verdict_differences_on_chronology_chains": int(
                drift.index.isin(hits.chain_id).sum()
            ),
            "exact_committed_report_assessments": len(hadiths),
            "recomputed_interval_feasibility_edges": len(edges),
            "exact_expert_lift_rows_at_published_threshold": len(
                original["assessment"]["defect_lift"]
            ),
        },
        "excluded_grade_collections": original["assessment"]["defect_lift_excludes"],
        "population": {
            "all_edges": len(edges),
            "all_link_occurrences": len(links),
            "impossible_edges": len(impossible),
            "impossible_occurrences": len(hits),
            "edges_by_impossible_strict_inequality": {
                k: int(edge_rows[k].sum())
                for k in ("student_born_after_teacher_death", "teacher_born_after_student_death")
            },
            "edge_descriptor_counts": {
                k: int(edge_rows[k].sum())
                for k in [
                    *categories,
                    "any_is_terminal",
                    "any_student_is_source_pos0",
                    "any_student_matches_book_author",
                ]
            },
            "edges_only_inferred": int(edge_rows.n_recorded.eq(0).sum()),
            "edges_mixed_recorded_inferred": int(
                (edge_rows.n_recorded.gt(0) & edge_rows.ever_inferred).sum()
            ),
            "edges_absolute_death_gap_over_150": int(edge_rows.death_gap.abs().gt(150).sum()),
            "edge_descriptor_intersections": intersections.to_dict("records"),
            "compiler_author_and_provenance_occurrences": crossed.to_dict("records"),
        },
        "occurrence_causes": cause_counts.reset_index().to_dict("records"),
        "occurrence_causes_by_provenance": cause_by_provenance.to_dict("records"),
        "edge_causes": edge_rows.edge_cause.value_counts().sort_index().to_dict(),
        "unresolved": {
            "occurrences": int(hits.cause.isin(UNRESOLVED).sum()),
            "edges_with_unresolved_occurrence": hits.loc[hits.cause.isin(UNRESOLVED)]
            .groupby(KEY)
            .ngroups,
        },
        "reviewed_cases": list(cases.values()),
        "original": original_stats,
        "evidence_adjusted_replay": replay_stats
        | {
            "excluded_chains": int(hits.loc[excluded, "chain_id"].nunique()),
            "reports_losing_all_assessed_routes": int(
                (original_reports.best_verdict.notna() & after.best_verdict.isna()).sum()
            ),
            "reports_changing_best_verdict_with_routes": int(
                (
                    after.best_verdict.notna()
                    & original_reports.best_verdict.ne(after.best_verdict)
                ).sum()
            ),
        },
        "recorded_only_after_evidence_adjustment": recorded_stats,
        "confirmed_exposure_comparison": {
            "acceptable_reports_by_exposure": exposure.value_counts().sort_index().to_dict(),
            "expert_chronology_lift_all_sample_sizes": records(confirmed_lift),
        },
    }
    if supplements:
        summary["supplemental_reviews"] = [
            {"filename": path.name, "sha256": sha256(path)} for path in supplements
        ]
    write_outputs(out, hits, edge_rows, original_reports, after, exposure, drift, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=ROOT / "data/graph")
    parser.add_argument("--db", type=Path, default=ROOT / DEFAULT_PATH)
    parser.add_argument("--reviews", type=Path, default=ROOT / "docs/chronology-audit-cases.json")
    parser.add_argument("--supplemental-reviews", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    graph, out = args.graph.resolve(), args.out.resolve()
    if out.is_relative_to(graph):
        parser.error("--out must be outside the committed graph directory")
    result = run(graph, args.db, args.reviews, out, supplements=tuple(args.supplemental_reviews))
    print(json.dumps(result["population"], indent=2))


if __name__ == "__main__":
    main()
