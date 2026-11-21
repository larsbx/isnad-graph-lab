# Chronology follow-up and independent biography comparison

21 November 2026 · Isnad Graph Lab main revision `870ef04fee5a6551a863f9c29a8da1d669a38dc8`

The second source review reduces Salīm al-Hilālī’s flagged chronology sample from 29 to **16**. The repository's published comparison requires at least 20 flagged reports per grader. The original 34-report association merits qualification in light of the source review. A separate biography audit produces **2,719 provisional identity pairs** and a frozen **200-pair adjudication sample**. Its agreement figures describe comparable source fields on provisional pairs. Precision on the review sample is pending.

## P0.1 · Al-Hilālī’s comparison

The original cohort consists of 34 *Muwaṭṭaʾ* reports, 31 of them flagged through inferred routes. I re-read the route text and linked name offsets for all 34. Five had already been excluded in PR #10. The new review identifies twelve additional inferred splices and one splice in a recorded sanad, all with independently addressable occurrences in the pinned corpus. The replay omits these routes because recovering the chain requires resolving passage structure or a missed narrator. Reconstructing those routes is a separate source task. Each exclusion removes a different report from this comparison. [Original chronology audit](chronology-audit.md) · [New source decisions](chronology-hilali-cases.json)

| Review decision | Corpus report IDs |
|---|---|
| Inferred splice previously reviewed | 34395, 34621, 35196, 35763, 35862 |
| Additional inferred splice | 34570, 34956, 35197, 35287, 35407, 35446, 35524, 35621, 35745, 35776, 35883, 35921 |
| Additional recorded splice | 35080, sanad 48708 |
| Attribution or route still unresolved | 34461, 34462, 34463, 34586, 35083, 35200, 35267, 35411, 35431, 35445, 35495, 35633, 35724, 35748, 35975, 36042 |

