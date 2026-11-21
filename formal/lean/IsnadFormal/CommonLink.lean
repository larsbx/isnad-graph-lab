/-!
# The common link (Schacht, Juynboll)

The chains of one report that go back to one Companion form a *bundle*. Seen
from the Companion, the bundle often runs as a *single strand*: each narrator
passes the report to one student only. The first narrator who passes it to
several students is the *common link*. Schacht (*The Origins of Muhammadan
Jurisprudence*, 1950, p. 172) took him as the report's likely originator;
Juynboll (*Muslim Tradition*, 1983, ch. 5) as at least its first broadcaster.
Either reading needs the property this file proves: **the common link lies on
every chain of the bundle that reaches his generation.**

`SingleStrand B s` says that in the bundle `B` every link out of each node of
`s` goes to the next node of `s`. `strand_agrees` proves that then every chain
starting where `s` starts agrees with `s` as far as both go; `common_link_on_chain`
draws the conclusion.

The graph relaxes "only student" to "a student carrying at least a share
`δ` of the chains" (`isnad_graph.analysis.strand`, δ = 0.8). `strand` below is
that procedure, executable; the conformance runner checks it, and the common
link it yields, against the Python on bundles of the committed graph.

At δ ≥ 1, on chains that repeat no narrator (all but 0.05 % of the graph's),
the two notions coincide: `strand_single` proves the computed strand is a
`SingleStrand`, and `commonLink_on_chain` that the computed common link lies on
every chain of the bundle that reaches his generation. At δ < 1 the strand is
not single, and no such statement holds: a share `1 − δ` of a node's chains
may leave it.
-/

namespace Isnad

/-- The links of a chain, teacher first. -/
def chainLinks : List Int → List (Int × Int)
  | a :: b :: r => (a, b) :: chainLinks (b :: r)
  | _ => []

/-- In the bundle `B`, every link out of `n` goes to `s`. -/
def onlyStudent (B : List (List Int)) (n s : Int) : Prop :=
  ∀ p ∈ B.flatMap chainLinks, p.1 = n → p.2 = s

/-- Every node of the strand passes the report to the next one only. -/
def SingleStrand (B : List (List Int)) : List Int → Prop
  | a :: b :: r => onlyStudent B a b ∧ SingleStrand B (b :: r)
  | _ => True

theorem prefix_cons {a : Int} {l m : List Int} (h : l <+: m) : a :: l <+: a :: m :=
  let ⟨t, e⟩ := h; ⟨t, by simp [← e]⟩

/-- **The strand is followed.** In a single strand, every chain of the bundle
(indeed every chain made of the bundle's links) that starts where the strand
starts agrees with it as far as both go. -/
theorem strand_agrees (B : List (List Int)) : ∀ (s ch : List Int), SingleStrand B s →
    (∀ p ∈ chainLinks ch, p ∈ B.flatMap chainLinks) → ch.head? = s.head? → ch <+: s ∨ s <+: ch
  | [], _, _, _, _ => .inr (List.nil_prefix)
  | [_], [], _, _, hh => by simp at hh
  | [a], c :: cs, _, _, hh => .inr ⟨cs, by simp_all⟩
  | _ :: _ :: _, [], _, _, hh => by simp at hh
  | a :: b :: r, [c], _, _, hh => .inl ⟨b :: r, by simp_all⟩
  | a :: b :: r, c :: e :: cs, ⟨hab, hr⟩, hL, hh => by
    simp only [List.head?_cons, Option.some.injEq] at hh
    subst hh
    have heb : e = b := hab (c, e) (hL _ (by simp [chainLinks])) rfl
    subst heb
    rcases strand_agrees B (e :: r) (e :: cs) hr
      (fun p hp => hL p (by simp [chainLinks, hp])) rfl with h | h
    · exact .inl (prefix_cons h)
    · exact .inr (prefix_cons h)

/-- **The common link lies on every chain that reaches his generation.** If
`s ++ [cl]` is a single strand from the Companion to the common link `cl`,
every chain of the bundle from that Companion with at least as many narrators
passes through `cl`. -/
theorem common_link_on_chain {B : List (List Int)} {s : List Int} {cl : Int}
    (hs : SingleStrand B (s ++ [cl])) {ch : List Int} (hch : ch ∈ B)
    (hh : ch.head? = (s ++ [cl]).head?) (hlen : (s ++ [cl]).length ≤ ch.length) : cl ∈ ch := by
  have hL : ∀ p ∈ chainLinks ch, p ∈ B.flatMap chainLinks :=
    fun p hp => List.mem_flatMap.2 ⟨ch, hch, hp⟩
  rcases strand_agrees B _ ch hs hL hh with h | h
  · rw [h.eq_of_length (Nat.le_antisymm h.length_le hlen)]; simp
  · exact h.subset (by simp)

/-! ## The executable strand -/

/-- Chains of `B` with a link out of `n`. -/
def nFrom (B : List (List Int)) (n : Int) : Nat :=
  (B.filter fun ch => (chainLinks ch).any (·.1 == n)).length

/-- Chains of `B` with the link `n → s`. -/
def nTo (B : List (List Int)) (n s : Int) : Nat :=
  (B.filter fun ch => (chainLinks ch).contains (n, s)).length

/-- The busiest student of `n` and his chains; the smallest id among ties. -/
def topStudent (B : List (List Int)) (n : Int) : Option (Int × Nat) :=
  let students := ((B.flatMap chainLinks).filterMap fun p => if p.1 == n then some p.2 else none).eraseDups
  students.foldl (init := none) fun acc s =>
    let k := nTo B n s
    match acc with
    | some (s', k') => if k > k' || (k == k' && s < s') then some (s, k) else acc
    | none => some (s, k)

/-- `top / all ≥ num / den`, in integers. -/
def dominates (num den top all : Nat) : Bool := top * den ≥ num * all

def strandGo (B : List (List Int)) (num den : Nat) : Nat → List Int → List Int
  | f + 1, x :: acc =>
    match topStudent B x with
    | some (s, k) => if dominates num den k (nFrom B x) && !(x :: acc).contains s
        then strandGo B num den f (s :: x :: acc) else x :: acc
    | none => x :: acc
  | _, acc => acc

/-- From the Companion `c`, follow the busiest student while he carries at
least `num / den` of the chains, and stop before a narrator already on it. -/
def strand (B : List (List Int)) (num den : Nat) (c : Int) : List Int :=
  (strandGo B num den (B.flatten.eraseDups.length + 1) [c]).reverse

/-- Where the strand stops, if it branches there and carries `minChains` chains. -/
def commonLink (B : List (List Int)) (num den minChains : Nat) (c : Int) : Option Int :=
  let x := (strand B num den c).getLast?.getD c
  match topStudent B x with
  | some (_, k) => if !dominates num den k (nFrom B x) && nFrom B x ≥ minChains then some x else none
  | none => none

/-! ## The executable strand is a single strand

At dominance `num / den ≥ 1`, on chains that repeat no narrator, every step
`strand` takes is to the *only* student: the strand is a `SingleStrand`, so
`common_link_on_chain` applies to the common link the graph computes. -/

theorem chainLinks_mem {l : List Int} {p : Int × Int} (h : p ∈ chainLinks l) : p.1 ∈ l ∧ p.2 ∈ l := by
  match l, h with
  | a :: b :: r, h =>
    simp only [chainLinks, List.mem_cons] at h
    rcases h with rfl | h
    · simp
    · have := chainLinks_mem h; exact ⟨List.mem_cons_of_mem _ this.1, List.mem_cons_of_mem _ this.2⟩

/-- A chain without repeats has one link out of each narrator. -/
theorem link_unique {l : List Int} (hl : l.Nodup) {x y z : Int}
    (hy : (x, y) ∈ chainLinks l) (hz : (x, z) ∈ chainLinks l) : y = z := by
  match l, hl, hy, hz with
  | a :: b :: r, hl, hy, hz =>
    simp only [chainLinks, List.mem_cons, Prod.mk.injEq] at hy hz
    have ha : a ∉ b :: r := (List.nodup_cons.1 hl).1
    rcases hy with ⟨hxa, hyb⟩ | hy <;> rcases hz with ⟨hxa', hzb⟩ | hz
    · rw [hyb, hzb]
    · exact absurd (by simpa [hxa] using (chainLinks_mem hz).1) ha
    · exact absurd (by simpa [hxa'] using (chainLinks_mem hy).1) ha
    · exact link_unique (List.nodup_cons.1 hl).2 hy hz

theorem filter_length_mono {α} {p q : α → Bool} : ∀ {B : List α}, (∀ a ∈ B, p a → q a) →
    (B.filter p).length ≤ (B.filter q).length
  | [], _ => by simp
  | b :: B, h => by
    have ih := filter_length_mono (B := B) fun a ha => h a (List.mem_cons_of_mem _ ha)
    have hb := h b (List.mem_cons_self ..)
    cases hpb : p b <;> cases hqb : q b <;> simp_all <;> omega

/-- If every `p`-element is a `q`-element and there are as many, every
`q`-element is a `p`-element. -/
theorem filter_length_eq {α} {p q : α → Bool} : ∀ {B : List α}, (∀ a ∈ B, p a → q a) →
    (B.filter q).length ≤ (B.filter p).length → ∀ a ∈ B, q a → p a
  | [], _, _, a, ha, _ => by simp at ha
  | b :: B, hpq, hle, a, ha, hqa => by
    have hpq' : ∀ x ∈ B, p x → q x := fun x hx => hpq x (List.mem_cons_of_mem _ hx)
    have mono := filter_length_mono hpq'
    have IH := @filter_length_eq α p q B hpq'
    have hb := hpq b (List.mem_cons_self ..)
    cases hpb : p b <;> cases hqb : q b <;>
      simp only [List.filter_cons, hpb, hqb, ite_true, ite_false, List.length_cons,
        Bool.false_eq_true] at hle hb
    · rcases List.mem_cons.1 ha with rfl | ha
      · simp_all
      · exact IH hle a ha hqa
    · omega
    · simp at hb
    · rcases List.mem_cons.1 ha with rfl | ha
      · exact hpb
      · exact IH (by omega) a ha hqa

theorem foldl_inv {α β} (P : α → Prop) (f : α → β → α) (hf : ∀ a b, P a → P (f a b)) :
    ∀ (l : List β) (a : α), P a → P (l.foldl f a)
  | [], _, h => h
  | b :: l, a, h => foldl_inv P f hf l (f a b) (hf a b h)

theorem topStudent_count {B : List (List Int)} {n s : Int} {k : Nat}
    (h : topStudent B n = some (s, k)) : k = nTo B n s := by
  unfold topStudent at h
  refine foldl_inv (fun acc => ∀ s k, acc = some (s, k) → k = nTo B n s) _ ?_ _ none
    (by simp) s k h
  intro acc x hacc s k e
  cases acc with
  | none => simp only [Option.some.injEq, Prod.mk.injEq] at e; obtain ⟨rfl, rfl⟩ := e; rfl
  | some p =>
    simp only at e
    split at e
    · simp only [Option.some.injEq, Prod.mk.injEq] at e; obtain ⟨rfl, rfl⟩ := e; rfl
    · exact hacc s k e

/-- A dominant top student is the only one, on chains without repeats. -/
theorem dominant_only {B : List (List Int)} (hnd : ∀ ch ∈ B, ch.Nodup) {num den : Nat}
    (hd : 0 < den) (hnum : den ≤ num) {x s : Int} {k : Nat}
    (ht : topStudent B x = some (s, k)) (hdom : dominates num den k (nFrom B x) = true) :
    onlyStudent B x s := by
  have hle : nFrom B x ≤ nTo B x s := by
    have h1 : num * nFrom B x ≤ k * den := of_decide_eq_true hdom
    have h2 : den * nFrom B x ≤ den * k :=
      calc den * nFrom B x ≤ num * nFrom B x := Nat.mul_le_mul_right _ hnum
        _ ≤ k * den := h1
        _ = den * k := Nat.mul_comm ..
    exact topStudent_count ht ▸ Nat.le_of_mul_le_mul_left h2 hd
  intro p hp hpx
  obtain ⟨ch, hch, hpl⟩ := List.mem_flatMap.1 hp
  have hto := filter_length_eq
    (p := fun ch : List Int => (chainLinks ch).contains (x, s))
    (q := fun ch : List Int => (chainLinks ch).any fun p : Int × Int => p.1 == x)
    (fun ch _ h => by
      simp only [List.contains_iff_mem, List.any_eq_true, beq_iff_eq] at h ⊢
      exact ⟨_, h, rfl⟩) hle ch hch (by
      simp only [List.any_eq_true, beq_iff_eq]; exact ⟨p, hpl, hpx⟩)
  simp only [List.contains_iff_mem] at hto
  obtain ⟨a, b⟩ := p
  simp only at hpx; subst hpx
  exact link_unique (hnd ch hch) hpl hto

theorem singleStrand_snoc {B : List (List Int)} {x s : Int} :
    ∀ {l : List Int}, SingleStrand B (l ++ [x]) → onlyStudent B x s → SingleStrand B (l ++ [x, s])
  | [], _, h => ⟨h, trivial⟩
  | [_], hl, h => ⟨hl.1, h, trivial⟩
  | _ :: b :: r, hl, h => ⟨hl.1, singleStrand_snoc (l := b :: r) hl.2 h⟩

theorem strandGo_single {B : List (List Int)} (hnd : ∀ ch ∈ B, ch.Nodup) {num den : Nat}
    (hd : 0 < den) (hnum : den ≤ num) :
    ∀ f acc, SingleStrand B acc.reverse → SingleStrand B (strandGo B num den f acc).reverse
  | 0, acc, h => by simpa [strandGo] using h
  | _ + 1, [], h => by simpa [strandGo] using h
  | f + 1, x :: acc, h => by
    unfold strandGo
    split
    · rename_i s k ht
      split
      · rename_i hc
        apply strandGo_single hnd hd hnum f
        simp only [List.reverse_cons, List.append_assoc, List.singleton_append] at h ⊢
        exact singleStrand_snoc h (dominant_only hnd hd hnum ht (by simp_all))
      · exact h
    · exact h

/-- **The graph's strand is a single strand** at dominance `≥ 1` on chains
without repeats. -/
theorem strand_single {B : List (List Int)} (hnd : ∀ ch ∈ B, ch.Nodup) {num den : Nat}
    (hd : 0 < den) (hnum : den ≤ num) (c : Int) : SingleStrand B (strand B num den c) :=
  strandGo_single hnd hd hnum _ [c] trivial

theorem strandGo_cons (B : List (List Int)) (num den : Nat) :
    ∀ f x acc, ∃ y t, strandGo B num den f (x :: acc) = y :: t
  | 0, x, acc => ⟨x, acc, rfl⟩
  | f + 1, x, acc => by
    unfold strandGo
    split
    · split
      · exact strandGo_cons B num den f _ _
      · exact ⟨_, _, rfl⟩
    · exact ⟨_, _, rfl⟩

theorem strandGo_root (B : List (List Int)) (num den : Nat) (c : Int) :
    ∀ f acc u, acc = u ++ [c] → ∃ u', strandGo B num den f acc = u' ++ [c]
  | 0, _, u, h => ⟨u, by simp [strandGo, h]⟩
  | _ + 1, [], u, h => by simp at h
  | f + 1, x :: acc, u, h => by
    unfold strandGo
    split
    · rename_i s _ _
      split
      · exact strandGo_root B num den c f _ (s :: u) (by simp [h])
      · exact ⟨u, h⟩
    · exact ⟨u, h⟩

/-- **The computed common link lies on every chain that reaches his
generation**, at dominance `≥ 1` on chains without repeats. -/
theorem commonLink_on_chain {B : List (List Int)} (hnd : ∀ ch ∈ B, ch.Nodup) {num den m : Nat}
    (hd : 0 < den) (hnum : den ≤ num) {c cl : Int} (h : commonLink B num den m c = some cl)
    {ch : List Int} (hch : ch ∈ B) (hh : ch.head? = some c)
    (hlen : (strand B num den c).length ≤ ch.length) : cl ∈ ch := by
  have hs := strand_single hnd hd hnum c
  obtain ⟨y, t, hyt⟩ := strandGo_cons B num den (B.flatten.eraseDups.length + 1) c []
  obtain ⟨u, hu⟩ := strandGo_root B num den c (B.flatten.eraseDups.length + 1) [c] [] rfl
  have hst : strand B num den c = t.reverse ++ [y] := by simp [strand, hyt]
  have hhead : (strand B num den c).head? = some c := by simp [strand, hu]
  have hcl : cl = y := by
    unfold commonLink at h
    rw [hst, List.getLast?_concat, Option.getD_some] at h
    dsimp only at h
    split at h
    · split at h
      · exact (Option.some.inj h).symm
      · simp at h
    · simp at h
  subst hcl
  rw [hst] at hs hhead hlen
  exact common_link_on_chain hs hch (hh.trans hhead.symm) hlen

/-- The theorem is not vacuous: at δ = 1 a bundle that runs 1 → 2 → 3 and
fans out at 3 has its common link at 3. -/
example : commonLink [[1, 2, 3, 10], [1, 2, 3, 11], [1, 2, 3, 12]] 1 1 3 1 = some 3 := by decide

end Isnad
