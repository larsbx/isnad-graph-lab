// -*- mode: Bluespec; -*-
/**
 * The transmission of one report, as the isnad records it.
 *
 * A report starts with the source (the Prophet ﷺ). It spreads by hearings: a
 * teacher who holds it tells a student who does not, in some year when both
 * are alive, the teacher at least A_TEACH and the student at least A_HEAR years
 * old. The student names his teacher with a formula: an explicit one (samāʿ,
 * ḥaddathanā) or an ambiguous one (ʿan). Or he commits irsāl: he names his
 * teacher's teacher and drops the teacher, leaving a gap in the isnad. Each
 * holder's isnad is the chain the report came down as he names it. Time only
 * moves forward.
 *
 * The safety properties are the classical conditions on an isnad, stated
 * over every reachable state, each the dynamic counterpart of a theorem in
 * formal/lean:
 *
 * - rootedAtSource: every isnad starts at the source and ends at its holder;
 * - prefixClosed: the isnad of every narrator on an isnad is its prefix up to
 *   him; the isnads form a tree, so a bundle is one (`CommonLink`);
 * - ittisal: every link not marked as a gap is a hearing that happened, with
 *   both alive (muʿāṣara), and every gap hides a hearing from the dropped
 *   narrator;
 * - chronologicalOrder: the hearings along an isnad happen in order;
 * - refutationSound: no hearing happens between narrators whose lifespans
 *   the graph's rule refutes (`refuted_sound`);
 * - weakestLink: a student's isnad grades no better than his teacher's
 *   (`append_no_better`);
 * - gapCaps: an isnad with a gap is ḍaʿīf or worse (`gap_caps`);
 * - sahihExactly: an isnad is ṣaḥīḥ exactly when it has no gap and all its
 *   narrators are ranked 1–3 (`sahih_iff`);
 * - tadlisInherited: an ʿan from a mudallis is a defect of every isnad below
 *   it (al-Shāfiʿī's rule, `tadlis_iff_rejected`).
 *
 * The lives are a small concrete instance: D was born after B died, so the
 * pair B → D is refuted. B is a mudallis.
 */
module lives {
  type Narrator = str
  type Via = str  // how a holder names his source: "sama", "an" or "irsal"

  pure val SOURCE: Narrator = "P"
  pure val NARRATORS: Set[Narrator] = Set("P", "A", "B", "C", "D")
  pure val BIRTH: Narrator -> int = Map("P" -> -53, "A" -> -20, "B" -> 10, "C" -> 40, "D" -> 95)
  pure val DEATH: Narrator -> int = Map("P" -> 11, "A" -> 57, "B" -> 90, "C" -> 130, "D" -> 160)
  /// Ibn Ḥajar's ranks (formal/lean `Grade`); the source is not ranked.
  pure val RANK: Narrator -> int = Map("P" -> 0, "A" -> 1, "B" -> 3, "C" -> 4, "D" -> 8)
  pure val MUDALLIS: Set[Narrator] = Set("B")
  pure val MODES: Set[Via] = Set("sama", "an")
  pure val A_HEAR = 5
  pure val A_TEACH = 20
  pure val FIRST = -53
  pure val LAST = 160

  /// Where the truth of some comparison changes: `y ≥ L` at L (L a birth, or
  /// a birth plus a minimum age), `y ≤ D` at D + 1 (D a death); 0 and 1 cut out
  /// the initial year. Between two consecutive cuts lies one *region*.
  pure val CUTS: Set[int] = Set(FIRST, 0, 1).union(NARRATORS.map(n => Set(
      BIRTH.get(n), BIRTH.get(n) + A_HEAR, BIRTH.get(n) + A_TEACH, DEATH.get(n) + 1)).flatten())
  /// Years a behaviour can use at most: the initial year and one per hearing.
  pure val SPAN = 4
  /// The first SPAN years of every region. See `transmissionRegions`.
  pure val REGIONS: Set[int] = FIRST.to(LAST).filter(y => CUTS.exists(c =>
    c <= y and y - c < SPAN and CUTS.forall(d => d <= y implies d <= c)))
}

/// The model, for any set of years in which hearings may happen.
module transmissionSpec {
  import lives.*
  const YEARS: Set[int]

  pure def alive(n: Narrator, y: int): bool = BIRTH.get(n) <= y and y <= DEATH.get(n)

  /// The graph's refutation of teacher t → student s (formal/lean `refuted`, exact dates).
  pure def refuted(t: Narrator, s: Narrator): bool =
    BIRTH.get(s) > DEATH.get(t) or BIRTH.get(t) > DEATH.get(s)

  // ── grading (formal/lean `Grade`, `Chain`) ──────────────────────────────
  pure def rankVerdict(r: int): int =
    if (r <= 3) 0 else if (r <= 6) 1 else if (r <= 9) 2 else if (r == 10) 3 else if (r == 11) 4 else 5

  pure def maxInt(a: int, b: int): int = if (a >= b) a else b

