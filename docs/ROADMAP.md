# Roadmap

What is built, what is known to be wrong or weak, and what comes next, in
priority order. Each open item has the evidence that motivates it and an
acceptance criterion: what must be true for it to be closed.

The priority levels are:

- **P0**: a published number may be wrong;
- **P1**: an assumption the model rests on is untested;
- **P2**: coverage, presentation, infrastructure.

All figures are from `data/graph` as built at the head of the branch that
introduced this file.

## Done

| milestone | PR | what it delivers |
|---|---|---|
| Annotated isnad graph | #1 | narrators, transmissions, chains (recorded + inferred), invariants |
| Corpus and external editions | #2 | Arabic texts, translations, 7 aligned editions with modern gradings, transmission modes |
| Assessment and CI | #4 | structural verdicts, defects, defect lift vs expert graders, CI |
| Common-link statistics | #5 | CMH score and exact p for defect lift |
| Visualization | #6 | vendored math-vizops core, typed-graph export, Isnad Atlas page |
| Grade provenance | #3 | cross-recension and edition identity on every grading row |
| Time and place | #7 | the parts listed below |

The time-and-place milestone (#7) consists of:

- lifespan intervals and edge feasibility (`lifespan.py`);
- al-Thurayya geocoding (`geo.py`) and per-century flows (`history.py`);
- the Isnad Chronicle page, with its map context (`basemap.py`) and narrator
  lifelines (`lives.py`);
- the literature survey (`docs/secondary-literature.md`).

## P0: correctness of published numbers

### P0.1 Diagnose the "impossible" links

**Evidence.** Of 14,194 links whose documented lifespans cannot meet:

- 95% have a book compiler as the student;
- 51% come from the inferred chains;
- 68% rest on a single chain.

That pattern points to compiler identification, an unmarked taʿlīq, or a
misread inferred chain, not to chronology. These links raise the `CHRONOLOGY`
defect, which feeds the structural verdicts and the defect lift.

**Work.**

- Classify each impossible link by cause: compiler link, inferred link,
  identity collision (the next item), or a genuine date conflict.
- Treat a compiler link the source does not connect as a gap (taʿlīq), not a
  transmission.

**Done when** every impossible link has a cause class, the classes are in
the manifest, and the `CHRONOLOGY` defect counts only genuine conflicts. The
reproduction and defect-lift figures are then re-reported.

### P0.2 A second source for dates and places, and identity errors

**Evidence.** 36% of impossible links have deaths more than 150 years apart,
which no lifespan explains: a homonym or a mis-linked narrator. The source's
`death_year` and `iqama` have never been compared with an independent record.

**Work.**

- Link the CC0 muslimscholars narrator set (Kaggle, about 24k narrators) by
  name, kunya, nisba, generation and death year, following Wirahman 2026.
- Report agreement rates for death year (exact, ±2, ±10) and residence.
- List the links whose endpoint identities disagree between the sources.

**Done when** there is a pinned, tested linkage table with precision measured
on a hand-checked sample of at least 200, and disagreement rates are in the
manifest.

### P0.3 Lifeline phases that discriminate

**Evidence.** In 86% of the 300 embedded lifelines, the "hearing and teaching
both possible" phase covers more than 70% of the life. Each phase is the union
of all link windows, so one long-lived peer stretches it across the life.

**Work.** Define each phase from the chain-weighted 10th–90th percentile of
link years, and keep the union only as a faint outer bound.

**Done when** the share of lifelines dominated by "both" is reported, and a
test shows a narrator with a late-starting teaching career getting a distinct
teaching-only stretch.

### P0.4 Show estimated births as estimates

**Evidence.** 121 of the 300 lifelines (40%) take their birth from the prior,
death minus 80. Their stop years and phase boundaries inherit that assumption,
but they are drawn exactly like recorded dates.

**Work.**

- Draw prior-based stretches hatched.
- Carry the window interval of each stop through to the page, not only its
  midpoint.
- Label the birth basis on every lifeline.

**Done when** no estimated quantity on the page is drawn the same way as a
recorded one.

## P1: assumptions to test

### P1.1 Where a hearing happened

**Evidence.** A stop sits at the other narrator's home (`iqama`), which is the
place the record says they lived, not where a given hearing happened.
Companions are placed where they settled after the conquests.

**Work.**

- Flag narrators with more than one recorded residence.
- Use the death place as a late-life anchor.
- Show a stop's alternative places.

**Done when** the multi-residence share is reported, and stops for such
narrators show their alternatives.

### P1.2 Sensitivity to the constants

**Evidence.**

- `A_TEACH = 20` is a modelling choice; 8.5% of lifeline links cannot be placed
  under it.
- `L_MAX = 120`, `TYPICAL_LIFE = 80` and the 95% tabaqa interval each move
  verdicts.

**Work.** Re-run with A_TEACH ∈ {15, 20, 30, 40}, L_MAX ∈ {100, 120, 140} and
coverage ∈ {0.9, 0.95, 0.99}, and tabulate the verdict counts and the
unplaced share.

**Done when** a sensitivity table is in `docs/` and the README cites which
conclusions are robust to it.

### P1.3 Check the tabaqa-imputed deaths

**Evidence.** About 27k narrators get a death interval from their tabaqa, and
the `implausible` verdict depends on it. Its coverage has not been measured.

**Work.** Hide each recorded death in turn, impute it from the tabaqa, and
measure how often the true year falls inside the interval, per tabaqa.

**Done when** empirical coverage is reported per tabaqa and is ≥ 0.9 for the
tabaqat in use. Otherwise the interval is widened.

### P1.4 Province-level places

**Evidence.** 7.5% of lifeline stops, and all province-only homes, sit at a
province centroid.

**Work.**

- Draw centroids distinctly on the map and on lifelines.
- Exclude them from distance and same-city figures, or report both with and
  without them.

**Done when** both are reported.

### P1.5 First-century distances

**Evidence.** The 1st-century chain-weighted median distance (344 km) places
companions at the homes they settled in after the conquests.

**Work.** Report it with and without Prophet → companion links.

## P2: coverage, presentation, infrastructure

| item | what is wrong now | how |
|---|---|---|
| P2.1 Lifelines for every placed narrator | only the 300 most-cited are embedded | per-narrator JSON published beside the page, loaded on demand |
| P2.2 Label layout on lifelines | stop labels collide in dense clusters | label placement by collision avoidance; leader lines |
| P2.3 Page reproducibility in CI | nothing checks that the Atlas and Chronicle rebuild from the committed graph | CI fetches the pinned basemap and builds both pages, checking their stamps |
| P2.4 Route-network distances | distances are great-circle | travel days over al-Thurayya `routes.json` (about 30 km per stage) |
| P2.5 Comparison with Sanadset | chains have one source | align Sanadset 650K (CC BY 4.0) chains to measure agreement of `chains` |
| P2.6 Quantitative comparison with the literature | comparison is qualitative (`docs/secondary-literature.md`) | reproduce Romanov's regional curves and Bulliet's age structure where the data allow |
