# External grading provenance audit — 2026-10-11

Audited base: `ae62c494bb1f61ee088abaf2b4d5c24b2764a257` (PR #2).
No open corrective PR was found at the start of this audit.

## Findings and policy

`align_editions` carries the Nasāʾī cross-recension flag. Previously,
`alignment_table` retained it, but `grade_table` and the translation export
lost it and the latter retained only the score. The graph persists these tables
without enriching grading records. Existing graph analysis and NetworkX exports
use narrator/transmission/chain data, not external gradings. This audit found no
implemented propagation of these grades into narrator or source-report verdicts.
Raw table consumers can nevertheless misinterpret a linked attribution.

Keep all associations and original grader names, verdict strings, external
numbers and source IDs. Classify cross-recension links explicitly; exclude them
from default source-report grading queries until independently verified. A
collection code is not an edition identity. New builds carry the Arabic and
English upstream filename/revision identifiers separately, source book ID and
revision, and explicit Ṣughrā/Kubrā work labels for Nasāʾī. These identify the
builder's declared pinned inputs; they do not authenticate arbitrary replacement
files passed to `build`. Use the existing SHA-256-verified fetch workflow.

Every grading row and translation now carries the entry index, alignment score,
cross-recension flag, edition/source identities, alignment status, runner-up score,
margin, number of top-scoring candidates, textual relation, source-entry
multiplicity and `independently_verified=False`. No independent verification is
asserted by this correction. Multiple critics and external entries remain separate.
Unmatched external grades remain present with nullable `hadith_id` and status
`unmatched`; they cannot be returned by a source-report query.

`alignment_status` is `ambiguous` for tied top candidates, `plausible` for other
accepted associations, and `unmatched` otherwise. The deterministic lowest-ID
tie break remains unchanged. Diagnostics are relative to the existing candidate
retrieval using non-formulaic trigrams; candidates suppressed by `max_df` are
not examined. A nonzero runner-up margin does not prove uniqueness or accuracy.
Near ties can be screened by the query's `min_score_margin`; no calibrated
confidence threshold is claimed.

`text_relation=normalized_exact` means equality after the project's Arabic
normalizer. Otherwise an accepted association is `textual_correspondence`.
Neither normalized equality nor score 1 independently verifies a grading's
applicability to a different recension. Containment omits frequent trigrams from
candidate scoring, is asymmetric, and is not a probability of correctness.

## Guarded usage and compatibility

```python
# Conservative defaults: excludes cross-recension, ties and unknown provenance.
g.grades_of(hadith_id)
# Explicitly explore qualified associations, still returned with provenance.
g.grades_of(hadith_id, include_cross_recension=True, include_ambiguous=True)
# Screen small candidate margins; threshold is exploratory, not validated.
g.grades_of(hadith_id, min_score_margin=0.1)
```

The checked-in Parquet bundle remains byte-for-byte unchanged. It lacks the new
diagnostics, so `grades_of` fails closed with a rebuild instruction. Raw access
remains available. Rebuild graph and corpus using the pinned source fetch and
existing `isnad-graph build` / `isnad-graph corpus` commands. The full 1.6 GB
source database was not downloaded or rebuilt in this audit; new diagnostics
have been validated on miniature fixtures, not computed for the full corpus.

For legacy raw-table audits, join grades to alignments on **collection,
hadithnumber, hadith_id**, with `validate="many_to_one"`. Joining on hadith_id
alone creates a product among many external entries. Do not drop unmatched
rows or interpret them as ordinary edition associations.

## Reproducible committed-data evidence

Run `python tools/audit_grade_provenance.py` from the repository root. The saved
JSON alongside this note records the complete output against the audited bundle.
It checks report multiplicity, grading joins and strict versus non-strict order
using the independently stored source report numbers.

Nasāʾī has 4,305 alignment rows for 4,149 distinct reports. 305 external entries
participate in many-to-one associations. There are 12,827 linked cross-recension
grade attributions and 4,218 unmatched Nasāʾī grade attributions. No Nasāʾī
containment score is 1; median score is 0.6707. These numbers establish exposure
and uncertainty, not incorrect assignments. The source `books` table identifies
book 17 as «السنن الكبرى للنسائي», independently confirming the source-side
work identity. Order agreement and shared source positions are corroborating
structure, not independent textual verification.

## Remaining verification

Exact normalized matches, plausible textual correspondences and unresolved
recension differences must remain distinct. Full Arabic texts are not in the
committed graph. A defensible next textual audit needs the verified pinned source
texts and external editions, and comparison against a separately sourced edition
or scholarly cross-reference. Stratify by ties, small margins, many-to-one links,
order reversals and score bands. Compare isnad, matn, chapter, numbering and
critic attribution separately. Record verifier, evidence and edition identifiers
before changing any independent-verification status. Do not infer verification
from a strong score or re-label unmatched records as false matches.

Validation: focused synthetic cross-recension, many-to-one, tie, unmatched,
translation export, no-edition and legacy-query regressions; existing full test
suite and Ruff. No original attribution or accepted alignment is discarded.
