# Chronology audit of the isnād graph

21 November 2026 · Graph revision `21f5fcc77c1f4e5f44ca9cc9fc28ef981dc3b8bb`

The committed graph reproduces **14,194 impossible edges** across **52,102 link occurrences**. The evidence-adjusted replay reduces the number of chains carrying `CHRONOLOGY` from **49,245 to 29,021**. Reports where every structurally acceptable route carries the flag fall from **14,276 to 14,243**. The replay retains the legacy flag on 31,175 unresolved occurrences for comparability. One reviewed occurrence has a corroborated date conflict. The unresolved population leaves P0.1 open. [Roadmap](ROADMAP.md)

## Population

| Descriptor | Impossible edges | Share |
|---|---:|---:|
| Student ends any chain in the whole graph | 13,525 | 95.29% |
| Pair actually occurs at the end of at least one chain | 6,310 | 44.46% |
| Pair actually ends at the source’s raw position 0 in at least one recorded sanad | 2,926 | 20.61% |
| Terminal student matches the book author in at least one occurrence | 759 | 5.35% |
| Any inferred occurrence | 7,249 | 51.07% |
| Inferred occurrences only | 6,408 | 45.15% |
| One chain only | 9,693 | 68.29% |
| Absolute difference between point death years exceeds 150 AH years | 5,042 | 35.52% |

