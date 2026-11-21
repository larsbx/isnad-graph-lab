import Hadith.ClassicalCriteria
import IsnadFormal.Grade

/-!
# The graph's structural ṣaḥīḥ code

The graph uses observed gap markers and narrator ranks to score a stored
chain. Ibn al-Ṣalāḥ's definition (*ʿUlūm al-ḥadīth*, type 1) calls for
established continuity, uprightness and precision throughout, and findings
on shudhūdh and a disqualifying ʿilla. Ibn Ḥajar's intrinsic criteria use
these findings for a reviewed āḥād report (`Hadith.ClassicalCriteria`).
A missing gap marker records what the graph observed. Assessing the actual
transmission and checking the report against competing evidence require
source findings. Here `sahih_iff` characterizes the corpus code.
-/

namespace Isnad

/-- A chain as the verdict sees it: the rank of every narrator below the
Prophet ﷺ (`none` when unranked), and whether each link is a gap (irsāl,
inqiṭāʿ, taʿlīq, or an unnamed narrator), with the ends' gaps. -/
structure Chain where
  ranks : List (Option Nat)
  gaps : List Bool
  headGap : Bool := false
  tailGap : Bool := false

/-- The weakest (largest) rank of a list. -/
def worstOf : List Nat → Nat
  | [] => 0
  | x :: xs => max x (worstOf xs)

namespace Chain

def worst (c : Chain) : Nat := worstOf (c.ranks.map effRank)

/-- No gap is marked in the graph record. -/
def connected (c : Chain) : Prop := c.headGap = false ∧ c.tailGap = false ∧ ∀ g ∈ c.gaps, g = false

def gap (c : Chain) : Bool := c.headGap || c.tailGap || c.gaps.any id

def verdict (c : Chain) : Verdict := structuralVerdict (some c.worst) c.gap

def append (c d : Chain) : Chain :=
  ⟨c.ranks ++ d.ranks, c.gaps ++ d.gaps, c.headGap || d.headGap, c.tailGap || d.tailGap⟩

end Chain

theorem worstOf_le {l : List Nat} {k : Nat} : worstOf l ≤ k ↔ ∀ x ∈ l, x ≤ k := by
  induction l with
  | nil => simp [worstOf]
  | cons x xs ih => rw [List.forall_mem_cons, ← ih]; exact Nat.max_le

theorem worstOf_append (l m : List Nat) : worstOf (l ++ m) = max (worstOf l) (worstOf m) := by
  induction l with
  | nil => simp [worstOf]
  | cons x xs ih => simp [worstOf, ih, Nat.max_assoc]

theorem effRank_le_three {r : Option Nat} : effRank r ≤ 3 ↔ ∃ k, r = some k ∧ k ≤ 3 := by
  cases r <;> simp [effRank, majhulRank]

theorem Chain.gap_false_iff (c : Chain) : c.gap = false ↔ c.connected := by
  simp [Chain.gap, Chain.connected, List.any_eq_false, and_assoc]

/-- The graph code is ṣaḥīḥ exactly when there is no marked gap and all
supplied ranks meet the cutoff. The empty fold is an algebraic identity. -/
theorem sahih_iff (c : Chain) :
    c.verdict = .sahih ↔ c.connected ∧ ∀ r ∈ c.ranks, ∃ k, r = some k ∧ k ≤ 3 := by
  rw [← Chain.gap_false_iff]
  unfold Chain.verdict structuralVerdict
  cases hg : c.gap
  · simp only [Bool.false_eq_true, ite_false, effRank, rankVerdict_sahih, Chain.worst,
      worstOf_le, List.mem_map, true_and]
    constructor
    · intro h r hr; exact effRank_le_three.mp (h _ ⟨r, hr, rfl⟩)
    · rintro h _ ⟨r, hr, rfl⟩; exact effRank_le_three.mpr (h r hr)
  · simp only [ite_true, Bool.true_eq_false, false_and, iff_false]
    intro h
    have := congrArg Verdict.code h
    rw [Verdict.worse_code] at this
    simp [Verdict.code] at this

/-- **The weakest link.** Joining two chains never gives a better verdict than either. -/
theorem append_no_better (c d : Chain) : c.verdict.code ≤ (c.append d).verdict.code :=
  structuralVerdict_mono
    (by simp only [Chain.worst, Chain.append, List.map_append, worstOf_append]; omega)
    (by simp only [Chain.gap, Chain.append, List.any_append, Bool.or_eq_true]
        rintro ((h | h) | h) <;> simp [h])

/-- A chain with a marked head gap does not receive the graph's ṣaḥīḥ code. -/
theorem mursal_not_sahih (c : Chain) (h : c.headGap = true) : c.verdict ≠ .sahih := by
  intro hs
  have := ((sahih_iff c).mp hs).1.1
  simp_all

/-- A fixed ṣaḥīḥ graph score is compatible with both an established intrinsic
grade and an unresolved ʿilla review. This is a synthetic witness about the
inputs to the two checks. -/
theorem structural_sahih_with_pending_review :
    ∃ c : Chain, c.verdict = .sahih ∧
      ∃ r : Hadith.ClassicalCriteria.RouteFindings,
        Hadith.ClassicalCriteria.intrinsicGrade .established r = some .sahihLiDhatihi ∧
        Hadith.ClassicalCriteria.intrinsicGrade .established
          { r with freeOfQadihIlla := .unresolved } = none :=
  ⟨⟨[some 3], [false], false, false⟩, by decide,
    ⟨.established, .established, .full, .established, .established⟩, by decide, by decide⟩

end Isnad
