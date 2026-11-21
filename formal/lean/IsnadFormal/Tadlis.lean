import Hadith.ClassicalCriteria

/-!
# Explicit hearing for a narrator known for tadlīs

Al-Shāfiʿī's *al-Risāla* (ed. Aḥmad Shākir, p. 378) requires an explicit
statement of hearing such as *ḥaddathanī* or *samiʿtu* from a known mudallis
for the narration at issue. The formula check concerns this requirement.
The graph's `TADLIS` and `TADLIS_WEAK` flags only record ambiguous formulas.
A link with an unread or written label alone still lacks the required explicit
hearing formula in this check.
-/

namespace Isnad
open Hadith.ClassicalCriteria (Finding)

/-- The four classes of transmission formula (`isnad_graph.sigha`). -/
inductive ModeClass where
  | explicit | written | ambiguous | unread
  deriving DecidableEq, Repr

/-- The explicit-hearing condition under this rule. The finding concerns the
wording of the report on the route being judged, independently of graph flags. -/
def shafiiAccepts (mudallis : Bool) (explicitHearing : Finding) : Bool :=
  !mudallis || decide (explicitHearing = .established)

/-- The graph's tadlīs defect (`assess.assess_chains`). -/
def tadlisDefect (mudallis : Bool) (m : ModeClass) : Bool := mudallis && m == .ambiguous

theorem tadlis_iff_ambiguous (mudallis : Bool) (m : ModeClass) :
    tadlisDefect mudallis m = true ↔ mudallis = true ∧ m = .ambiguous := by
  cases mudallis <;> cases m <;> decide

theorem shafii_requires_explicit (h : Finding) :
    shafiiAccepts true h = true ↔ h = .established := by simp [shafiiAccepts]

/-- An explicit statement meets this hearing requirement. -/
theorem explicit_clears (mudallis : Bool) : shafiiAccepts mudallis .established = true := by
  cases mudallis <;> decide

example : tadlisDefect true .unread = false ∧ shafiiAccepts true .unresolved = false := by decide
example : tadlisDefect true .written = false ∧ shafiiAccepts true .unresolved = false := by decide

end Isnad
