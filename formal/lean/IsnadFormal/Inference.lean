/-!
# Inferring a chain from the narrators a text names

`isnad_graph.inference`, transcribed. Some reports (chiefly *mawqūf* and
*maqṭūʿ*) come without a recorded sanad, but their text names narrators before
the *matn*. The rule infers a chain from those names and is deliberately
conservative: it abstains rather than guesses, when

* the *matn* boundary is unknown;
* the isnad switches routes (*taḥwīl*, a free-standing «ح»);
* no narrator is named before the *matn*;
* some name before the *matn* does not resolve to a known narrator.

Otherwise the chain is the named narrators in text order.

This file proves:

* `tahwil_iff`: the scanner finds «ح» exactly when it stands between two
  characters that are not Arabic letters (the Python regular expression
  `(?<![ء-ٰٟ-ۓ])ح(?![ء-ٰٟ-ۓ])`);
* `infer_isSome_iff`: `abstention` gives no reason exactly when `infer` gives
  a chain;
* `infer_iff`: the rule infers a chain exactly when none of the four reasons
  to abstain holds, and the chain is then the resolved names before the
  *matn*;
* `infer_text_order`: those names come in text order;
* `matn_ignored`: names inside the *matn* never change the result.

The isnad mentions are filtered and then stably sorted by position; the
Python sorts and then filters. With a stable sort the two agree; the
conformance vectors include ties to check it.
-/

namespace Isnad

structure Mention where
  rawi : Option Int
  start : Nat
  stop : Nat
  deriving Repr, DecidableEq

/-- An Arabic letter or mark in the rule's sense: U+0621–U+065F or U+0670–U+06D3. -/
def arabic (c : Char) : Bool :=
  (0x621 ≤ c.toNat && c.toNat ≤ 0x65F) || (0x670 ≤ c.toNat && c.toNat ≤ 0x6D3)

/-- Scan for a free-standing «ح»; `prev`: the character before is Arabic. -/
def tahwilGo : Bool → List Char → Bool
  | _, [] => false
  | prev, c :: r => (c == 'ح' && !prev && !(r.head?.map arabic).getD false) || tahwilGo (arabic c) r

def tahwil (s : List Char) : Bool := tahwilGo false s

inductive Abstention where
  | noMatnBoundary | tahwil | noIsnadMentions | unresolvedMention
  deriving DecidableEq, Repr

def Abstention.name : Abstention → String
  | noMatnBoundary => "no_matn_boundary" | tahwil => "tahwil"
  | noIsnadMentions => "no_isnad_mentions" | unresolvedMention => "unresolved_mention"

/-- The mentions before the *matn*, in text order. -/
def isnadMentions (ms : List Mention) (matn : Nat) : List Mention :=
  (ms.filter (·.stop ≤ matn)).mergeSort (fun a b => a.start ≤ b.start)

def resolved (known : List Int) (x : Mention) : Bool := x.rawi.any (known.contains ·)

/-- Why the rule abstains, given the boundary `m` and the mentions `isn` before it. -/
def abstainOn (isn : List Mention) (m : Nat) (text : List Char) (known : List Int) :
    Option Abstention :=
  if tahwil (text.take m) then some .tahwil
  else if isn = [] then some .noIsnadMentions
  else if isn.all (resolved known) then none
  else some .unresolvedMention

def inferOn (isn : List Mention) (m : Nat) (text : List Char) (known : List Int) :
    Option (List Int) :=
  if abstainOn isn m text known = none then some (isn.filterMap (·.rawi)) else none

def abstention (ms : List Mention) (matn : Option Nat) (text : List Char) (known : List Int) :
    Option Abstention :=
  match matn with
  | none => some .noMatnBoundary
  | some m => abstainOn (isnadMentions ms m) m text known

def infer (ms : List Mention) (matn : Option Nat) (text : List Char) (known : List Int) :
    Option (List Int) :=
  match matn with
  | none => none
  | some m => inferOn (isnadMentions ms m) m text known

/-! ## The taḥwīl scanner -/

theorem getLast?_cons_getD {f : Char → Bool} {p : Bool} (c : Char) (l : List Char) :
    (((c :: l).getLast?).map f).getD p = ((l.getLast?).map f).getD (f c) := by
  cases l with
  | nil => rfl
  | cons d l => rw [List.getLast?_cons_cons]; cases h : (d :: l).getLast? <;> simp_all

theorem tahwilGo_iff : ∀ (s : List Char) (prev : Bool), tahwilGo prev s = true ↔
    ∃ l r, s = l ++ 'ح' :: r ∧ ((l.getLast?).map arabic).getD prev = false ∧
      ((r.head?).map arabic).getD false = false
  | [], prev => by simp [tahwilGo]
  | c :: s, prev => by
    simp only [tahwilGo, Bool.or_eq_true, Bool.and_eq_true, beq_iff_eq, Bool.not_eq_true',
      tahwilGo_iff s (arabic c)]
    constructor
    · rintro (⟨⟨rfl, hp⟩, hr⟩ | ⟨l, r, rfl, hl, hr⟩)
      · exact ⟨[], s, rfl, hp, hr⟩
      · exact ⟨c :: l, r, rfl, by rw [getLast?_cons_getD]; exact hl, hr⟩
    · rintro ⟨l, r, hs, hl, hr⟩
      cases l with
      | nil =>
        simp only [List.nil_append, List.cons.injEq] at hs
        obtain ⟨rfl, rfl⟩ := hs
        exact .inl ⟨⟨rfl, hl⟩, hr⟩
      | cons d l =>
        simp only [List.cons_append, List.cons.injEq] at hs
        obtain ⟨rfl, rfl⟩ := hs
        exact .inr ⟨l, r, rfl, by rwa [getLast?_cons_getD] at hl, hr⟩

