import IsnadFormal.CommonLink
import IsnadFormal.Phases

/-!
# Region reduction: why TLC may check the transmission model over fewer years

`formal/quint/transmission.qnt` lets hearings happen in any year of a range;
`transmissionRegions` keeps only the first `k` years of every *region*, a
stretch between consecutive *cuts*. TLC can search that model exhaustively.
This file proves the reduction sound and complete for any model whose guards
and invariants read years only through

* `c ≤ y` for a cut `c` (a lower threshold `L` is the cut `L`; an upper one
  `y ≤ D` is `¬ (D + 1 ≤ y)`, the cut `D + 1`), and
* `y ≤ y'` between years,

closed under negation and conjunction (`Fm`). `reduction`: if a valuation of
the year variables (all the years one behaviour uses) has at most `k`
distinct values in every region, some valuation into the regions' first `k`
years gives every such formula the same truth value. A behaviour of
`transmission` is one such valuation (its guards and invariants at every
step are such formulas), so it maps to a behaviour of `transmissionRegions`
with the same invariant values; the converse holds because the region years
are years. `Conformance.lean` checks that Quint's `REGIONS` is
`regionYears` of the model's cuts.

The map is `g x = start x + rank x − 1`: `start x` is the last cut at or
below `x`; `rank x` counts the distinct values in `x`'s region up to `x`.
-/

namespace Isnad.Regions

/-! ## Cuts and regions -/

/-- No cut separates `x` and `y`. -/
def same (C : List Int) (x y : Int) : Prop := ∀ c ∈ C, c ≤ x ↔ c ≤ y

instance (C : List Int) (x y : Int) : Decidable (same C x y) := by unfold same; infer_instance

/-- The last cut at or below `y` (`first` below every year in play). -/
def start (first : Int) (C : List Int) (y : Int) : Int := (C.filter (· ≤ y)).foldr max first

