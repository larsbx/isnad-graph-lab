#!/bin/bash
# PreToolUse (Bash): a `git push` runs the full gate first and is blocked if it
# fails. Nothing reaches the remote that the gate has not passed.
set -uo pipefail
cmd="$(python3 -c 'import json, sys; print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))')"
case "$cmd" in
  *"git push"*) ;;
  *) exit 0 ;;
esac
cd "$CLAUDE_PROJECT_DIR"
if ! tools/verify.sh > /tmp/isnad-verify-push.log 2>&1; then
  echo "push blocked: tools/verify.sh failed (log: /tmp/isnad-verify-push.log)" >&2
  tail -20 /tmp/isnad-verify-push.log >&2
  exit 2
fi
exit 0
