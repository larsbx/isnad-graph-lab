/-!
# The defect lift's statistics

`isnad_graph.assess.stratified_inference`, transcribed. A comparison is a list
of strata (the structural verdicts *ṣaḥīḥ*, *ḥasan*); each stratum is a 2×2
table: of `n1` reports with the defect `a` were rejected by the grader, of `n0`
without it `b`. With `t = n1 + n0` and `r = a + b`:

* the Mantel–Haenszel risk ratio `Σ a·n0/t / Σ b·n1/t`;
* the signed CMH score `Σ (a − n1·r/t) / √(Σ n1·n0·r·(t−r) / (t²·(t−1)))`;
* the exact conditional p: given every stratum's margins, `a` is
  hypergeometric, with weight `C(n1, x)·C(n0, r − x)` on `x`; the strata are
  independent; p is twice the smaller inclusive tail of `Σ a`, capped at 1.

The exact test is stated here over the integers, as pooled tail weights; no
real number enters. This file proves:

* **the labels do not matter**: swapping *flagged* and *clean* negates the
  score, keeps the variance, inverts the risk ratio, and leaves the exact p
  unchanged (`score_swap`, `var_swap`, `mh_swap`, `pExact_swap`);
* **the null case**: a degenerate stratum (one margin empty, or all or none
  rejected) has no score and no variance, and leaves the exact p unchanged
  (`degenerate_score`, `var_eq_zero_iff`, `pExact_degenerate`);
* **p is a probability**: `0 < p ≤ 1` (`pExact_pos`, `pExact_le`).

The conformance runner recomputes the comparisons exactly and checks the
Python's floating-point values against them.
-/

namespace Isnad

/-! ## Binomial coefficients -/

def choose : Nat → Nat → Nat
  | _, 0 => 1
  | 0, _ + 1 => 0
  | n + 1, k + 1 => choose n k + choose n (k + 1)

theorem choose_eq_zero_of_lt : ∀ {n k : Nat}, n < k → choose n k = 0
  | 0, _ + 1, _ => rfl
  | n + 1, k + 1, h => by
    simp only [choose, choose_eq_zero_of_lt (by omega : n < k), choose_eq_zero_of_lt (by omega : n < k + 1)]

theorem choose_pos : ∀ {n k : Nat}, k ≤ n → 0 < choose n k
  | _, 0, _ => by simp [choose]
  | n + 1, k + 1, h => by simp only [choose]; have := choose_pos (n := n) (k := k) (by omega); omega

theorem choose_one : ∀ n, choose n 1 = n
  | 0 => rfl
  | n + 1 => by rw [choose, choose_one n]; simp [choose]; omega

theorem choose_succ_right : ∀ n k, choose n (k + 1) * (k + 1) = choose n k * (n - k)
  | 0, k => by simp [choose]
  | n + 1, 0 => by simp [choose, choose_one]; omega
  | n + 1, j + 1 => by
    have h1 := choose_succ_right n j
    have h2 := choose_succ_right n (j + 1)
    simp only [choose]
    by_cases hn : j + 1 ≤ n
    · obtain ⟨d, rfl⟩ : ∃ d, n = j + 1 + d := ⟨n - (j + 1), by omega⟩
      have e1 : j + 1 + d - j = d + 1 := by omega
      have e2 : j + 1 + d - (j + 1) = d := by omega
      have e3 : j + 1 + d + 1 - (j + 1) = d + 1 := by omega
      rw [e1] at h1; rw [e2] at h2; rw [e3]
      grind
    · have c1 := choose_eq_zero_of_lt (n := n) (k := j + 1) (by omega)
      have c2 := choose_eq_zero_of_lt (n := n) (k := j + 2) (by omega)
      have : n + 1 - (j + 1) = 0 := by omega
      simp [c1, c2, this]

/-- `C(n, k)` by the multiplicative formula, for execution. -/
def chooseFast (n : Nat) : Nat → Nat
  | 0 => 1
  | k + 1 => chooseFast n k * (n - k) / (k + 1)

theorem chooseFast_eq (n : Nat) : ∀ k, chooseFast n k = choose n k
  | 0 => by simp [chooseFast, choose]
  | k + 1 => by
    rw [chooseFast, chooseFast_eq n k, ← choose_succ_right, Nat.mul_div_cancel _ (by omega)]

/-! ## Sums over ranges -/

