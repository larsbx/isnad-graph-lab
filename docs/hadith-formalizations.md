# Symbolic formalizations of ḥadīth science

Isnad Graph Lab assigns a structural verdict to an isnād and records defects
in transmission. The al-Albānī track evaluates whether supplied routes and
critical evidence support a report’s grade, then gives the uṣūl kernel a typed
admission decision. Both use Ibn Ḥajar’s twelve narrator ranks. Their verdict
scales and the roles they give to tadlīs and corroboration differ.

| Source | Revision examined | Formal layers |
| --- | --- | --- |
| Isnad Graph Lab | [`c8262de`](https://github.com/larsbx/isnad-graph-lab/commit/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879) | Lean definitions and theorems, Python graph conformance, Quint transmission model checked with Apalache |
| Uṣūl al-Fiqh Deontic Circuits | [`4b1b468`](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/commit/4b1b46838c0d57970bb8b71c8642c45ae596625e) | Lean al-Albānī kernel and uṣūl admission, independent SWI-Prolog oracle |

## The rules side by side

| Question | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| **What makes a route structurally sound?** | `sahih_iff` characterizes the structural ṣaḥīḥ verdict by connectivity and a known rank of at most 3 for every modeled narrator. It encodes the first three conditions of Ibn al-Ṣalāḥ’s definition. The absence of shudhūdh (anomaly) and ʿilla (hidden defect) lies outside that theorem. [Lean](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Chain.lean#L26-L88) | `Isnad.verdict` takes the weakest link after applying continuity and the selected tadlīs policy. `Isnad.verdict_le_link` proves the bound for every link. A gap precludes ḥujja for that chain. Hidden defects and stronger conflicting reports enter route assessment as supplied critical evidence. [Lean](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L18-L20) · [Weakest link and gap](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L59-L68) · [Proofs](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L100-L155) |
| **Can teacher and student have met?** | `refuted_sound` rules out contemporaneity (muʿāṣara) for all lifespans admitted by the supplied bounds. `unrefuted_complete` gives an overlap witness when the two bounds are well formed and the pair is unrefuted. `liqa_muasara` derives overlap from a candidate meeting (liqāʾ) year within both lives. The executable `impossible_sound` uses documented bounds. [Interval proofs](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Chronology.lean#L26-L81) · [Executable classifier](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Classify.lean#L30-L91) | Continuity is a field of `Link`. The *Nukhba* classifier uses supplied meeting and contemporaneity facts to distinguish tadlīs from irsāl khafī (hidden disconnection). [Link input](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L47-L62) · [Hidden gaps](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Nukhba.lean#L101-L111) |
| **How does the transmission wording matter?** | `tadlisDefect = mudallis ∧ ambiguous`. `tadlis_iff_rejected` connects it to the encoded al-Shāfiʿī screen. The screen flags ambiguity. Its `written` and `unread` cases supply no positive evidence of hearing. The Python assessment records tadlīs and chronology as flags. Only the gap flag caps the structural grade. [Lean](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/Tadlis.lean#L16-L33) · [Assessment](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/src/isnad_graph/assess.py#L54-L104) | `acceptsTadlis` accepts explicit hearing and allows ambiguous ʿanʿana from tiers 1–2 under `Policy.ibnHajar`. A rejected formula caps the link at ḍaʿīf. Explicit hearing clears this check while the narrator’s underlying grade still applies. [Lean](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Isnad.lean#L25-L96) |
| **How do multiple routes combine?** | The report keeps the best structural verdict and the bitwise intersection of defects over acceptable routes. `common_link_on_chain` proves a path-membership result under the exact single-strand hypothesis. The executable 80% common-link heuristic has its own conformance vectors. [Report assessment](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/src/isnad_graph/assess.py#L98-L104) · [Single-strand theorem and heuristic](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/IsnadFormal/CommonLink.lean#L33-L118) | `judgeRI` can raise the best grade by one rung through an accepted corroboration argument. It counts distinct supplied madār identifiers for routes of grade ḍaʿīf or higher. The default strict policy also requires an independent follower whose weakest rank is at least as good as the base route’s. [Guard and bound](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L25-L91) · [Strict policy](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L225-L318) |
| **What happens when critical evidence conflicts?** | The graph preserves critic assessments and externally attributed grades alongside the structural verdict. Edition alignment has its own provenance and uncertainty. [Grading provenance](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/docs/external-grade-provenance.md#L6-L45) | For route corroboration, an objection can defeat the lift and an answer can reinstate it. A surviving critic’s ruling or matn criterion can lower the result. For narrator criticism, `JarhTadil.judge` uses the strongest qualifying jarḥ and taʿdīl, and the supplied qarīna where applicable. A lone qāṭiʿ side wins against a non-qāṭiʿ side. Two qāṭiʿ sides, or unresolved non-qāṭiʿ conflict, give tawaqquf. [Route objections and caps](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L103-L184) · [Critic resolution](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/JarhTadil.lean#L47-L124) |

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

Rank 5 or 6 alone changes the grade across models even on a continuous route
with explicit hearing. A comparison keyed only by verdict numbers would also
lose the graph’s distinct rank-11 verdict.

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

Ibn Ḥajar’s *Nukhba* taxonomy has its own typed outputs. The finite counts 1,
2 and 3 or more select gharīb, ʿazīz and mashhūr. Mutawātir takes a separate
supplied `unbounded` constructor, which is the only case yielding qaṭʿ in
`knowledge_qat_iff`. Gap position, number and consecutiveness classify
muʿallaq, mursal, muʿḍal and munqaṭiʿ. The ten causes of criticism split five each into
ʿadāla and ḍabṭ. Its jabr classifier records the *Nuzha*’s specified causes of
repair. The project’s al-Albānī profile also permits repair of majhūl al-ʿayn
when the route guards hold, a divergence recorded in `majhul_gap`.
[Route counts and gap classes](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Nukhba.lean#L29-L111) · [Criticism and jabr](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Nukhba.lean#L113-L192)

For conflict between accepted reports, `muarada` uses the uṣūl order jamʿ
(reconciliation), naskh (abrogation), tarjīḥ (preference), then tawaqquf
(suspension), taking evidence for the earlier options as inputs. At the
uṣūl admission boundary, `admitted_iff_yaqin` proves that a supplied grade is
admitted exactly when it meets the project’s certainty-for-action threshold.
The qualifying verdicts are ḥasan and ṣaḥīḥ. Both map to ẓann in this
interface. [Conflict order](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Usul/Taarud.lean#L12-L42) · [Nukhba connection](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Nukhba.lean#L194-L201) · [Ḥujja admission](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Usul/Seam.lean#L22-L41)

## Worked comparisons

The following inputs are synthetic, with ranks, formulas and objections
stipulated. In the graph column, a report verdict is the best structural
grade of its routes.

| Input | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| Connected route, explicit hearing, weakest narrator rank 5 | Structural ḥasan | Prima facie ḍaʿīf |
| Otherwise sound rank-3 route with ambiguous ʿan, narrator marked mudallis and assigned tier 2 | Structural ṣaḥīḥ with a tadlīs flag | Ṣaḥīḥ under the default tier policy |
| Same route with tier 3 instead | Structural ṣaḥīḥ with a tadlīs flag | Ḍaʿīf under the default tier policy |
| Two ḍaʿīf routes, both with weakest narrator rank 9, distinct madār, no objection | Best structural grade stays ḍaʿīf | Ḥasan li-ghayrihi under the strict guard |
| Same two routes with a common madār | Best structural grade stays ḍaʿīf | Ḍaʿīf, since one madār supplies one support |
| Distinct madār, with objection $1\to0$, then a reply $2\to1$ | Best structural grade stays ḍaʿīf | Ḍaʿīf with the objection, then ḥasan li-ghayrihi after the reply |

[Graph grade and defect rules](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/src/isnad_graph/assess.py#L54-L104) · [Lean chain fixtures](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/HadithTest/Chains.lean#L12-L40) · [Strict route fixtures](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L103-L121) · [Strict rank-9 example](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/Hadith/Turuq.lean#L272-L276)

## Evidence and reproduction

| Check | Isnad Graph Lab | al-Albānī kernel |
| --- | --- | --- |
| **Proof replay** | The Lean build checks the theorems. `Audit.lean` checks theorem dependencies in `Isnad` against `propext`, `Classical.choice` and `Quot.sound`. [Axiom audit](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/Audit.lean#L9-L22) | `lake build HadithTest` checks the Lean definitions and fixtures, including generated scale, grading and admission guards. [Lean test entry point](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/HadithTest.lean) |
| **Executable agreement** | The Lean runner compares 51 verdict rows, 7,963 chronology rows, 2,946 phase rows and 2,974 common-link rows with Python and committed data. This covers the exported cases, including the full rank/gap verdict domain and sampled chronology and bundle cases. [Exporter](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/tools/export_vectors.py#L60-L153) · [Runner](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/formal/lean/Conformance.lean#L68-L89) | The independent Prolog oracle recomputes verdicts, grounded extensions, rulings and the admission gate from corpus JSON. For the 45 *al-Ḍaʿīfa* entries, the recorded comparison gives 33 agreements under the rule calculation and 44 when the cited rulings are included. The count allows agreement with a source verdict expressed as a bound. [Oracle](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/oracle/hadith_oracle.pl) · [Corpus results](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/docs/roadmap-albani-hadith-methodology.md#L58-L66) · [Bounded verdict case](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/docs/roadmap-albani-hadith-methodology.md#L218-L222) |
| **Run from the pinned checkout** | Install the project with `python -m pip install -e '.[dev]'` and run `tools/formal-setup.sh` followed by `tools/verify.sh`. [Process](https://github.com/larsbx/isnad-graph-lab/blob/c8262de43aa8fd9e174a17a25b8a55eb4b5f8879/docs/PROCESS.md#L80-L117) | Run `lake build HadithTest` from `formal/lean` and `formal/oracle/run_all.sh` from the repository root with SWI-Prolog available. [Toolchain](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/formal/lean/lean-toolchain) · [Oracle workflow](https://github.com/larsbx/usul-al-fiqh-deontic-circuits/blob/4b1b46838c0d57970bb8b71c8642c45ae596625e/.github/workflows/fixtures.yml#L66-L119) |

Historical interpretation depends on independently sourced narrator identities,
the attachment of formulas to the stated routes, the reliability of dates,
and evidence for shared weaknesses and critical objections. The graph’s
common link identifies a structural position in a bundle. The kernel’s
distinct madār test uses supplied identifiers for the relevant weakness or
common narrator.
