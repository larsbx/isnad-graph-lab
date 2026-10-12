# isnad-graph-lab

A complete, annotated graph of the recorded hadith chains of narration (asānīd).
It covers **715,790 reports from 425 classical collections**, **696,953 chains**,
**49,845 narrator nodes** and **330,628 teacher → student edges**. The graph is
layered with jarḥ wa-taʿdīl assessments, gap annotations, chronology checks,
Juynboll-style common links and, read from the texts themselves, the **mode of
transmission of every link** (حدثنا / أخبرنا / عن / أنّ …), with tadlīs-risk
flags. It is also aligned to public-domain Arabic and English editions of the
seven canonical collections, which carry **67,716 modern gradings**. A structural
isnad verdict per chain is tested against those experts; see
[Isnad assessment](#isnad-assessment).

The built graph is committed in [`data/graph/`](data/graph) (≈ 35 MB of zstd
Parquet plus `manifest.json`). The full text corpus (715,790 Arabic reports and
the English translations, ≈ 130 MB) is rebuilt locally into `data/corpus/`.
Everything is deterministically rebuildable from pinned, hash-verified sources.

```python
from isnad_graph import IsnadGraph

g = IsnadGraph.load("data/graph")
g.verify()                    # 15 structural invariants, all True (also run in CI)
G = g.to_networkx()           # nx.DiGraph, every node and edge annotated
g.students(-1).head()         # the Prophet's busiest transmitters: Abū Hurayra, Anas, ʿĀʾisha, …
```

## Scope: what "the entirety" means here

The source is **«الجامع» Hadith Knowledge Graph** ([`emadjumaah/hadith-kg`](https://huggingface.co/datasets/emadjumaah/hadith-kg),
CC‑BY‑4.0). It is a cleaned, entity-linked export of the Jāmiʿ al-Ḥadīth
database, dumped in 2017. It is the largest openly licensed corpus in which
every narrator in every chain is resolved to a biography. It spans the canonical
six books and also musnads, muṣannafs, muʿjams, ajzāʾ, tafsīr, tārīkh and zuhd works.

The graph contains **every chain recorded in that corpus**: all 577,024 sanads,
verified one-for-one by an invariant. Its limits are worth stating precisely:

| | |
|---|---|
| Recorded chains | 577,024, covering all 403,368 marfūʿ and qudsī reports that have one |
| Inferred chains | 119,929, for mawqūf and maqṭūʿ reports, which the source stores without a sanad (see [Inference](#inferred-chains)) |
| Not chained | 179,672 reports with no identified narrator in the text; a further 12,544 where inference abstains |
| Out of scope | Collections absent from the source, and Shīʿī and Ibāḍī corpora |

## Sources and corpus

| source | license | used for |
|---|---|---|
| [«الجامع» Hadith Knowledge Graph](https://huggingface.co/datasets/emadjumaah/hadith-kg) @ `8ae7e3d5` | CC‑BY‑4.0 | reports, chains, narrators, critics; the Arabic texts with narrator-mention offsets |
| [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api) @ `df57907b` | Unlicense (public domain) | Arabic and English editions of Bukhārī, Muslim, Abū Dāwūd, Tirmidhī, Nasāʾī, Ibn Mājah and the Muwaṭṭaʾ, with modern gradings |

Every file is pinned by revision and sha256 (`source.py`). `isnad-graph corpus`
writes:

* `data/corpus/texts.parquet`: every report's full Arabic text with its isnad
  and matn offsets, plus book, number, type and grade (410M characters);
* `data/corpus/translations.parquet`: 36k English translations, keyed by the
  source `hadith_id` where aligned.

## The model

Let **N** be the set of narrators, with the synthetic node ☉ = the Prophet ﷺ
(id `-1`). A **chain** is a path

  c = (v₀ → v₁ → … → vₖ), with vᵢ ∈ N ∪ {☉} and links ℓᵢ ∈ 𝔽,

ordered in **transmission direction**: apex (☉ or the companion/successor
speaking) first, compiler last. 𝔽 = the bit-flags {IRSAL, INQITA, TALIQ,
MUBHAM}; ℓᵢ = 0 is an unbroken named link.

The source encodes gaps as *pseudo-narrators* (`موضع إرسال`, `موضع انقطاع`,
`موضع تعليق`, `اسم مبهم`, `غير معرف`). As nodes they would be giant fake hubs:
`موضع إرسال` alone sits atop 32,493 chains. Normalization therefore folds each
run of markers into the flag of the link it interrupts. A top-level irsāl in a
marfūʿ report becomes the link ☉ ⇢[IRSAL] tābiʿī. Markers above a non-prophetic
apex become `head_gap`; markers below the compiler (e.g. a muʿallaq) become
`tail_gap`.

The **transmission graph** G = (N, E) aggregates links:
(u, v) ∈ E ⟺ ∃ c, i : (vᵢ, vᵢ₊₁) = (u, v). Each edge carries its
multiplicities and the flag histogram.

Proven invariants, checked on every build (`g.verify()`, recorded in the manifest):

1. every edge endpoint and path node is a node; **no gap marker lies on any path**;
2. |ℓ(c)| = |c| − 1 for every chain;
3. **link mass is conserved**: Σₑ n_links(e) = Σ_c |ℓ(c)| = 4,554,366; one
   transmission mode per link, and each edge's mode histogram sums to its links;
4. provenance partitions links: n_recorded + n_inferred = n_links on every edge;
5. no unflagged self-loops;
6. ☉ occurs exactly as the apex of prophetic chains and nowhere else;
7. every recorded source sanad is present; every chain, assessment, critic and
   alignment reference resolves; each external entry is aligned at most once.

The chain algebra (`chains.normalize`) is additionally property-tested with
Hypothesis. The properties are: narrator conservation, exactly-once accounting of
every marker, idempotence and marker-freeness.

## Tables (`data/graph/*.parquet`)

| table | rows | one row is … | key annotations |
|---|---:|---|---|
| `narrators` | 49,845 | a node | `kind` (narrator · prophet · marker · stub), name, nasab, grade `rank`/`rank_no` (1 companion … 12 fabricator), `tabaka` (generation), birth/death year (AH), residence, tadlīs/ikhtilāṭ flags, Bukhārī/Muslim narrator, `n_chains`, `n_hadiths`, `n_teachers`, `n_students`, `n_as_apex`, `n_as_compiler`; hearing profile `n_links_read`, `explicit_share`, `an_share` |
| `transmissions` | 330,628 | an edge teacher `src` → student `dst` | `n_links`, `n_chains`, `n_hadiths`, `n_books`, `n_recorded`/`n_inferred`, `n_direct`, `n_irsal`, `n_inqita`, `n_taliq`, `n_mubham`, `tabaka_delta`, `death_gap`, `chronology`; mode histogram `mode_sama` … `mode_unread`, `top_mode` |
| `chains` | 696,953 | a hyperedge (one isnad) | `path` (ids, apex → compiler), `links` (flag per link), `modes` (transmission mode per link), `n_modes_borrowed`, `n_tadlis_risk`, structural `verdict`, `defects`, `worst_rank`, `head_gap`, `tail_gap`, `repeats`, `provenance`, `sanad_id`, `hadith_id`, `book_id`, `group_id`, isnad verdict (`isnad_hukm`, `isnad_verdict`) |
| `hadiths` | 715,790 | a report | book, number, page, type (qudsī/marfūʿ/mawqūf/maqṭūʿ), grade `hukm`, meaning group, matn offsets, `n_chains_recorded`, `n_chains_inferred`, `best_verdict`, `shared_defects` |
| `books` | 425 | a collection | author, death year, edition, genre (`tasnif`) |
| `groups` | 20,745 | a *meaning*: all narrations of one matn | overall grade, live `n_hadiths`, `n_books`, `n_chains`, `n_companions` |
| `topics` | 54,862 | a node of the subject tree | nested set (`lft`, `rgt`), parent, link to a group |
| `critics` | 1,015 | a jarḥ wa-taʿdīl authority | death year, generation, rank |
| `assessments` | 127,863 | an edge critic → narrator | the verdict `qawl` verbatim |
| `common_links` | 187,616 | a (partial) common link | see below |
| `alignments` | 33,729 | an external edition entry ↔ source report | `collection`, `hadithnumber` (the edition's numbering, as on sunnah.com), `chapter`, containment `score`, `cross_recension` |
| `external_grades` | 67,716 | a modern grading of an entry | `grader` (al-Albānī, Zubair ʿAlī Zaʾī, al-Arnaʾūṭ, Abū Ghudda, Aḥmad Shākir, Bashshār ʿAwwād …), `grade`, parsed `verdict` and `scope` (isnad / hadith / corroborated), `hadith_id` (NA for the 5,455 on unaligned entries) |

`manifest.json` holds provenance: the source repo, revision, sha256, license and
the source's own build report. It also holds the counts, the invariant results,
the inferred-layer accounting and the inference validation.

### Edge annotations

* **`chronology`**: `impossible` if the student was born after the teacher died,
  `consistent` if both dates are known and compatible, otherwise `unknown`. Counts:
  13,754 impossible, 59,089 consistent, 257,785 unknown. Birth years are sparse.
* **`tabaka_delta`** = generation(student) − generation(teacher). It uses the
  source's 1–38 generation scale (not Ibn Ḥajar's 12). A negative value is an
  inversion worth inspecting.
* **flags**: per edge, how many of its links were irsāl, inqiṭāʿ, taʿlīq or
  through an unnamed narrator. Totals: 32,497 / 13,839 / 3,989 / 14,594.

### Common links

Within each meaning group, chains are **bundled by companion**. For a node, the
*top share* is the fraction of its chains carried on by its busiest student.
Detection descends from the companion along the single strand while the top
share is ≥ 0.8. The first node where it drops below that is the bundle's
**common link**, provided it carries ≥ 3 chains. Every other node with ≥ 2
students and no dominant one is a **partial common link**. The result is
26,432 common links.

This is a test case, not just a demo. For *«إنما الأعمال بالنيات»* the descent
runs ʿUmar → ʿAlqama → al-Taymī and stops at **Yaḥyā b. Saʿīd al-Anṣārī**
(fan-out 38, 96.7% of the bundle). That is the classical common link. Yazīd
b. Hārūn, Ibn al-Mubārak, Mālik, Ḥammād b. Zayd and Ibn ʿUyayna appear among
the partial common links. The case is pinned as a regression test.

### Inferred chains

The source stores mawqūf and maqṭūʿ reports without a sanad, but it does keep
the entity-linked narrator mentions in their text. `inference.py` reads those
mentions in text order, up to the matn boundary. It **abstains** when the
boundary is unknown, when the isnad contains a taḥwīl «ح», or when any mention
is unresolved. A chain naming a single narrator is kept as an attribution
(59,166 such chains) and contributes no edge.

The rule is validated on all 302,229 reports that have exactly one *recorded*
sanad. It attempts 99.5% of them, with **precision 95.8%**: exact either without
the compiler (237,468) or including it (50,685), against 12,611 mismatches. Most
mismatches are isnads cut short by an early matn boundary in late compilations
such as Tārīkh Dimashq. Inferred links are always tagged `inferred`, and
`to_networkx(recorded_only=True)` excludes them.

### Transmission modes

`sigha.py` reads the formula between consecutive narrator mentions in the isnad
text and assigns each chain link one of 13 modes in four classes:

* **explicit hearing:** samāʿ, taḥdīth, ikhbār, qirāʾa, liqāʾ (sāʾaltu, raʾaytu …);
* **written:** kitāba, ijāza, wijāda;
* **ambiguous:** ʿan, anna, qāla, dhakara, rawā;
* **unread.**

The rules were mined from the corpus's most frequent gap strings:

1. **The last formula governs.** «يحدث عن X» is ʿan.
2. **Post-posed verbs upgrade the previous link.** In «أن عروة حدثه أن», the
   حدثه turns that *anna* link into taḥdīth.
3. **Co-narrators share a formula.** «A و B قالا حدثنا C».
4. **Taḥwīl restarts the route.** A «ح» starts the route again at the compiler,
   or at the isnad's first narrator.
5. **Anonymous narrators are bridged.** A link over «عن شيخ» takes the
   student's formula.
6. **Unnamed kin split a gap.** «عن أبيه عن» divides the gap into two hops.
7. **The Prophet's link is read just inside the matn,** where the source's matn
   boundary usually puts «قال رسول الله ﷺ».

Links a report's text omits are read from up to three preceding reports of the
same book, following the «بهذا الإسناد» convention. This borrowed 139,751
readings, and the count is recorded per chain.

Of 4,554,366 links:

| class | share |
|---|---:|
| explicit | 47.7% |
| ambiguous | 43.9% (ʿan alone 1.51M) |
| written | < 0.1% |
| unread | 8.4% |

Checks:

* Ṣaḥīḥ al-Bukhārī 1 reads exactly as its isnad: samāʿ ×3, ikhbār, taḥdīth ×3.
* The compilers' own links have the expected profiles: Aḥmad 91% taḥdīth,
  Ibn ʿAsākir 75% ikhbār, the Muwaṭṭaʾ 77% ʿan.
* The famous mudallisūn narrate overwhelmingly by ʿan: al-Aʿmash 95%, Qatāda
  87%, Abū Isḥāq al-Sabīʿī 88%. Ibn Jurayj, known for «أخبرني», is at 49%
  explicit.

`n_tadlis_risk` counts links where the student is a known mudallis and the
formula is ambiguous, i.e. the classical ʿanʿana of a mudallis. 144,613 chains
have at least one.

### Isnad assessment

`assess.py` gives every chain a **structural verdict**: the weakest narrator's
rank (1 companion … 12 fabricator) decides ṣaḥīḥ / ḥasan / ḍaʿīf / very weak /
accused / mawḍūʿ, and any gap caps the chain at ḍaʿīf. This is the source's own
rule. Rebuilt from the graph alone, it reproduces the source's 577,024 per-chain
verdicts **90.7% exactly** and **94.3% on acceptable vs rejected**.

It cannot see how links were transmitted, so each chain also carries
**defects** read from the texts:

* `TADLIS`: ʿan, anna, qāla … by a mudallis graded thiqa;
* `TADLIS_WEAK`: the same by a mudallis graded ṣadūq or below;
* `CHRONOLOGY`: the student was born after the teacher died;
* `GAP`: a gap marker on the chain.

A report's `shared_defects` are those on *every* acceptable route; a single
clean route rescues it.

Do the defects matter? Folding them into the verdict naively *lowers* agreement
with every expert, so the right test is predictive. Take reports whose
structural verdict is acceptable. Does "every acceptable route carries the
defect" raise the rate at which a grader rejects them? `defect_lift` answers
this per grader. It compares within the ṣaḥīḥ and ḥasan strata, pooled by
Mantel–Haenszel, because a ṣadūq mudallis makes a chain ḥasan by construction.
It counts each report once per grader: parallel edition entries aligned to
one report are collapsed, and a report a grader grades both ways is dropped and
counted as `n_conflicting`. It uses uncorroborated grades only, and excludes
cross-recension associations
(Nasāʾī), which are not grades of the source report (see
[External editions](#external-editions)).

| grader | ṣadūq-level mudallis: MH RR; exact p | thiqa mudallis: MH RR; exact p |
|---|---|---|
| Zubair ʿAlī Zaʾī | 1.884; 8.05×10⁻²⁰ | 2.374; 4.79×10⁻⁶³ |
| al-Albānī | 1.427; 5.44×10⁻⁵ | 1.404; 9.17×10⁻⁶ |
| Shuʿayb al-Arnaʾūṭ | 1.447; 0.00175 | 1.508; 0.000195 |
| Aḥmad Shākir | 1.412; 0.0604 | 1.271; 0.128 |

These are observational associations in the aligned corpus. Both mudallis
categories show positive adjusted evidence for the first three named graders;
Shākir's comparisons do not meet a nominal two-sided 0.05 threshold. The earlier
claims of significance for every grader and essentially only Zaʾī for thiqa
mudallisūn are withdrawn. These results do not independently establish a
grader's doctrine, a transmission defect's cause, or a historical or
jurisprudential conclusion.

`reject_flagged` and `reject_clean` remain **descriptive marginal rates**.
`risk_ratio_mh` pools within structural-verdict strata. `z_cmh` is a signed,
uncorrected stratified score; `p_exact` is the primary inferential statistic,
an exact conditional two-sided test using twice the smaller inclusive tail.
It conditions on each stratum's exposure and rejection totals, supports sparse
and zero-cell tables without pseudocounts, and tests conditional independence,
not the value of an estimated common risk ratio. The generic `z` field is removed.
The exported stratum counts make overlap, sparsity and differing effects inspectable.

The chronology association for Salīm al-Hilālī remains strong (MH RR 8.742,
exact p 1.16×10⁻¹⁹; 34 flagged reports). It does not identify which historical
mechanism explains the association. All comparisons, exclusions and attribution
remain in `manifest.json` under `assessment.defect_lift`.
See [the inference audit](docs/stratified-defect-inference.md) for full results,
family-wise adjustment, assumptions, and reproducibility.

### External editions

Edition numbering differs from the source's: Bukhārī has 7,589 entries against
7,031 reports. Muslim's parallel routes are numbered separately, while the
source merges them into one report with several sanads. `align.py` therefore
maps each edition entry to the source report that best **contains** it. It
compares normalized word-trigram sets after stripping honorifics, which
editions spell out, abbreviate as ﷺ, or omit, and keeps matches at ≥ 0.5.

**Order consistency** checks non-decreasing successive source positions; equal
positions count as consistent. It is an aggregate diagnostic, not a probability
of correctness. The aligner never sees numbering.

| collection | aligned | order consistency |
|---|---:|---:|
| Bukhārī | 97.1% | 0.993 |
| Muslim | 92.8% | 0.998 |
| Abū Dāwūd | 99.3% | 0.998 |
| Tirmidhī | 95.5% | 0.996 |
| Ibn Mājah | 97.2% | 0.998 |
| Muwaṭṭaʾ (Yaḥyā) | 94.5% | 0.999 |
| Nasāʾī | 74.7% | 0.900 |

The Nasāʾī alignment is cross-recension: the edition is al-Sunan al-Ṣughrā
mapped onto the source's al-Kubrā. It is flagged `cross_recension` in newly built alignment, grading and translation
tables. See [the provenance audit and guarded-query policy](docs/external-grade-provenance.md).
The committed bundle predates these fields on grading rows; rebuild before using
`grades_of`, which rejects legacy grading schemas.

## Usage

```bash
uv venv && uv pip install -e ".[dev]"
isnad-graph stats                                 # counts from the committed graph
isnad-graph chain 1                               # render the chains of hadith 1
isnad-graph export isnad.graphml --min-chains 2   # for Gephi / Cytoscape (also: --format gexf)
isnad-graph verify                                # re-check invariants
isnad-graph tree trees.json 319 397               # laid-out isnad trees of meaning groups, per companion
```

```python
g.render_chain(cid)        # 'محمد رسول الله ﷺ ⇢[IRSAL] سالم بن عبد الله → الزهري → …'
g.teachers(7272)           # al-Zuhrī's teachers, by number of chains
g.chains_of(hadith_id)     # every chain of a report
g.frame("common_links")    # any table as a DataFrame (tables are immutable Arrow)
```

### Rebuild from source

```bash
isnad-graph fetch    # pinned hadith-kg.db (1.6 GB) + 14 hadith-api editions, sha256-verified
isnad-graph build    # ≈ 5 min, ≈ 3 GB RAM → data/graph/
isnad-graph corpus   # ≈ 8 min → data/corpus/ (texts + translations)
pytest               # 122 tests: unit, property and fixture tests, plus regressions on data/graph
```

## Layout

```
src/isnad_graph/
  schema.py      vocabulary: LinkFlag, NodeKind, Provenance, marker names
  chains.py      pure chain algebra: source chain → normalized annotated path
  inference.py   conservative chain inference from in-text mentions
  arabic.py      Arabic normalization for matching
  sigha.py       transmission modes from the isnad text (rules 1–7)
  align.py       text alignment of external editions (trigram containment)
  corpus.py      external editions, alignment and grade tables, corpus export
  analysis.py    edge aggregation, chronology, common links, tadlīs risk, hearing profiles
  assess.py      structural verdicts, defects, grade parsing, defect lift vs experts
  subgraph.py    one meaning group's isnads as laid-out trees per companion bundle
  build.py       the only SQL: source DB → IsnadGraph
  graph.py       IsnadGraph: immutable Arrow tables, queries, networkx view, invariants
  source.py      pinned sources, fetch + sha256 verification
  cli.py
tests/           fixture DB built from the source's verbatim DDL (tests/fixtures/schema.sql)
data/graph/      the built graph (committed)
data/corpus/     the text corpus (local, rebuilt by `isnad-graph corpus`)
```

## License and attribution

The code is MIT. The graph in `data/graph/` is a derivative of
*«الجامع» Hadith Knowledge Graph* by Hugging Face user `emadjumaah`, licensed under
[CC‑BY‑4.0](https://creativecommons.org/licenses/by/4.0/), revision
`8ae7e3d5`. It is redistributed under the same license. The alignments, English
translations and modern gradings come from
[hadith-api](https://github.com/fawazahmed0/hadith-api), which is in the public
domain. Narrator grades, verdicts, dates and gradings are their authors'
judgements, not this project's.
