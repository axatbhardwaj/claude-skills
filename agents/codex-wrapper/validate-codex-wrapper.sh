#!/bin/bash
# PreToolUse hook for the codex-wrapper agent. FAILS CLOSED.
# Bash: entire command must match the fixed launcher, read-only git, or
#       mkdir under /tmp/codex-wrapper — no shell metacharacters anywhere.
# Write/Edit: only under /tmp/codex-wrapper/ (prompt files).
# JSON extraction: jq preferred, python3 fallback; neither present => block.

INPUT=$(cat)

extract() {  # extract <jq-path> e.g. .tool_name
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$INPUT" | jq -r "$1 // empty" 2>/dev/null
  elif command -v python3 >/dev/null 2>&1; then
    printf '%s' "$INPUT" | python3 -c '
import json,sys
path=sys.argv[1].lstrip(".").split(".")
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
for k in path:
    d=d.get(k) if isinstance(d,dict) else None
    if d is None: sys.exit(0)
print(d)' "$1" 2>/dev/null
  fi
}

command -v jq >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1 || {
  echo "Blocked: neither jq nor python3 available; codex-wrapper hook fails closed." >&2; exit 2; }

TOOL=$(extract .tool_name)
[ -n "$TOOL" ] || { echo "Blocked: no tool_name in hook input; failing closed." >&2; exit 2; }

allow() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

if [ "$TOOL" = "Write" ] || [ "$TOOL" = "Edit" ]; then
  FP=$(extract .tool_input.file_path)
  case "$FP" in
    /tmp/codex-wrapper/*) allow "prompt file under /tmp/codex-wrapper" ;;
    *) echo "Blocked: codex-wrapper may write only under /tmp/codex-wrapper/. Got: $FP" >&2; exit 2 ;;
  esac
fi

[ "$TOOL" = "Bash" ] || exit 0
CMD=$(extract .tool_input.command)
[ -n "$CMD" ] || { echo "Blocked: empty Bash command; failing closed." >&2; exit 2; }

# Whole-string matches only. Arg charset excludes ; & | < > $ ` ( ) " ' \ and whitespace tricks.
ARG='[A-Za-z0-9._/~=^@:+-]+'
LAUNCHER_RE="^(~|/home/[A-Za-z0-9_-]+|${HOME})/\.claude/agents/run-codex-task\.sh( --(mode|model|workspace|prompt-file) ${ARG})+$"
GIT_RE="^git (rev-parse|status|diff|log|show|ls-files)( ${ARG})*$"
MKDIR_RE="^mkdir -p /tmp/codex-wrapper(/${ARG})?$"

echo "$CMD" | grep -Eq "$LAUNCHER_RE" && allow "approved codex launcher"
echo "$CMD" | grep -Eq "$GIT_RE"      && allow "read-only git inspection"
echo "$CMD" | grep -Eq "$MKDIR_RE"    && allow "wrapper temp dir"

echo "Blocked by codex-wrapper policy. Allowed: the run-codex-task.sh launcher, read-only git (rev-parse/status/diff/log/show/ls-files), mkdir under /tmp/codex-wrapper — single commands, no shell metacharacters. Got: $CMD" >&2
exit 2