  pure def below(c: List[Narrator]): List[Narrator] = c.slice(1, length(c))

  pure def worst(c: List[Narrator]): int = below(c).foldl(0, (m, n) => maxInt(m, RANK.get(n)))

  pure def links(c: List[Narrator]): Set[(Narrator, Narrator)] =
    c.indices().filter(i => i > 0).map(i => (c[i - 1], c[i]))

  pure def last(c: List[Narrator]): Narrator = c[length(c) - 1]

  var now: int
  var holders: Set[Narrator]
  var isnad: Narrator -> List[Narrator]
  var via: Narrator -> Via
  var heardIn: Narrator -> int
  var hearings: Set[(Narrator, Narrator, int)]

  /// Some narrator below the source names his source by `how`.
  def namedBy(c: List[Narrator], how: (Narrator, Via) => bool): bool =
    c.indices().exists(i => i > 0 and how(c[i], via.get(c[i])))

  def gap(c: List[Narrator]): bool = namedBy(c, (n, v) => v == "irsal")

  def verdict(c: List[Narrator]): int =
    maxInt(rankVerdict(worst(c)), if (gap(c)) 2 else 0)

  def tadlis(c: List[Narrator]): bool = namedBy(c, (n, v) => MUDALLIS.contains(n) and v == "an")

  action init = all {
    now' = 0,
    holders' = Set(SOURCE),
    isnad' = Map(SOURCE -> [SOURCE]),
    via' = Map(SOURCE -> "sama"),
    heardIn' = Map(SOURCE -> 0),
    hearings' = Set(),
  }

  /// `s` hears from `t` in year `y`, and names as his source `named`'s isnad.
  action tell(t: Narrator, s: Narrator, y: int, named: List[Narrator], how: Via): bool = all {
    holders.contains(t),
    not(holders.contains(s)),
    y >= now,
    alive(t, y),
    alive(s, y),
    y - BIRTH.get(t) >= A_TEACH,
    y - BIRTH.get(s) >= A_HEAR,
    now' = y,
    holders' = holders.union(Set(s)),
    isnad' = isnad.put(s, named.append(s)),
    via' = via.put(s, how),
    heardIn' = heardIn.put(s, y),
    hearings' = hearings.union(Set((t, s, y))),
  }

  /// `s` hears from `t` and names him with formula `m`.
  action hearAt(t: Narrator, s: Narrator, y: int, m: Via): bool = all {
    MODES.contains(m),
    tell(t, s, y, isnad.get(t), m),
  }

  /// Irsāl: `s` hears from `u` but names `u`'s teacher, dropping `u`.
  action irsal(u: Narrator, s: Narrator, y: int): bool = all {
    holders.contains(u),
    u != SOURCE,
    tell(u, s, y, isnad.get(u).slice(0, length(isnad.get(u)) - 1), "irsal"),
  }

  action idle = all {
    now' = now, holders' = holders, isnad' = isnad, via' = via, heardIn' = heardIn,
    hearings' = hearings,
  }

  /// Any holder may tell any non-holder in any year from now on, if the
  /// guards allow it, explicitly, ambiguously, or by irsāl.
  action step = any {
    all {
      holders != NARRATORS,
      nondet t = holders.oneOf()
      nondet s = NARRATORS.exclude(holders).oneOf()
      nondet y = YEARS.filter(y => y >= now).oneOf()
      nondet m = MODES.oneOf()
      any { hearAt(t, s, y, m), irsal(t, s, y) },
    },
    idle,
  }

  // ── witnesses the simulator must reach (tools/verify.sh: non-vacuity) ──
  val noThreeLinkIsnad: bool = holders.forall(h => length(isnad.get(h)) < 4)
  val noGap: bool = holders.forall(h => not(gap(isnad.get(h))))
  val noTadlis: bool = holders.forall(h => not(tadlis(isnad.get(h))))
  val noHasan: bool = holders.forall(h => verdict(isnad.get(h)) != 1)

  // ── safety ───────────────────────────────────────────────────────────────
  val rootedAtSource: bool = holders.forall(h =>
    isnad.get(h).head() == SOURCE and last(isnad.get(h)) == h)

  val prefixClosed: bool = holders.forall(h =>
    isnad.get(h).indices().forall(i =>
      holders.contains(isnad.get(h)[i]) and isnad.get(isnad.get(h)[i]) == isnad.get(h).slice(0, i + 1)))

  val ittisal: bool = holders.forall(h =>
    links(isnad.get(h)).forall(((a, b)) =>
      if (via.get(b) == "irsal")
        hearings.exists(((x, y, yr)) => y == b and isnad.get(x) == isnad.get(a).append(x))
      else
        hearings.exists(((x, y, yr)) => x == a and y == b and alive(a, yr) and alive(b, yr))))

  val chronologicalOrder: bool = holders.forall(h =>
    links(isnad.get(h)).forall(((a, b)) => heardIn.get(a) <= heardIn.get(b)))

