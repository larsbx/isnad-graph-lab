/-!
# Grading an isnad: the verdict of a single rank

The source grades every narrator on Ibn Ḥajar's twelve *marātib* (Taqrīb
al-Tahdhīb, muqaddima):

| rank | Ibn Ḥajar's level                                   |
|-----:|-----------------------------------------------------|
| 1    | the Companions                                      |
| 2    | the most emphatic praise (*awthaq al-nās*, *thiqa thiqa*) |
| 3    | *thiqa*, *mutqin*, *thabt*                          |
| 4    | *ṣadūq*, *lā baʾsa bihi*                            |
| 5    | *ṣadūq* with a defect of memory or doctrine         |
| 6    | *maqbūl* (accepted when corroborated)               |
| 7    | *mastūr* / *majhūl al-ḥāl*                          |
| 8    | *ḍaʿīf*                                             |
| 9    | *majhūl* (unknown)                                  |
| 10   | *matrūk*                                            |
| 11   | *muttaham bi-l-kadhib*                              |
| 12   | *kadhdhāb*, *waḍḍāʿ*                                |

The source's verdict for a rank (and `isnad_graph.assess.structural_verdict`)
is: ranks 1–3 *ṣaḥīḥ*, 4–6 *ḥasan*, 7–9 *ḍaʿīf*, 10 very weak, 11 accused,
12 fabricated. A narrator the source does not rank is *majhūl*: rank 9.
-/

namespace Isnad

/-- The source's isnad verdict codes, best first (`sanads.matn_no`). -/
inductive Verdict where
  | sahih | hasan | daif | veryDaif | accused | mawdu
  deriving DecidableEq, Repr

namespace Verdict

def code : Verdict → Nat
  | sahih => 0 | hasan => 1 | daif => 2 | veryDaif => 3 | accused => 4 | mawdu => 5

def ofCode : Nat → Verdict
  | 0 => sahih | 1 => hasan | 2 => daif | 3 => veryDaif | 4 => accused | _ => mawdu

/-- The worse of two verdicts. -/
def worse (a b : Verdict) : Verdict := ofCode (max a.code b.code)

/-- *Maqbūl*: accepted, i.e. *ṣaḥīḥ* or *ḥasan*. -/
def acceptable (v : Verdict) : Prop := v.code ≤ 1

theorem code_ofCode {n : Nat} (h : n ≤ 5) : (ofCode n).code = n := by
  match n, h with
  | 0, _ | 1, _ | 2, _ | 3, _ | 4, _ | 5, _ => rfl

theorem code_le (v : Verdict) : v.code ≤ 5 := by cases v <;> decide

theorem worse_code (a b : Verdict) : (worse a b).code = max a.code b.code :=
  code_ofCode (by have := code_le a; have := code_le b; omega)

end Verdict

/-- The rank of *majhūl*, given to a narrator the source does not rank. -/
def majhulRank : Nat := 9

/-- A narrator's rank, unknown read as *majhūl*. -/
def effRank : Option Nat → Nat
  | none => majhulRank
  | some r => r

/-- The verdict a rank supports on its own. -/
def rankVerdict (r : Nat) : Verdict :=
  if r ≤ 3 then .sahih else if r ≤ 6 then .hasan else if r ≤ 9 then .daif
  else if r = 10 then .veryDaif else if r = 11 then .accused else .mawdu

/-- The structural verdict: the weakest rank decides, and a gap caps it at *ḍaʿīf*. -/
def structuralVerdict (worst : Option Nat) (gap : Bool) : Verdict :=
  let v := rankVerdict (effRank worst)
  if gap then v.worse .daif else v

theorem rankVerdict_mono {r s : Nat} (h : r ≤ s) : (rankVerdict r).code ≤ (rankVerdict s).code := by
  unfold rankVerdict
  repeat' split
  all_goals simp only [Verdict.code]
  all_goals omega

theorem rankVerdict_sahih {r : Nat} : rankVerdict r = .sahih ↔ r ≤ 3 := by
  unfold rankVerdict
  repeat' split
  all_goals simp_all
  all_goals omega

theorem rankVerdict_acceptable {r : Nat} : (rankVerdict r).acceptable ↔ r ≤ 6 := by
  unfold rankVerdict Verdict.acceptable
  repeat' split
  all_goals simp only [Verdict.code]
  all_goals omega

/-- An unranked narrator is never enough for *ṣaḥīḥ*: he is *majhūl*. -/
theorem unknown_not_sahih (gap : Bool) : structuralVerdict none gap ≠ .sahih := by
  cases gap <;> decide

/-- Any gap caps the verdict at *ḍaʿīf* or worse. -/
theorem gap_caps (w : Option Nat) : 2 ≤ (structuralVerdict w true).code := by
  simp only [structuralVerdict, ite_true, Verdict.worse_code]
  exact Nat.le_max_right _ _

/-- A gap never makes a verdict *ṣaḥīḥ* or *ḥasan*. -/
theorem gap_not_acceptable (w : Option Nat) : ¬ (structuralVerdict w true).acceptable := by
  have := gap_caps w
  unfold Verdict.acceptable
  omega

end Isnad
