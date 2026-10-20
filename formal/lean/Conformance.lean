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
  `[bLo, dLo, dHi, bDoc, dRec, conflict]`.
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
  return if v && c then 0 else 1
