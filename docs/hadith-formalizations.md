# Symbolic formalizations of ḥadīth science

The shared [Lean criteria](../formal/lean/Hadith/ClassicalCriteria.lean)
take reviewed findings about a report and its isnād. Isnad Graph Lab
scores recorded chain structure and flags transmission defects. The
al-Albānī replay profile computes candidate grades on the evidence supplied
for its fixtures. Report-specific critical findings supply the inputs to the
classical checks.

## From the source wording to the proof

| Criterion | What the proof requires |
| --- | --- |
| **Ṣaḥīḥ and ḥasan li-dhātihi.** Ibn al-Ṣalāḥ states continuity, uprightness and precision throughout, absence of shudhūdh, and absence of a disqualifying ʿilla. Ibn Ḥajar specifies full precision for ṣaḥīḥ li-dhātihi and lighter precision for ḥasan li-dhātihi in the āḥād classification. | `intrinsic_sahih_iff` and `intrinsic_hasan_iff` require the relevant findings for the report. An unresolved ʿilla leaves the intrinsic grade open even if the graph score is ṣaḥīḥ. [Ibn al-Ṣalāḥ, type 1](https://ar.wikisource.org/wiki/%D8%AD%D8%AF%D9%8A%D8%AB_%D8%B5%D8%AD%D9%8A%D8%AD) · [Ibn Ḥajar, *Nukhba*, v04:p722](https://github.com/OpenITI/0875AH/blob/5835c183b8bbf4ea454d5c1be2b168b669403771/data/0852IbnHajarCasqalani/0852IbnHajarCasqalani.NukhbatFikar/0852IbnHajarCasqalani.NukhbatFikar.Shamela0005940-ara1#L89-L101) |
| **The sixth narrator rank.** Ibn Ḥajar uses maqbūl where the narrator is followed and layyin al-ḥadīth otherwise. His fifth rank includes several transmitter conditions. | `sixthRankStatus` distinguishes a reviewed qualifying follower, a finding against such a follower and an unresolved review. This describes the narrator in that use. The two numerical score maps below are corpus and replay conventions. [*Taqrīb*, introduction, v01:p074](https://github.com/OpenITI/0875AH/blob/5835c183b8bbf4ea454d5c1be2b168b669403771/data/0852IbnHajarCasqalani/0852IbnHajarCasqalani.TaqribTahdhib/0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed) |
| **Tadlīs and ʿanʿana.** Al-Shāfiʿī requires explicit hearing from a known mudallis. Muslim describes a presumption where reliable narrators could meet and hear, and where contrary evidence is absent. He singles out known mudallis narrators for inquiry into hearing. | `shafii_requires_explicit` consumes a finding about the formula for the report. The graph’s ambiguity flag is a separate check. `MuslimAnanaFindings.Presumption` requires all its findings. `unrefuted_complete` proves a date-overlap witness under well-formed bounds. [Al-Shāfiʿī, *al-Risāla*, p. 378](https://github.com/OpenITI/0225AH/blob/2cfdc8cf1b89abfd15463d1c429fbb822aa5d9a5/data/0204Shafici/0204Shafici.Risala/0204Shafici.Risala.Shamela0008180-ara1) · [Muslim, *Muqaddima*, pp. 29–33](https://github.com/OpenITI/0275AH/blob/44e1c36738a2bf5c14dafa232a6ae1891e6171cd/data/0261Muslim/0261Muslim.Sahih/0261Muslim.Sahih.Shamela0001727-ara1.mARkdown) |
| **Jabr by a qualified follower.** The *Nuzha* passage makes repair depend on the cause of weakness and a matching follower at least as reliable as the transmitter followed. | `jabr_iff` checks the listed cause and a reviewed matching follower. Two grade labels with different madār IDs can satisfy the project’s replay guard while the source criterion remains unresolved. [*Nuzha*, v01:p104–p105](https://github.com/OpenITI/0875AH/blob/5835c183b8bbf4ea454d5c1be2b168b669403771/data/0852IbnHajarCasqalani/0852IbnHajarCasqalani.NuzhatNazar/0852IbnHajarCasqalani.NuzhatNazar.Shamela0001565-ara1#L1104-L1118) · [Lean](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/Nukhba.lean) |
| **Tawātur.** Ibn Ḥajar gives four conditions, including sufficient multiplicity throughout, sensory basis and the imparting of knowledge. | The tawātur constructor requires all four findings. For a documented example of the āḥād branch, the *Nuzha* cites the intentions report’s singular early transmission. The fixture replays that cited multiplicity. [*Nuzha*, v01:p041–p043 and v01:p048–p049](https://github.com/OpenITI/0875AH/blob/5835c183b8bbf4ea454d5c1be2b168b669403771/data/0852IbnHajarCasqalani/0852IbnHajarCasqalani.NuzhatNazar/0852IbnHajarCasqalani.NuzhatNazar.Shamela0001565-ara1#L110-L217) · [Lean fixture](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/HadithTest/Chains.lean) |

## Revisions for the corpus and replay profiles

The pins below identify the numerical profiles used in the worked examples.
The source criteria are shared from the
[reconciled Lean revision](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/ClassicalCriteria.lean).

| Source | Revision examined | Formal layers |
| --- | --- | --- |
| Isnad Graph Lab | [`c8262de`](https://github.com/larsbx/isnad-graph-lab/commit/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879) | Lean definitions and theorems, Python graph conformance, Quint transmission model checked with Apalache |
| Uṣūl al-Fiqh Deontic Circuits | [`4b1b468`](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/commit/4b1b46838c0d57970bb8b71c8642c45ae596625e) | Lean al-Albānī kernel and uṣūl admission, independent SWI-Prolog oracle |

## The rules side by side

| Question | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| **How does the chain score work?** | `sahih_iff` characterizes the corpus’s ṣaḥīḥ code by the absence of marked gaps and the rank cutoff. `structural_sahih_with_pending_review` keeps that score fixed while the intrinsic grade changes with the reviewed evidence. [Lean](../formal/lean/IsnadFormal/Chain.lean) | `Isnad.verdict` takes the weakest link after applying the continuity input and selected tadlīs policy. `Isnad.verdict_le_link` proves the bound for each link in this profile. [Lean](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/Isnad.lean) |
| **What do the recorded dates permit?** | `refuted_sound` rules out overlap for all lifespans admitted by the supplied bounds. `unrefuted_complete` gives an overlap witness for well-formed bounds when refutation fails. Historical hearing or encounter needs its own evidence. [Lean](../formal/lean/IsnadFormal/Chronology.lean) | Continuity and hearing are supplied inputs. The *Nukhba* classifier uses reviewed meeting and contemporaneity findings within its hidden-gap taxonomy. [Hidden gaps](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/Nukhba.lean) |
| **How does the transmission wording matter?** | `tadlis_iff_ambiguous` characterizes the graph flag. `shafii_requires_explicit` checks a report-level finding of explicit hearing for a known mudallis. A written or unread label alone leaves that finding unresolved. Only the gap flag caps the structural grade. [Lean](../formal/lean/IsnadFormal/Tadlis.lean) · [Assessment](../src/isnad_graph/assess.py) | `acceptsTadlis` accepts explicit hearing and permits ambiguous ʿanʿana from tiers 1–2 under the project’s Ibn Ḥajar profile. A rejected formula caps the link at ḍaʿīf. The narrator’s score remains an independent input. [Lean](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/Isnad.lean) |
| **How do multiple routes combine?** | The report keeps the best structural verdict and the bitwise intersection of defects over acceptable routes. `common_link_on_chain` proves a path-membership result under the exact single-strand hypothesis. The executable 80% common-link heuristic has its own conformance vectors. [Report assessment](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/src/isnad_graph/assess.py#L98-L104) · [Single-strand theorem and heuristic](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/CommonLink.lean#L33-L118) | `judgeRI` can raise the best grade by one rung through an accepted corroboration argument. It counts distinct supplied madār identifiers for routes of grade ḍaʿīf or higher. The strict policy compares whole-route floors as a proxy for the follower comparison. [Guard and bound](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L25-L91) · [Strict policy](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L225-L318) |
| **What happens when critical evidence conflicts?** | The graph preserves critic assessments and externally attributed grades alongside the structural verdict. Edition alignment has its own provenance and uncertainty. [Grading provenance](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/docs/external-grade-provenance.md#L6-L45) | For route corroboration, an objection can defeat the lift and an answer can reinstate it. A surviving critic’s ruling or matn criterion can lower the result. The project’s al-Muʿallimī profile `JarhTadil.judge` uses the strongest qualifying jarḥ and taʿdīl, and the supplied qarīna where applicable. A lone qāṭiʿ side wins against a non-qāṭiʿ side. Two qāṭiʿ sides, or unresolved non-qāṭiʿ conflict, give tawaqquf. [Route objections and caps](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L103-L184) · [Critic resolution](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/JarhTadil.lean#L47-L124) |

### The rank maps and weakest-link equations

| Ibn Ḥajar rank | Graph rank verdict (code) | al-Albānī prima facie verdict (rank) |
| --- | --- | --- |
| 1–3 | ṣaḥīḥ (0) | ṣaḥīḥ (4) |
| 4 | ḥasan (1) | ḥasan (3) |
| 5–6 | ḥasan (1) | ḍaʿīf (2) |
| 7–9 | ḍaʿīf (2) | ḍaʿīf (2) |
| 10 | very weak (3) | ḍaʿīf jiddan (1) |
| 11 | accused (4) | ḍaʿīf jiddan (1) |
| 12 | mawḍūʿ (5) | mawḍūʿ (0) |

In the graph, larger verdict codes are weaker. Let $w$ be the maximum
effective rank, with a missing grade read as rank 9, and let $g$ be 1 if there
is a gap at either end or on any link and 0 otherwise. With $G$ the graph rank
map above, the chain’s verdict code is $\max(G(w),2g)$.
[Rank map and monotonicity](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Grade.lean#L29-L114) · [Chain representation](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Chain.lean#L26-L52)

In the al-Albānī scale, larger verdict ranks are stronger. With $A$ the
prima facie map above, a link $\ell$ of narrator rank $r_\ell$ contributes
$A(r_\ell)$ if it passes continuity and the tadlīs policy, and
$\min(A(r_\ell),2)$ otherwise. The chain’s verdict rank is the minimum of
its link ranks, with 4 as the empty fold’s identity. The strict corroboration
check uses a separate **narrator-rank floor**. It takes the maximum narrator
rank and counts a gap or a policy-rejected formula as at least rank 9.
[Rank map](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Grade.lean#L47-L125) · [Link and chain verdict](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L59-L68) · [Narrator-rank floor](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L158-L163)

Rank 5 or 6 alone changes the **profile score** across models even on a
continuous route with explicit hearing. Ibn Ḥajar’s sixth-rank condition
requires a qualifying-follower finding for the specific narration.

### Chronology and transmission in the graph

For teacher $T$ and student $S$, let $b^-$ be the earliest allowed birth and
$d^+$ the latest allowed death. The interval refutation is

$$
\operatorname{refuted}(T,S) \iff b^-_S > d^+_T \;\lor\; b^-_T > d^+_S.
$$

The overlap witness establishes possibility under the supplied bounds. An
attested encounter needs independent evidence. With exact dates and
nonnegative minimum ages $a_T,a_S$, a hearing at those ages is feasible iff
$\max(b_T+a_T,b_S+a_S)\le\min(d_T,d_S)$. Separately, `phases_partition`
proves that the life’s half-open cells are covered by contiguous, nonempty
phases of the correct window-membership kind, with different kinds on adjacent
phases. [Interval and hearing-window theorems](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Chronology.lean#L40-L81) · [Lifeline theorem](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Phases.lean#L297-L303) · [Source chronology audit](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/docs/chronology-followup.md)

The Quint state stores the current year, holders, named chains, formulas and
actual hearings **within the model**. A student can name a teacher via samāʿ
or ʿan, or hear from a teacher and omit that teacher via irsāl. The safety
conjunction checks rootedness, prefix closure, hearing and gap witnesses,
chronological order, refutation, weakest-link grading, gap caps, the exact
condition for structural ṣaḥīḥ, and inherited tadlīs flags. Apalache checks a
five-role instance including the source, with a bound of four steps. The
Quint invariants are finite process checks alongside the Lean theorems.
[Quint model](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/quint/transmission.qnt#L38-L193) · [Pinned bound](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/toolchain.toml#L12-L20)

### Corroboration, classification and admission in the kernel

Let $x\to y$ mean that argument $x$ attacks argument $y$ in a finite argument
file. Starting with the empty set, the grounded procedure iterates

$$
F(S)=\{a : \forall b,\ (b\to a)\Rightarrow\exists c\in S,\ c\to b\}.
$$

Lean’s `mem_step_iff` identifies each executable step on the finite argument
indices with this defense operator. The lift is argument 0. It can raise a
best grade of ḍaʿīf or ḥasan by one rung when it survives and the route guards
hold. Severe weakness supplies no support. A grounded ruling can cap even the
best single-route grade. `ghayri_iff` characterizes a change from the best
route in the uncapped aggregation, and the refined order places
li-ghayrihi below li-dhātihi at the same grade.
[Grounded semantics](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Usul/Grounded.lean#L13-L44) · [Caps and refined order](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L124-L220)

Ibn Ḥajar’s *Nukhba* taxonomy has typed outcomes for route multiplicity, gap
position and the ten causes of criticism. The āḥād branch uses the minimum
multiplicity across the route levels. The tawātur branch requires the four
findings in the *Nuzha*. `knowledge_qat_iff` concerns the project’s epistemic
projection. The *Nuzha* also allows some āḥād reports with corroborating
indications to impart inferential knowledge under Ibn Ḥajar’s preferred
view.

The `jabr` predicate checks the source’s named causes with a reviewed
qualifying follower. A distinct madār label and a whole-route minimum rank
can satisfy the project profile without establishing the required follower
comparison. The profile’s treatment of majhūl al-ʿayn stays visible in
`majhul_gap`. [Reconciled *Nukhba* module](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/Hadith/Nukhba.lean)

For conflict between accepted reports, `muarada` uses the uṣūl order jamʿ
(reconciliation), naskh (abrogation), tarjīḥ (preference), then tawaqquf
(suspension), taking evidence for the earlier options as inputs. At the
uṣūl admission boundary, `admitted_iff_yaqin` proves that a supplied grade is
admitted exactly when it meets the project’s certainty-for-action threshold.
The qualifying verdicts are ḥasan and ṣaḥīḥ. Both map to ẓann in this
interface. [Conflict order](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Usul/Taarud.lean#L12-L42) · [Nukhba connection](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Nukhba.lean#L194-L201) · [Ḥujja admission](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Usul/Seam.lean#L22-L41)

## Worked comparisons

The following inputs are synthetic, with ranks, formulas and objections
stipulated. Both columns show profile computations. In the graph column, a report
score is the best structural score of its routes.

| Input | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| Connected route, explicit hearing, weakest narrator rank 5 | Structural ḥasan | Prima facie ḍaʿīf |
| Otherwise sound rank-3 route with ambiguous ʿan, narrator marked mudallis and assigned tier 2 | Structural ṣaḥīḥ with a tadlīs flag | Ṣaḥīḥ under the default tier policy |
| Same route with tier 3 instead | Structural ṣaḥīḥ with a tadlīs flag | Ḍaʿīf under the default tier policy |
| Two ḍaʿīf routes, both with weakest narrator rank 9, distinct madār, no objection | Best structural grade stays ḍaʿīf | Replay score of ḥasan li-ghayrihi under the strict guard |
| Same two routes with a common madār | Best structural grade stays ḍaʿīf | Ḍaʿīf, since one madār supplies one support |
| Distinct madār, with objection $1\to0$, then a reply $2\to1$ | Best structural grade stays ḍaʿīf | Ḍaʿīf with the objection, then ḥasan li-ghayrihi after the reply |

[Graph grade and defect rules](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/src/isnad_graph/assess.py#L54-L104) · [Lean chain fixtures](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/HadithTest/Chains.lean#L12-L40) · [Strict route fixtures](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L103-L121) · [Strict rank-9 example](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L272-L276)

## Evidence and reproduction

| Check | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| **Proof replay** | The Lean build checks the shared classical criteria and the graph theorems. `Audit.lean` checks theorem dependencies in `Isnad` against `propext`, `Classical.choice` and `Quot.sound`. [Axiom audit](../formal/lean/Audit.lean) | `lake build HadithTest` checks the source criteria, the profile and the fixtures, including generated scale, grading and admission guards. [Lean test entry point](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/d9c012a4c5de04aa934152fbf678173aa1b4eb3f/formal/lean/HadithTest.lean) |
| **Executable agreement** | The Lean runner compares 51 structural verdict rows, 7,963 chronology rows, 2,946 phase rows and 2,974 common-link rows with Python and committed data. This covers the exported cases, including the full rank/gap verdict domain and sampled chronology and bundle cases. [Exporter](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/tools/export_vectors.py#L60-L153) · [Runner](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/Conformance.lean#L68-L89) | The independent Prolog oracle recomputes verdicts, grounded extensions, rulings and the admission gate from corpus JSON. For the 45 *al-Ḍaʿīfa* entries, the recorded comparison gives 33 agreements under the rule calculation and 44 when the cited rulings are included. The count allows agreement with a source verdict expressed as a bound. [Oracle](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/oracle/hadith_oracle.pl) · [Corpus results](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/docs/roadmap-albani-hadith-methodology.md#L58-L66) · [Bounded verdict case](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/docs/roadmap-albani-hadith-methodology.md#L218-L222) |
| **Run from the pinned checkout** | Install the project with `python -m pip install -e '.[dev]'` and run `tools/formal-setup.sh` followed by `tools/verify.sh`. [Process](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/docs/PROCESS.md#L80-L117) | Run `lake build HadithTest` from `formal/lean` and `formal/oracle/run_all.sh` from the repository root with SWI-Prolog available. [Toolchain](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/lean-toolchain) · [Oracle workflow](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/.github/workflows/fixtures.yml#L66-L119) |

Historical interpretation depends on independently sourced narrator identities,
the attachment of formulas to the stated routes, the reliability of dates,
and evidence for shared weaknesses and critical objections. The graph’s
common link identifies a structural position in a bundle. The kernel’s
distinct madār test uses supplied identifiers for the relevant weakness or
common narrator.
