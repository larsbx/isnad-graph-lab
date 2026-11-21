import Lean.Data.Json
import Std.Data.HashSet
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
  chain | null]`, each mention `[rawi | null, start, end]`;
* `stratified`: `[strata, rr | null, status, z | null, p | null, informative]`,
  each stratum `[a, n1, b, n0]`. Recomputed exactly: the risk ratio to its
  3 decimals, z to its 4 (by squares: z = S/√V), p to a relative 1e-9.

With `--regions FILE` it instead checks the Quint model's critical years
(`tools/verify.sh` writes FILE from the Quint REPL): `REGIONS` is
`Regions.regionYears CUTS SPAN FIRST LAST`, and FIRST, 0 and 1 are cuts and
SPAN ≥ 1, the side conditions of `Regions.reduction` and
`Regions.perRegion_of_initial`; and that the lives, ages and cuts there
are `Model.Q.lives` and `Model.Q.cuts`, for which `Model.Q.transmission_iff_regions`
is proved.

With `--itf DIR` it replays every Quint trace in DIR (`quint run --out-itf`):
from `Model.init`, each next state must be an idle step or one of
`Model.successors`, each of which is a `Model.step` (`successors_step`), and
must agree with Quint's state on every variable.

With `--count N` it enumerates every state reachable in `Model` over the
region years and checks there are N: the number TLC finds for
`transmissionRegions`. With the replay, which shows Quint's steps are
`Model.step`s, the equal count shows `Model` adds none.
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

namespace Replay
open Isnad.Model

def narrator : String → Except String Model.Q
  | "P" => pure .P | "A" => pure .A | "B" => pure .B | "C" => pure .C | "D" => pure .D
  | x => throw s!"unknown narrator {x}"

def via : String → Except String Via
  | "sama" => pure .sama | "an" => pure .an | "irsal" => pure .irsal
  | x => throw s!"unknown formula {x}"

def big (j : Json) : Except String Int := do
  let x ← j.getObjValAs? String "#bigint"
  match x.toInt? with
  | some i => pure i
  | none => throw s!"bad integer {x}"

def tagged (tag : String) (j : Json) : Except String (List Json) := do
  return (← j.getObjValAs? (Array Json) tag).toList

def pairs (j : Json) : Except String (List (Json × Json)) := do
  (← tagged "#map" j).mapM fun p => do let a ← p.getArr?; pure (a[0]!, a[1]!)

/-- A Quint state, as observed. -/
structure Obs where
  now : Int
  holders : List Model.Q
  isnad : List (Model.Q × List Model.Q)
  via : List (Model.Q × Via)
  heardIn : List (Model.Q × Int)
  hearings : List (Model.Q × Model.Q × Int)

def obs (vars : List String) (st : Json) : Except String Obs := do
  let get (v : String) : Except String Json := do
    match vars.find? (·.endsWith ("::" ++ v)) with
    | some k => st.getObjVal? k
    | none => throw s!"no variable {v}"
  let str (j : Json) := j.getStr?
  return {
    now := ← big (← get "now")
    holders := ← (← tagged "#set" (← get "holders")).mapM fun j => do narrator (← str j)
    isnad := ← (← pairs (← get "isnad")).mapM fun (k, v) => do
      pure (← narrator (← str k), ← (← v.getArr?).toList.mapM fun j => do narrator (← str j))
    via := ← (← pairs (← get "via")).mapM fun (k, v) => do pure (← narrator (← str k), ← via (← str v))
    heardIn := ← (← pairs (← get "heardIn")).mapM fun (k, v) => do pure (← narrator (← str k), ← big v)
    hearings := ← (← tagged "#set" (← get "hearings")).mapM fun h => do
      let t ← tagged "#tup" h
      pure (← narrator (← str t[0]!), ← narrator (← str t[1]!), ← big t[2]!) }

def sameSet {α} [BEq α] (a b : List α) : Bool := a.all b.contains && b.all a.contains

/-- The Lean state agrees with Quint's on every variable (maps on their keys, the holders). -/
def agree (s : St Model.Q) (o : Obs) : Bool :=
  s.now == o.now && sameSet s.holders o.holders && sameSet (o.isnad.map (·.1)) o.holders &&
    o.isnad.all (fun (n, l) => s.isnad n == l) && o.via.all (fun (n, v) => s.via n == v) &&
    o.heardIn.all (fun (n, y) => s.heardIn n == y) && sameSet (o.via.map (·.1)) o.holders &&
    sameSet (o.heardIn.map (·.1)) o.holders && sameSet s.hearings o.hearings

def inYears (y : Int) : Bool := decide (Model.Q.first ≤ y ∧ y ≤ Model.Q.last)

/-- Replay one trace: its hearings' formulas, or why it fails. -/
def trace (j : Json) : Except String (List Via) := do
  let vars ← j.getObjValAs? (List String) "vars"
  let states ← (← j.getObjValAs? (Array Json) "states").toList.mapM (obs vars)
  let some o0 := states.head? | throw "empty trace"
  unless agree (init Model.Q.lives) o0 do throw "the first state is not Model.init"
  let mut cur := init Model.Q.lives
  let mut hearings : List Via := []
  for o in states.tail do
    if agree cur o then continue
    match (successors Model.Q.lives inYears Model.Q.all cur o.now).find? (agree · o) with
    | some s =>
      let u := s.holders.head!
      cur := s; hearings := s.via u :: hearings
    | none => throw s!"no Model.step reaches the state at now = {o.now}"
  return hearings

def run (dir : String) : IO UInt32 := do
  let files := (← System.FilePath.readDir dir).filter (·.fileName.endsWith ".itf.json")
  let mut steps : List Via := []
  let mut bad := 0
  for f in files do
    match trace (← IO.ofExcept (Json.parse (← IO.FS.readFile f.path))) with
    | .ok vs => steps := vs ++ steps
    | .error e => bad := bad + 1; if bad ≤ 5 then IO.println s!"  {f.fileName}: {e}"
  let n (v : Via) := (steps.filter (· == v)).length
  IO.println s!"replay: {files.size - bad}/{files.size} Quint traces are Model.step runs: \
    {n .sama} samāʿ, {n .an} ʿan, {n .irsal} irsāl hearings"
  -- every kind of step must occur, or the replay says nothing about it
  return if bad == 0 && files.size > 0 && n .sama > 0 && n .an > 0 && n .irsal > 0 then 0 else 1

/-- A state as TLC tells states apart: its variables, maps on their keys. -/
def key (s : St Model.Q) : String :=
  let hs := Model.Q.all.filter s.holders.contains
  let hear := (s.hearings.map fun (t, u, y) => s!"{t.name}{u.name}{y}").mergeSort
  s!"{s.now}|" ++ String.intercalate ";" (hs.map fun n =>
      s!"{n.name}:{(s.isnad n).map Model.Q.name}:{repr (s.via n)}:{s.heardIn n}") ++ "|" ++
    String.intercalate "," hear

/-- Every successor in a region year, each teacher and student taken once. -/
def regionSuccessors (years : List Int) (s : St Model.Q) : List (St Model.Q) :=
  let L := Model.Q.lives
  let inY (y : Int) := years.contains y
  s.holders.flatMap fun t => (Model.Q.all.filter (!s.holders.contains ·)).flatMap fun u =>
    let lo := max s.now (max (L.birth t + L.aT) (L.birth u + L.aH))
    let hi := min (L.death t) (L.death u)
    (years.filter fun y => lo ≤ y && y ≤ hi).flatMap fun y =>
      ([Via.sama, Via.an].filterMap fun m => tellB L inY s t u y (s.isnad t) m) ++
        (if t ≠ L.src then (tellB L inY s t u y (s.isnad t).dropLast .irsal).toList else [])

def count (want : Nat) : IO UInt32 := do
  let years := Regions.regionYears Model.Q.cuts Model.Q.span Model.Q.first Model.Q.last
  let s0 := init Model.Q.lives
  let mut seen : Std.HashSet String := {}
  seen := seen.insert (key s0)
  let mut queue : Array (St Model.Q) := #[s0]
  let mut i := 0
  while h : i < queue.size do
    for s' in regionSuccessors years queue[i] do
      let k := key s'
      unless seen.contains k do
        seen := seen.insert k
        queue := queue.push s'
    i := i + 1
  IO.println s!"count: Model reaches {seen.size} states over the region years; TLC found {want}"
  return if seen.size == want then 0 else 1

end Replay

def regions (path : String) : IO UInt32 := do
  let j ← IO.ofExcept (Json.parse (← IO.FS.readFile path))
  let get (k : String) : IO Int := IO.ofExcept (j.getObjValAs? Int k)
  let ints (k : String) : IO (List Int) := IO.ofExcept (j.getObjValAs? (List Int) k)
  let first ← get "first"
  let last ← get "last"
  let span := (← get "span").toNat
  let cuts ← ints "cuts"
  let quint ← ints "regions"
  let lean := Regions.regionYears cuts span first last
  let sides := cuts.contains first && cuts.contains 0 && cuts.contains 1 && span ≥ 1
  IO.println s!"regions: {quint.length} Quint years, {lean.length} by regionYears, side conditions {sides}"
  -- the constants `Model.Q.transmission_iff_regions` is proved for
  let L := Model.Q.lives
  let life (k : String) (f : Model.Q → Int) : IO Bool := do
    let m ← IO.ofExcept (j.getObjValAs? Json k)
    Model.Q.all.allM fun n => do pure ((← IO.ofExcept (m.getObjValAs? Int n.name)) == f n)
  let same := first == Model.Q.first && last == Model.Q.last && span == Model.Q.span &&
    (← get "a_hear") == L.aH && (← get "a_teach") == L.aT && (← life "birth" L.birth) &&
    (← life "death" L.death) && Replay.sameSet cuts Model.Q.cuts
  IO.println s!"lives: Quint's constants are Model.Q's: {same}"
  return if sides && same && lean == quint.mergeSort then 0 else 1

def main (args : List String) : IO UInt32 := do
  if let ["--regions", path] := args then return ← regions path
  if let ["--itf", dir] := args then return ← Replay.run dir
  if let ["--count", n] := args then return ← Replay.count n.toNat!
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
