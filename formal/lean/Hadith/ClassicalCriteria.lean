/-!
# Intrinsic grades and the sixth rank in Ibn Ḥajar

Ibn al-Ṣalāḥ, *Maʿrifat Anwāʿ ʿIlm al-Ḥadīth*, type 1, defines ṣaḥīḥ by a
connected isnād, integrity and precision throughout, and freedom from
shudhūdh and a disqualifying ʿilla. Ibn Ḥajar, *Nukhbat al-Fikar*
(`src:openiti-nukhba-shamela5940/v04:p722`), names the intrinsic grades
of an āḥād report and distinguishes lighter precision from full precision.

Each field records a critical finding for the report and route under review.
Continuity, integrity, and precision concern the entire route. Findings about
shudhūdh and ʿilla concern that report on the reviewed evidence. An unresolved
finding supplies neither a positive premise nor a refutation.
-/

namespace Hadith.ClassicalCriteria

inductive Finding where
  | established | refuted | unresolved
  deriving DecidableEq, Repr

/-- Precision across the transmitters on the route, assessed for this report. -/
inductive Dabt where
  | full | light | inadequate | unresolved
  deriving DecidableEq, Repr

structure RouteFindings where
  ittisal : Finding
  adala : Finding
  dabt : Dabt
  freeOfShudhudh : Finding
  freeOfQadihIlla : Finding
  deriving Repr

namespace RouteFindings

/-- The conditions shared by ṣaḥīḥ li-dhātihi and ḥasan li-dhātihi. -/
def Common (r : RouteFindings) : Prop :=
  r.ittisal = .established ∧ r.adala = .established ∧
    r.freeOfShudhudh = .established ∧ r.freeOfQadihIlla = .established

instance (r : RouteFindings) : Decidable r.Common := by
  unfold Common
  infer_instance

/-- Ibn al-Ṣalāḥ's ṣaḥīḥ conditions for the report and its isnād. -/
def SahihConditions (r : RouteFindings) : Prop := r.Common ∧ r.dabt = .full

/-- Ibn Ḥajar's conditions for ḥasan li-dhātihi, within the āḥād classification. -/
def HasanConditions (r : RouteFindings) : Prop := r.Common ∧ r.dabt = .light

end RouteFindings

inductive IntrinsicGrade where
  | sahihLiDhatihi | hasanLiDhatihi
  deriving DecidableEq, Repr

/-- Classify an āḥād report by its own route. `none` withholds an intrinsic grade. -/
def intrinsicGrade (ahad : Finding) (r : RouteFindings) : Option IntrinsicGrade :=
  if ahad = .established ∧ r.Common then
    match r.dabt with
    | .full => some .sahihLiDhatihi
    | .light => some .hasanLiDhatihi
    | .inadequate | .unresolved => none
  else none

theorem intrinsic_sahih_iff (ahad : Finding) (r : RouteFindings) :
    intrinsicGrade ahad r = some .sahihLiDhatihi ↔
      ahad = .established ∧ r.SahihConditions := by
  unfold intrinsicGrade RouteFindings.SahihConditions
  split
  · rename_i h
    cases hd : r.dabt <;> simp_all
  · rename_i h
    constructor
    · simp
    · rintro ⟨scope, common, _⟩
      exact (h ⟨scope, common⟩).elim

theorem intrinsic_hasan_iff (ahad : Finding) (r : RouteFindings) :
    intrinsicGrade ahad r = some .hasanLiDhatihi ↔
      ahad = .established ∧ r.HasanConditions := by
  unfold intrinsicGrade RouteFindings.HasanConditions
  split
  · rename_i h
    cases hd : r.dabt <;> simp_all
  · rename_i h
    constructor
    · simp
    · rintro ⟨scope, common, _⟩
      exact (h ⟨scope, common⟩).elim

theorem intrinsic_none_of_unreviewed_defect (ahad : Finding) (r : RouteFindings)
    (h : r.freeOfQadihIlla = .unresolved) : intrinsicGrade ahad r = none := by
  simp [intrinsicGrade, RouteFindings.Common, h]

/-- The wording of the sixth *martaba* in the introduction to *Taqrīb al-Tahdhīb*
(`src:openiti-taqrib-jk121/v01:p074`). The finding concerns a qualifying
mutābaʿa of this narration. The outcome describes the narrator in this usage. -/
inductive SixthRankStatus where
  | maqbul | layyinAlHadith
  deriving DecidableEq, Repr

def sixthRankStatus : Finding → Option SixthRankStatus
  | .established => some .maqbul
  | .refuted => some .layyinAlHadith
  | .unresolved => none

theorem sixth_rank_maqbul_iff (h : Finding) :
    sixthRankStatus h = some .maqbul ↔ h = .established := by cases h <;> decide

theorem sixth_rank_layyin_iff (h : Finding) :
    sixthRankStatus h = some .layyinAlHadith ↔ h = .refuted := by cases h <;> decide

end Hadith.ClassicalCriteria