theorem le_sum_map {f : Nat → Nat} : ∀ {l : List Nat} {x : Nat}, x ∈ l → f x ≤ (l.map f).sum
  | y :: l, x, h => by
    rcases List.mem_cons.1 h with rfl | h
    · simp
    · have := le_sum_map (f := f) h; simp; omega

theorem sum_map_le {f g : Nat → Nat} : ∀ {l : List Nat}, (∀ x ∈ l, f x ≤ g x) →
    (l.map f).sum ≤ (l.map g).sum
  | [], _ => by simp
  | x :: l, h => by
    have := h x (by simp); have := sum_map_le (l := l) fun y hy => h y (by simp [hy])
    simp; omega

/-- Summing over `[lo', lo' + n)` is summing the reflection `x ↦ r − x` over `[lo, lo + n)`. -/
theorem sum_range'_reflect (g : Nat → Nat) : ∀ (n lo lo' r : Nat), lo + lo' + n = r + 1 →
    ((List.range' lo' n).map g).sum = ((List.range' lo n).map fun x => g (r - x)).sum
  | 0, _, _, _, _ => rfl
  | n + 1, lo, lo', r, h => by
    rw [List.range'_concat, List.range'_succ, List.map_append, List.sum_append,
      sum_range'_reflect g n (lo + 1) lo' r (by omega)]
    have : r - lo = lo' + 1 * n := by omega
    simp [this]; omega

/-! ## Tables -/

/-- A stratum: `a` of `n1` flagged reports rejected, `b` of `n0` clean ones. -/
structure Table where
  a : Nat
  n1 : Nat
  b : Nat
  n0 : Nat
  deriving Repr, DecidableEq

namespace Table

def t (s : Table) : Nat := s.n1 + s.n0
def r (s : Table) : Nat := s.a + s.b
def Valid (s : Table) : Prop := s.a ≤ s.n1 ∧ s.b ≤ s.n0
/-- Flagged and clean exchanged. -/
def swap (s : Table) : Table := ⟨s.b, s.n0, s.a, s.n1⟩
/-- One margin empty, or none or all rejected: the margins fix `a`. -/
def Degenerate (s : Table) : Prop := s.n1 = 0 ∨ s.n0 = 0 ∨ s.r = 0 ∨ s.r = s.t

/-- The support of `a` given the margins, `[max 0 (r − n0), min n1 r]`. -/
def lo (s : Table) : Nat := s.r - s.n0
def hi (s : Table) : Nat := min s.n1 s.r
def supp (s : Table) : List Nat := List.range' s.lo (s.hi + 1 - s.lo)
/-- The hypergeometric weight of `a = x`: `C(n1, x)·C(n0, r − x)`. -/
def w (s : Table) (x : Nat) : Nat := chooseFast s.n1 x * chooseFast s.n0 (s.r - x)

/-- `t · (a − n1·r/t)`: the stratum's score, scaled. -/
def score (s : Table) : Int := (s.t : Int) * s.a - s.n1 * s.r
/-- `t²·(t−1) · Var a`. -/
def varNum (s : Table) : Nat := s.n1 * s.n0 * s.r * (s.t - s.r)
/-- The Mantel–Haenszel terms, `a·n0` and `b·n1`, each over `t`. -/
def mhNum (s : Table) : Nat := s.a * s.n0
def mhDen (s : Table) : Nat := s.b * s.n1

theorem mem_supp {s : Table} {x : Nat} : x ∈ s.supp ↔ s.lo ≤ x ∧ x ≤ s.hi := by
  simp only [supp, List.mem_range'_1]; omega

theorem a_mem_supp {s : Table} (h : s.Valid) : s.a ∈ s.supp := by
  rw [mem_supp]; unfold lo hi r; unfold Valid at h; omega

theorem w_pos {s : Table} {x : Nat} (hx : x ∈ s.supp) : 0 < s.w x := by
  rw [mem_supp] at hx; unfold lo hi at hx
  simp only [w, chooseFast_eq]
  exact Nat.mul_pos (choose_pos (by omega)) (choose_pos (by omega))

theorem swap_t (s : Table) : s.swap.t = s.t := by simp [swap, t]; omega
theorem swap_r (s : Table) : s.swap.r = s.r := by simp [swap, r]; omega

theorem w_swap {s : Table} {x : Nat} (hx : x ∈ s.supp) : s.swap.w (s.r - x) = s.w x := by
  rw [mem_supp] at hx; unfold lo hi at hx
  simp only [w, swap_r]
  simp only [swap]
  rw [show s.r - (s.r - x) = x by omega, Nat.mul_comm]

/-- Summing over the swapped stratum's support is summing over the reflection. -/
theorem sum_supp_swap {s : Table} (h : s.Valid) (g : Nat → Nat) :
    (s.swap.supp.map g).sum = (s.supp.map fun x => g (s.r - x)).sum := by
  unfold supp
  have e : s.swap.hi + 1 - s.swap.lo = s.hi + 1 - s.lo := by
    unfold hi lo; rw [swap_r]; simp only [swap]; unfold r Valid at *; omega
  rw [e]
  exact sum_range'_reflect g _ _ _ _ (by unfold hi lo; rw [swap_r]; simp only [swap]; unfold r Valid at *; omega)

theorem supp_degenerate {s : Table} (h : s.Valid) (hd : s.Degenerate) : s.supp = [s.a] := by
  have : s.lo = s.a ∧ s.hi + 1 - s.lo = 1 := by
    unfold lo hi; unfold Degenerate t r at hd; unfold r; unfold Valid at h; omega
  have h2 : s.hi + 1 - s.a = 1 := this.1 ▸ this.2
  simp [supp, this.1, h2]

/-! ### Score, variance, risk ratio -/

theorem score_swap (s : Table) : s.swap.score = - s.score := by
  simp only [score, swap, t, r]; push_cast; grind

theorem var_swap (s : Table) : s.swap.varNum = s.varNum := by
  simp only [varNum, swap_t, swap_r]; simp only [swap]; grind

theorem mh_swap (s : Table) : s.swap.mhNum = s.mhDen ∧ s.swap.mhDen = s.mhNum := by
  simp [mhNum, mhDen, swap, Nat.mul_comm]

theorem degenerate_score {s : Table} (h : s.Valid) (hd : s.Degenerate) : s.score = 0 := by
  unfold Degenerate t r at hd; unfold Valid at h
  rcases hd with hd | hd | hd | hd
  · have : s.a = 0 := by omega
    simp [score, t, r, hd, this]
  · have : s.b = 0 := by omega
    simp only [score, t, r, hd, this]; push_cast; grind
  · have : s.a = 0 := by omega
    have hb : s.b = 0 := by omega
    simp [score, t, r, this, hb]
  · have ha : s.a = s.n1 := by omega
    have hb : s.b = s.n0 := by omega
    simp only [score, t, r, ha, hb]; push_cast; grind

/-- **The null case.** A stratum has no variance exactly when it is degenerate. -/
theorem var_eq_zero_iff {s : Table} (h : s.Valid) : s.varNum = 0 ↔ s.Degenerate := by
  unfold varNum Degenerate t r; unfold Valid at h
  simp only [Nat.mul_eq_zero]; omega

end Table

/-! ## The exact conditional test -/

open Table

/-- Weight of the outcomes with `Σ a ≤ c`. -/
def tailLe : List Table → Int → Nat
  | [], c => if 0 ≤ c then 1 else 0
  | s :: ss, c => (s.supp.map fun x => s.w x * tailLe ss (c - x)).sum

/-- Weight of the outcomes with `Σ a ≥ c`. -/
def tailGe : List Table → Int → Nat
  | [], c => if c ≤ 0 then 1 else 0
  | s :: ss, c => (s.supp.map fun x => s.w x * tailGe ss (c - x)).sum

def total : List Table → Nat
  | [] => 1
  | s :: ss => (s.supp.map s.w).sum * total ss

def observed (ss : List Table) : Int := (ss.map fun s => (s.a : Int)).sum
def margins (ss : List Table) : Int := (ss.map fun s => (s.r : Int)).sum

/-- The exact two-sided p, `min(T, 2·min(L, R)) / T`, as numerator and denominator. -/
def pExact (ss : List Table) : Nat × Nat :=
  (min (total ss) (2 * min (tailLe ss (observed ss)) (tailGe ss (observed ss))), total ss)

theorem tails_swap : ∀ (ss : List Table), (∀ s ∈ ss, s.Valid) → ∀ c : Int,
    tailLe (ss.map swap) (margins ss - c) = tailGe ss c ∧
      tailGe (ss.map swap) (margins ss - c) = tailLe ss c
  | [], _, c => by simp only [List.map, tailLe, tailGe, margins, List.sum_nil]; constructor <;> split <;> split <;> omega
  | s :: ss, hv, c => by
    have hs := hv s (by simp)
    have ih := tails_swap ss (fun s h => hv s (by simp [h]))
    simp only [List.map, tailLe, tailGe]
    rw [sum_supp_swap hs, sum_supp_swap hs]
    constructor
    all_goals
      refine congrArg List.sum (List.map_congr_left fun x hx => ?_)
      rw [w_swap hx]
      have hxr : x ≤ s.r := by rw [mem_supp] at hx; unfold hi at hx; omega
      have : margins (s :: ss) - c - ((s.r - x : Nat) : Int) = margins ss - (c - x) := by
        simp only [margins, List.map, List.sum_cons]; omega
      rw [this]
    · rw [(ih (c - x)).1]
    · rw [(ih (c - x)).2]

theorem total_swap : ∀ (ss : List Table), (∀ s ∈ ss, s.Valid) → total (ss.map swap) = total ss
  | [], _ => rfl
  | s :: ss, hv => by
    have hs := hv s (by simp)
    simp only [List.map, total, total_swap ss (fun s h => hv s (by simp [h])), sum_supp_swap hs]
    congr 2
    exact List.map_congr_left fun x hx => w_swap hx

theorem observed_swap (ss : List Table) : observed (ss.map swap) = margins ss - observed ss := by
  induction ss with
  | nil => simp [observed, margins]
  | cons s ss ih => simp only [observed, margins, List.map, List.sum_cons] at *; simp only [swap, r] at *; omega

/-- **The labels do not matter.** Swapping flagged and clean leaves the exact p unchanged. -/
theorem pExact_swap (ss : List Table) (hv : ∀ s ∈ ss, s.Valid) : pExact (ss.map swap) = pExact ss := by
  simp only [pExact, observed_swap, total_swap ss hv, (tails_swap ss hv _).1, (tails_swap ss hv _).2,
    Nat.min_comm (tailGe ss _)]

theorem tailLe_pos : ∀ (ss : List Table), (∀ s ∈ ss, s.Valid) → ∀ c, observed ss ≤ c → 0 < tailLe ss c
  | [], _, c, h => by
    simp only [observed, List.map, List.sum_nil] at h; simp [tailLe, h]
  | s :: ss, hv, c, h => by
    have hs := hv s (by simp)
    have hm := a_mem_supp hs
    have := le_sum_map (f := fun x => s.w x * tailLe ss (c - x)) hm
    have := Nat.mul_pos (w_pos hm) (tailLe_pos ss (fun s h => hv s (by simp [h])) (c - s.a)
      (by simp only [observed, List.map, List.sum_cons] at h; simp only [observed]; omega))
    simp only [tailLe]; omega

theorem tailGe_pos : ∀ (ss : List Table), (∀ s ∈ ss, s.Valid) → ∀ c, c ≤ observed ss → 0 < tailGe ss c
  | [], _, c, h => by
    simp only [observed, List.map, List.sum_nil] at h; simp [tailGe, h]
  | s :: ss, hv, c, h => by
    have hs := hv s (by simp)
    have hm := a_mem_supp hs
    have := le_sum_map (f := fun x => s.w x * tailGe ss (c - x)) hm
    have := Nat.mul_pos (w_pos hm) (tailGe_pos ss (fun s h => hv s (by simp [h])) (c - s.a)
      (by simp only [observed, List.map, List.sum_cons] at h; simp only [observed]; omega))
    simp only [tailGe]; omega

theorem sum_mul_right {f : Nat → Nat} (k : Nat) : ∀ l : List Nat,
    (l.map f).sum * k = (l.map fun x => f x * k).sum
  | [] => by simp
  | x :: l => by simp [Nat.add_mul, sum_mul_right k l]

theorem tailLe_le_total : ∀ (ss : List Table) (c : Int), tailLe ss c ≤ total ss
  | [], c => by simp only [tailLe, total]; split <;> omega
  | s :: ss, c => by
    simp only [tailLe, total, sum_mul_right]
    exact sum_map_le fun x _ => Nat.mul_le_mul_left _ (tailLe_le_total ss _)

/-- **p is a probability**: `0 < p ≤ 1`. -/
theorem pExact_pos (ss : List Table) (hv : ∀ s ∈ ss, s.Valid) : 0 < (pExact ss).1 := by
  have hl := tailLe_pos ss hv _ (Int.le_refl _)
  have hg := tailGe_pos ss hv _ (Int.le_refl _)
  have ht := tailLe_le_total ss (observed ss)
  simp only [pExact]; omega

theorem pExact_le (ss : List Table) : (pExact ss).1 ≤ (pExact ss).2 := Nat.min_le_left _ _

/-- **The null case.** A degenerate stratum scales every weight by the same
positive factor, so the exact p is unchanged. -/
theorem pExact_degenerate {s : Table} (ss : List Table) (h : s.Valid) (hd : s.Degenerate) :
    pExact (s :: ss) = (s.w s.a * (pExact ss).1, s.w s.a * (pExact ss).2) ∧ 0 < s.w s.a := by
  refine ⟨?_, w_pos (a_mem_supp h)⟩
  have ho : observed (s :: ss) - s.a = observed ss := by
    simp only [observed, List.map, List.sum_cons]; omega
  simp only [pExact, tailLe, tailGe, total, supp_degenerate h hd, List.map, List.sum_cons,
    List.sum_nil, Nat.add_zero, ho]
  rw [Nat.mul_min_mul_left, Nat.mul_left_comm 2, Nat.mul_min_mul_left]

/-! ### Execution

The same test over weight lists computed once per stratum. -/

def wts (s : Table) : List (Nat × Nat) := s.supp.map fun x => (x, s.w x)

def tailLeW : List (List (Nat × Nat)) → Int → Nat
  | [], c => if 0 ≤ c then 1 else 0
  | W :: Ws, c => (W.map fun p => p.2 * tailLeW Ws (c - p.1)).sum

def tailGeW : List (List (Nat × Nat)) → Int → Nat
  | [], c => if c ≤ 0 then 1 else 0
  | W :: Ws, c => (W.map fun p => p.2 * tailGeW Ws (c - p.1)).sum

def totalW : List (List (Nat × Nat)) → Nat
  | [] => 1
  | W :: Ws => (W.map (·.2)).sum * totalW Ws

def pExactFast (ss : List Table) : Nat × Nat :=
  let W := ss.map wts
  let o := observed ss
  (min (totalW W) (2 * min (tailLeW W o) (tailGeW W o)), totalW W)

theorem tailLeW_eq : ∀ (ss : List Table) c, tailLeW (ss.map wts) c = tailLe ss c
  | [], _ => rfl
  | s :: ss, c => by simp only [List.map_cons, tailLeW, tailLe, wts, List.map_map, tailLeW_eq ss]; rfl

theorem tailGeW_eq : ∀ (ss : List Table) c, tailGeW (ss.map wts) c = tailGe ss c
  | [], _ => rfl
  | s :: ss, c => by simp only [List.map_cons, tailGeW, tailGe, wts, List.map_map, tailGeW_eq ss]; rfl

theorem totalW_eq : ∀ ss : List Table, totalW (ss.map wts) = total ss
  | [] => rfl
  | s :: ss => by simp only [List.map_cons, totalW, total, wts, List.map_map, totalW_eq ss]; rfl

theorem pExactFast_eq (ss : List Table) : pExactFast ss = pExact ss := by
  simp [pExactFast, pExact, tailLeW_eq, tailGeW_eq, totalW_eq]

/-! ## Pooled score -/

/-- A sum of fractions `p/q`, as one fraction. -/
def fsum : List (Int × Nat) → Int × Nat
  | [] => (0, 1)
  | (p, q) :: l => ((fsum l).1 * q + p * (fsum l).2, q * (fsum l).2)

/-- The pooled score `Σ (a − n1·r/t)` over the strata with `t > 0`. -/
def score (ss : List Table) : Int × Nat :=
  fsum ((ss.filter fun s => s.t ≠ 0).map fun s => (s.score, s.t))

theorem fsum_neg : ∀ l : List (Int × Nat),
    fsum (l.map fun x => (-x.1, x.2)) = (-(fsum l).1, (fsum l).2)
  | [] => by simp [fsum]
  | (p, q) :: l => by
    simp only [List.map, fsum, fsum_neg l, Prod.mk.injEq]
    constructor <;> grind

/-- **The labels do not matter** for the pooled score: it changes sign. -/
theorem score_swap_pooled (ss : List Table) :
    score (ss.map swap) = (-(score ss).1, (score ss).2) := by
  unfold score
  have hf : (fun s : Table => decide (s.t ≠ 0)) ∘ swap = fun s => decide (s.t ≠ 0) := by
    funext s; simp [swap_t]
  rw [List.filter_map, hf, List.map_map, ← fsum_neg, List.map_map]
  congr 1
  exact List.map_congr_left fun s _ => by simp [Table.score_swap, swap_t]

end Isnad
