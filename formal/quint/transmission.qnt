// -*- mode: Bluespec; -*-
/**
 * The transmission of one report, as the isnad records it.
 *
 * A report starts with the source (the Prophet ﷺ). It spreads by hearings: a
 * teacher who holds it tells a student who does not, in some year when both
 * are alive, the teacher at least A_TEACH and the student at least A_HEAR years
 * old. Each holder's isnad is the chain of hearings that brought the report to
 * them. Time only moves forward.
 *
 * The safety properties are the classical conditions on an isnad, stated
 * over every reachable state:
 *
 * - rootedAtSource: every isnad starts at the source and ends at its holder;
 * - ittisal: every link of every isnad is a hearing that happened, with both
 *   alive (muʿāṣara);
 * - chronologicalOrder: the hearings along an isnad happen in order;
 * - refutationSound: no hearing happens between narrators whose lifespans
 *   the graph's rule refutes. This is the dynamic counterpart of
 *   `Isnad.refuted_sound` in formal/lean.
 *
 * The lives are a small concrete instance: D was born after B died, so the
 * pair B → D is refuted.
 */
module transmission {
  type Narrator = str

  pure val SOURCE: Narrator = "P"
  pure val NARRATORS: Set[Narrator] = Set("P", "A", "B", "C", "D")
  pure val BIRTH: Narrator -> int = Map("P" -> -53, "A" -> -20, "B" -> 10, "C" -> 40, "D" -> 95)
  pure val DEATH: Narrator -> int = Map("P" -> 11, "A" -> 57, "B" -> 90, "C" -> 130, "D" -> 160)
  pure val A_HEAR = 5
  pure val A_TEACH = 20
  pure val YEARS = (-53).to(160)

  pure def alive(n: Narrator, y: int): bool = BIRTH.get(n) <= y and y <= DEATH.get(n)

  /// The graph's refutation of teacher t → student s (formal/lean `refuted`, exact dates).
  pure def refuted(t: Narrator, s: Narrator): bool =
    BIRTH.get(s) > DEATH.get(t) or BIRTH.get(t) > DEATH.get(s)

  var now: int
  var holders: Set[Narrator]
  var isnad: Narrator -> List[Narrator]
  var heardIn: Narrator -> int
  var hearings: Set[(Narrator, Narrator, int)]

  action init = all {
    now' = 0,
    holders' = Set(SOURCE),
    isnad' = Map(SOURCE -> [SOURCE]),
    heardIn' = Map(SOURCE -> 0),
    hearings' = Set(),
  }

  action hearAt(t: Narrator, s: Narrator, y: int): bool = all {
    holders.contains(t),
    not(holders.contains(s)),
    y >= now,
    alive(t, y),
    alive(s, y),
    y - BIRTH.get(t) >= A_TEACH,
    y - BIRTH.get(s) >= A_HEAR,
    now' = y,
    holders' = holders.union(Set(s)),
    isnad' = isnad.put(s, isnad.get(t).append(s)),
    heardIn' = heardIn.put(s, y),
    hearings' = hearings.union(Set((t, s, y))),
  }

  action idle = all {
    now' = now, holders' = holders, isnad' = isnad, heardIn' = heardIn, hearings' = hearings,
  }

  /// Any holder may tell any non-holder in any year from now on, if the
  /// guards of `hearAt` allow it.
  action step = any {
    all {
      holders != NARRATORS,
      nondet t = holders.oneOf()
      nondet s = NARRATORS.exclude(holders).oneOf()
      nondet y = YEARS.filter(y => y >= now).oneOf()
      hearAt(t, s, y),
    },
    idle,
  }

  /// A witness the simulator should reach: some report travels three links.
  val noThreeLinkIsnad: bool = holders.forall(h => length(isnad.get(h)) < 4)

  // ── safety ───────────────────────────────────────────────────────────────
  val rootedAtSource: bool = holders.forall(h =>
    isnad.get(h).head() == SOURCE and isnad.get(h)[length(isnad.get(h)) - 1] == h)

  def links(c: List[Narrator]): Set[(Narrator, Narrator)] =
    c.indices().filter(i => i > 0).map(i => (c[i - 1], c[i]))

  val ittisal: bool = holders.forall(h =>
    links(isnad.get(h)).forall(((a, b)) =>
      hearings.exists(((x, y, yr)) => x == a and y == b and alive(a, yr) and alive(b, yr))))

  val chronologicalOrder: bool = holders.forall(h =>
    links(isnad.get(h)).forall(((a, b)) => heardIn.get(a) <= heardIn.get(b)))

  val refutationSound: bool = hearings.forall(((t, s, yr)) => not(refuted(t, s)))

  val safety: bool = rootedAtSource and ittisal and chronologicalOrder and refutationSound

  // ── witnesses ────────────────────────────────────────────────────────────
  /// A connected isnad P → A → C is reachable.
  run chainExistsTest =
    init
      .then(hearAt("P", "A", 5))
      .then(hearAt("A", "C", 50))
      .then(all { assert(isnad.get("C") == ["P", "A", "C"]), assert(safety), idle })

  /// B cannot teach D: D was born after B died.
  run refutedPairCannotHearTest =
    init
      .then(hearAt("P", "A", 5))
      .then(hearAt("A", "B", 40))
      .then(hearAt("B", "D", 100))
      .fail()

  /// A child below A_HEAR cannot hear: B was one when the Prophet died.
  run tooYoungCannotHearTest = init.then(hearAt("P", "B", 11)).fail()

  /// Time does not run backwards.
  run noHearingInThePastTest =
    init
      .then(hearAt("P", "A", 5))
      .then(hearAt("A", "B", 4))
      .fail()
}