In report 35080, the text runs through Jaʿfar b. Muḥammad and his father, then describes al-Miqdād visiting ʿAlī. Al-Miqdād names ʿUthmān in quoted speech. The stored sanad links ʿUthmān and ʿAlī as consecutive transmitters. In inferred report 35745, the printed passage names Sunayn Abū Jamīla in the chain and places ʿUmar inside the ensuing story. The entity spans skip Sunayn. In report 35407, they serialize three authorities whom Sulaymān names together as having assigned the same inheritance share. A simple attribution with *ʿan*, *anna* or *qāla*, such as the one in report 35200, remains open pending further route evidence. [Muwaṭṭaʾ, Hajj passage](https://sunnah.com/search?q=Suqya) · [Muwaṭṭaʾ, report 2155](https://www.islam.museum/ar/passage/muwatta-22-2155/)

| Graph assessment | Committed | PR #10 replay | Follow-up replay |
|---|---:|---:|---:|
| Flagged occurrences | 52,102 | 31,176 | 31,163 |
| Flagged chains | 49,245 | 29,021 | 29,008 |
| Reports flagged on every acceptable route | 14,276 | 14,243 | 14,230 |
| Structurally acceptable reports | 336,934 | 336,901 | 336,888 |

| Al-Hilālī comparison | Flagged | Unflagged | Rejected among flagged | MH risk ratio | Exact p | Meets the 20-report rule |
|---|---:|---:|---:|---:|---:|---|
| Committed | 34 | 1,159 | 26/34 | 8.742 | 1.16e−19 | Yes |
| PR #10 replay | 29 | 1,159 | 23/29 | 8.935 | 4.65e−18 | Yes |
| Follow-up replay | 16 | 1,159 | 12/16 | 7.985 | 3.52e−9 | No |
| Follow-up, recorded routes only | 2 | 517 | 1/2 | 5.250 | 0.433 | No |

The small-sample statistics above are exploratory. Their values depend on the selected cohort and finishing the source adjudication. No grader reaches the existing publication threshold for chronology in the follow-up replay. The source-verdict reproduction rates remain 90.66% exact and 94.33% acceptable versus rejected at the published precision, with 577,019 recorded chains in the replay denominator. The audit leaves **31,162 link occurrences** unresolved on 12,396 edges. The gap/rank calculation and the validity of a narrated event remain separate questions. [Defect-lift inference](stratified-defect-inference.md)

## P0.2 · Second-source linkage

The input is version 1 of Fahd's *Hadith Narrators Dataset*, a 24,326-row extract of MuslimScholars. The audit verifies CSV SHA-256 `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11`. It uses reciprocal unique normalized Arabic names or aliases with either two genealogical markers or one marker and a final nisba. Short exact aliases remain leads for review. Competing exact candidates remain ambiguous. Kunya and nisba are preserved where they are part of the attested name. Death years, coarse companion status, geography and shared teacher/student relationships are compared after selection. This keeps a death-year disagreement available for measurement. The graph's 38-layer generation numbers and the second source's generation labels use separate scales. [Dataset](https://www.kaggle.com/datasets/fahd09/hadith-narrators) · [Wirahman’s 2026 preprint](https://arxiv.org/abs/2607.05424)

Death-year agreement uses exact points from both sources; a range or uncertain date has no point comparison. The original MuslimScholars label preserves BH and AH and may preserve multiple alternatives, so the scraper's numeric conversion is bypassed. Residence agreement means sharing a readily mapped city label between `iqama` and `places_of_stay`; region-only records do not enter that comparison. Some labels describe different portions of a narrator’s mobility. The teacher/student check uses graph pairs with at least one provably recorded, direct occurrence and provisional matches at both ends.

| Field | All provisional identity pairs | Provisional matches at impossible-edge endpoints |
|---|---:|---:|
| Identity pairs | 2,719 | 440 |
| Exact death year | 371/452 (82.08%) | 216/264 (81.82%) |
| Death years within 2 | 417/452 (92.26%) | 243/264 (92.05%) |
| Death years within 10 | 430/452 (95.13%) | 253/264 (95.83%) |
| At least one common mapped residence city | 1,278/1,326 (96.38%) | 306/312 (98.08%) |
| Broad companion category agrees | 2,635/2,719 | 434/440 |
| At least one corroborating teacher or student | 816 | 295 |

Only 126 of the 14,194 impossible edges have provisional matches at both endpoints. A further 2,212 have one. The edge table gives 880 leads based on a competing or weak name match, a large date disagreement or a companion-category conflict. These counts measure field agreement in the provisional matched subset. Identity precision awaits adjudication of the frozen sample.

### Examined cases

- **A short alias joins two different people.** MuslimScholars 10942 has the unqualified name ʿAbd al-Raḥmān b. Jubayr, a Ḥimṣ residence and the Syrian transmitter's father and associates. Graph record 4334 is the Egyptian muezzin, while graph record 4335 carries the Ḥimṣ scholar's full lineage. An exact match on the unqualified name alone points to 4334. The stronger rule withholds the proposal as underspecified. The evidence concerns the cross-database join; each underlying graph route still requires its own source check. [Al-Mizzī’s Egyptian entry](https://sunnah.com/narrator/4334) · [Al-Mizzī’s Ḥimṣ entry](https://sunnah.com/narrator/4335)
- **The second file also contains date discrepancies.** For ʿAmr b. Marzūq al-Bāhilī (graph 6200, MuslimScholars 20268), the dates are 224 and 124 AH. Al-Mizzī gives 224, with a 223 alternative. The cited accounts support the graph date. [Al-Mizzī, *Tahdhīb al-Kamāl*](https://www.islamweb.net/ar/library/content/1001/5536/عمرو-بن-مرزوق-الباهلي-أبو-عثمان-البصري)
- **Competing dates change the conclusion for three edges.** Sulaymān b. Kathīr al-ʿAbdī (3621, 20235) has the 133 AH reading in the graph and the 163 reading in MuslimScholars. Ibn Ḥibbān gives 133 and al-Dhahabī gives 163. Using the [133, 163] envelope for just this narrator makes three of his four originally impossible edges consistent with overlap, affecting twelve link occurrences. One of the three is the Ibn Mājah route from Sulaymān to ʿAbd al-Raḥmān b. Mahdī (4493). Both recorded readings are preserved in the sensitivity analysis. [Ibn Ḥibbān’s date](https://islamicurdubooks.com/narratorsdb/rawy-details.php?page=1&rawyid=2630&tab=quotes) · [Al-Dhahabī’s biography](https://ar.wikisource.org/wiki/سير_أعلام_النبلاء/سليمان_بن_كثير_العبدي)

The versioned review sample is selected by hashing the ID pairs before consulting their dates and residence results. It includes source IDs and names, and separate columns for the review decision, supporting locator and notes. The scoring tool accepts `same`, `different` and `uncertain`, rejects duplicate or out-of-sample rows and requires evidence for a decisive label. It reports bounds while there are unadjudicated pairs. The targeted case reviews above serve as diagnostics outside the precision sample. P0.2 remains open until the 200-pair review yields an observed precision estimate.

## Reproduce

Run from the repository root with the project installed in editable mode. The source download for the chronology replay is the 1.6 GB checksummed graph source.

```bash
python -m pip install -e '.[dev]'
python -c 'from isnad_graph.source import fetch; print(fetch())'
python tools/audit_chronology.py --supplemental-reviews docs/chronology-hilali-cases.json \
  --out ../chronology-followup-output

curl -fL 'https://api.kaggle.com/v1/datasets/download/fahd09/hadith-narrators?datasetVersionNumber=1' \
  -o ../hadith-narrators-v1.zip
unzip -p ../hadith-narrators-v1.zip all_rawis.csv > ../all_rawis.csv
python tools/audit_biographies.py --source-csv ../all_rawis.csv --out ../biography-audit-output
python -m pytest -q
```

Pass a completed copy of `identity_review_sample.csv` as `--review-csv` to score it. The biography outputs include the proposed and competing identities, comparable source fields, and flags for individual impossible edges. The supplemental chronology receipt carries its own case-file digest and can be compared directly to PR #10 or the committed assessment. The [date witness replay](#date-witness-replay) is additional sensitivity evidence.

### Date witness replay

```python
from pathlib import Path

import pandas as pd
from isnad_graph.lifespan import feasibility, lifespans

graph = Path("data/graph")
narrators = pd.read_parquet(graph / "narrators.parquet")
edges = pd.read_parquet(graph / "transmissions.parquet")
target = narrators.id.eq(3621)
incident = edges.loc[(edges.src.eq(3621) | edges.dst.eq(3621))
                     & edges.chronology.eq("impossible")]
spans = lifespans(narrators)
alternative = narrators.copy()
alternative.loc[target, "death_year_raw"] = "133 - 163"
spans.loc[target] = lifespans(alternative).loc[target]
after = feasibility(incident, spans)
print(after[["src", "dst", "n_links", "chronology"]].to_string(index=False))
```

The two biographical datasets can draw on the same classical books. The checks address the graph's input provenance and the behavior of the structural model. Historical authentication requires independent analysis of individual chains, their texts and the transmission literature. [Graph source](https://huggingface.co/datasets/emadjumaah/hadith-kg) · [Formal verification scope](PROCESS.md)
