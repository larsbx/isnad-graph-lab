# isnad-graph-lab

A complete, annotated graph of the recorded hadith chains of narration (asānīd).
It covers **715,790 reports from 425 classical collections**, **696,953 chains**,
**49,845 narrator nodes** and **330,628 teacher → student edges**. The graph is
layered with jarḥ wa-taʿdīl assessments, gap annotations, chronology checks and
Juynboll-style common links.

The built graph is committed in [`data/graph/`](data/graph) (≈ 32 MB of zstd
Parquet plus `manifest.json`). It is deterministically rebuildable from a pinned,
hash-verified source.

```python
from isnad_graph import IsnadGraph

g = IsnadGraph.load("data/graph")
g.verify()                    # 11 structural invariants, all True
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
3. **link mass is conserved**: Σₑ n_links(e) = Σ_c |ℓ(c)| = 4,554,366;
4. provenance partitions links: n_recorded + n_inferred = n_links on every edge;
5. no unflagged self-loops;
6. ☉ occurs exactly as the apex of prophetic chains and nowhere else;
7. every recorded source sanad is present; every chain, assessment and critic reference resolves.

The chain algebra (`chains.normalize`) is additionally property-tested with
Hypothesis. The properties are: narrator conservation, exactly-once accounting of
every marker, idempotence and marker-freeness.

## Tables (`data/graph/*.parquet`)

| table | rows | one row is … | key annotations |
|---|---:|---|---|
| `narrators` | 49,845 | a node | `kind` (narrator · prophet · marker · stub), name, nasab, grade `rank`/`rank_no` (1 companion … 12 fabricator), `tabaka` (generation), birth/death year (AH), residence, tadlīs/ikhtilāṭ flags, Bukhārī/Muslim narrator, `n_chains`, `n_hadiths`, `n_teachers`, `n_students`, `n_as_apex`, `n_as_compiler` |
| `transmissions` | 330,628 | an edge teacher `src` → student `dst` | `n_links`, `n_chains`, `n_hadiths`, `n_books`, `n_recorded`/`n_inferred`, `n_direct`, `n_irsal`, `n_inqita`, `n_taliq`, `n_mubham`, `tabaka_delta`, `death_gap`, `chronology` |
| `chains` | 696,953 | a hyperedge (one isnad) | `path` (ids, apex → compiler), `links` (flag per link), `head_gap`, `tail_gap`, `repeats`, `provenance`, `sanad_id`, `hadith_id`, `book_id`, `group_id`, isnad verdict (`isnad_hukm`, `isnad_verdict`) |
| `hadiths` | 715,790 | a report | book, number, page, type (qudsī/marfūʿ/mawqūf/maqṭūʿ), grade `hukm`, meaning group, matn offsets, `n_chains_recorded`, `n_chains_inferred` |
| `books` | 425 | a collection | author, death year, edition, genre (`tasnif`) |
| `groups` | 20,745 | a *meaning*: all narrations of one matn | overall grade, live `n_hadiths`, `n_books`, `n_chains`, `n_companions` |
| `topics` | 54,862 | a node of the subject tree | nested set (`lft`, `rgt`), parent, link to a group |
| `critics` | 1,015 | a jarḥ wa-taʿdīl authority | death year, generation, rank |
| `assessments` | 127,863 | an edge critic → narrator | the verdict `qawl` verbatim |
| `common_links` | 187,616 | a (partial) common link | see below |

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

## Usage

```bash
uv venv && uv pip install -e ".[dev]"
isnad-graph stats                                 # counts from the committed graph
isnad-graph chain 1                               # render the chains of hadith 1
isnad-graph export isnad.graphml --min-chains 2   # for Gephi / Cytoscape (also: --format gexf)
isnad-graph verify                                # re-check invariants
```

```python
g.render_chain(cid)        # 'محمد رسول الله ﷺ ⇢[IRSAL] سالم بن عبد الله → الزهري → …'
g.teachers(7272)           # al-Zuhrī's teachers, by number of chains
g.chains_of(hadith_id)     # every chain of a report
g.frame("common_links")    # any table as a DataFrame (tables are immutable Arrow)
```

### Rebuild from source

```bash
isnad-graph fetch    # downloads the pinned hadith-kg.db (1.6 GB) and verifies its sha256
isnad-graph build    # ≈ 2–3 min, ≈ 3 GB RAM → data/graph/
pytest               # 42 tests: unit, property and fixture tests, plus regressions on data/graph
```

## Layout

```
src/isnad_graph/
  schema.py      vocabulary: LinkFlag, NodeKind, Provenance, marker names
  chains.py      pure chain algebra: source chain → normalized annotated path
  inference.py   conservative chain inference from in-text mentions
  analysis.py    edge aggregation, chronology, common links (DataFrame → DataFrame)
  build.py       the only SQL: source DB → IsnadGraph
  graph.py       IsnadGraph: immutable Arrow tables, queries, networkx view, invariants
  source.py      pinned source spec, fetch + sha256 verification
  cli.py
tests/           fixture DB built from the source's verbatim DDL (tests/fixtures/schema.sql)
data/graph/      the built graph
```

## License and attribution

The code is MIT. The graph in `data/graph/` is a derivative of
*«الجامع» Hadith Knowledge Graph* by Hugging Face user `emadjumaah`, licensed under
[CC‑BY‑4.0](https://creativecommons.org/licenses/by/4.0/), revision
`8ae7e3d5`. It is redistributed under the same license. Narrator grades,
verdicts and dates are the source's, not this project's judgements.
