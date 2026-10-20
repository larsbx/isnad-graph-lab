import IsnadFormal.Chronology

/-!
# The graph's chronology verdict, as an executable model

`isnad_graph.lifespan.feasibility`, transcribed. Each end of a link carries what
the graph knows (`Life`): the lower bound of the birth and the bounds of the
death (each possibly missing), whether the birth is documented (by record or by
age at death), whether the death is recorded, and whether the biography
contradicts itself. The verdict is the first that applies of
`unknown`, `conflict`, `impossible`, `implausible`, `consistent`.

`impossible_sound` connects the executable verdict to `Chronology`: whenever
it says `impossible`, no true dates within the documented bounds make the two
contemporaries. The conformance runner (`Conformance.lean`) checks this
function against the Python implementation's verdicts on the real graph.
-/

namespace Isnad

structure Life where
  bLo : Option Int
  dLo : Option Int
  dHi : Option Int
  bDoc : Bool
  dRec : Bool
  conflict : Bool
  deriving Repr

def gtOpt : Option Int → Option Int → Bool
  | some a, some b => decide (a > b)
  | _, _ => false

/-- The birth lower bound used: under `strict`, only a documented one. -/
def Life.birth (strict : Bool) (x : Life) : Option Int := if strict && !x.bDoc then none else x.bLo

/-- The death upper bound used: under `strict`, only a recorded one. -/
def Life.death (strict : Bool) (x : Life) : Option Int := if strict && !x.dRec then none else x.dHi

def refutes (strict : Bool) (t s : Life) : Bool :=
  gtOpt (s.birth strict) (t.death strict) || gtOpt (t.birth strict) (s.death strict)

inductive Chronology where
  | unknown | conflict | impossible | implausible | consistent
  deriving DecidableEq, Repr

def Chronology.name : Chronology → String
  | unknown => "unknown" | conflict => "conflict" | impossible => "impossible"
  | implausible => "implausible" | consistent => "consistent"

def chronology (t s : Life) : Chronology :=
  if t.dLo.isNone || s.dLo.isNone then .unknown
  else if t.conflict || s.conflict then .conflict
  else if refutes true t s then .impossible
  else if refutes false t s then .implausible
  else .consistent

theorem gtOpt_true {a b : Option Int} (h : gtOpt a b = true) : ∃ x y, a = some x ∧ b = some y ∧ x > y := by
  cases a <;> cases b <;> simp_all [gtOpt]

theorem birth_strict {x : Life} {v : Int} (h : x.birth true = some v) : x.bDoc = true ∧ x.bLo = some v := by
  unfold Life.birth at h; cases hd : x.bDoc <;> simp_all

theorem death_strict {x : Life} {v : Int} (h : x.death true = some v) : x.dRec = true ∧ x.dHi = some v := by
  unfold Life.death at h; cases hd : x.dRec <;> simp_all

/-- True dates `b`, `d` consistent with what `x` documents. -/
def Life.documents (x : Life) (b d : Int) : Prop :=
  (∀ v, x.bDoc = true → x.bLo = some v → v ≤ b) ∧ (∀ v, x.dRec = true → x.dHi = some v → d ≤ v)

theorem chronology_impossible {t s : Life} (h : chronology t s = .impossible) : refutes true t s = true := by
  unfold chronology at h
  repeat' split at h
  all_goals first | assumption | simp_all

/-- **Soundness of the executable verdict.** When the graph says *impossible*,
the two were contemporaries under no dates its documented bounds allow. -/
theorem impossible_sound {t s : Life} (h : chronology t s = .impossible) {bt dt bs ds : Int}
    (ht : t.documents bt dt) (hs : s.documents bs ds) : ¬ muasara bt dt bs ds := by
  have hr := chronology_impossible h
  unfold refutes at hr
  unfold muasara
  rcases Bool.or_eq_true _ _ ▸ hr with h1 | h1
  · obtain ⟨x, y, hx, hy, hxy⟩ := gtOpt_true h1
    obtain ⟨hd, hb⟩ := birth_strict hx
    obtain ⟨hr', hd'⟩ := death_strict hy
    have := hs.1 x hd hb; have := ht.2 y hr' hd'; omega
  · obtain ⟨x, y, hx, hy, hxy⟩ := gtOpt_true h1
    obtain ⟨hd, hb⟩ := birth_strict hx
    obtain ⟨hr', hd'⟩ := death_strict hy
    have := ht.1 x hd hb; have := hs.2 y hr' hd'; omega

end Isnad