/-- **The scanner is the regular expression.** A text has *taḥwīl* exactly
when some «ح» in it has no Arabic letter right before or right after it. -/
theorem tahwil_iff (s : List Char) : tahwil s = true ↔
    ∃ l r, s = l ++ 'ح' :: r ∧ ((l.getLast?).map arabic).getD false = false ∧
      ((r.head?).map arabic).getD false = false :=
  tahwilGo_iff s false

/-! ## The rule -/

theorem mem_isnadMentions {ms : List Mention} {m : Nat} {x : Mention} :
    x ∈ isnadMentions ms m ↔ x ∈ ms ∧ x.stop ≤ m := by
  simp [isnadMentions, List.mem_mergeSort]

/-- **The rule abstains exactly when it should.** It infers a chain iff the
*matn* boundary is known, there is no *taḥwīl* before it, some narrator is
named before it, and every name before it is a known narrator; the chain is
then those narrators. -/
theorem infer_iff {ms : List Mention} {matn : Option Nat} {text : List Char} {known : List Int}
    {ch : List Int} :
    infer ms matn text known = some ch ↔
      ∃ m, matn = some m ∧ tahwil (text.take m) = false ∧ isnadMentions ms m ≠ [] ∧
        (∀ x ∈ ms, x.stop ≤ m → ∃ r, x.rawi = some r ∧ r ∈ known) ∧
        ch = (isnadMentions ms m).filterMap (·.rawi) := by
  cases matn with
  | none => simp [infer]
  | some m =>
    have hres : (isnadMentions ms m).all (resolved known) = true ↔
        ∀ x ∈ ms, x.stop ≤ m → ∃ r, x.rawi = some r ∧ r ∈ known := by
      simp only [List.all_eq_true, mem_isnadMentions, resolved, and_imp]
      refine forall_congr' fun x => imp_congr_right fun _ => imp_congr_right fun _ => ?_
      cases x.rawi <;> simp
    simp only [Option.some.injEq, exists_eq_left', ← hres]
    simp only [infer, inferOn, abstainOn]
    by_cases ht : tahwil (text.take m) = true
    · simp [ht]
    · by_cases he : isnadMentions ms m = []
      · simp [ht, he]
      · by_cases ha : (isnadMentions ms m).all (resolved known) = true
        · simp [ht, he, ha, eq_comm]
        · simp [ht, he, ha]

/-- `abstention` gives no reason exactly when `infer` gives a chain. -/
theorem infer_isSome_iff {ms : List Mention} {matn : Option Nat} {text : List Char}
    {known : List Int} : (infer ms matn text known).isSome ↔ abstention ms matn text known = none := by
  cases matn with
  | none => simp [infer, abstention]
  | some m => simp only [infer, abstention, inferOn]; split <;> simp_all

/-- The names come in text order. -/
theorem infer_text_order {ms : List Mention} {m : Nat} {text : List Char} {known : List Int}
    {ch : List Int} (h : infer ms (some m) text known = some ch) :
    (isnadMentions ms m).Pairwise (fun a b => a.start ≤ b.start) ∧
      (isnadMentions ms m).length = ch.length := by
  obtain ⟨_, he, -, -, hall, rfl⟩ := infer_iff.1 h
  cases he
  have hsome : ∀ x ∈ isnadMentions ms m, ∃ r, x.rawi = some r := fun x hx =>
    let ⟨r, e, _⟩ := hall x (mem_isnadMentions.1 hx).1 (mem_isnadMentions.1 hx).2
    ⟨r, e⟩
  constructor
  · have := List.pairwise_mergeSort (le := fun a b : Mention => decide (a.start ≤ b.start))
      (fun a b c h₁ h₂ => by simp at *; omega) (fun a b => by simp; omega)
      (ms.filter (·.stop ≤ m))
    simpa [isnadMentions] using this
  · generalize isnadMentions ms m = L at hsome ⊢
    induction L with
    | nil => rfl
    | cons x L ih =>
      obtain ⟨r, e⟩ := hsome x (List.mem_cons_self ..)
      simp [e, ih fun y hy => hsome y (List.mem_cons_of_mem _ hy)]

/-- **Names inside the *matn* are ignored.** -/
theorem matn_ignored {ms extra : List Mention} {m : Nat} (text : List Char) (known : List Int)
    (h : ∀ x ∈ extra, m < x.stop) :
    infer (ms ++ extra) (some m) text known = infer ms (some m) text known := by
  have : isnadMentions (ms ++ extra) m = isnadMentions ms m := by
    have hx : extra.filter (fun x => decide (x.stop ≤ m)) = [] :=
      List.filter_eq_nil_iff.2 fun x hx => by have := h x hx; simp; omega
    simp only [isnadMentions, List.filter_append, hx, List.append_nil]
  simp only [infer, this]

end Isnad
