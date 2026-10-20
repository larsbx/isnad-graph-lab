#!/usr/bin/env bash
# Install the pinned verification toolchains (formal/toolchain.toml), verifying
# every download by sha256. Idempotent: anything already installed and verified
# is kept. Prints the PATH entry to use.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE="${ISNAD_FORMAL_CACHE:-$HOME/.cache/isnad-formal}"
mkdir -p "$CACHE"
pin() { python3 -c "import sys, tomllib; print(tomllib.load(open(sys.argv[3], 'rb'))[sys.argv[1]][sys.argv[2]])" "$1" "$2" "$ROOT/formal/toolchain.toml"; }

fetch() {  # url sha256 dest
  if [ -f "$3" ] && echo "$2  $3" | sha256sum -c --status; then return; fi
  curl -sSfL --retry 4 --retry-delay 2 -o "$3.part" "$1"
  echo "$2  $3.part" | sha256sum -c --status || { echo "sha256 mismatch: $1" >&2; rm -f "$3.part"; exit 1; }
  mv "$3.part" "$3"
}

# Lean (core only; the archive includes lake)
LEAN_DIR="$CACHE/$(pin lean dir)"
if [ ! -x "$LEAN_DIR/bin/lean" ]; then
  fetch "$(pin lean url)" "$(pin lean sha256)" "$CACHE/lean.zip"
  python3 - "$CACHE/lean.zip" "$CACHE" <<'PY'
import os, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as z:
    for i in z.infolist():
        p = z.extract(i, sys.argv[2])
        if mode := (i.external_attr >> 16) & 0o777:
            os.chmod(p, mode)
PY
  rm -f "$CACHE/lean.zip"
fi
"$LEAN_DIR/bin/lean" --version | grep -q "version $(pin lean version)," || { echo "wrong Lean" >&2; exit 1; }

# Apalache, where quint verify looks for it
APA="$HOME/.quint/apalache-dist-$(pin apalache version)"
if [ ! -f "$APA/apalache/lib/apalache.jar" ]; then
  fetch "$(pin apalache url)" "$(pin apalache sha256)" "$CACHE/apalache.tgz"
  mkdir -p "$APA" && tar xzf "$CACHE/apalache.tgz" -C "$APA" && rm -f "$CACHE/apalache.tgz"
fi

# Quint, exactly as package-lock.json pins it
(cd "$ROOT/formal/quint" && npm ci --no-fund --no-audit --no-update-notifier --loglevel=error)
[ "$(cd "$ROOT/formal/quint" && npx quint --version)" = "$(pin quint version)" ] || { echo "wrong Quint" >&2; exit 1; }

echo "$LEAN_DIR/bin"
