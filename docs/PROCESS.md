# Process: proof-driven development

Classical grading criteria take findings whose textual sources are cited.
Graph theorems concern recorded ranks, links and dates. Conformance checks
compare the implementations on exported cases. A claim about an actual
transmission requires evidence at the report and route level.

## The layers

| layer | where | checks | tool |
|---|---|---|---|
| definition | `formal/lean/Hadith/ClassicalCriteria.lean`, `formal/lean/IsnadFormal/*.lean` | the cited criteria and the graph’s observational inputs | — |
| theorem | the same files | consequences of the stated premises | Lean 4.34.1, core only |
| axiom audit | `formal/lean/Audit.lean` | no `sorry`; only `propext`, `Classical.choice`, `Quot.sound` | Lean |
| conformance | `formal/lean/Conformance.lean`, `formal/vectors/` | the Python verdicts, lifeline phases, common links and defect-lift statistics on the committed graph, and the chain inference and statistics on seeded cases, equal the Lean model's | Lean executable |
| process model | `formal/quint/transmission.qnt` | invariants over every reachable state of a transmission | Quint 0.33.0; Apalache 0.62.1 and the TLC it bundles (TLA+) |
| implementation | `src/isnad_graph/` | unit, property and regression tests | pytest |

## What is formalized

| Claim | Source or scope | Formal statement | Theorem |
|---|---|---|---|
| Intrinsic ṣaḥīḥ and ḥasan | Ibn al-Ṣalāḥ, first type, and Ibn Ḥajar, *Nukhba*, v04:p722 | `ClassicalCriteria.intrinsicGrade` | `intrinsic_sahih_iff`, `intrinsic_hasan_iff` |
| Sixth narrator rank | Ibn Ḥajar, *Taqrīb*, v01:p074 | `sixthRankStatus` | `sixth_rank_maqbul_iff`, `sixth_rank_layyin_iff` |
| Structural ṣaḥīḥ code and the rank-9 fallback | Graph score using the source’s rank scale | `Chain.verdict`, `rankVerdict`, `effRank` | `sahih_iff`, `rankVerdict_mono`, `unknown_not_sahih` |
| Effect of adding ranks and gap markers | Graph score | `Chain.append`, `structuralVerdict` | `append_no_better`, `gap_caps`, `gap_not_acceptable`, `mursal_not_sahih` |
| Presumption of hearing for ʿanʿana under specified conditions | Muslim, *Muqaddimat al-Ṣaḥīḥ*, pp. 29–33 | `MuslimAnanaFindings.Presumption` | `muslim_presumption_requires_review` |
| Dates at which both could be alive | Interval constraints | `muasara`, `withinBothLives` | `refuted_sound`, `unrefuted_complete`, `liqa_muasara`, `refuted_no_attested_meeting` |
| Explicit hearing from a known mudallis | al-Shāfiʿī, *al-Risāla*, p. 378 | `shafiiAccepts` | `shafii_requires_explicit`, `explicit_clears` |
| Flag for a known mudallis with ambiguous wording | Graph defect labeling | `tadlisDefect` | `tadlis_iff_ambiguous` |
| the graph's chronology verdict | `lifespan.feasibility` | `chronology` | `impossible_sound` |
| the lifeline window with minimum ages | `lives.lifeline` | `window_iff` | `window_iff` |
| the lifeline's phases | `lives.phases` | `phases` | `phases_partition` (tiling, maximality, pointwise soundness) |
| the common link lies on every chain of its bundle | Schacht, *Origins*, p. 172; Juynboll, *Muslim Tradition*, ch. 5 | `SingleStrand`, `strand`, `commonLink` | `strand_agrees`, `common_link_on_chain`; at δ ≥ 1 without repeats `strand_single`, `commonLink_on_chain` |
| TLC may check the transmission model over its critical years only | the region construction of timed automata (Alur and Dill, 1994), here over years | `Regions.same`, `inRegions`, `regionYears`, `Fm` | `reduction`, `perRegion_of_initial` |
| … for the model's own transition relation | `transmission.qnt`, transcribed (`Model.step`, `Model.Reach`) | `Model.Inv`, `St.map` | `Model.sim`, `Model.inv_map`, `Model.regions_iff`, `Model.Q.transmission_iff_regions`; `successors_step` |
| the defect lift: MH risk ratio, signed CMH score, exact conditional p | Mantel and Haenszel (1959); `docs/stratified-defect-inference.md` | `Table`, `tailLe`, `tailGe`, `pExact`, `score` | `pExact_swap`, `score_swap_pooled`, `var_swap`, `mh_swap`, `pExact_degenerate`, `degenerate_score`, `var_eq_zero_iff`, `pExact_pos`, `pExact_le`, `pExactFast_eq` |
| a chain is inferred from in-text names only when nothing is in doubt | `inference.infer_source_chain` | `infer`, `abstention`, `tahwil` | `infer_iff`, `infer_isSome_iff`, `tahwil_iff`, `infer_text_order`, `matn_ignored` |

