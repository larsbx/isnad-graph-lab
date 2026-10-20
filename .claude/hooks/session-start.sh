#!/bin/bash
# SessionStart: install the pinned toolchains and run the quick gate, so every
# session starts from the same verified state (docs/PROCESS.md).
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0  # local machines: run tools/formal-setup.sh and tools/verify.sh yourself
fi
cd "$CLAUDE_PROJECT_DIR"

python3 -m pip install --quiet --disable-pip-version-check -e ".[dev]"
LEAN_BIN="$(tools/formal-setup.sh | tail -1)"
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  echo "export PATH=\"$LEAN_BIN:\$PATH\"" >> "$CLAUDE_ENV_FILE"
fi

# The gate's state is reported, never hidden; a red gate does not block the
# session, which may be the one that fixes it.
if tools/verify.sh --quick > /tmp/isnad-verify.log 2>&1; then
  echo "isnad-graph-lab: quick gate passed (full gate: tools/verify.sh)"
else
  echo "isnad-graph-lab: QUICK GATE FAILED. Fix before pushing; log: /tmp/isnad-verify.log"
  tail -20 /tmp/isnad-verify.log
fi
