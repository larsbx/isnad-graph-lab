/-!
# *Muʿāṣara* and *liqāʾ*: when two lives allow a transmission

A link is *muttaṣil* only if the student can have heard from the teacher. The
classical standards differ in what they demand:

* **Muslim** (*Muqaddimat al-Ṣaḥīḥ*): *muʿāṣara*, the two were contemporaries
  and a meeting was possible, provided the narrator is not a *mudallis*;
* **al-Bukhārī and ʿAlī b. al-Madīnī** (as Ibn Rajab and Ibn Ḥajar report them):
  *thubūt al-liqāʾ*, at least one meeting is established.

Both need the lives to overlap. The graph knows lives only up to intervals: a
birth in `[bLo, bHi]`, a death in `[dLo, dHi]`. This file proves:

* the graph's refutation is sound: when the bounds refute a pair, no dates
  within them make the two contemporaries;
* it is the best possible: when they do not refute it, some dates within them
  do;
* *liqāʾ* implies *muʿāṣara*, so a refuted link fails both standards;
* the window the lifelines use, with minimum ages, is non-empty exactly when a
  hearing at those ages can fit.
-/

namespace Isnad

/-- What the graph knows of a life. -/
structure Bounds where
  bLo : Int
  bHi : Int
  dLo : Int
  dHi : Int

/-- True dates `b`, `d` that the bounds allow. -/
def Bounds.admits (B : Bounds) (b d : Int) : Prop :=
  B.bLo ≤ b ∧ b ≤ B.bHi ∧ B.dLo ≤ d ∧ d ≤ B.dHi ∧ b ≤ d

/-- The bounds allow some life at all. -/
def Bounds.wellFormed (B : Bounds) : Prop := B.bLo ≤ B.bHi ∧ B.dLo ≤ B.dHi ∧ B.bLo ≤ B.dHi

/-- *Muʿāṣara*: the lives `[bt, dt]` and `[bs, ds]` overlap. -/
def muasara (bt dt bs ds : Int) : Prop := bs ≤ dt ∧ bt ≤ ds

/-- *Liqāʾ*: a meeting in year `τ` with both alive. -/
def liqa (bt dt bs ds τ : Int) : Prop := bt ≤ τ ∧ τ ≤ dt ∧ bs ≤ τ ∧ τ ≤ ds

/-- The graph's refutation of teacher `T` → student `S`. -/
def refuted (T S : Bounds) : Prop := S.bLo > T.dHi ∨ T.bLo > S.dHi

instance (T S : Bounds) : Decidable (refuted T S) := by unfold refuted; infer_instance

/-- **Soundness.** A refuted pair were contemporaries under no admitted dates. -/
theorem refuted_sound {T S : Bounds} (h : refuted T S) {bt dt bs ds : Int}
    (ht : T.admits bt dt) (hs : S.admits bs ds) : ¬ muasara bt dt bs ds := by
  unfold refuted at h; unfold Bounds.admits at ht hs; unfold muasara; omega

/-- **Completeness.** An unrefuted pair were contemporaries under some admitted dates. -/
theorem unrefuted_complete {T S : Bounds} (h : ¬ refuted T S)
    (wt : T.wellFormed) (ws : S.wellFormed) :
    ∃ bt dt bs ds, T.admits bt dt ∧ S.admits bs ds ∧ muasara bt dt bs ds := by
  unfold refuted at h; unfold Bounds.wellFormed at wt ws
  exact ⟨T.bLo, T.dHi, S.bLo, S.dHi, by unfold Bounds.admits; omega,
    by unfold Bounds.admits; omega, by unfold muasara; omega⟩

/-- al-Bukhārī's standard implies Muslim's: a meeting makes them contemporaries. -/
theorem liqa_muasara {bt dt bs ds τ : Int} (h : liqa bt dt bs ds τ) : muasara bt dt bs ds := by
  unfold liqa at h; unfold muasara; omega

/-- A refuted link fails both standards: no admitted dates allow a meeting. -/
theorem refuted_no_liqa {T S : Bounds} (h : refuted T S) {bt dt bs ds τ : Int}
    (ht : T.admits bt dt) (hs : S.admits bs ds) : ¬ liqa bt dt bs ds τ :=
  fun hl => refuted_sound h ht hs (liqa_muasara hl)

/-- **The lifeline window.** With a teacher at least `aT` and a student at least
`aH` years old (both non-negative), a hearing fits iff
`max (bt + aT) (bs + aH) ≤ min dt ds`. -/
theorem window_iff (bt dt bs ds aT aH : Int) (hT : 0 ≤ aT) (hH : 0 ≤ aH) :
    max (bt + aT) (bs + aH) ≤ min dt ds ↔
      ∃ τ, liqa bt dt bs ds τ ∧ bt + aT ≤ τ ∧ bs + aH ≤ τ := by
  constructor
  · intro h; exact ⟨max (bt + aT) (bs + aH), by unfold liqa; omega, by omega, by omega⟩
  · rintro ⟨τ, hl, h1, h2⟩; unfold liqa at hl; omega

end Isnad
