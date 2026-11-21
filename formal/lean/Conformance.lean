import Lean.Data.Json
import IsnadFormal

/-!
# Conformance: the Python implementation against the Lean model

Reads `formal/vectors/conformance.json`, written by
`tools/export_vectors.py` from the committed graph, and recomputes every
verdict with the Lean definitions. It exits non-zero on the first category
with a mismatch, and prints the mismatches it found.

* `verdict`: `[worst_rank | null, gap, expected_code]`, the full domain and
  every combination stored on a chain;
* `chronology`: `[teacher, student, expected]`, each end
  `[bLo, dLo, dHi, bDoc, dRec, conflict]`;
* `phases`: `[birth, death, hearing | null, teaching | null, expected]` in
  half-years, each expected phase `[kind, from, to]`;
* `common_link`: `[companion, chains, strand, common_link | null]`, under
  `parameters.dominance = [num, den]` and `parameters.min_chains`;
* `inference`: `[mentions, matn | null, text, known, abstention | null,
  chain | null]`, each mention `[rawi | null, start, end]`.
-/

open Lean Isnad

def optInt (j : Json) : Except String (Option Int) :=
  if j.isNull then pure none else some <$> j.getInt?

def life (j : Json) : Except String Life := do
  let a ← j.getArr?
  unless a.size == 6 do throw s!"life needs 6 fields: {j.compress}"
  return { bLo := ← optInt a[0]!, dLo := ← optInt a[1]!, dHi := ← optInt a[2]!,
           bDoc := ← a[3]!.getBool?, dRec := ← a[4]!.getBool?, conflict := ← a[5]!.getBool? }

