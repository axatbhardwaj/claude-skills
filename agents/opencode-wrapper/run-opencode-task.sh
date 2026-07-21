#!/bin/bash
# Fixed opencode launcher. The opencode-wrapper agent may ONLY execute this script.
# Mirrors run-codex-task.sh: model allowlist, mode mapping, clean-tree precondition,
# unique run dirs, exit-code capture, pre/post snapshots, machine-readable report.
#
# CRITICAL DIFFERENCE FROM CODEX
# ------------------------------
# codex has `--sandbox read-only`; opencode has NO sandbox and NO read-only mode
# (verified 2026-07-20 against opencode 1.15.5: the only permission flag is
# --dangerously-skip-permissions). Per global CLAUDE.md, opencode's own permission
# model is not trustworthy (documented silent-fallback bugs), so the integrity
# snapshot below IS the boundary.
#
# This is DETECTION, NOT PREVENTION. A review-mode run that writes cannot be
# stopped mid-flight; it is detected afterwards, reported as
# launcher_status:"review_violated_readonly", and exits non-zero. The chair must
# treat that status as a compromised run and revert the workspace itself.
# Future hardening: run review in a throwaway `git worktree` so writes are
# structurally unable to reach the real tree.
#
# Modes of invocation:
#   Foreground:  run-opencode-task.sh --mode M --model X --workspace D --prompt-file F
#   Detached:    ... plus --detach  -> prints {launcher_status:"detached", run_dir}
#   Standing:    --session <id> continues a recorded opencode session.
#   Wait/poll:   run-opencode-task.sh --wait <run_dir> [--wait-seconds N]
set -u

command -v jq >/dev/null 2>&1 || { echo "run-opencode-task.sh requires jq" >&2; exit 69; }
command -v opencode >/dev/null 2>&1 || { echo "run-opencode-task.sh requires the opencode CLI on PATH" >&2; exit 69; }

usage() { echo "usage: run-opencode-task.sh --mode implementation|review --model kimi|glm|qwen|deepseek|minimax --workspace <dir> --prompt-file <path> [--variant high|max|minimal] [--session <id>] [--detach] | --wait <run_dir> [--wait-seconds <n>]" >&2; exit 64; }

MODE="" MODEL="" WORKSPACE="" PROMPT_FILE="" VARIANT="" DETACH=0 RUN_DIR_ARG="" WAIT_DIR="" WAIT_SECS=540 SESSION_ID=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 || usage ;;
    --model) MODEL="${2:-}"; shift 2 || usage ;;
    --workspace) WORKSPACE="${2:-}"; shift 2 || usage ;;
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2 || usage ;;
    --variant) VARIANT="${2:-}"; shift 2 || usage ;;
    --session) SESSION_ID="${2:-}"; shift 2 || usage ;;
    --detach) DETACH=1; shift ;;
    --run-dir) RUN_DIR_ARG="${2:-}"; shift 2 || usage ;;   # internal: detached self-reinvocation
    --wait) WAIT_DIR="${2:-}"; shift 2 || usage ;;
    --wait-seconds) WAIT_SECS="${2:-}"; shift 2 || usage ;;
    *) usage ;;
  esac
done

# ---- Wait/poll mode: no opencode involved, safe to call repeatedly. ----
if [ -n "$WAIT_DIR" ]; then
  case "$WAIT_DIR" in /tmp/opencode-wrapper/run-*) ;; *) echo "refusing --wait outside /tmp/opencode-wrapper: $WAIT_DIR" >&2; exit 64 ;; esac
  case "$WAIT_SECS" in ''|*[!0-9]*) usage ;; esac
  ELAPSED=0
  while [ "$ELAPSED" -lt "$WAIT_SECS" ]; do
    if [ -s "$WAIT_DIR/report.json" ] && jq empty "$WAIT_DIR/report.json" 2>/dev/null; then
      cat "$WAIT_DIR/report.json"
      [ "$(jq -r .launcher_status "$WAIT_DIR/report.json")" = "ok" ] && exit 0 || exit 5
    fi
    sleep 5; ELAPSED=$((ELAPSED + 5))
  done
  jq -n --arg run_dir "$WAIT_DIR" '{launcher_status:"still_running", run_dir:$run_dir}'
  exit 7
fi

[ -n "$MODE" ] && [ -n "$MODEL" ] && [ -n "$WORKSPACE" ] && [ -n "$PROMPT_FILE" ] || usage

case "$MODE" in
  implementation|review) ;;
  *) echo "invalid --mode: $MODE" >&2; exit 64 ;;
