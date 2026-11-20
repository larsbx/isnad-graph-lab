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
link it yields, against the Python on bundles of the committed graph. At
δ = 1 on chains without a repeated narrator the two notions coincide; that
bridge is not proved here.
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

end Isnad