The roadmap’s rounded 95%, 51% and 68% reproduce using the first, fifth and seventh rows. The author match requires a unique normalized name or nickname and a matching recorded death year. It matches 98 of the 425 book records. Short author titles are one limit on coverage. `books.author_no` and `rawis.id` are separate source ID spaces. A raw position-0 narrator can be the first narrator in a segment. The per-book check uses the named author of that specific book. The manifest gives the full intersections of the three roadmap descriptors. 20,885 occurrences already carry a gap flag. The 52,102 occurrences represent 1.14% of 4,554,366 chain links. At edge level the denominator is 330,628, giving 4.29%. [Chain construction](../src/isnad_graph/build.py) · [Pinned source artifacts](https://huggingface.co/datasets/emadjumaah/hadith-kg)

The lifespan screen uses **both** strict inequalities. The student is born after the teacher’s latest recorded death on 13,620 edges. The teacher is born after the student's latest recorded death on 574 edges. “Documented” here includes a birth bound calculated from a recorded death and a recorded age. It describes the bounds the graph used. The witness columns preserve both directions, the dates and their bases. [Feasibility implementation](../src/isnad_graph/lifespan.py)

## Occurrence classes

| Evidence | Recorded occurrences | Inferred occurrences | Edges with this class |
|---|---:|---:|---:|
| Gap encoded in the source | 18,700 | 96 | 1,495 |
| Taʿlīq encoded in the source | 2,089 | 0 | 1,062 |
| Reviewed compiler suspension | 2 | 0 | 2 |
| Compiler chain cut by segmentation | 1 | 0 | 1 |
| Reviewed compiler’s written citation | 1 | 0 | 1 |
| Inferred pair with an explicit indirect formula | 0 | 24 | 17 |
| Co-narrators joined by inference | 0 | 3 | 3 |
| Reviewed inference splice | 0 | 7 | 6 |
| Reviewed name/identity mismatch | 1 | 0 | 1 |
| Reviewed biographical-date discrepancy | 2 | 0 | 1 |
| Corroborated documented conflict, scoped to one route | 1 | 0 | 1 |
| Possible identity collision | 2,345 | 464 | 993 |
| Suspected compiler boundary, connection unresolved | 385 | 23 | 225 |
| Inferred connection, cause unresolved | 0 | 13,934 | 6,984 |
| Direct wording and disjoint recorded dates, historical inputs unresolved | 2,055 | 0 | 1,013 |
| Other unresolved occurrence | 11,969 | 0 | 4,347 |

Each occurrence is keyed by report, chain and link depth. The audit replays the raw sanad or the mention inference before assigning a class. The co-narrator rule requires a receiving verb, an adjacent pair and a dual speaking verb that introduces their common teacher. The indirect-formula rule requires an explicit phrase such as “it reached me that”, or the vocalized passive “I was told”. Ambiguous syntax, a receiving verb inside a name span, repeated endpoints or a route switch can cause abstention. The review case file binds individual exceptions to Arabic anchors in the pinned source, and the occurrence table retains offsets and formula witnesses.

Classes can coexist on an aggregated edge. 1,556 edges have mixed occurrence causes. 31,175 occurrences on 12,399 edges remain unresolved. Name matches are triage leads. Death gaps, infrequent appearance, a final position elsewhere and an unread formula carry no independent finding of artifact. 1,223 already-marked suspensions sit at a strictly matched book author boundary.

### Reviewed examples

| Corpus locator | Evidence and interpretation |
|---|---|
| Al-Dāraquṭnī, reports 115003 and 115004, sanads 149999 and 150001 | The printed sequence quotes al-ʿAlāʾ and al-Zuhrī in third person, with separate connected reports around the citations. The KG supplied unflagged links from both men to the compiler. The replay adds **TALIQ** to these two occurrences. In 115003 another acceptable route survives. In 115004 the added gap caps the only route at ḍaʿīf. [Printed edition, p. 263](https://ablibrary.net/book_content/b/5099/263?lang=ar) |
| Al-Ḥākim, reports 80433–80434, sanad 100884 | The segmented report begins with al-Wāqidī. The prior KG row and the continuous printed entry 6716 supply the chain from al-Ḥākim through Ibn Baṭṭa, al-Ḥasan b. al-Jahm and al-Ḥusayn b. al-Faraj. The replay omits the cut route pending reconstruction of its prefix. [Printed edition, vol. 4, entry 6716](https://www.cia.gov/library/abbottabad-compound/FB/FBC885B7AE55FB4581F988B4F7E8D33Bvol4.pdf) |
| Al-Khaṭīb al-Baghdādī, report 571218, sanad 484857 | The compiler identifies Ibn al-Furāt's handwritten book as his source. Its use is compatible with the compiler's birth eight years after the writer's death. This occurrence leaves the direct-contact screen as a written citation. [Printed edition, p. 109](https://ablibrary.net/book_content/b/5912/109?lang=ar) |
| Al-Bukhārī, report 5659, inferred chain 7399 | The text includes Abū Usāma and al-Aʿmash between Isḥāq and Shaqīq. The linked mentions omit them and inference creates the direct pair. [Ṣaḥīḥ al-Bukhārī 6097](https://sunnah.com/bukhari:6097) |
| Ibn ʿAsākir, report 576029, inferred chain 583913 | The linked endpoint spans are 241 and 379 characters, and each contains several names and receiving verbs. Treating either as a single name creates a spurious adjacency. The audit abstains from the local formula rule on such spans and the case review records the splice. See the pinned SQLite report and its linked mention spans 162–403 and 406–785. |
| Al-Tirmidhī, report 14393, inferred chain 25668 | Qatāda says he **was told** what Abū Hurayra said, leaving the intermediary unnamed. The source stored consecutive mentions. The replay models the gap as **INQITA**, which also changes how this report enters the grader comparison. [Jāmiʿ al-Tirmidhī 2070](https://sunnah.com/tirmidhi:2070) |
| Mālik's *Muwaṭṭaʾ*, reports 34395, 34621, 35196, 35763 and 35862 | The linked names identify participants in events. For example, report 35763 identifies ʿUmar as the recipient of a theft complaint, inside the account related by Yaḥyā b. ʿAbd al-Raḥmān b. Ḥāṭib. These five source readings were reviewed to trace the original al-Hilālī comparison. [Al-Suyūṭī’s commentary, report 1468](https://thahabi.org/book/13713/read/762) |
| Ibn ʿAsākir, report 587927, sanad 499022 | The text names ʿAbd al-Raḥmān, while the linked biography and stored sanad name ʿAbd al-Raḥīm (rawi 75503). Related Ibn ʿAsākir passages use al-Ḥaddād as an intermediary between ʿAbd al-Raḥīm and Abū Nuʿaym. The spelling, identity and route need resolution together. The replay omits this route. [Parallel usage in Tārīkh Dimashq](https://islamport.com/l/trj/4962/25250.htm) |
| Al-Ḍiyāʾ, report 93450, sanad 126793 | The printed name matches the nickname of candidate ID 29543. The committed record has a differently spelled nickname and also includes the printed spelling among its nisbas. ID 29543’s dates could overlap Tamīm (ID 13215). Adopting that ID would create a conflict with the preceding teacher (ID 28230, d. 376 AH). The lexically suggested substitution remains unresolved. See the pinned SQLite rows for report 93450 and rawis 29539, 29543, 13215 and 28230. |
| Abū Dāwūd, report 17653, sanads 29441 and 29442 | The graph gives Abū al-Yasar a birth year of 35 AH. Al-Mizzī identifies the same Kaʿb b. ʿAmr al-Sulamī as twenty years old at Badr. The replay omits those occurrences with their disputed date; adopting a replacement year would be a separate biographical correction. [Tahdhīb al-Kamāl, entry 4978](https://sunna.alifta.gov.sa/BookToc/ViewServicePage?bookId=48&mainId=452909) · [Route in Sunan Abī Dāwūd](https://dorar.net/h/Oi9aaXzc/osoul) |
| Ibn Mājah, report 27690, sanad 41819 | The printed route places Muḥammad b. Yaḥyā b. Ḥabbān (b. 47 AH) immediately after ʿAbd Allāh b. Salām (d. 43 AH) in transmission order, using *ʿan*. Direct contact is incompatible with those biographies. The adjacent printed variant names Yūsuf b. ʿAbd Allāh b. Salām as an intermediary. The confirmed conflict stays scoped to the first route. [Ibn Mājah 1095 and variant](https://bayan.alwa7i.com/hadith/sunan-ibn-majah/1102) · [Ibn Ḥabbān's biography](https://islamweb.net/ar/library/content/60/772/%D9%85%D8%AD%D9%85%D8%AF-%D8%A8%D9%86-%D9%8A%D8%AD%D9%8A%D9%89) · [Ibn Salām's biography](https://islamweb.net/ar/library/index.php?ID=218&bk_no=60&flag=1&page=bookcontents) |


## Assessment and grader comparisons

The original replay starts from the committed assessments. The evidence-adjusted replay clears the direct-contact `CHRONOLOGY` bit on source-marked gaps, adds the evidenced gaps on unmarked occurrences, and omits routes with a reviewed ambiguity or parsing error that needs reconstruction. The recorded-only sensitivity uses the remaining recorded routes. Retained unreviewed direct links keep their original flag in these two replays. The confirmed-exposure analysis counts a report as exposed when every acceptable retained route contains a corroborated conflict. It excludes reports whose exposure is unresolved and uses reports with an unflagged acceptable route as the comparison group. A report with no acceptable route is outside the exposure comparison.

| Metric | Committed | Evidence-adjusted | Evidence-adjusted, recorded routes only |
|---|---:|---:|---:|
| Assessed routes | 696,953 | 696,939 | 577,020 |
| Reports with an assessed route | 523,297 | 523,285 | 403,366 |
| Structurally acceptable reports | 336,934 | 336,901 | 233,037 |
| Chronology-flagged occurrences | 52,102 | 31,176 | 16,755 |
| Edges with a flagged occurrence | 14,194 | 12,399 | 5,780 |
| Chronology-flagged chains | 49,245 | 29,021 | 16,264 |
| Reports with at least one flagged chain | 41,286 | 24,575 | 11,818 |
| Reports with chronology shared by all acceptable routes | 14,276 | 14,243 | 4,230 |

The evidence-adjusted replay omits 14 routes, leaving 12 reports without an assessed route. It adds 26 link-gap flags, and 23 reports with a surviving route change best structural verdict. The recorded-chain reproduction rates (exact verdict and acceptable/rejected) are 90.66% and 94.33% in the committed data and 90.66% and 94.33% in the evidence-adjusted replay at the published precision. See the JSON for the denominator and full best-verdict distributions.

### Salīm al-Hilālī

All 34 originally flagged reports in this comparison come from the *Muwaṭṭaʾ*. Thirty-one are exposed via inferred routes and three via recorded routes. The scoped reading of five inferred reports addresses one concrete source of exposure. The same expert-grade handling is used across scenarios. It removes the cross-recension Nasāʾī collection and corroborated grades, collapses parallel editions per grader and report, excludes conflicting rejections, and stratifies on ṣaḥīḥ/ḥasan for the Mantel–Haenszel risk ratio and exact conditional test. [Grade provenance](external-grade-provenance.md) · [Defect-lift method](stratified-defect-inference.md)

| Scenario | Flagged reports | Unflagged reports in cohort | Rejected among flagged | Rejected among unflagged | MH risk ratio | Exact p |
|---|---:|---:|---:|---:|---:|---:|
| Committed | 34 | 1,159 | 76.47% | 8.28% | 8.742 | 1.16e-19 |
| Evidence-adjusted | 29 | 1,159 | 79.31% | 8.28% | 8.935 | 4.65e-18 |
| Recorded routes only, evidence-adjusted | 3 | 517 | 66.67% | 2.71% | 7.000 | 0.0853 |
| Confirmed exposure only, with comparison routes | 0 | 1,159 | — | 8.28% | — | — |

The published method requires at least 20 exposed reports per grader. The recorded-only row is a small-sample sensitivity and changes which reports are eligible. In the adjudicated comparison, Across the corpus, 14,242 structurally acceptable reports have unresolved shared exposure and 322,658 have an acceptable route clear of this screen. One report has a corroborated conflict on every acceptable retained route. Three edition graders rate that report acceptable at the **report** scope. Its occurrence-level conflict and the report’s grading answer different questions. The confirmed-exposure comparison is too sparse for a corpus-wide estimate. The manifest includes each grader’s denominators, exclusions and verdict strata.

## Reproduction

Run these commands from a checkout containing the auditor and the graph tables pinned above. The source fetch downloads the 1.6 GB SQLite database and verifies its checksum.

```bash
python -m pip install -e '.[dev]'
python -c 'from isnad_graph.source import fetch; print(fetch())'
python tools/audit_chronology.py --out ../chronology-audit-output
python -m pytest -q
```

The audit checks the SHA-256 of the upstream SQLite file, recalculates the interval rule on 330,628 edges, reproduces 49,245 source chain replays, and matches all 696,953 committed chain defect masks and 715,790 committed report assessments. The 16 committed lift rows reproduce, with relative tolerance 1e−12 for exact p-values. Recomputing the unrelated rank field exposed 42 rank differences and 13 verdict differences, with 2 rank differences and zero verdict differences among chronology-flagged chains. The replays use the committed ranks and verdicts and apply only evidenced gap caps or route exclusions. The difference file provides the affected IDs.

`audit_manifest.json` gives input hashes, runtime versions, population intersections, cause totals, original statistics and the three comparison views. `edges.csv` has a row per impossible edge. `occurrences.csv` carries source locators and evidence per chain occurrence. `affected_reports.csv` shows changes and unresolved exposures. `baseline_assessment_differences.csv` identifies the separate build drift. The [source review cases](chronology-audit-cases.json) record the cited decisions used by the auditor. The complete test suite passed **233 tests**.

The source material is derived from Emad Jumaah’s al-Jāmiʿ Hadith Knowledge Graph, revision `8ae7e3d5be284a6b32a989cd41866343fc19501c`, CC BY 4.0. The corpus’s existing structural rules and formal verification describe the graph under its inputs. A chain-level conflict with documented dates addresses the feasibility of that route; historical authenticity additionally depends on the transmitted text, other routes, biographies and criticism. [Source dataset](https://huggingface.co/datasets/emadjumaah/hadith-kg) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) · [Project verification scope](PROCESS.md)
