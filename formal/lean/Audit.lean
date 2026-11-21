import Lean
import IsnadFormal

/-!
The audit covers `Isnad` and the shared `Hadith.ClassicalCriteria` module and
allows Lean's three standard axioms. Run by `tools/verify.sh`.
-/

open Lean Elab Command in
#eval show CommandElabM Unit from do
  let allowed := [``propext, ``Classical.choice, ``Quot.sound]
  let mut checked := 0
  let mut bad : Array (Name × Name) := #[]
  for (n, ci) in (← getEnv).constants.toList do
    if ((`Isnad).isPrefixOf n || (`Hadith.ClassicalCriteria).isPrefixOf n) &&
        ci matches .thmInfo _ then
      checked := checked + 1
      for a in ← liftCoreM (collectAxioms n) do
        unless allowed.contains a do bad := bad.push (n, a)
  if bad.isEmpty then
    logInfo m!"axiom audit: {checked} theorems use only propext, Classical.choice, Quot.sound"
  else
    throwError m!"axiom audit failed: {bad.toList}"