def verdictRow (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let w ← (← optInt a[0]!).mapM fun i => pure i.toNat
  let got := (structuralVerdict w (← a[1]!.getBool?)).code
  let want ← a[2]!.getNat?
  return (got == want, s!"{j.compress} → {got}")

def chronologyRow (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let got := (chronology (← life a[0]!) (← life a[1]!)).name
  let want ← a[2]!.getStr?
  return (got == want, s!"{j.compress} → {got}")

def window (j : Json) : Except String Window :=
  if j.isNull then pure none else do
    let a ← j.getArr?
    return some (← a[0]!.getInt?, ← a[1]!.getInt?)

def phasesRow (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let got := (phases (← a[0]!.getInt?) (← a[1]!.getInt?) (← window a[2]!) (← window a[3]!)).map
    fun s => Json.arr #[s.kind.name, s.lo, s.hi]
  return (Json.arr got.toArray == a[4]!, s!"{j.compress} → {(Json.arr got.toArray).compress}")

def ints (j : Json) : Except String (List Int) := do (← j.getArr?).toList.mapM (·.getInt?)

def commonLinkRow (num den minChains : Nat) (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let c ← a[0]!.getInt?
  let B ← (← a[1]!.getArr?).toList.mapM ints
  let s := strand B num den c
  let cl := commonLink B num den minChains c
  let want ← if a[3]!.isNull then pure none else some <$> a[3]!.getInt?
  return (s == (← ints a[2]!) && cl == want, s!"bundle of {c}: strand {s}, common link {cl}")

def mention (j : Json) : Except String Mention := do
  let a ← j.getArr?
  return { rawi := ← optInt a[0]!, start := ← a[1]!.getNat?, stop := ← a[2]!.getNat? }

def inferenceRow (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let ms ← (← a[0]!.getArr?).toList.mapM mention
  let matn ← if a[1]!.isNull then pure none else some <$> a[1]!.getNat?
  let text := (← a[2]!.getStr?).toList
  let known ← ints a[3]!
  let why := (abstention ms matn text known).map (·.name)
  let ch := infer ms matn text known
  let wantWhy ← if a[4]!.isNull then pure none else some <$> a[4]!.getStr?
  let wantCh ← if a[5]!.isNull then pure none else some <$> ints a[5]!
  return (why == wantWhy && ch == wantCh, s!"{j.compress} → {why}, {ch}")

/-! Exact rationals `n / d`, `d > 0`, enough for the checks. -/
structure Q where
  n : Int
  d : Nat

def Q.ofFrac (p : Int × Nat) : Q := ⟨p.1, p.2⟩
def Q.ofJson (j : Json) : Except String Q := do
  let x ← j.getNum?
  return ⟨x.mantissa, 10 ^ x.exponent⟩
def Q.sub (a b : Q) : Q := ⟨a.n * b.d - b.n * a.d, a.d * b.d⟩
def Q.le (a b : Q) : Bool := a.n * b.d ≤ b.n * a.d
def Q.abs (a : Q) : Q := ⟨a.n.natAbs, a.d⟩
def Q.add (a b : Q) : Q := ⟨a.n * b.d + b.n * a.d, a.d * b.d⟩
def Q.mul (a b : Q) : Q := ⟨a.n * b.n, a.d * b.d⟩
def Q.div (a b : Q) : Q := ⟨a.n * b.d * (if b.n < 0 then -1 else 1), a.d * b.n.natAbs⟩
def Q.near (a b tol : Q) : Bool := (a.sub b).abs.le tol
/-- `S / √V ≥ x`, for `V > 0`, without square roots. -/
def geRoot (S V x : Q) : Bool :=
  if x.n ≤ 0 then S.n ≥ 0 || (S.mul S).le ((x.mul x).mul V)
  else S.n > 0 && ((x.mul x).mul V).le (S.mul S)
def leRoot (S V x : Q) : Bool := geRoot ⟨-S.n, S.d⟩ V ⟨-x.n, x.d⟩

def stratifiedRow (j : Json) : Except String (Bool × String) := do
  let a ← j.getArr?
  let ss ← (← a[0]!.getArr?).toList.mapM fun t => do
    let v ← t.getArr?
    return (⟨← v[0]!.getNat?, ← v[1]!.getNat?, ← v[2]!.getNat?, ← v[3]!.getNat?⟩ : Table)
  let pos := ss.filter (·.t ≠ 0)
  let num := Q.ofFrac (fsum (pos.map fun s => ((s.mhNum : Int), s.t)))
  let den := Q.ofFrac (fsum (pos.map fun s => ((s.mhDen : Int), s.t)))
  let status := if den.n ≠ 0 then "finite" else if num.n ≠ 0 then "infinite" else "undefined"
  let rrOk ← if den.n = 0 then pure a[1]!.isNull else do
    pure (Q.near (num.div den) (← Q.ofJson a[1]!) ⟨5000001, 10 ^ 10⟩)
  let S := Q.ofFrac (score ss)
  let V := Q.ofFrac (fsum ((ss.filter (·.t > 1)).map fun s => ((s.varNum : Int), s.t * s.t * (s.t - 1))))
  let informative := (ss.filter fun s => s.t > 1 && s.varNum > 0).length
  let zpOk ← if V.n = 0 then pure (a[3]!.isNull && a[4]!.isNull) else do
    let z ← Q.ofJson a[3]!
    let tol : Q := ⟨500001, 10 ^ 10⟩
    let p := pExactFast ss
    let pq ← Q.ofJson a[4]!
    let exact : Q := ⟨p.1, p.2⟩
    pure (geRoot S V (z.sub tol) && leRoot S V (z.add tol) &&
      Q.near pq exact (exact.mul ⟨1, 10 ^ 9⟩))
  let ok := rrOk && zpOk && status == (← a[2]!.getStr?) && informative == (← a[5]!.getNat?)
  return (ok, s!"{a[0]!.compress}: status {status}, informative {informative}")

def check (name : String) (rows : Array Json)
    (row : Json → Except String (Bool × String)) : IO Bool := do
  let mut bad : Array String := #[]
  for r in rows do
    let (ok, msg) ← IO.ofExcept (row r)
    unless ok do bad := bad.push msg
  IO.println s!"{name}: {rows.size - bad.size}/{rows.size} agree"
  for m in bad.toList.take 10 do IO.println s!"  mismatch {m}"
  return bad.isEmpty

def main (args : List String) : IO UInt32 := do
  let path := args.headD "../vectors/conformance.json"
  let j ← IO.ofExcept (Json.parse (← IO.FS.readFile path))
  let v ← check "verdict" (← IO.ofExcept (j.getObjValAs? (Array Json) "verdict")) verdictRow
  let c ← check "chronology" (← IO.ofExcept (j.getObjValAs? (Array Json) "chronology")) chronologyRow
  let p ← check "phases" (← IO.ofExcept (j.getObjValAs? (Array Json) "phases")) phasesRow
  let par ← IO.ofExcept (j.getObjVal? "parameters")
  let dom ← IO.ofExcept (par.getObjValAs? (Array Nat) "dominance")
  let minChains ← IO.ofExcept (par.getObjValAs? Nat "min_chains")
  let l ← check "common_link" (← IO.ofExcept (j.getObjValAs? (Array Json) "common_link"))
    (commonLinkRow dom[0]! dom[1]! minChains)
  let i ← check "inference" (← IO.ofExcept (j.getObjValAs? (Array Json) "inference")) inferenceRow
  let st ← check "stratified" (← IO.ofExcept (j.getObjValAs? (Array Json) "stratified")) stratifiedRow
  return if v && c && p && l && i && st then 0 else 1