  val refutationSound: bool = hearings.forall(((t, s, yr)) => not(refuted(t, s)))

  /// The teacher an isnad names for holder h ≠ source.
  def named(h: Narrator): Narrator = isnad.get(h)[length(isnad.get(h)) - 2]

  val weakestLink: bool = holders.exclude(Set(SOURCE)).forall(h =>
    verdict(isnad.get(h)) >= verdict(isnad.get(named(h))))

  val gapCaps: bool = holders.forall(h => gap(isnad.get(h)) implies verdict(isnad.get(h)) >= 2)

  val sahihExactly: bool = holders.forall(h =>
    (verdict(isnad.get(h)) == 0) iff
      (not(gap(isnad.get(h))) and below(isnad.get(h)).foldl(true, (ok, n) => ok and RANK.get(n) <= 3)))

  val tadlisInherited: bool = holders.exclude(Set(SOURCE)).forall(h =>
    tadlis(isnad.get(named(h))) implies tadlis(isnad.get(h)))

  val safety: bool = rootedAtSource and prefixClosed and ittisal and chronologicalOrder
    and refutationSound and weakestLink and gapCaps and sahihExactly and tadlisInherited

}

/// The model over every year from the Prophet's birth to the last death:
/// checked by the simulator and, to a bounded depth, by Apalache.
module transmission {
  import lives.*
  import transmissionSpec(YEARS = FIRST.to(LAST)).*

  // ── runs ─────────────────────────────────────────────────────────────────
  /// A connected ṣaḥīḥ isnad P → A → B is reachable, and grades ṣaḥīḥ.
  run chainExistsTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "B", 40, "sama"))
      .then(all { assert(isnad.get("B") == ["P", "A", "B"]), assert(verdict(isnad.get("B")) == 0),
                  assert(safety), idle })

  /// C (ṣadūq, rank 4) makes the isnad ḥasan at best.
  run hasanBelowSaduqTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "C", 50, "sama"))
      .then(all { assert(verdict(isnad.get("C")) == 1), assert(safety), idle })

  /// C hears from B but names A: a gap, so ḍaʿīf; the hearing from B stays recorded.
  run irsalLeavesAGapTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "B", 40, "sama"))
      .then(irsal("B", "C", 60))
      .then(all { assert(isnad.get("C") == ["P", "A", "C"]), assert(gap(isnad.get("C"))),
                  assert(verdict(isnad.get("C")) == 2), assert(hearings.contains(("B", "C", 60))),
                  assert(safety), idle })

  /// B, a mudallis, says ʿan: a defect for B and for C below him.
  run tadlisIsInheritedTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "B", 40, "an"))
      .then(hearAt("B", "C", 70, "sama"))
      .then(all { assert(tadlis(isnad.get("B"))), assert(tadlis(isnad.get("C"))), assert(safety), idle })

  /// B cannot teach D: D was born after B died.
  run refutedPairCannotHearTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "B", 40, "sama"))
      .then(hearAt("B", "D", 100, "sama"))
      .fail()

  /// Nor can D claim B by irsāl from C unless C really heard: C must hold it first.
  run irsalNeedsARealHearingTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(irsal("C", "D", 120))
      .fail()

  /// A child below A_HEAR cannot hear: B was one when the Prophet died.
  run tooYoungCannotHearTest = init.then(hearAt("P", "B", 11, "sama")).fail()

  /// Time does not run backwards.
  run noHearingInThePastTest =
    init
      .then(hearAt("P", "A", 5, "sama"))
      .then(hearAt("A", "B", 4, "sama"))
      .fail()

  /// The source does not commit irsāl: there is no one above him to name.
  run sourceCannotBeDroppedTest = init.then(irsal("P", "A", 5)).fail()
}

/**
 * The same model over REGIONS only, checked exhaustively by TLC.
 *
 * Years enter the guards and the invariants only through comparisons with
 * thresholds (`y ≥ L` for a birth or a birth plus a minimum age, `y ≤ D` for a
 * death) and with each other (`y ≥ now`, `heardIn(a) ≤ heardIn(b)`). Within a
 * region every threshold comparison has one truth value. A behaviour uses at
 * most SPAN + 1 distinct years: 0, which is a region of its own, and one per
 * hearing, at most SPAN. So there is an order-preserving injection g from the
 * years a behaviour uses into REGIONS that keeps each year in its region (a
 * region has all its years in REGIONS, or at least SPAN). Applying g to every
 * year maps the behaviour to one of this module in which every guard and
 * every invariant has the same truth value at every step; REGIONS ⊆
 * FIRST..LAST gives the converse. The invariants hold in `transmission` iff
 * they hold here.
 *
 * Each hearing adds a holder and there are SPAN narrators below the source,
 * so every behaviour reaches its last state within SPAN hearings: TLC's
 * search of this module covers every reachable state, at every depth.
 */
module transmissionRegions {
  import lives.*
  import transmissionSpec(YEARS = REGIONS).*
}
