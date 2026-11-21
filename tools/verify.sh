#!/usr/bin/env bash
# The gate: every claim the repository makes is checked here, in this order.
#   1. vendored code matches its pins;  2. lint;  3. tests (incl. vector freshness)
#   4. Lean: the theorems build, use only the standard axioms, and the Python
#      verdicts, phases and common links conform to the Lean model on the
#      committed graph
#   5. Quint: unit runs, non-vacuity witnesses, a seeded simulation, and
#      Apalache bounded model checking
# Usage: tools/verify.sh [--quick]   (--quick: skip pytest and Apalache)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
QUICK="${1:-}"
pin() { python3 -c "import sys, tomllib; print(tomllib.load(open(sys.argv[3], 'rb'))[sys.argv[1]][sys.argv[2]])" "$1" "$2" "$ROOT/formal/toolchain.toml"; }
step() { printf '\n== %s\n' "$*"; }

export PATH="${ISNAD_FORMAL_CACHE:-$HOME/.cache/isnad-formal}/$(pin lean dir)/bin:$PATH"

step "vendored pins";  python vendor/python/vendoring/check_vendored_sync.py
step "lint";           ruff check .
if [ "$QUICK" != "--quick" ]; then step "tests"; python -m pytest -q; fi

step "lean: theorems"
(cd formal/lean && lake build 2>&1 | tee /dev/stderr | grep -q "Build completed successfully") \
  || { echo "lean build failed" >&2; exit 1; }
step "lean: axiom audit";  (cd formal/lean && lake env lean Audit.lean)
step "lean: conformance";  (cd formal/lean && lake exe conformance ../vectors/conformance.json)

QB="--backend $(pin quint backend) --seed $(pin quint seed)"
SIM="--max-samples=2000 --max-steps=10"
quint() { (cd formal/quint && npx quint "$@"); }
step "quint: typecheck and tests"
quint typecheck transmission.qnt && quint test $QB transmission.qnt
step "quint: non-vacuity (the simulator reaches each witness)"
for w in noThreeLinkIsnad noGap noTadlis noHasan; do
  if quint run transmission.qnt $QB $SIM --invariant=$w --verbosity=0 >/dev/null 2>&1; then
    echo "vacuous: the simulator never violated $w" >&2; exit 1
  fi
  echo "reached: not $w"
done
step "quint: simulation"
quint run transmission.qnt $QB $SIM --invariant=safety --verbosity=1
if [ "$QUICK" != "--quick" ]; then
  step "quint: Apalache bounded model checking"
  APA_VERSION="$(pin apalache version)"; APA_STEPS="$(pin apalache max_steps)"
  quint verify transmission.qnt --invariant=safety --apalache-version "$APA_VERSION" \
    --max-steps "$APA_STEPS" --verbosity=1
  rm -rf formal/quint/_apalache-out
fi
step "all checks passed"
