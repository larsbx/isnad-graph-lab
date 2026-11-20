/-!
# The phases of a lifeline partition the life

`isnad_graph.lives.phases`, transcribed. A life `[b, d]` is cut by two
windows, *hearing* (from the narrator's teachers) and *teaching* (to the
narrator's students), each clipped to the life, into maximal stretches of one
kind: `hearing`, `teaching`, `both` or `quiet`.

Years are integers here; the conformance vectors carry half-years (every
estimate in the graph is a multiple of ½), so the unit is half a year. A stretch
`[a, b]` is read as the unit cells `x ∈ [a, b)`; a window `[lo, hi]` holds the
cell `x` when `lo ≤ x < hi`.

`phases_partition` proves, for any life `b < d` and any windows:

* **tiling**: the phases run contiguously from `b` to `d`, each non-empty;
* **maximality**: neighbouring phases differ in kind;
* **soundness**: every cell of a phase lies in exactly the windows its kind says.

Every cell of the life thus lies in exactly one phase, of the right kind.
-/

namespace Isnad

inductive Phase where
  | quiet | hearing | teaching | both
  deriving DecidableEq, Repr

namespace Phase

def of : Bool → Bool → Phase
  | true, true => both | true, false => hearing | false, true => teaching | false, false => quiet

def name : Phase → String
  | quiet => "quiet" | hearing => "hearing" | teaching => "teaching" | both => "both"

end Phase

/-- A window `[lo, hi]`, or none. -/
abbrev Window := Option (Int × Int)

namespace Window

/-- The window covers the stretch `[a, b]` (Python's `inside`). -/
def covers : Window → Int → Int → Bool
  | some (lo, hi), a, b => decide (lo ≤ a ∧ b ≤ hi)
  | none, _, _ => false

/-- The window holds the cell `x`. -/
def holds : Window → Int → Bool
  | some (lo, hi), x => decide (lo ≤ x ∧ x < hi)
  | none, _ => false

def clip (b d : Int) : Window → Window :=
  Option.map fun (lo, hi) => (min (max lo b) d, min (max hi b) d)

def ends : Window → List Int
  | some (lo, hi) => [lo, hi]
  | none => []

end Window

/-- The kind of the cell `x`. -/
def phaseAt (h t : Window) (x : Int) : Phase := .of (h.holds x) (t.holds x)

structure Seg where
  kind : Phase
  lo : Int
  hi : Int
  deriving DecidableEq, Repr

/-- Insert into a strictly increasing list, dropping a duplicate. -/
def ins (x : Int) : List Int → List Int
  | [] => [x]
  | y :: ys => if x < y then x :: y :: ys else if x = y then y :: ys else y :: ins x ys

/-- The cut points, sorted without duplicates (Python's `sorted({…})`). -/
def cuts (b d : Int) (h t : Window) : List Int := (b :: d :: h.ends ++ t.ends).foldr ins []

/-- One stretch per pair of consecutive cuts (Python's `pairwise`). -/
def segs (h t : Window) : List Int → List Seg
  | a :: b :: r => ⟨.of (h.covers a b) (t.covers a b), a, b⟩ :: segs h t (b :: r)
  | _ => []

/-- Join a stretch onto the merged rest when the kinds agree. -/
def glue (s : Seg) : List Seg → List Seg
  | q :: qs => if s.kind = q.kind then ⟨s.kind, s.lo, q.hi⟩ :: qs else s :: q :: qs
  | [] => [s]

def merge (l : List Seg) : List Seg := l.foldr glue []

def phases (b d : Int) (h t : Window) : List Seg :=
  let h := h.clip b d
  let t := t.clip b d
  merge (segs h t (cuts b d h t))

/-- `l` runs contiguously from `a` to `z` in non-empty stretches. -/
inductive Tiles : Int → Int → List Seg → Prop
  | one {k a z} : a < z → Tiles a z [⟨k, a, z⟩]
  | cons {k a m z l} : a < m → Tiles m z l → Tiles a z (⟨k, a, m⟩ :: l)

/-- Neighbours differ in kind. -/
def Alternates : List Seg → Prop
  | s :: q :: r => s.kind ≠ q.kind ∧ Alternates (q :: r)
  | _ => True

/-! ## Cuts -/

theorem mem_ins {x y : Int} {l : List Int} : y ∈ ins x l ↔ y = x ∨ y ∈ l := by
  induction l with
  | nil => simp [ins]
  | cons z zs ih =>
    unfold ins; split
    · simp
    · split
      · subst_vars; simp
      · simp only [List.mem_cons, ih]; exact or_left_comm

theorem sorted_ins {x : Int} {l : List Int} (h : l.Pairwise (· < ·)) : (ins x l).Pairwise (· < ·) := by
  induction l with
  | nil => simp [ins]
  | cons y ys ih =>
    rw [List.pairwise_cons] at h
    unfold ins; split
    · refine List.pairwise_cons.2 ⟨fun z hz => ?_, List.pairwise_cons.2 h⟩
      rcases List.mem_cons.1 hz with rfl | hz
      · assumption
      · have := h.1 z hz; omega
    · split
      · exact List.pairwise_cons.2 h
      · refine List.pairwise_cons.2 ⟨fun z hz => ?_, ih h.2⟩
        rcases mem_ins.1 hz with rfl | hz
        · omega
        · exact h.1 z hz

theorem mem_foldr_ins {y : Int} : ∀ {L : List Int}, y ∈ L.foldr ins [] ↔ y ∈ L
  | [] => by simp
  | x :: xs => by simp [List.foldr_cons, mem_ins, mem_foldr_ins]

theorem sorted_foldr_ins : ∀ L : List Int, (L.foldr ins []).Pairwise (· < ·)
  | [] => by simp
  | _ :: xs => sorted_ins (sorted_foldr_ins xs)

theorem clip_ends {b d : Int} (hbd : b ≤ d) {w : Window} : ∀ e ∈ (w.clip b d).ends, b ≤ e ∧ e ≤ d := by
  rcases w with _ | ⟨lo, hi⟩ <;> simp [Window.clip, Window.ends] <;> omega

theorem mem_cuts {b d : Int} {h t : Window} {y : Int} :
    y ∈ cuts b d h t ↔ y = b ∨ y = d ∨ y ∈ h.ends ∨ y ∈ t.ends := by
  unfold cuts; rw [mem_foldr_ins]; simp

theorem sorted_cuts (b d : Int) (h t : Window) : (cuts b d h t).Pairwise (· < ·) := sorted_foldr_ins _

/-! ## Stretches between consecutive cuts -/

theorem tiles_lt {a z : Int} {l : List Seg} (h : Tiles a z l) : a < z := by
  induction h with
  | one hlt => exact hlt
  | cons ham _ ih => omega

theorem tiles_bounds {a z : Int} {l : List Seg} (h : Tiles a z l) : ∀ s ∈ l, a ≤ s.lo ∧ s.hi ≤ z := by
  induction h with
  | one => intro s hs; simp at hs; subst hs; exact ⟨Int.le_refl _, Int.le_refl _⟩
  | cons ham ht ih =>
    intro s hs
    rcases List.mem_cons.1 hs with rfl | hs
    · exact ⟨Int.le_refl _, Int.le_of_lt (tiles_lt ht)⟩
    · have := ih s hs; omega

theorem segs_tiles (h t : Window) : ∀ (a z : Int) (l : List Int), (a :: l).Pairwise (· < ·) →
    (∀ c ∈ l, c ≤ z) → z ∈ a :: l → a < z → Tiles a z (segs h t (a :: l))
  | a, z, [], _, _, hz, haz => by simp at hz; omega
  | a, z, c :: l, hs, hle, hz, haz => by
    have hac : a < c := List.rel_of_pairwise_cons hs (List.mem_cons_self ..)
    have hs' := hs.of_cons
    by_cases hcz : c = z
    · subst hcz
      cases l with
      | nil => exact .one hac
      | cons e l =>
        have := List.rel_of_pairwise_cons hs' (List.mem_cons_self ..)
        have := hle e (by simp); omega
    · refine .cons hac (segs_tiles h t c z l hs' (fun e he => hle e (by simp [he])) ?_ ?_)
      · rcases List.mem_cons.1 hz with rfl | hz
        · omega
        · exact hz
      · have := hle c (by simp); omega

theorem segs_sound (h t : Window) : ∀ (l : List Int), l.Pairwise (· < ·) → ∀ s ∈ segs h t l,
    s.kind = .of (h.covers s.lo s.hi) (t.covers s.lo s.hi) ∧ s.lo < s.hi ∧ s.lo ∈ l ∧
      ∀ c ∈ l, c ≤ s.lo ∨ s.hi ≤ c
  | [], _, s, hs => by simp [segs] at hs
  | [_], _, s, hs => by simp [segs] at hs
  | a :: b :: r, hp, s, hs => by
    simp only [segs, List.mem_cons] at hs
    have hab : a < b := List.rel_of_pairwise_cons hp (List.mem_cons_self ..)
    rcases hs with rfl | hs
    · refine ⟨rfl, hab, by simp, fun c hc => ?_⟩
      dsimp only
      rcases List.mem_cons.1 hc with rfl | hc
      · omega
      · rcases List.mem_cons.1 hc with rfl | hc
        · omega
        · have := List.rel_of_pairwise_cons hp.of_cons hc; omega
    · have ⟨hk, hlt, hlo, hc⟩ := segs_sound h t (b :: r) hp.of_cons s (by simpa [segs] using hs)
      refine ⟨hk, hlt, List.mem_cons_of_mem _ hlo, fun c hc' => ?_⟩
      rcases List.mem_cons.1 hc' with rfl | hc'
      · exact .inl (Int.le_of_lt (List.rel_of_pairwise_cons hp hlo))
      · exact hc c hc'

/-- On a stretch between consecutive cuts, a window whose ends are cuts
covers the stretch iff it holds any one cell of it. -/
theorem covers_holds {w : Window} {a b x : Int} (hw : ∀ e ∈ w.ends, e ≤ a ∨ b ≤ e)
    (hax : a ≤ x) (hxb : x < b) : w.covers a b = w.holds x := by
  rcases w with _ | ⟨lo, hi⟩
  · rfl
  · simp only [Window.ends, List.mem_cons, List.not_mem_nil, or_false, forall_eq_or_imp,
      forall_eq] at hw
    simp only [Window.covers, Window.holds, decide_eq_decide]
    omega

theorem holds_clip {w : Window} {b d x : Int} (hbx : b ≤ x) (hxd : x < d) :
    (w.clip b d).holds x = w.holds x := by
  rcases w with _ | ⟨lo, hi⟩
  · rfl
  · simp only [Window.clip, Option.map, Window.holds, decide_eq_decide]; omega

/-! ## Merging -/

theorem glue_head (s : Seg) (l : List Seg) : ∃ q qs, glue s l = q :: qs ∧ q.lo = s.lo := by
  unfold glue; split
  · split <;> exact ⟨_, _, rfl, rfl⟩
  · exact ⟨_, _, rfl, rfl⟩

theorem merge_cons (s : Seg) (l : List Seg) : merge (s :: l) = glue s (merge l) := rfl

theorem merge_head {a z : Int} {l : List Seg} (h : Tiles a z l) : ∃ q qs, merge l = q :: qs ∧ q.lo = a := by
  cases h with
  | one => exact ⟨_, _, rfl, rfl⟩
  | cons => rw [merge_cons]; exact glue_head ..

theorem merge_tiles {a z : Int} {l : List Seg} (h : Tiles a z l) : Tiles a z (merge l) := by
  induction h with
  | one hlt => exact .one hlt
  | @cons k a m z l ham _ ih =>
    rw [merge_cons]
    generalize merge l = ml at ih ⊢
    cases ih with
    | @one k' _ _ hmz =>
      by_cases hk : k = k'
      · simp only [glue, hk, ite_true]; exact .one (by omega)
      · simp only [glue, hk, ite_false]; exact .cons ham (.one hmz)
    | @cons k' _ m' _ _ hmm' ht =>
      by_cases hk : k = k'
      · simp only [glue, hk, ite_true]; exact .cons (by omega) ht
      · simp only [glue, hk, ite_false]; exact .cons ham (.cons hmm' ht)

theorem merge_alternates : ∀ l : List Seg, Alternates (merge l)
  | [] => trivial
  | s :: l => by
    rw [merge_cons]
    have ih := merge_alternates l
    generalize merge l = ml at ih ⊢
    match ml, ih with
    | [], _ => trivial
    | [q], _ => by_cases hk : s.kind = q.kind <;> simp [glue, hk, Alternates]
    | q :: r :: rs, ih =>
      by_cases hk : s.kind = q.kind
      · simp only [glue, hk, ite_true]; exact ⟨hk ▸ ih.1, ih.2⟩
      · simp only [glue, hk, ite_false]; exact ⟨hk, ih⟩

/-- Every cell of a merged phase lies in a stretch of the same kind. -/
theorem merge_sound {a z : Int} {l : List Seg} (h : Tiles a z l) :
    ∀ s ∈ merge l, ∀ x, s.lo ≤ x → x < s.hi → ∃ s' ∈ l, s'.kind = s.kind ∧ s'.lo ≤ x ∧ x < s'.hi := by
  induction h with
  | one => intro s hs x h1 h2; simp [merge, glue] at hs; subst hs; exact ⟨_, by simp, rfl, h1, h2⟩
  | @cons k a m z l ham ht ih =>
    intro s hs x h1 h2
    obtain ⟨q, qs, hq, hqlo⟩ := merge_head ht
    rw [merge_cons, hq] at hs
    rw [hq] at ih
    have lift : ∀ s ∈ q :: qs, s.lo ≤ x → x < s.hi →
        ∃ s' ∈ (⟨k, a, m⟩ :: l : List Seg), s'.kind = s.kind ∧ s'.lo ≤ x ∧ x < s'.hi :=
      fun s hs h1 h2 => let ⟨s', h, e⟩ := ih s hs x h1 h2; ⟨s', List.mem_cons_of_mem _ h, e⟩
    by_cases hk : k = q.kind
    · simp only [glue, hk, ite_true, List.mem_cons] at hs
      rcases hs with rfl | hs
      · by_cases hxm : x < m
        · exact ⟨_, List.mem_cons_self .., hk, h1, hxm⟩
        · exact lift q (List.mem_cons_self ..) (by omega) h2
      · exact lift s (List.mem_cons_of_mem _ hs) h1 h2
    · simp only [glue, hk, ite_false, List.mem_cons] at hs
      rcases hs with rfl | hs | hs
      · exact ⟨_, List.mem_cons_self .., rfl, h1, h2⟩
      · exact lift s (by simp [hs]) h1 h2
      · exact lift s (List.mem_cons_of_mem _ hs) h1 h2

/-! ## The theorem -/

/-- **The phases partition the life.** They tile `[b, d]`, neighbours differ,
and every cell of a phase lies in exactly the windows its kind names. -/
theorem phases_partition {b d : Int} (hbd : b < d) (h t : Window) :
    Tiles b d (phases b d h t) ∧ Alternates (phases b d h t) ∧
      ∀ s ∈ phases b d h t, ∀ x, s.lo ≤ x → x < s.hi → phaseAt h t x = s.kind := by
  have hph : phases b d h t = merge (segs (h.clip b d) (t.clip b d) (cuts b d (h.clip b d) (t.clip b d))) := rfl
  rw [hph]
  generalize h' : h.clip b d = H, t' : t.clip b d = T
  have hin : ∀ y ∈ cuts b d H T, b ≤ y ∧ y ≤ d := fun y hy => by
    rcases mem_cuts.1 hy with rfl | rfl | hy | hy
    · omega
    · omega
    · exact clip_ends (w := h) (by omega) y (h' ▸ hy)
    · exact clip_ends (w := t) (by omega) y (t' ▸ hy)
  have hsorted := sorted_cuts b d H T
  have hbmem : b ∈ cuts b d H T := mem_cuts.2 (.inl rfl)
  have hdmem : d ∈ cuts b d H T := mem_cuts.2 (.inr (.inl rfl))
  have hHmem : ∀ e ∈ H.ends, e ∈ cuts b d H T := fun e he => mem_cuts.2 (.inr (.inr (.inl he)))
  have hTmem : ∀ e ∈ T.ends, e ∈ cuts b d H T := fun e he => mem_cuts.2 (.inr (.inr (.inr he)))
  generalize cuts b d H T = L at hin hsorted hbmem hdmem hHmem hTmem ⊢
  match L, hin, hsorted, hbmem, hdmem, hHmem, hTmem with
  | [], _, _, hb, _, _, _ => simp at hb
  | c :: l, hin, hsorted, hbmem, hdmem, hHmem, hTmem =>
    have hcb : c = b := by
      have := (hin c (List.mem_cons_self ..)).1
      rcases List.mem_cons.1 hbmem with hb | hb
      · exact hb.symm
      · have := List.rel_of_pairwise_cons hsorted hb; omega
    subst hcb
    have htiles : Tiles c d (segs H T (c :: l)) :=
      segs_tiles H T c d l hsorted (fun e he => (hin e (List.mem_cons_of_mem _ he)).2) hdmem hbd
    refine ⟨merge_tiles htiles, merge_alternates _, fun s hs x h1 h2 => ?_⟩
    obtain ⟨s', hs', hk, h1', h2'⟩ := merge_sound htiles s hs x h1 h2
    obtain ⟨hk', -, -, hgrid⟩ := segs_sound H T (c :: l) hsorted s' hs'
    have hx : c ≤ x ∧ x < d := by have := tiles_bounds (merge_tiles htiles) s hs; omega
    rw [← hk, hk', covers_holds (fun e he => hgrid e (hHmem e he)) h1' h2',
      covers_holds (fun e he => hgrid e (hTmem e he)) h1' h2', ← h', ← t']
    simp only [phaseAt, holds_clip hx.1 hx.2]

end Isnad
