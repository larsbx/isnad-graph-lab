import IsnadFormal.Regions

/-!
# The transmission model, and why TLC may check it over the region years

`formal/quint/transmission.qnt` (`transmissionSpec`), transcribed: a report
spreads from the source by hearings; a student hears from a holder in a year
`y` of `Y` when both are alive, the teacher at least `aT` and the student at
least `aH` years old, and `y` is not before the last hearing. He names his
source explicitly or ambiguously (the teacher's isnad), or by irsāl (the
teacher's isnad without the teacher). The narrators, lives and ages are
parameters; Quint's are one instance.

The invariants of `safety` split in two. Those that read no year
(`rootedAtSource`, `prefixClosed`, the irsāl half of `ittisal`,
`refutationSound`, `weakestLink`, `gapCaps`, `sahihExactly`,
`tadlisInherited`) depend on the holders, their isnads and formulas, and who
heard whom: they are any predicate `P` of `St.yearFree`. Those that read years,
the hearing half of `ittisal` and `chronologicalOrder`, are transcribed.

`regions_iff`: for every such `P`, the invariants hold in every state
reachable over the years `[first, last]` iff they hold in every state
reachable over the region years, when the cuts contain every threshold of
the guards, `first`, 0 and 1, and a region holds as many years as there are
narrators below the source. That is `transmission` against
`transmissionRegions`.

The idle step of the Quint model changes nothing and is left out: it adds
no reachable state.
-/

namespace Isnad.Model

inductive Via where
  | sama | an | irsal
  deriving DecidableEq, Repr

/-- The lives and ages of a model. -/
structure Lives (N : Type) where
  src : N
  birth : N → Int
  death : N → Int
  aH : Int
  aT : Int

structure St (N : Type) where
  now : Int
  holders : List N
  isnad : N → List N
  via : N → Via
  heardIn : N → Int
  hearings : List (N × N × Int)

variable {N : Type} [DecidableEq N] (L : Lives N)

def upd {β : Type} (f : N → β) (a : N) (b : β) : N → β := fun x => if x = a then b else f x

def alive (n : N) (y : Int) : Prop := L.birth n ≤ y ∧ y ≤ L.death n

def init : St N :=
  ⟨0, [L.src], fun n => if n = L.src then [L.src] else [], fun _ => .sama, fun _ => 0, []⟩

/-- `u` hears from `t` in year `y` of `Y` and names `named` as his source's isnad. -/
def tell (Y : Int → Prop) (s : St N) (t u : N) (y : Int) (named : List N) (how : Via) (s' : St N) :
    Prop :=
  t ∈ s.holders ∧ u ∉ s.holders ∧ Y y ∧ s.now ≤ y ∧ alive L t y ∧ alive L u y ∧
    L.birth t + L.aT ≤ y ∧ L.birth u + L.aH ≤ y ∧
    s' = ⟨y, u :: s.holders, upd s.isnad u (named ++ [u]), upd s.via u how, upd s.heardIn u y,
      (t, u, y) :: s.hearings⟩

/-- `hearAt` with an explicit or ambiguous formula, or `irsal`. -/
def step (Y : Int → Prop) (s s' : St N) : Prop :=
  ∃ t u y, (∃ m, (m = Via.sama ∨ m = Via.an) ∧ tell L Y s t u y (s.isnad t) m s') ∨
    (t ≠ L.src ∧ tell L Y s t u y (s.isnad t).dropLast .irsal s')

inductive Reach (Y : Int → Prop) : St N → Prop
  | init : Reach Y (init L)
  | step {s s'} : Reach Y s → step L Y s s' → Reach Y s'

/-- The links of an isnad, teacher first (Quint's `links`). -/
def links : List N → List (N × N)
  | a :: b :: r => (a, b) :: links (b :: r)
  | _ => []

/-- What the year-free invariants read. -/
def St.yearFree (s : St N) : List N × (N → List N) × (N → Via) × List (N × N) :=
  (s.holders, s.isnad, s.via, s.hearings.map fun p => (p.1, p.2.1))

/-- The hearing half of `ittisal`: a link not marked as irsāl is a hearing
with both alive. -/
def hearsAlive (s : St N) : Prop :=
  ∀ h ∈ s.holders, ∀ p ∈ links (s.isnad h), s.via p.2 ≠ .irsal →
    ∃ yr, (p.1, p.2, yr) ∈ s.hearings ∧ alive L p.1 yr ∧ alive L p.2 yr

/-- `chronologicalOrder`. -/
def chronological (s : St N) : Prop :=
  ∀ h ∈ s.holders, ∀ p ∈ links (s.isnad h), s.heardIn p.1 ≤ s.heardIn p.2

def Inv (P : List N × (N → List N) × (N → Via) × List (N × N) → Prop) (s : St N) : Prop :=
  P s.yearFree ∧ hearsAlive L s ∧ chronological s

/-! ## Facts about reachable states -/

/-- Every reachable state remembers its years in `heardIn`. -/
structure Facts (first last : Int) (s : St N) : Prop where
  src_mem : L.src ∈ s.holders
  outside : ∀ n, n ∉ s.holders → s.heardIn n = 0
  src_zero : s.heardIn L.src = 0
  now : s.now = 0 ∨ ∃ n ∈ s.holders, s.now = s.heardIn n
  hearing : ∀ p ∈ s.hearings, p.2.2 = s.heardIn p.2.1
  recipient : ∀ p ∈ s.hearings, p.2.1 ∈ s.holders
  range : ∀ n, first ≤ s.heardIn n ∧ s.heardIn n ≤ last

theorem upd_eq {β : Type} (f : N → β) (a : N) (b : β) (x : N) :
    upd f a b x = if x = a then b else f x := rfl

theorem tell_facts {Y : Int → Prop} {first last : Int} (hY : ∀ y, Y y → first ≤ y ∧ y ≤ last)
    {s s' : St N} {t u y named how} (hf : Facts L first last s) (h : tell L Y s t u y named how s') :
    Facts L first last s' := by
  obtain ⟨-, hu, hy, -, -, -, -, -, rfl⟩ := h
  have hsrc : u ≠ L.src := fun e => hu (e ▸ hf.src_mem)
  refine ⟨List.mem_cons_of_mem _ hf.src_mem, fun n hn => ?_, ?_, .inr ⟨u, by simp, by simp [upd]⟩,
    fun p hp => ?_, fun p hp => ?_, fun n => ?_⟩
  · simp only [List.mem_cons, not_or] at hn
    simp [upd, hn.1, hf.outside n hn.2]
  · simp [upd, Ne.symm hsrc, hf.src_zero]
  · rcases List.mem_cons.1 hp with rfl | hp
    · simp [upd]
    · have := hf.hearing p hp
      by_cases e : p.2.1 = u
      · exact absurd (e ▸ hf.recipient p hp) hu
      · simp [upd, e, this]
  · rcases List.mem_cons.1 hp with rfl | hp
    · simp
    · exact List.mem_cons_of_mem _ (hf.recipient p hp)
  · by_cases e : n = u
    · simp [upd, e]; exact hY y hy
    · simp [upd, e]; exact hf.range n

theorem reach_facts {Y : Int → Prop} {first last : Int} (hY : ∀ y, Y y → first ≤ y ∧ y ≤ last)
    (h0 : first ≤ 0 ∧ 0 ≤ last) {s : St N} (h : Reach L Y s) : Facts L first last s := by
  induction h with
  | init => exact ⟨by simp [init], fun n hn => rfl, rfl, .inl rfl, by simp [init], by simp [init],
      fun _ => h0⟩
  | step _ hst ih =>
    obtain ⟨t, u, y, ⟨m, -, ht⟩ | ⟨-, ht⟩⟩ := hst
    · exact tell_facts L hY ih ht
    · exact tell_facts L hY ih ht

/-! ## Relabelling the years -/

/-- Every year relabelled by `g`. -/
def St.map (g : Int → Int) (s : St N) : St N :=
  ⟨g s.now, s.holders, s.isnad, s.via, g ∘ s.heardIn, s.hearings.map fun p => (p.1, p.2.1, g p.2.2)⟩

/-- The years a state uses: 0 and the years of its hearings. -/
def years (s : St N) (y : Int) : Prop := y = 0 ∨ ∃ n, y = s.heardIn n

/-- Every threshold a guard compares a year with is a cut. -/
def Cuts (C : List Int) : Prop :=
  ∀ n, L.birth n ∈ C ∧ L.birth n + L.aH ∈ C ∧ L.birth n + L.aT ∈ C ∧ L.death n + 1 ∈ C

/-- `g` keeps every comparison the model makes on the years `U`, and lands in `R`. -/
structure Good (C : List Int) (R : Int → Prop) (g : Int → Int) (U : Int → Prop) : Prop where
  zero : g 0 = 0
  order : ∀ x y, U x → U y → (x ≤ y ↔ g x ≤ g y)
  cut : ∀ x, U x → ∀ c ∈ C, (c ≤ x ↔ c ≤ g x)
  lands : ∀ x, U x → R (g x)

variable {L}

theorem Good.mono {C R g} {U V : Int → Prop} (h : Good C R g V) (hUV : ∀ x, U x → V x) : Good C R g U :=
  ⟨h.zero, fun x y hx hy => h.order x y (hUV x hx) (hUV y hy), fun x hx => h.cut x (hUV x hx),
    fun x hx => h.lands x (hUV x hx)⟩

omit [DecidableEq N] in
theorem alive_iff {C R g U} (hC : Cuts L C) (hg : Good C R g U) {x : Int} (hx : U x) (n : N) :
    alive L n x ↔ alive L n (g x) := by
  have h1 := hg.cut x hx _ (hC n).1
  have h2 := hg.cut x hx _ (hC n).2.2.2
  unfold alive; omega

theorem map_init {g : Int → Int} (hz : g 0 = 0) : (init L).map g = init L := by
  simp only [St.map, init, hz, List.map_nil]
  congr 1
  funext n; simp [hz]

theorem years_tell {Y : Int → Prop} {first last} {s s' : St N} {t u y named how}
    (hf : Facts L first last s) (h : tell L Y s t u y named how s') :
    (∀ x, years s x → years s' x) ∧ years s' y ∧ years s' s.now := by
  obtain ⟨-, hu, -, -, -, -, -, -, rfl⟩ := h
  have old : ∀ n, n ∈ s.holders → upd s.heardIn u y n = s.heardIn n := fun n hn => by
    simp [upd, show n ≠ u from fun e => hu (e ▸ hn)]
  refine ⟨fun x hx => ?_, .inr ⟨u, by simp [upd]⟩, ?_⟩
  · rcases hx with rfl | ⟨n, rfl⟩
    · exact .inl rfl
    · by_cases hn : n ∈ s.holders
      · exact .inr ⟨n, (old n hn).symm⟩
      · exact .inl (hf.outside n hn)
  · rcases hf.now with e | ⟨n, hn, e⟩
    · exact .inl e
    · exact .inr ⟨n, by simp only; rw [old n hn]; exact e⟩

theorem map_tell {Y : Int → Prop} {first last C R g} (hC : Cuts L C) {s s' : St N} {t u y named how}
    (hf : Facts L first last s) (h : tell L Y s t u y named how s') (hg : Good C R g (years s')) :
    tell L R (s.map g) t u (g y) named how (s'.map g) := by
  obtain ⟨_, hy', hnow⟩ := years_tell hf h
  obtain ⟨ht, hu, -, hle, hat, hau, hbt, hbu, rfl⟩ := h
  have cy := hg.cut y hy'
  refine ⟨ht, hu, hg.lands y hy', (hg.order _ _ hnow hy').1 hle, (alive_iff hC hg hy' t).1 hat,
    (alive_iff hC hg hy' u).1 hau, (cy _ (hC t).2.2.1).1 hbt, (cy _ (hC u).2.1).1 hbu, ?_⟩
  simp only [St.map, List.map_cons]
  congr 1
  funext n; simp only [Function.comp, upd]; split <;> rfl

theorem map_step {Y : Int → Prop} {first last C R g} (hC : Cuts L C) {s s' : St N}
    (hf : Facts L first last s) (h : step L Y s s') :
    (∀ x, years s x → years s' x) ∧ (Good C R g (years s') → step L R (s.map g) (s'.map g)) := by
  obtain ⟨t, u, y, ⟨m, hm, ht⟩ | ⟨hsrc, ht⟩⟩ := h
  · exact ⟨(years_tell hf ht).1, fun hg => ⟨t, u, g y, .inl ⟨m, hm, map_tell hC hf ht hg⟩⟩⟩
  · exact ⟨(years_tell hf ht).1, fun hg => ⟨t, u, g y, .inr ⟨hsrc, map_tell hC hf ht hg⟩⟩⟩

/-- **Simulation.** Relabelling a reachable state's years by a good `g` gives a
state reachable over the years `g` lands in. -/
theorem sim {Y : Int → Prop} {first last C R g} (hC : Cuts L C)
    (hY : ∀ y, Y y → first ≤ y ∧ y ≤ last) (h0 : first ≤ 0 ∧ 0 ≤ last) {s : St N}
    (h : Reach L Y s) (hg : Good C R g (years s)) : Reach L R (s.map g) := by
  induction h with
  | init => rw [map_init hg.zero]; exact .init
  | @step s s' hs hst ih =>
    have hf := reach_facts L hY h0 hs
    obtain ⟨hsub, hmap⟩ := map_step (g := g) (C := C) (R := R) hC hf hst
    exact .step (ih (hg.mono hsub)) (hmap hg)

omit [DecidableEq N] in
/-- **The invariants keep their truth value** under a good relabelling. -/
theorem inv_map {first last C R g} (hC : Cuts L C) {s : St N} (hf : Facts L first last s)
    (hg : Good C R g (years s)) (P : List N × (N → List N) × (N → Via) × List (N × N) → Prop) :
    Inv L P s ↔ Inv L P (s.map g) := by
  have hyf : (s.map g).yearFree = s.yearFree := by
    simp only [St.yearFree, St.map, List.map_map]; rfl
  have hyr : ∀ p ∈ s.hearings, years s p.2.2 := fun p hp => .inr ⟨p.2.1, hf.hearing p hp⟩
  unfold Inv hearsAlive chronological
  rw [hyf]
  simp only [St.map, Function.comp]
  refine and_congr Iff.rfl (and_congr ?_ ?_)
  · refine forall_congr' fun h => imp_congr_right fun _ => forall_congr' fun p =>
      imp_congr_right fun _ => imp_congr_right fun _ => ⟨?_, ?_⟩
    · rintro ⟨yr, hm, ha, hb⟩
      have hy := hyr _ hm
      exact ⟨g yr, List.mem_map.2 ⟨_, hm, rfl⟩, (alive_iff hC hg hy _).1 ha, (alive_iff hC hg hy _).1 hb⟩
    · rintro ⟨yr, hm, ha, hb⟩
      obtain ⟨q, hq, e⟩ := List.mem_map.1 hm
      simp only [Prod.mk.injEq] at e
      obtain ⟨e1, e2, e3⟩ := e
      have hy := hyr q hq
      refine ⟨q.2.2, ?_, (alive_iff hC hg hy _).2 (e3 ▸ ha), (alive_iff hC hg hy _).2 (e3 ▸ hb)⟩
      rw [← e1, ← e2]; exact hq
  · exact forall_congr' fun h => imp_congr_right fun _ => forall_congr' fun p =>
      imp_congr_right fun _ => hg.order _ _ (.inr ⟨_, rfl⟩) (.inr ⟨_, rfl⟩)

/-! ## The region relabelling is good -/

open Regions in
theorem good_regions {first last : Int} {k : Nat} {C : List Int} (hfirst : first ∈ C)
    (h0c : (0 : Int) ∈ C) (h1c : (1 : Int) ∈ C) (h0 : first ≤ 0 ∧ 0 ≤ last) {ns : List N}
    (hns : ∀ n, n ∈ ns) (hk : ns.length ≤ k + 1) (hk1 : 1 ≤ k) {s : St N}
    (hf : Facts L first last s) :
    ∃ g, Good C (fun y => first ≤ y ∧ y ≤ last ∧ inRegions C k y) g (years s) := by
  let vals := (0 :: ns.map s.heardIn).foldr Isnad.ins []
  have hmem : ∀ x, x ∈ vals ↔ x = 0 ∨ ∃ n, x = s.heardIn n := fun x => by
    simp only [vals, Isnad.mem_foldr_ins, List.mem_cons, List.mem_map]
    exact or_congr Iff.rfl ⟨fun ⟨n, _, e⟩ => ⟨n, e.symm⟩, fun ⟨n, e⟩ => ⟨n, hns n, e.symm⟩⟩
  have hv : vals.Nodup := (Isnad.sorted_foldr_ins _).imp Int.ne_of_lt
  have hfv : ∀ x ∈ vals, first ≤ x := fun x hx => by
    rcases (hmem x).1 hx with rfl | ⟨n, rfl⟩
    · exact h0.1
    · exact (hf.range n).1
  have hlen : vals.length ≤ k + 1 := by
    have hsub : ∀ x ∈ vals, x ∈ 0 :: (ns.erase L.src).map s.heardIn := fun x hx => by
      rcases (hmem x).1 hx with rfl | ⟨n, rfl⟩
      · simp
      · by_cases e : n = L.src
        · subst e; simp [hf.src_zero]
        · exact List.mem_cons_of_mem _ (List.mem_map.2 ⟨n, List.mem_erase_of_ne e |>.2 (hns n), rfl⟩)
    have := hv.length_le_of_subset hsub
    have := List.length_erase_of_mem (hns L.src)
    have : 0 < ns.length := List.length_pos_of_mem (hns L.src)
    simp only [List.length_cons, List.length_map] at *
    omega
  have h0v : (0 : Int) ∈ vals := (hmem 0).2 (.inl rfl)
  have hk' : ∀ x ∈ vals, (vals.filter fun y => decide (same C y x)).length ≤ k :=
    fun x _ => perRegion_of_initial h0c h1c h0v hlen hk1 hv x
  have hyv : ∀ x, years s x → x ∈ vals := fun x hx => (hmem x).2 hx
  refine ⟨g first C vals, ⟨?_, fun x y hx hy => g_le_iff hfirst hv hfv (hyv x hx) (hyv y hy),
    fun x hx c hc => ((g_same hfirst hv hfv (hyv x hx)) c hc).symm, fun x hx => ?_⟩⟩
  · have hb := g_between (C := C) hfirst hv hfv h0v
    have := le_start (first := first) h0c (Int.le_refl 0)
    omega
  · have hb := g_between (C := C) hfirst hv hfv (hyv x hx)
    have hlast : x ≤ last := by
      rcases hx with rfl | ⟨n, rfl⟩
      · exact h0.2
      · exact (hf.range n).2
    exact ⟨Int.le_trans first_le_start hb.1, Int.le_trans hb.2 hlast,
      g_inRegions hfirst hv hfv hk' (hyv x hx)⟩

theorem reach_mono {Y Y' : Int → Prop} (h : ∀ y, Y' y → Y y) {s : St N} (hs : Reach L Y' s) :
    Reach L Y s := by
  induction hs with
  | init => exact .init
  | step _ hst ih =>
    obtain ⟨t, u, y, ⟨m, hm, ⟨a, b, hy, rest⟩⟩ | ⟨hsrc, ⟨a, b, hy, rest⟩⟩⟩ := hst
    · exact .step ih ⟨t, u, y, .inl ⟨m, hm, ⟨a, b, h y hy, rest⟩⟩⟩
    · exact .step ih ⟨t, u, y, .inr ⟨hsrc, ⟨a, b, h y hy, rest⟩⟩⟩

/-- **The region reduction for the transmission model.** The invariants hold
in every state reachable over the years `[first, last]` iff they hold in
every state reachable over the region years: `transmission` against
`transmissionRegions`. -/
theorem regions_iff {first last : Int} {k : Nat} (C : List Int) (hC : Cuts L C) (hfirst : first ∈ C)
    (h0c : (0 : Int) ∈ C) (h1c : (1 : Int) ∈ C) (h0 : first ≤ 0 ∧ 0 ≤ last) (ns : List N)
    (hns : ∀ n, n ∈ ns) (hk : ns.length ≤ k + 1) (hk1 : 1 ≤ k)
    (P : List N × (N → List N) × (N → Via) × List (N × N) → Prop) :
    (∀ s, Reach L (fun y => first ≤ y ∧ y ≤ last) s → Inv L P s) ↔
      (∀ s, Reach L (fun y => first ≤ y ∧ y ≤ last ∧ Regions.inRegions C k y) s → Inv L P s) := by
  constructor
  · exact fun h s hs => h s (reach_mono (fun y hy => ⟨hy.1, hy.2.1⟩) hs)
  · intro h s hs
    have hf := reach_facts L (fun y hy => hy) h0 hs
    obtain ⟨g, hg⟩ := good_regions (L := L) hfirst h0c h1c h0 hns hk hk1 hf
    exact (inv_map hC hf hg P).2 (h _ (sim hC (fun y hy => hy) h0 hs hg))

/-! ## Execution, for replaying Quint's traces -/

variable (L)

instance (n : N) (y : Int) : Decidable (alive L n y) := by unfold alive; infer_instance

/-- `tell`, executable: the next state, if the guards hold. -/
def tellB (inY : Int → Bool) (s : St N) (t u : N) (y : Int) (named : List N) (how : Via) :
    Option (St N) :=
  if t ∈ s.holders ∧ u ∉ s.holders ∧ inY y = true ∧ s.now ≤ y ∧ alive L t y ∧ alive L u y ∧
      L.birth t + L.aT ≤ y ∧ L.birth u + L.aH ≤ y
  then some ⟨y, u :: s.holders, upd s.isnad u (named ++ [u]), upd s.via u how, upd s.heardIn u y,
    (t, u, y) :: s.hearings⟩
  else none

/-- Every successor in year `y`: each teacher and student, each formula, and irsāl. -/
def successors (inY : Int → Bool) (all : List N) (s : St N) (y : Int) : List (St N) :=
  all.flatMap fun t => all.flatMap fun u =>
    ([Via.sama, Via.an].filterMap fun m => tellB L inY s t u y (s.isnad t) m) ++
      (if t ≠ L.src then (tellB L inY s t u y (s.isnad t).dropLast .irsal).toList else [])

variable {L}

theorem tellB_sound {inY : Int → Bool} {s s' : St N} {t u y named how}
    (h : tellB L inY s t u y named how = some s') : tell L (fun y => inY y = true) s t u y named how s' := by
  unfold tellB at h
  split at h
  · rename_i hg
    obtain ⟨h1, h2, h3, h4, h5, h6, h7, h8⟩ := hg
    exact ⟨h1, h2, h3, h4, h5, h6, h7, h8, (Option.some.inj h).symm⟩
  · cases h

/-- **Every successor is a step** of the transcribed relation. -/
theorem successors_step {inY : Int → Bool} {all : List N} {s s' : St N} {y : Int}
    (h : s' ∈ successors L inY all s y) : step L (fun y => inY y = true) s s' := by
  simp only [successors, List.mem_flatMap, List.mem_append, List.mem_filterMap, List.mem_cons,
    List.not_mem_nil, or_false] at h
  obtain ⟨t, -, u, -, ⟨m, hm, ht⟩ | hi⟩ := h
  · exact ⟨t, u, y, .inl ⟨m, hm, tellB_sound ht⟩⟩
  · split at hi
    · rename_i hsrc
      exact ⟨t, u, y, .inr ⟨hsrc, tellB_sound (Option.mem_toList.1 hi |> Option.mem_def.1)⟩⟩
    · simp at hi

/-! ## The Quint model's instance -/

/-- `transmission.qnt`'s narrators. -/
inductive Q where
  | P | A | B | C | D
  deriving DecidableEq, Repr, Inhabited

namespace Q

def all : List Q := [P, A, B, C, D]

def name : Q → String
  | P => "P" | A => "A" | B => "B" | C => "C" | D => "D"

/-- `lives` in `transmission.qnt`. -/
def lives : Lives Q where
  src := P
  birth | P => -53 | A => -20 | B => 10 | C => 40 | D => 95
  death | P => 11 | A => 57 | B => 90 | C => 130 | D => 160
  aH := 5
  aT := 20

def first : Int := -53
def last : Int := 160
def span : Nat := 4

/-- Quint's `CUTS`: `FIRST`, 0, 1, and each narrator's birth, birth plus each
minimum age, and death plus one. -/
def cuts : List Int :=
  [first, 0, 1] ++ all.flatMap fun n =>
    [lives.birth n, lives.birth n + lives.aH, lives.birth n + lives.aT, lives.death n + 1]

theorem mem_all (n : Q) : n ∈ all := by cases n <;> decide

theorem cuts_ok : Cuts lives cuts := by
  intro n; cases n <;> decide

/-- **`transmission` and `transmissionRegions` satisfy the same invariants.** -/
theorem transmission_iff_regions (P : List Q × (Q → List Q) × (Q → Via) × List (Q × Q) → Prop) :
    (∀ s, Reach lives (fun y => first ≤ y ∧ y ≤ last) s → Inv lives P s) ↔
      (∀ s, Reach lives (fun y => first ≤ y ∧ y ≤ last ∧ Regions.inRegions cuts span y) s →
        Inv lives P s) :=
  regions_iff cuts cuts_ok (by decide) (by decide) (by decide) (by decide) all mem_all
    (by decide) (by decide) P

end Q

end Isnad.Model