/-- `y` is among the first `k` years of its region (Quint's `REGIONS`). -/
def inRegions (C : List Int) (k : Nat) (y : Int) : Prop :=
  ∃ c ∈ C, c ≤ y ∧ y - c < k ∧ ∀ d ∈ C, d ≤ y → d ≤ c

instance (C : List Int) (k : Nat) (y : Int) : Decidable (inRegions C k y) := by
  unfold inRegions; infer_instance

/-- The years of `[first, last]` kept by the reduction. -/
def regionYears (C : List Int) (k : Nat) (first last : Int) : List Int :=
  ((List.range (last - first + 1).toNat).map fun i : Nat => first + (i : Int)).filter fun y => decide (inRegions C k y)

theorem same_refl (C : List Int) (x : Int) : same C x x := fun _ _ => Iff.rfl
theorem same_trans {C : List Int} {x y z : Int} (h1 : same C x y) (h2 : same C y z) : same C x z :=
  fun c hc => (h1 c hc).trans (h2 c hc)
theorem same_symm {C : List Int} {x y : Int} (h : same C x y) : same C y x := fun c hc => (h c hc).symm

theorem foldr_max_le {first y : Int} : ∀ {l : List Int}, (∀ x ∈ l, x ≤ y) → first ≤ y →
    l.foldr max first ≤ y
  | [], _, h => h
  | x :: l, hl, h => by
    have := foldr_max_le (l := l) (fun z hz => hl z (by simp [hz])) h
    have := hl x (by simp); simp only [List.foldr_cons]; omega

theorem le_foldr_max {first x : Int} : ∀ {l : List Int}, x ∈ l → x ≤ l.foldr max first
  | y :: l, h => by
    rcases List.mem_cons.1 h with rfl | h
    · simp only [List.foldr_cons]; omega
    · have := le_foldr_max (first := first) h; simp only [List.foldr_cons]; omega

theorem first_le_foldr_max {first : Int} : ∀ {l : List Int}, first ≤ l.foldr max first
  | [] => by simp
  | x :: l => by have := first_le_foldr_max (first := first) (l := l); simp only [List.foldr_cons]; omega

theorem foldr_max_mem {first : Int} : ∀ {l : List Int}, l.foldr max first ∈ first :: l
  | [] => by simp
  | x :: l => by
    simp only [List.foldr_cons]
    have ih := foldr_max_mem (first := first) (l := l)
    by_cases h : x ≤ l.foldr max first
    · rw [Int.max_eq_right h]; rcases List.mem_cons.1 ih with e | e <;> simp [e]
    · rw [Int.max_eq_left (by omega)]; simp

variable {first : Int} {C : List Int}

theorem start_le {y : Int} (h : first ≤ y) : start first C y ≤ y :=
  foldr_max_le (fun x hx => by simp at hx; exact hx.2) h

theorem le_start {c y : Int} (hc : c ∈ C) (hcy : c ≤ y) : c ≤ start first C y :=
  le_foldr_max (by simp [hc, hcy])

theorem first_le_start {y : Int} : first ≤ start first C y := first_le_foldr_max

theorem start_mem (hf : first ∈ C) {y : Int} : start first C y ∈ C := by
  rcases List.mem_cons.1 (foldr_max_mem (first := first) (l := C.filter (· ≤ y))) with e | e
  · rw [start, e]; exact hf
  · exact (List.mem_filter.1 e).1

/-- Between the start of its region and itself, a year has no cut. -/
theorem same_between {x z : Int} (h1 : start first C x ≤ z) (h2 : z ≤ x) : same C z x :=
  fun _ hc => ⟨fun h => Int.le_trans h h2, fun h => Int.le_trans (le_start hc h) h1⟩

theorem start_same {x y : Int} (h : same C x y) : start first C x = start first C y := by
  unfold start; congr 1; exact List.filter_congr fun c hc => by simp [h c hc]

/-! ## Counting -/

theorem length_split {α} (p : α → Bool) : ∀ l : List α,
    l.length = (l.filter p).length + (l.filter fun x => !p x).length
  | [] => rfl
  | x :: l => by
    have := length_split p l
    cases h : p x <;> simp [h] <;> omega

/-- At most `n` distinct integers lie in `[s, s + n)`. -/
theorem nodup_Ico (s : Int) : ∀ (n : Nat) (l : List Int), l.Nodup →
    (∀ v ∈ l, s ≤ v ∧ v < s + n) → l.length ≤ n
  | 0, [], _, _ => Nat.le_refl _
  | 0, v :: _, _, h => by have := h v (by simp); omega
  | n + 1, l, hl, h => by
    have ih := nodup_Ico s n (l.filter (· ≠ s + n)) (hl.filter _) fun v hv => by
      simp only [List.mem_filter, decide_eq_true_eq] at hv
      have := h v hv.1; omega
    have hsplit := length_split (fun v => decide (v ≠ s + n)) l
    have hone : (l.filter fun v => !decide (v ≠ s + n)).length ≤ 1 := by
      have hn := hl.filter (fun v => !decide (v ≠ s + n))
      generalize hm : l.filter (fun v => !decide (v ≠ s + n)) = m at hn
      have hm' : ∀ v ∈ m, v = s + n := fun v hv => by
        rw [← hm] at hv; simp only [List.mem_filter] at hv; simpa using hv.2
      match m, hn, hm' with
      | [], _, _ => simp
      | [_], _, _ => simp
      | a :: b :: _, hn, hm' =>
        have := hm' a (by simp); have := hm' b (by simp)
        exact absurd (by simp_all) (List.nodup_cons.1 hn).1
    omega

/-! ## The map -/

variable (first C)

/-- The distinct values in `x`'s region, up to `x`, among `vals`. -/
def below (vals : List Int) (x : Int) : List Int :=
  vals.filter fun v => decide (same C v x) && decide (v ≤ x)

def g (vals : List Int) (x : Int) : Int := start first C x + (below C vals x).length - 1

variable {first C}

theorem below_pos {vals : List Int} {x : Int} (hx : x ∈ vals) : 0 < (below C vals x).length :=
  List.length_pos_of_mem (a := x) (List.mem_filter.2 ⟨hx, by simp [same_refl C x]⟩)

theorem below_le (hf : first ∈ C) {vals : List Int} (hv : vals.Nodup) {x : Int} (hfx : first ≤ x) :
    ((below C vals x).length : Int) ≤ x - start first C x + 1 := by
  have hs := start_le (C := C) hfx
  have h := nodup_Ico (start first C x) (x - start first C x + 1).toNat (below C vals x)
    (hv.filter _) fun v hv' => by
      simp only [below, List.mem_filter, Bool.and_eq_true, decide_eq_true_eq] at hv'
      have := (hv'.2.1 _ (start_mem hf)).2 hs
      omega
  omega

section
variable (hf : first ∈ C) {vals : List Int} (hv : vals.Nodup) (hfv : ∀ x ∈ vals, first ≤ x)
include hf hv hfv

theorem g_between {x : Int} (hx : x ∈ vals) : start first C x ≤ g first C vals x ∧ g first C vals x ≤ x := by
  have := below_pos (C := C) hx
  have := below_le hf hv (hfv x hx)
  unfold g; omega

theorem g_same {x : Int} (hx : x ∈ vals) : same C (g first C vals x) x :=
  have h := g_between hf hv hfv hx; same_between h.1 h.2

theorem g_inRegions {k : Nat} (hk : ∀ x ∈ vals, (vals.filter fun y => decide (same C y x)).length ≤ k)
    {x : Int} (hx : x ∈ vals) : inRegions C k (g first C vals x) := by
  have hb := g_between hf hv hfv hx
  have hpos := below_pos (C := C) hx
  have hle : (below C vals x).length ≤ k := Nat.le_trans
    (Isnad.filter_length_mono fun y _ h => by simp only [Bool.and_eq_true] at h; exact h.1) (hk x hx)
  refine ⟨start first C x, start_mem hf, hb.1, ?_, fun d hd hdg => le_start hd (Int.le_trans hdg hb.2)⟩
  unfold g; omega

theorem g_strict {x y : Int} (hx : x ∈ vals) (hy : y ∈ vals) (hxy : x < y) :
    g first C vals x < g first C vals y := by
  by_cases hs : same C x y
  · have hlt : (below C vals x).length < (below C vals y).length := by
      apply Nat.lt_of_not_le
      intro hle
      have := Isnad.filter_length_eq (B := vals)
        (p := fun v => decide (same C v x) && decide (v ≤ x))
        (q := fun v => decide (same C v y) && decide (v ≤ y))
        (fun a _ h => by
          simp only [Bool.and_eq_true, decide_eq_true_eq] at h ⊢
          exact ⟨same_trans h.1 hs, Int.le_trans h.2 (Int.le_of_lt hxy)⟩) hle y hy
        (by simp [same_refl])
      simp at this; omega
    unfold g; rw [start_same hs]; omega
  · obtain ⟨c, hc⟩ := Classical.not_forall.1 hs
    obtain ⟨hc, hne⟩ := Classical.not_imp.1 hc
    have hcy : c ≤ y ∧ x < c := by
      by_cases h : c ≤ x
      · exact absurd ⟨fun _ => Int.le_trans h (Int.le_of_lt hxy), fun _ => h⟩ hne
      · exact ⟨Classical.byContradiction fun h' => hne ⟨fun h'' => absurd h'' h, fun h'' => absurd h'' h'⟩,
          by omega⟩
    have := (g_between hf hv hfv hx).2
    have := (g_between hf hv hfv hy).1
    have := le_start (first := first) hc hcy.1
    omega

theorem g_le_iff {x y : Int} (hx : x ∈ vals) (hy : y ∈ vals) :
    x ≤ y ↔ g first C vals x ≤ g first C vals y := by
  rcases Int.lt_trichotomy x y with h | rfl | h
  · have := g_strict hf hv hfv hx hy h; omega
  · omega
  · have := g_strict hf hv hfv hy hx h; omega

end

theorem cut_iff_same {c x y : Int} (hc : c ∈ C) (h : same C y x) : c ≤ x ↔ c ≤ y := (h c hc).symm

/-! ## Formulas over years -/

/-- What a guard or an invariant can say about years: a year is at or above a
cut, or one year is at most another; with negation and conjunction. -/
inductive Fm (V : Type) where
  | cut (c : Int) (v : V)
  | le (v w : V)
  | not (φ : Fm V)
  | and (φ ψ : Fm V)

namespace Fm

def eval {V : Type} (ρ : V → Int) : Fm V → Prop
  | cut c v => c ≤ ρ v
  | le v w => ρ v ≤ ρ w
  | not φ => ¬ φ.eval ρ
  | and φ ψ => φ.eval ρ ∧ ψ.eval ρ

/-- The formula's cuts are in `C` and its variables in `vars`. -/
def Over {V : Type} (C : List Int) (vars : List V) : Fm V → Prop
  | cut c v => c ∈ C ∧ v ∈ vars
  | le v w => v ∈ vars ∧ w ∈ vars
  | not φ => φ.Over C vars
  | and φ ψ => φ.Over C vars ∧ ψ.Over C vars

end Fm

/-- The distinct values of `ρ` on `vars`, sorted. -/
def values {V : Type} (vars : List V) (ρ : V → Int) : List Int := (vars.map ρ).foldr Isnad.ins []

/-- **The region reduction.** If the years a valuation uses fall at most `k`
to a region, mapping each through `g` lands in the regions' first `k` years,
never later than the year itself, and keeps every formula's truth value. -/
theorem reduction {V : Type} (hf : first ∈ C) (k : Nat) (vars : List V) (ρ : V → Int)
    (hρ : ∀ v ∈ vars, first ≤ ρ v)
    (hk : ∀ v ∈ vars, ((values vars ρ).filter fun y => decide (same C y (ρ v))).length ≤ k) :
    (∀ v ∈ vars, inRegions C k (g first C (values vars ρ) (ρ v)) ∧
        first ≤ g first C (values vars ρ) (ρ v) ∧ g first C (values vars ρ) (ρ v) ≤ ρ v) ∧
      ∀ φ : Fm V, φ.Over C vars → (φ.eval ρ ↔ φ.eval fun v => g first C (values vars ρ) (ρ v)) := by
  have hmem : ∀ v ∈ vars, ρ v ∈ values vars ρ := fun v hv =>
    Isnad.mem_foldr_ins.2 (List.mem_map.2 ⟨v, hv, rfl⟩)
  have hv : (values vars ρ).Nodup := (Isnad.sorted_foldr_ins _).imp Int.ne_of_lt
  have hfv : ∀ x ∈ values vars ρ, first ≤ x := fun x hx => by
    obtain ⟨v, hv, rfl⟩ := List.mem_map.1 (Isnad.mem_foldr_ins.1 hx); exact hρ v hv
  have hk' : ∀ x ∈ values vars ρ, ((values vars ρ).filter fun y => decide (same C y x)).length ≤ k :=
    fun x hx => by obtain ⟨v, hv', rfl⟩ := List.mem_map.1 (Isnad.mem_foldr_ins.1 hx); exact hk v hv'
  refine ⟨fun v hv' => ⟨g_inRegions hf hv hfv hk' (hmem v hv'), ?_, (g_between hf hv hfv (hmem v hv')).2⟩, ?_⟩
  · exact Int.le_trans first_le_start (g_between hf hv hfv (hmem v hv')).1
  · intro φ hφ
    induction φ with
    | cut c v => exact cut_iff_same hφ.1 (g_same hf hv hfv (hmem v hφ.2))
    | le v w => exact g_le_iff hf hv hfv (hmem v hφ.1) (hmem w hφ.2)
    | not φ ih => exact not_congr (ih hφ)
    | and φ ψ ih1 ih2 => exact and_congr (ih1 hφ.1) (ih2 hφ.2)

/-- **How many years share a region.** A behaviour of the transmission model
uses the initial year `x0` and one year per hearing, so at most `k + 1`
distinct values. If `x0` and `x0 + 1` are cuts, `x0` is a region of its own,
and no region holds more than `k` of them: the hypothesis of `reduction`. -/
theorem perRegion_of_initial {vals : List Int} {k : Nat} {x0 : Int} (h0 : x0 ∈ C) (h1 : x0 + 1 ∈ C)
    (hx0 : x0 ∈ vals) (hlen : vals.length ≤ k + 1) (hk : 1 ≤ k) (hv : vals.Nodup) (y : Int) :
    (vals.filter fun v => decide (same C v y)).length ≤ k := by
  by_cases hy : same C x0 y
  · -- the region of x0 is {x0}
    have : ∀ v ∈ vals.filter (fun v => decide (same C v y)), v = x0 := fun v hv' => by
      have hs := same_trans (List.mem_filter.1 hv' |>.2 |> of_decide_eq_true) (same_symm hy)
      have := (hs x0 h0).2 (Int.le_refl _); have := (hs (x0 + 1) h1); omega
    have hn := hv.filter (fun v => decide (same C v y))
    generalize vals.filter (fun v => decide (same C v y)) = m at this hn
    match m, hn, this with
    | [], _, _ => simp
    | [_], _, _ => simp; omega
    | a :: b :: _, hn, h =>
      have ha := h a (by simp)
      have hb := h b (by simp)
      exact absurd (by simp [ha, hb]) (List.nodup_cons.1 hn).1
  · have hlt : (vals.filter fun v => decide (same C v y)).length < (vals.filter fun _ => true).length := by
      apply Nat.lt_of_not_le; intro hle
      have := Isnad.filter_length_eq (B := vals) (p := fun v => decide (same C v y)) (q := fun _ => true)
        (fun _ _ _ => rfl) hle x0 hx0 rfl
      exact hy (of_decide_eq_true this)
    rw [show (vals.filter fun _ => true) = vals from List.filter_eq_self.2 fun _ _ => rfl] at hlt; omega

end Isnad.Regions
