#!/bin/bash
# Fixed Codex launcher. The codex-wrapper agent may ONLY execute this script.
# Owns: model allowlist, mode->sandbox mapping, clean-tree precondition,
# unique run dirs, stdin prompt piping, exit-code capture, pre/post git
# snapshots, and a machine-readable report.
set -u

command -v jq >/dev/null 2>&1 || { echo "run-codex-task.sh requires jq (pacman -S jq / apt install jq)" >&2; exit 69; }

usage() { echo "usage: run-codex-task.sh --mode implementation|review --model terra|sol|luna --workspace <dir> --prompt-file <path>" >&2; exit 64; }

MODE="" MODEL="" WORKSPACE="" PROMPT_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODE="${2:-}"; shift 2 ;;
    --model) MODEL="${2:-}"; shift 2 ;;
    --workspace) WORKSPACE="${2:-}"; shift 2 ;;
    --prompt-file) PROMPT_FILE="${2:-}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$MODE" ] && [ -n "$MODEL" ] && [ -n "$WORKSPACE" ] && [ -n "$PROMPT_FILE" ] || usage

# Mode -> sandbox is decided HERE, in code. Review is always read-only.
case "$MODE" in
  implementation) SANDBOX="workspace-write" ;;
  review)         SANDBOX="read-only" ;;
  *) echo "invalid --mode: $MODE" >&2; exit 64 ;;
esac

# Friendly-name -> model-ID allowlist. danger-full-access is unreachable by design.
case "$MODEL" in
  terra) MODEL_ID="gpt-5.6-terra" ;;
  sol)   MODEL_ID="gpt-5.6-sol" ;;
  luna)  MODEL_ID="gpt-5.6-luna" ;;
  *) echo "model not in allowlist: $MODEL" >&2; exit 64 ;;
esac

[ -d "$WORKSPACE" ] || { echo "workspace not found: $WORKSPACE" >&2; exit 66; }
[ -f "$PROMPT_FILE" ] || { echo "prompt file not found: $PROMPT_FILE" >&2; exit 66; }

mkdir -p /tmp/codex-wrapper
RUN_DIR=$(mktemp -d /tmp/codex-wrapper/run-XXXXXXXX)
cp "$PROMPT_FILE" "$RUN_DIR/prompt.md"
SCHEMA="$HOME/.claude/agents/codex-result.schema.json"
STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

git_list() { git -C "$WORKSPACE" "$@" 2>/dev/null; }
report() {  # report <status> <codex_exit> <result_valid>
  jq -n \
    --arg run_dir "$RUN_DIR" --arg mode "$MODE" --arg model "$MODEL_ID" \
    --arg sandbox "$SANDBOX" --arg workspace "$WORKSPACE" \
    --arg started "$STARTED_AT" --arg completed "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --arg launcher_status "$1" --argjson codex_exit "${2:-null}" --argjson result_valid "${3:-false}" \
    --arg baseline "${BASELINE:-}" \
    --argjson changed "$(git_list diff --name-only | jq -R . | jq -s .)" \
    --argjson staged "$(git_list diff --cached --name-only | jq -R . | jq -s .)" \
    --argjson untracked "$(git_list ls-files --others --exclude-standard | jq -R . | jq -s .)" \
    '{launcher_status:$launcher_status, run_dir:$run_dir, mode:$mode, model:$model,
      sandbox:$sandbox, workspace:$workspace, baseline_commit:$baseline,
      codex_exit_code:$codex_exit, result_file_valid:$result_valid,
      actual_changes:{modified:$changed, staged:$staged, untracked:$untracked},
      started_at:$started, completed_at:$completed,
      result_file:($run_dir+"/result.json"), stderr_file:($run_dir+"/stderr.log")}' \
    | tee "$RUN_DIR/report.json"
}

BASELINE=$(git_list rev-parse HEAD)

# Implementation requires a clean tree: without it, worker-change attribution is guesswork.
if [ "$MODE" = "implementation" ]; then
  if [ -n "$(git_list status --porcelain)" ]; then
    report "blocked_dirty_tree" null false
    exit 3
  fi
fi

codex exec \
  --ephemeral \
  -C "$WORKSPACE" \
  -m "$MODEL_ID" \
  -c model_reasoning_effort="xhigh" \
  --sandbox "$SANDBOX" \
  --output-schema "$SCHEMA" \
  --output-last-message "$RUN_DIR/result.json" \
  - < "$RUN_DIR/prompt.md" > "$RUN_DIR/stdout.log" 2> "$RUN_DIR/stderr.log"
CODEX_EXIT=$?

RESULT_VALID=false
[ -s "$RUN_DIR/result.json" ] && jq empty "$RUN_DIR/result.json" 2>/dev/null && RESULT_VALID=true

if [ "$CODEX_EXIT" -ne 0 ]; then STATUS="codex_failed"
elif [ "$RESULT_VALID" != "true" ]; then STATUS="invalid_result"
else STATUS="ok"; fi

report "$STATUS" "$CODEX_EXIT" "$RESULT_VALID"
[ "$STATUS" = "ok" ]