esac

# Friendly-name -> model-ID allowlist.
# ONLY opencode-go/* is reachable. The free `opencode/*-free` Zen tier may train on
# submitted data (global CLAUDE.md privacy rule), so it is structurally unreachable
# through this launcher — the same way codex's launcher makes danger-full-access
# unreachable. Adding a free-tier model here is a deliberate policy change.
case "$MODEL" in
  kimi)     MODEL_ID="opencode-go/kimi-k3" ;;       # the rupakara (UI/UX lane)
  glm)      MODEL_ID="opencode-go/glm-5.2" ;;
  qwen)     MODEL_ID="opencode-go/qwen3.7-max" ;;
  deepseek) MODEL_ID="opencode-go/deepseek-v4-pro" ;;
  minimax)  MODEL_ID="opencode-go/minimax-m3" ;;
  *) echo "model not in allowlist: $MODEL" >&2; exit 64 ;;
esac

case "$VARIANT" in ""|high|max|minimal) ;; *) echo "variant not in allowlist: $VARIANT" >&2; exit 64 ;; esac
[ -d "$WORKSPACE" ] || { echo "workspace not found: $WORKSPACE" >&2; exit 66; }
[ -f "$PROMPT_FILE" ] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 66; }
if [ -n "$SESSION_ID" ]; then
  printf '%s\n' "$SESSION_ID" | grep -Eq '^[A-Za-z0-9_-]{6,64}$' || { echo "invalid --session id: $SESSION_ID" >&2; exit 64; }
fi

mkdir -p /tmp/opencode-wrapper
if [ -n "$RUN_DIR_ARG" ]; then
  RUN_DIR="$RUN_DIR_ARG"
  [ -d "$RUN_DIR" ] || { echo "run dir not found: $RUN_DIR" >&2; exit 66; }
else
  RUN_DIR=$(mktemp -d /tmp/opencode-wrapper/run-XXXXXXXX)
  cp "$PROMPT_FILE" "$RUN_DIR/prompt.md"
fi
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

git_list() { git -C "$WORKSPACE" "$@" 2>/dev/null; }

# ---- Integrity snapshot: content hash manifest of the workspace. ----
# This is the read-only boundary for review mode. For very large trees the manifest
# is skipped and we fall back to git-only comparison; snapshot_mode records which.
SNAPSHOT_MODE="manifest"
FILE_COUNT=$(find "$WORKSPACE" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -20001 | wc -l)
if [ "$FILE_COUNT" -gt 20000 ]; then SNAPSHOT_MODE="git-only"; fi