The Quint model checks a synthetic process over time. A student names his
teacher explicitly (samāʿ) or ambiguously (ʿan), or the model records irsāl
by dropping that teacher. The process stipulates one mudallis. Its invariants
concern recorded paths and model hearings.

* `rootedAtSource`;
* `prefixClosed`: the isnads form a tree, as `CommonLink` assumes of a bundle;
* `ittisal`: every link a hearing with both alive, and every gap hides a real
  hearing from the dropped narrator;
* `chronologicalOrder`;
* `refutationSound`: no hearing between a refuted pair (`refuted_sound`);
* `weakestLink`: a student's isnad grades no better than his teacher's
  (`append_no_better`);
* `gapCaps`: a gap makes it ḍaʿīf or worse (`gap_caps`);
* `sahihExactly` characterizes the synthetic graph score by its gap and rank
  inputs (`sahih_iff`).
* `tadlisInherited` propagates a modeled ambiguous formula from a mudallis
  to chains through him (`tadlis_iff_ambiguous`).

Two model checkers check them. Apalache (SMT) checks every trace of
`transmission`, over every year, up to the pinned depth. TLC (explicit
state) searches every reachable state of `transmissionRegions`, the same
model over the critical years: the first four years of each region between
the thresholds the guards and invariants compare with. `Regions.reduction`
proves that formulas built from such comparisons keep their truth value
under the map onto those years, so the invariants hold in one model iff they
hold in the other. `Model.regions_iff` proves it for the transition relation
itself, transcribed from `transmission.qnt`, and for every invariant that reads
years only as `hearsAlive` and `chronological` do. The gate checks the
transcription three ways: Quint's constants and `REGIONS` are Lean's; 1,000
seeded simulation traces replay as `Model.step` runs (every kind of hearing
occurs); and Lean's region model reaches exactly the number of states TLC
finds (741,987). The replay shows Quint's steps are Lean's; the count, that
Lean adds none. Each hearing
adds a holder, so that search is complete at every depth: 741,987 distinct
states, depth 5.

The gate also checks non-vacuity: both the simulator and TLC must reach a
three-link isnad, a gap, a tadlīs defect and a ḥasan isnad, or the gate fails.

## The order of work

A change that touches a definition, a verdict or a dating rule goes through
these steps, each landing before the next:

1. **State the rule.** Write it in the Lean module doc with its classical
   source, and say what is out of scope.
2. **Formalize and prove.** Write the Lean definition and the theorems that
   characterize it. A theorem that fails to prove is a finding about the rule
   or the code. Two examples so far:
   * the window theorem needs non-negative ages;
   * an unranked narrator was graded ṣaḥīḥ, contradicting `unknown_not_sahih`.
3. **Make the implementation agree.** Write a failing pytest case from the
   theorem, then fix the code.
4. **Regenerate the vectors.** Run `python tools/export_vectors.py`.
   `tests/test_formal_vectors.py` fails until they are current.
5. **Model the process** when the change concerns time or order: add the
   invariant to `transmission.qnt` and a witness run.
6. **Run the gate**, `tools/verify.sh`. A push runs it anyway.

## Reproducibility

`formal/toolchain.toml` pins every toolchain:

* Lean: archive URL and sha256;
* Quint: exact version, with npm integrity hashes in `package-lock.json`, and
  the TypeScript evaluator, so nothing is downloaded at run time;
* Apalache: archive URL and sha256.

`tools/formal-setup.sh` installs exactly these, rejects a hash mismatch, and is
idempotent. All randomness is seeded:

* the Quint simulation uses seed `0x2a`;
* the vector selection is a pure function of the graph;
* Apalache's bounded check is exhaustive up to its step bound.

Verdicts must be identical whenever the gate is re-run on the same inputs.

## Hooks

`.claude/settings.json` registers two hooks.

* **SessionStart** (`.claude/hooks/session-start.sh`, cloud sessions):
  1. installs the Python package;
  2. installs the pinned toolchains;
  3. puts Lean on `PATH`;
  4. runs the quick gate (`tools/verify.sh --quick`: everything except pytest
     and Apalache).

  A red gate is reported, not hidden, and does not block the session that may
  fix it.
* **PreToolUse on `git push`** (`.claude/hooks/pre-push.sh`): runs the full
  gate and blocks the push if it fails.

CI runs the same script in the `formal` job.

Locally on x86_64 Linux, run `tools/formal-setup.sh` once, then
`tools/verify.sh`.
