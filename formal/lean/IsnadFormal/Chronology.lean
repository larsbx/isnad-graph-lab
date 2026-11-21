import Hadith.ClassicalCriteria

/-!
# *Muʿāṣara* and *liqāʾ*: when two lives allow a transmission

Muslim's *Muqaddimat al-Ṣaḥīḥ* (ed. ʿAbd al-Bāqī, pp. 29–33) describes
the presumption for an ambiguous transmission between trustworthy narrators
when meeting and hearing are possible and there is no contrary evidence.
He discusses separate examination of hearing for known mudallis narrators.
The findings for applying that presumption are recorded independently of
the arithmetic on life dates.

The graph knows lives up to intervals, with a birth in `[bLo, bHi]` and a
death in `[dLo, dHi]`. The interval proofs give:

* the graph's refutation is sound: when the bounds refute a pair, no dates
  within them make the two contemporaries;
* it is the best possible: when they do not refute it, some dates within them
  do;
* if there is a common year within the two lifetimes, the lifetimes overlap;
* the window the lifelines use, with minimum ages, is non-empty exactly when a
  hearing at those ages can fit.
-/

namespace Isnad
open Hadith.ClassicalCriteria (Finding)

/-- Independent findings about applying Muslim's presumption to an ʿanʿana.
An interval overlap is one input to investigating the possibility of meeting
and hearing. These findings also require consideration of the transmitters
and of evidence against meeting or hearing. -/
structure MuslimAnanaFindings where
  bothTrustworthy : Finding
  meetingAndHearingPossible : Finding
  freeOfKnownTadlis : Finding
  freeOfContraryEvidence : Finding

def MuslimAnanaFindings.Presumption (f : MuslimAnanaFindings) : Prop :=
  f.bothTrustworthy = .established ∧ f.meetingAndHearingPossible = .established ∧
    f.freeOfKnownTadlis = .established ∧ f.freeOfContraryEvidence = .established

theorem muslim_presumption_requires_review (f : MuslimAnanaFindings)
    (h : f.freeOfContraryEvidence = .unresolved) : ¬ f.Presumption := by
  simp [MuslimAnanaFindings.Presumption, h]

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

/-- The date constraint for two people being alive in year `τ`. -/
def withinBothLives (bt dt bs ds τ : Int) : Prop := bt ≤ τ ∧ τ ≤ dt ∧ bs ≤ τ ∧ τ ≤ ds

/-- Earlier name for the date constraint on a candidate meeting year. -/
abbrev liqa := withinBothLives

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

/-- A year within both lifetimes witnesses contemporaneity. -/
theorem liqa_muasara {bt dt bs ds τ : Int} (h : liqa bt dt bs ds τ) : muasara bt dt bs ds := by
  unfold liqa withinBothLives at h; unfold muasara; omega

/-- Under the admitted dates, a refuted link has no candidate meeting year. -/
theorem refuted_no_liqa {T S : Bounds} (h : refuted T S) {bt dt bs ds τ : Int}
    (ht : T.admits bt dt) (hs : S.admits bs ds) : ¬ liqa bt dt bs ds τ :=
  fun hl => refuted_sound h ht hs (liqa_muasara hl)

/-- An attested meeting must occur within both lifetimes. Subject to this
evidential premise, documented non-overlap rules out that meeting. -/
theorem refuted_no_attested_meeting {T S : Bounds} (h : refuted T S)
    {bt dt bs ds : Int} (ht : T.admits bt dt) (hs : S.admits bs ds)
    {attested : Int → Prop} (dates : ∀ τ, attested τ → withinBothLives bt dt bs ds τ)
    (τ : Int) : ¬ attested τ :=
  fun meet => refuted_no_liqa h ht hs (dates τ meet)

/-- **The lifeline window.** With a teacher at least `aT` and a student at least
`aH` years old (both non-negative), a hearing fits iff
`max (bt + aT) (bs + aH) ≤ min dt ds`. -/
theorem window_iff (bt dt bs ds aT aH : Int) (hT : 0 ≤ aT) (hH : 0 ≤ aH) :
    max (bt + aT) (bs + aH) ≤ min dt ds ↔
      ∃ τ, liqa bt dt bs ds τ ∧ bt + aT ≤ τ ∧ bs + aH ≤ τ := by
  constructor
  · intro h; exact ⟨max (bt + aT) (bs + aH), by unfold liqa withinBothLives; omega, by omega, by omega⟩
  · rintro ⟨τ, hl, h1, h2⟩; unfold liqa withinBothLives at hl; omega

end Isnad
