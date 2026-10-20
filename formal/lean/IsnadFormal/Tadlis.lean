/-!
# *Tadlīs*: al-Shāfiʿī's rule

al-Shāfiʿī (*al-Risāla*): the report of a narrator known for *tadlīs* is not
accepted until he says *ḥaddathanī* or *samiʿtu*, an explicit statement of
hearing. An ambiguous formula from him (*ʿan*, *anna*, *qāla* …) does not
establish hearing.

The graph's `TADLIS` and `TADLIS_WEAK` defects flag a link whose student is a
*mudallis* and whose formula is ambiguous. This file proves that is exactly
the set of links al-Shāfiʿī's rule does not accept.
-/

namespace Isnad

/-- The four classes of transmission formula (`isnad_graph.sigha`). -/
inductive ModeClass where
  | explicit | written | ambiguous | unread
  deriving DecidableEq, Repr

/-- al-Shāfiʿī's rule: a *mudallis* is heard only through an unambiguous formula. -/
def shafiiAccepts (mudallis : Bool) (m : ModeClass) : Bool := !mudallis || m != .ambiguous

/-- The graph's tadlīs defect (`assess.assess_chains`). -/
def tadlisDefect (mudallis : Bool) (m : ModeClass) : Bool := mudallis && m == .ambiguous

theorem tadlis_iff_rejected (mudallis : Bool) (m : ModeClass) :
    tadlisDefect mudallis m = !shafiiAccepts mudallis m := by
  cases mudallis <;> cases m <;> decide

/-- An explicit statement of hearing clears a *mudallis*. -/
theorem explicit_clears (mudallis : Bool) : shafiiAccepts mudallis .explicit = true := by
  cases mudallis <;> decide

end Isnad
