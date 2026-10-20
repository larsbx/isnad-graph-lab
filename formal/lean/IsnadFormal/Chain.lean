import IsnadFormal.Grade

/-!
# The *ṣaḥīḥ* isnad (Ibn al-Ṣalāḥ, *ʿUlūm al-ḥadīth*, first type)

> *al-ḥadīth al-ṣaḥīḥ* is the *musnad* whose isnad is connected by the
> transmission of an *ʿadl ḍābiṭ* from an *ʿadl ḍābiṭ* to its end, and which is
> neither *shādhdh* nor *muʿallal*.

That gives five conditions:

1. *ittiṣāl al-sanad*: every link is a direct transmission;
2. *ʿadāla* and
3. *ḍabṭ* of every narrator: Ibn Ḥajar's ranks 1–3;
4. no *shudhūdh*;
5. no *ʿilla*.

Conditions 4 and 5 are judgements made by comparing routes and texts, and are
outside a structural verdict. This file proves that the structural verdict
says *ṣaḥīḥ* exactly when conditions 1–3 hold, and that adding narrators can
only lower it: an isnad is as strong as its weakest link.
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

/-- Condition 1, *ittiṣāl*: no link is a gap. -/
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

/-- **Ibn al-Ṣalāḥ, conditions 1–3.** The structural verdict is *ṣaḥīḥ* exactly
when the isnad is connected and every narrator is ranked 1–3 (*ʿadl ḍābiṭ*). -/
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
theorem append_no_better (c d : Chain) : c.verdict.code ≤ (c.append d).verdict.code := by
  unfold Chain.verdict structuralVerdict Chain.append Chain.worst
  simp only [effRank, List.map_append, worstOf_append]
  have hm : (rankVerdict (worstOf (c.ranks.map effRank))).code ≤
      (rankVerdict (max (worstOf (c.ranks.map effRank)) (worstOf (d.ranks.map effRank)))).code :=
    rankVerdict_mono (Nat.le_max_left _ _)
  cases hc : c.gap <;> cases hcd : (Chain.gap ⟨c.ranks ++ d.ranks, c.gaps ++ d.gaps,
      c.headGap || d.headGap, c.tailGap || d.tailGap⟩)
  all_goals simp only [Bool.false_eq_true, ite_false, ite_true, Verdict.worse_code]
  all_goals simp only [Chain.gap, List.any_append, Bool.or_eq_true, Bool.or_eq_false_iff] at hc hcd
  all_goals first | omega | (simp_all; done) | skip
  all_goals simp [Verdict.code] at *
  all_goals omega

/-- A *mursal* (the Companion dropped: a gap at the head) is never *ṣaḥīḥ*. -/
theorem mursal_not_sahih (c : Chain) (h : c.headGap = true) : c.verdict ≠ .sahih := by
  intro hs
  have := ((sahih_iff c).mp hs).1.1
  simp_all

end Isnad