snapshot() {  # snapshot <outfile>
  if [ "$SNAPSHOT_MODE" = "manifest" ]; then
    find "$WORKSPACE" -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/.venv/*' -print0 2>/dev/null \
      | sort -z | xargs -0 -r sha256sum 2>/dev/null > "$1"
  else
    { git_list status --porcelain; git_list rev-parse HEAD; } > "$1"
  fi
}

report() {  # report <status> <opencode_exit> <result_valid> <integrity>
  jq -n \
    --arg run_dir "$RUN_DIR" --arg mode "$MODE" --arg model "$MODEL_ID" \
    --arg workspace "$WORKSPACE" --arg variant "$VARIANT" \
    --arg started "$STARTED_AT" --arg completed "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg launcher_status "$1" --argjson opencode_exit "${2:-null}" --argjson result_valid "${3:-false}" \
    --arg integrity "${4:-unknown}" --arg snapshot_mode "$SNAPSHOT_MODE" \
    --arg baseline "${BASELINE:-}" --arg session_id "${SESSION_ID:-}" \
    --argjson changed "$(git_list diff --name-only | jq -R . | jq -s .)" \
    --argjson staged "$(git_list diff --cached --name-only | jq -R . | jq -s .)" \
    --argjson untracked "$(git_list ls-files --others --exclude-standard | jq -R . | jq -s .)" \
    --argjson touched "$(jq -R . < "${RUN_DIR}/integrity-diff.txt" 2>/dev/null | jq -s . || echo '[]')" \
    '{launcher_status:$launcher_status, run_dir:$run_dir, mode:$mode, model:$model,
      variant:($variant | if . == "" then null else . end),
      workspace:$workspace, baseline_commit:$baseline,
      opencode_exit_code:$opencode_exit, result_file_valid:$result_valid,
      opencode_session_id:($session_id | if . == "" then null else . end),
      integrity:$integrity, snapshot_mode:$snapshot_mode,
      integrity_touched_paths:$touched,
      actual_changes:{modified:$changed, staged:$staged, untracked:$untracked},
      started_at:$started, completed_at:$completed,
      result_file:($run_dir+"/result.json"), stdout_file:($run_dir+"/stdout.log"),
      stderr_file:($run_dir+"/stderr.log")}' \
    | tee "$RUN_DIR/report.json"
}

BASELINE=$(git_list rev-parse HEAD)

# Implementation requires a clean tree: without it, worker-change attribution is guesswork.
if [ "$MODE" = "implementation" ]; then
  if [ -n "$(git_list status --porcelain)" ]; then
    report "blocked_dirty_tree" null false "not_checked"
    exit 3
  fi
fi

# ---- Detached mode: survive the caller's 10-minute Bash-tool cap. ----
if [ "$DETACH" -eq 1 ]; then
  setsid "$0" --mode "$MODE" --model "$MODEL" --workspace "$WORKSPACE" \
    --prompt-file "$RUN_DIR/prompt.md" ${VARIANT:+--variant "$VARIANT"} \
    ${SESSION_ID:+--session "$SESSION_ID"} --run-dir "$RUN_DIR" \
    >/dev/null 2>>"$RUN_DIR/detach.log" </dev/null &
  jq -n --arg run_dir "$RUN_DIR" --arg pid "$!" \
    '{launcher_status:"detached", run_dir:$run_dir, child_pid:($pid|tonumber)}'
  exit 0
fi

snapshot "$RUN_DIR/snapshot-before.txt"

# ---- Launch. Prompt is passed positionally; opencode run takes [message..]. ----
opencode run \
  --format json \
  --dir "$WORKSPACE" \
  -m "$MODEL_ID" \
  ${VARIANT:+--variant "$VARIANT"} \
  ${SESSION_ID:+--session "$SESSION_ID"} \
  "$(cat "$RUN_DIR/prompt.md")" \
  > "$RUN_DIR/stdout.log" 2> "$RUN_DIR/stderr.log"
OPENCODE_EXIT=$?

snapshot "$RUN_DIR/snapshot-after.txt"
diff "$RUN_DIR/snapshot-before.txt" "$RUN_DIR/snapshot-after.txt" > "$RUN_DIR/integrity-raw.diff" 2>/dev/null
# Extract just the touched paths for the report. The path is the LAST field in both
# snapshot shapes: "<hash>  <path>" (manifest mode) and "<XY> <path>" (git-only mode).
awk '/^[<>]/ && NF>1 {print $NF}' "$RUN_DIR/integrity-raw.diff" 2>/dev/null \
  | sort -u > "$RUN_DIR/integrity-diff.txt"

if [ -s "$RUN_DIR/integrity-diff.txt" ]; then INTEGRITY="workspace_modified"; else INTEGRITY="unchanged"; fi

# opencode emits a JSON event stream on stdout; the agent's structured result is the
# final assistant message. Extract it best-effort into result.json.
# NOTE (2026-07-20): the exact event schema is UNVERIFIED against a real run. If this
# yields nothing, report result_file_valid:false rather than failing the run, and the
# chair reads stdout.log directly. Fix this extractor after the first real dispatch.
: > "$RUN_DIR/result.json"
jq -s 'map(select(.type? // "" | test("message|text|assistant"; "i"))) | last // empty' \
  "$RUN_DIR/stdout.log" > "$RUN_DIR/result.json" 2>/dev/null \
  || jq -s 'last // empty' "$RUN_DIR/stdout.log" > "$RUN_DIR/result.json" 2>/dev/null

RESULT_VALID=false
[ -s "$RUN_DIR/result.json" ] && jq empty "$RUN_DIR/result.json" 2>/dev/null && RESULT_VALID=true

# FAIL CLOSED: a review run that touched the workspace is a policy violation,
# regardless of opencode's exit code.
if [ "$MODE" = "review" ] && [ "$INTEGRITY" = "workspace_modified" ]; then
  report "review_violated_readonly" "$OPENCODE_EXIT" "$RESULT_VALID" "$INTEGRITY"
  exit 4
fi

if [ "$OPENCODE_EXIT" -ne 0 ]; then STATUS="opencode_failed"
elif [ "$RESULT_VALID" != "true" ]; then STATUS="invalid_result"
else STATUS="ok"; fi

report "$STATUS" "$OPENCODE_EXIT" "$RESULT_VALID" "$INTEGRITY"
[ "$STATUS" = "ok" ]
