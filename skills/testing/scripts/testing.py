#!/usr/bin/env python3
"""
Testing — Adversarial Coverage Improvement.

Nine-step workflow with feedback loops:
  1:   DETECT - Identify test framework, conventions, directory structure
  2:   GREEN: COVERAGE - Analyze coverage gaps and rank by severity
  3:   RED: ATTACK - Find vulnerabilities via structured attack hypotheses
  4:   GREEN: VERIFY - Verify Red's claims, filter false positives
  5:   SANDBOX: VALIDATE - Execute runtime probes to confirm/deny findings
  6:   BLUE: WRITE TESTS - Write test cases for confirmed issues
  7:   QUALITY REVIEW - Score test quality (FAIL loops back to 6)
  8:   GREEN: FINAL REVIEW - Review + anti-slop gate (FAIL loops back to 6)
  9:   PRESENT RESULTS - Summarize findings to user

Steps 7 and 8 are quality gates with PASS/FAIL verdicts.
On FAIL, the workflow loops back to step 6 (Blue) with attempt+1.
Max 2 retries (attempt 3 forces forward to prevent infinite loops).

Adversarial red/blue/green team model:
  - Green (architect): analyzes, verifies, reviews
  - Red (adversarial-analyst): attacks via structured hypotheses
  - Sandbox (sandbox-executor): validates findings with runtime probes
  - Blue (developer): writes tests for confirmed issues
  - Quality (quality-reviewer): scores test quality
"""

import argparse
import shlex
import sys
from pathlib import Path, PurePosixPath


# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_STATE_DIR = ".testing-skill"

STEP_INPUTS = {
    2: ["01-project-context.md"],
    3: ["01-project-context.md", "02-coverage-gaps.md"],
    4: ["01-project-context.md", "03-red-findings.md"],
    5: ["01-project-context.md", "04-confirmed-issues.md"],
    6: ["01-project-context.md", "04-confirmed-issues.md", "05-sandbox-results.md"],
    7: ["04-confirmed-issues.md", "05-sandbox-results.md", "06-test-results.md"],
    8: [
        "04-confirmed-issues.md",
        "05-sandbox-results.md",
        "06-test-results.md",
        "07-quality-review.md",
    ],
    9: [
        "01-project-context.md",
        "02-coverage-gaps.md",
        "03-red-findings.md",
        "04-confirmed-issues.md",
        "05-sandbox-results.md",
        "06-test-results.md",
        "07-quality-review.md",
        "08-final-review.md",
    ],
}

STEP_OUTPUTS = {
    1: "01-project-context.md",
    2: "02-coverage-gaps.md",
    3: "03-red-findings.md",
    4: "04-confirmed-issues.md",
    5: "05-sandbox-results.md",
    6: "06-test-results.md",
    7: "07-quality-review.md",
    8: "08-final-review.md",
}


# ============================================================================
# INLINED DISPATCH PRIMITIVES
# ============================================================================
# From skills.lib.workflow.prompts — inlined to remove shared library dependency.

TASK_TOOL_INSTRUCTION = """\
Claude Code:
  Use the Task tool with:
    - subagent_type: {agent_type}
    - model: {model_param}
    - prompt: the task below plus the listed state-file inputs
    - run_in_background: false or omitted

Codex:
  If current instructions and tools allow subagents, use an inherited-model
  subagent for this bounded task. Use read-only/explorer-style delegation for
  analysis steps and a code-writing worker only for the Blue test-writing step.
  If subagents are unavailable or disallowed, do this step locally."""

SUBAGENT_TEMPLATE = """\
DISPATCH SUB-AGENT
==================

{task_tool_block}

TASK FOR THE SUB-AGENT:
{task_section}

The sub-agent must return only the requested analysis or edit summary. After it
returns, save the exact final response to the step output file before continuing."""


def task_tool_instruction(agent_type: str, model: str | None) -> str:
    """Tell main agent how to spawn sub-agent via Task tool."""
    model_param = model if model else "omit (use default)"
    return TASK_TOOL_INSTRUCTION.format(agent_type=agent_type, model_param=model_param)


def subagent_dispatch(
    agent_type: str,
    prompt: str = "",
    model: str | None = None,
) -> str:
    """Generate prompt for single sub-agent dispatch."""
    task_section = prompt if prompt else "(No additional task - agent follows invoke command)"
    return SUBAGENT_TEMPLATE.format(
        task_tool_block=task_tool_instruction(agent_type, model),
        task_section=task_section,
    )


def format_step(body: str, next_cmd: str = "", title: str = "",
                if_pass: str = "", if_fail: str = "",
                pass_label: str = "VERDICT: PASS",
                fail_label: str = "VERDICT: FAIL") -> str:
    """Assemble complete workflow step: title + body + invoke directive."""
    if title:
        header = f"{title}\n{'=' * len(title)}\n\n"
        body = header + body

    if if_pass and if_fail:
        invoke = (
            f"NEXT STEP (MANDATORY -- execute exactly one):\n"
            f"    Working directory: current project root\n"
            f"    {pass_label}  ->  {if_pass}\n"
            f"    {fail_label}  ->  {if_fail}\n\n"
            f"This is a mechanical routing decision. Do not interpret, summarize, "
            f"or assess the results.\n"
            f"Match the exact verdict label, then execute the matching command."
        )
        return f"{body}\n\n{invoke}"
    elif next_cmd:
        invoke = (
            f"NEXT STEP:\n"
            f"    Working directory: current project root\n"
            f"    Command: {next_cmd}\n\n"
            f"Execute this command now."
        )
        return f"{body}\n\n{invoke}"
    else:
        return f"{body}\n\nWORKFLOW COMPLETE - Return the output from the step above. Do not summarize."


# ============================================================================
# MESSAGE TEMPLATES
# ============================================================================

# --- STEP 1: DETECT ---------------------------------------------------------

DETECT_INSTRUCTIONS = (
    "Identify the project's test framework and conventions:\n"
    "\n"
    "1. Look for test config: `pytest.ini`, `pyproject.toml`, `jest.config.*`, "
    "`vitest.config.*`, `Cargo.toml`, `go.mod`, `package.json` (scripts.test), "
    "`.github/workflows/*`, `Makefile`, etc.\n"
    "2. Look for test directories: `tests/`, `test/`, `__tests__/`, `spec/`, "
    "`*_test.go`, etc.\n"
    "3. Determine the test runner command (e.g., `pytest`, `npm test`, "
    "`cargo test`, `go test ./...`)\n"
    "4. Note the test file naming pattern (e.g., `test_*.py`, `*.test.ts`, "
    "`*_test.go`)\n"
    "5. Read 1-2 existing test files to learn conventions: imports, assertion "
    "style, naming patterns, setup/teardown\n"
    "6. Collect the project's directory structure (source dirs, entry points, "
    "key modules)\n"
    "\n"
    "Save all of this as PROJECT_CONTEXT — you will pass it to every subagent."
)

# --- STEP 2: GREEN - COVERAGE ANALYSIS -------------------------------------

COVERAGE_INSTRUCTIONS = (
    "You are GREEN TEAM (architect role) performing coverage analysis.\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT from Step 1 in your prompt. "
    "Use it to understand the codebase.\n"
    "\n"
    "Your task:\n"
    "- Read all source files and all test files\n"
    "- Map what is tested vs. what is not\n"
    "- Identify critical untested paths: public APIs, error handling, edge "
    "cases, complex logic branches\n"
    "- Rank gaps by severity (high = public-facing or error-prone, low = "
    "internal utilities)\n"
    "- Output a structured coverage map and a ranked list of the top untested "
    "critical paths\n"
    "\n"
    "The orchestrator will save your output as COVERAGE_GAPS."
)

# --- STEP 3: RED - ATTACK --------------------------------------------------

RED_INSTRUCTIONS = (
    "You are RED TEAM (adversarial analyst role).\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT and COVERAGE_GAPS in your "
    "prompt.\n"
    "\n"
    "Your task:\n"
    "- Target the untested areas Green identified\n"
    "- Systematically probe these four categories:\n"
    "  1. Boundary Failures: off-by-one, empty/max inputs, type boundaries\n"
    "  2. State & Concurrency: race conditions, stale state, resource exhaustion\n"
    "  3. Error Handling Gaps: unhandled exceptions, silent failures, missing cleanup\n"
    "  4. Bypass Logic: validation bypass, business rule violations, encoding tricks\n"
    "- For each finding, produce a structured Attack Hypothesis:\n"
    "    ATTACK HYPOTHESIS #N\n"
    "      Target: [specific function/module/endpoint]\n"
    "      Vector: [exact attack approach]\n"
    "      Expected Failure: [what breaks and how]\n"
    "      Severity: [CRITICAL | HIGH | MEDIUM | LOW]\n"
    "      Category: [Boundary | State | ErrorHandling | Bypass]\n"
    "- Do NOT write tests or fixes — output hypotheses only\n"
    "\n"
    "The orchestrator will save your output as RED_FINDINGS."
)

# --- STEP 4: GREEN - VERIFY RED'S CLAIMS -----------------------------------

VERIFY_INSTRUCTIONS = (
    "You are GREEN TEAM (architect role) verifying Red's findings.\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT and RED_FINDINGS in your "
    "prompt.\n"
    "\n"
    "Your task:\n"
    "- Evaluate each of Red's Attack Hypotheses architecturally\n"
    "- Read the actual source code for each affected location\n"
    "- Classify each finding as: CONFIRMED BUG, DESIGN LIMITATION, or "
    "FALSE POSITIVE\n"
    "- For false positives, explain why (e.g., 'this path is unreachable "
    "because...')\n"
    "- For confirmed bugs, note the root cause\n"
    "- Output only the confirmed issues — strip false positives entirely\n"
    "\n"
    "The orchestrator will save your output as CONFIRMED_ISSUES.\n"
    "\n"
    "IMPORTANT: End your response with one of these verdicts:\n"
    "  VERDICT: ISSUES FOUND — if any issues are confirmed\n"
    "  VERDICT: ALL CLEAR — if no issues are confirmed (all false positives)"
)

# --- STEP 5: SANDBOX - VALIDATE ---------------------------------------------

SANDBOX_INSTRUCTIONS = (
    "You are SANDBOX EXECUTOR validating confirmed findings with runtime probes.\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT and CONFIRMED_ISSUES in your "
    "prompt.\n"
    "\n"
    "Your task:\n"
    "- For each confirmed issue, generate and execute a minimal diagnostic probe\n"
    "- Probes must be self-contained, deterministic, and leave no artifacts\n"
    "- Use subprocess.run() with list args only (never shell=True), timeout=30\n"
    "- Write probes to /tmp only; delete after execution\n"
    "- If Docker is available, use --network none for containerized probes\n"
    "- If execution is not possible, mark as UNVERIFIABLE with explanation\n"
    "\n"
    "For each finding, output:\n"
    "    SANDBOX RESULT #N\n"
    "      Hypothesis: [ref to ATTACK HYPOTHESIS #N]\n"
    "      Verdict: CONFIRMED | REFUTED | UNVERIFIABLE\n"
    "      Execution Evidence:\n"
    "        Probe: [code snippet]\n"
    "        Exit Code: [result]\n"
    "        Stdout/Stderr: [truncated to 500 chars each]\n"
    "      Analysis: [what evidence proves]\n"
    "      Enrichment: [stack trace, actual vs expected for Blue Team]\n"
    "\n"
    "This step is informational — always proceed to the next step regardless "
    "of verdicts. Do NOT gate on results.\n"
    "\n"
    "The orchestrator will save your output as SANDBOX_RESULTS."
)

# --- STEP 6: BLUE - WRITE TESTS --------------------------------------------

BLUE_INSTRUCTIONS = (
    "You are BLUE TEAM (developer role) writing tests.\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT, CONFIRMED_ISSUES, "
    "SANDBOX_RESULTS, and test conventions from Step 1 in your prompt.\n"
    "\n"
    "Your task:\n"
    "- Prioritize issues by sandbox verdict: CONFIRMED first, then "
    "UNVERIFIABLE, skip REFUTED entirely\n"
    "- Write test cases ONLY for confirmed issues — not false positives, "
    "not design limitations\n"
    "- Match the project's test conventions exactly (file naming, imports, "
    "assertion library, setup patterns)\n"
    "- Place test files in the project's existing test directory following "
    "its organization\n"
    "- Run the new tests with the project's test runner to verify they "
    "execute correctly\n"
    "- Tests that expose a confirmed bug SHOULD fail — that's expected and "
    "correct\n"
    "- Tests for edge cases that aren't bugs should pass\n"
    "- Output: list of test files written, what each test covers, and "
    "pass/fail results\n"
    "\n"
    "If the orchestrator passes QUALITY_REVIEW or FINAL_REPORT with feedback "
    "on weak, failing, or unnecessary tests, address the reviewer's feedback: "
    "rewrite weak tests, remove unnecessary ones, keep strong tests unchanged.\n"
    "\n"
    "The orchestrator will save your output as TEST_RESULTS."
)

# --- STEP 7: QUALITY REVIEW ------------------------------------------------

QUALITY_REVIEW_INSTRUCTIONS = (
    "You are reviewing the quality of Blue Team's tests.\n"
    "\n"
    "The orchestrator will pass CONFIRMED_ISSUES, SANDBOX_RESULTS, and "
    "TEST_RESULTS in your prompt.\n"
    "\n"
    "Your task:\n"
    "- For each test, assess whether it meaningfully covers the confirmed issue\n"
    "- Cross-reference tests against sandbox execution evidence — tests for "
    "CONFIRMED issues should reproduce the probe's failure mode\n"
    "- Check for: correct assertions, edge case coverage, no false passes, "
    "proper isolation\n"
    "- Score each test as: STRONG (covers issue thoroughly), ADEQUATE "
    "(covers core case), or WEAK (superficial or incorrect)\n"
    "- For WEAK tests, explain what's missing and what would make it STRONG\n"
    "- Output a quality scorecard with per-test scores and an overall "
    "assessment\n"
    "\n"
    "The orchestrator will save your output as QUALITY_REVIEW.\n"
    "\n"
    "IMPORTANT: End your response with one of these verdicts:\n"
    "  VERDICT: PASS — if all tests score STRONG or ADEQUATE\n"
    "  VERDICT: FAIL — if any test scores WEAK"
)

# --- STEP 8: GREEN - FINAL REVIEW ------------------------------------------

REVIEW_INSTRUCTIONS = (
    "You are GREEN TEAM (architect role) performing final review.\n"
    "\n"
    "The orchestrator will pass CONFIRMED_ISSUES, SANDBOX_RESULTS, "
    "TEST_RESULTS, and QUALITY_REVIEW in your prompt.\n"
    "\n"
    "Your task:\n"
    "- Incorporate the quality reviewer's scores into your assessment\n"
    "- Include sandbox execution evidence in your final assessment — note "
    "which issues were runtime-confirmed vs unverifiable\n"
    "- For WEAK-scored tests, flag them for rewrite\n"
    "- Evaluate whether each test is actually necessary — reject tests that:\n"
    "  - Duplicate existing coverage\n"
    "  - Test trivial/obvious behavior that doesn't need a test\n"
    "  - Are overly defensive or test implementation details rather than behavior\n"
    "- Mark unnecessary tests for REMOVAL in the final report\n"
    "- For each confirmed bug, propose a fix plan: what to change, where, "
    "and why (do NOT implement fixes)\n"
    "- Assess overall test suite improvement from this run\n"
    "- Output a final report with: confirmed issues summary, test quality "
    "assessment (incorporating quality scores), and proposed fix plans\n"
    "\n"
    "The orchestrator will save your output as FINAL_REPORT.\n"
    "\n"
    "IMPORTANT: End your response with one of these verdicts:\n"
    "  VERDICT: PASS — if all tests are necessary, acceptable quality, "
    "and fix plans are complete\n"
    "  VERDICT: FAIL — if any tests should be removed, rewritten, or "
    "critical issues remain"
)

# --- STEP 9: PRESENT RESULTS -----------------------------------------------

PRESENT_INSTRUCTIONS = (
    "Summarize the full adversarial testing pipeline results to the user:\n"
    "\n"
    "1. **Coverage gaps found**: count from Step 2 (COVERAGE_GAPS)\n"
    "2. **Red team findings**: count from Step 3 (RED_FINDINGS), note Attack "
    "Hypothesis format used\n"
    "3. **Confirmed after verification**: count from Step 4 — note how many "
    "false positives were filtered\n"
    "4. **Sandbox validation**: from Step 5 (SANDBOX_RESULTS) — count "
    "CONFIRMED vs REFUTED vs UNVERIFIABLE, highlight any findings that "
    "changed status after runtime probing\n"
    "5. **Tests written**: file paths from Step 6, with pass/fail status\n"
    "6. **Quality scores**: from Step 7, per-test STRONG/ADEQUATE/WEAK "
    "ratings\n"
    "7. **Proposed fixes**: from Step 8, for user approval before "
    "implementing\n"
    "\n"
    "Present this as a clear, actionable summary. The user decides what to "
    "fix next."
)


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def shell_cmd(*parts: str) -> str:
    """Build a shell-safe command string for copy/paste instructions."""
    return " ".join(shlex.quote(part) for part in parts)


def workflow_command(
    step: int,
    target: str = "",
    attempt: int = 1,
    state_dir: str = DEFAULT_STATE_DIR,
) -> str:
    parts = ["python3", str(SCRIPT_PATH), "--step", str(step), "--state-dir", state_dir]
    if target:
        parts.extend(["--target", target])
    if attempt > 1:
        parts.extend(["--attempt", str(attempt)])
    return shell_cmd(*parts)


def build_next_command(
    step: int,
    target: str = "",
    attempt: int = 1,
    state_dir: str = DEFAULT_STATE_DIR,
) -> str | None:
    """Build invoke command for next step, threading --target and --attempt."""
    if step == 1:
        return workflow_command(2, target, attempt, state_dir)
    elif step == 2:
        return workflow_command(3, target, attempt, state_dir)
    elif step == 3:
        return workflow_command(4, target, attempt, state_dir)
    elif step == 4:
        return None  # conditional branching handled in format_output
    elif step == 5:
        return workflow_command(6, target, attempt, state_dir)
    elif step == 6:
        return workflow_command(7, target, attempt, state_dir)
    elif step == 7:
        return None if attempt <= 2 else workflow_command(8, target, attempt, state_dir)
    elif step == 8:
        return None if attempt <= 2 else workflow_command(9, target, attempt, state_dir)
    elif step == 9:
        return None  # terminal
    return None


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

# Static steps: (title, instructions) tuples for steps with constant content
STATIC_STEPS = {
    1: ("Detect", DETECT_INSTRUCTIONS),
    9: ("Present Results", PRESENT_INSTRUCTIONS),
}

# Dynamic steps: (title, agent_type, model, instructions)
# Steps 2-8 use subagent_dispatch, producing dispatch blocks as body content
DYNAMIC_STEPS = {
    2: ("Green: Coverage Analysis", "architect", "opus", COVERAGE_INSTRUCTIONS),
    3: ("Red: Attack", "adversarial-analyst", "sonnet", RED_INSTRUCTIONS),
    4: ("Green: Verify", "architect", "opus", VERIFY_INSTRUCTIONS),
    5: ("Sandbox: Validate", "sandbox-executor", "sonnet", SANDBOX_INSTRUCTIONS),
    6: ("Blue: Write Tests", "developer", "sonnet", BLUE_INSTRUCTIONS),
    7: ("Quality Review", "quality-reviewer", "sonnet", QUALITY_REVIEW_INSTRUCTIONS),
    8: ("Green: Final Review", "architect", "opus", REVIEW_INSTRUCTIONS),
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def _scope_prefix(target: str) -> str:
    """Build scope constraint prefix for prompts when --target is set."""
    if not target:
        return ""
    return (
        f"SCOPE CONSTRAINT: Only analyze files under `{target}/`. "
        f"Ignore all source and test files outside this directory.\n\n"
    )


def state_path(state_dir: str, filename: str) -> str:
    return str(PurePosixPath(state_dir) / filename)


def state_guidance(step: int, state_dir: str) -> str:
    lines: list[str] = []
    inputs = STEP_INPUTS.get(step, [])
    output = STEP_OUTPUTS.get(step)
    if inputs:
        lines.append("READ STATE FILES before this step:")
        lines.extend(f"- {state_path(state_dir, filename)}" for filename in inputs)
    if output:
        if lines:
            lines.append("")
        lines.append("SAVE OUTPUT:")
        lines.append(f"- Write the exact final result for this step to {state_path(state_dir, output)}")
    if not lines:
        return ""
    return "\n".join(lines) + "\n\n"


def format_output(
    step: int,
    target: str = "",
    attempt: int = 1,
    state_dir: str = DEFAULT_STATE_DIR,
) -> str:
    """Format output for the given step.

    Static steps use format_step directly.
    Dynamic steps wrap subagent_dispatch output in format_step.
    Steps 4, 7, 8 use conditional branching (if_pass/if_fail).
    Step 4: ALL_CLEAR skips to results, ISSUES_FOUND continues to step 5.
    Steps 7, 8 force forward when attempt > 2 (max retries exceeded).
    """
    scope = _scope_prefix(target)
    state = state_guidance(step, state_dir)

    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
        next_cmd = build_next_command(step, target, attempt, state_dir)
        return format_step(
            state + scope + instructions, next_cmd or "", title=f"TESTING - {title}"
        )

    elif step in DYNAMIC_STEPS:
        title, agent_type, model, instructions = DYNAMIC_STEPS[step]
        body = subagent_dispatch(
            agent_type=agent_type,
            prompt=state + scope + instructions,
            model=model,
        )

        if step == 4:
            # ALL CLEAR skips directly to results; confirmed issues continue to sandbox.
            return format_step(
                body,
                title=f"TESTING - {title}",
                if_pass=workflow_command(9, target, attempt, state_dir),
                if_fail=workflow_command(5, target, attempt, state_dir),
                pass_label="VERDICT: ALL CLEAR",
                fail_label="VERDICT: ISSUES FOUND",
            )
        elif step == 7:
            if attempt <= 2:
                return format_step(
                    body,
                    title=f"TESTING - {title}",
                    if_pass=workflow_command(8, target, attempt, state_dir),
                    if_fail=workflow_command(6, target, attempt + 1, state_dir),
                )
            else:
                next_cmd = build_next_command(step, target, attempt, state_dir)
                return format_step(
                    body, next_cmd or "", title=f"TESTING - {title}"
                )
        elif step == 8:
            if attempt <= 2:
                return format_step(
                    body,
                    title=f"TESTING - {title}",
                    if_pass=workflow_command(9, target, attempt, state_dir),
                    if_fail=workflow_command(6, target, attempt + 1, state_dir),
                )
            else:
                next_cmd = build_next_command(step, target, attempt, state_dir)
                return format_step(
                    body, next_cmd or "", title=f"TESTING - {title}"
                )
        else:
            # Linear steps: 2, 3, 5, 6 — always forward to next
            next_cmd = build_next_command(step, target, attempt, state_dir)
            return format_step(
                body, next_cmd or "", title=f"TESTING - {title}"
            )

    else:
        return f"ERROR: Invalid step {step}"


# ============================================================================
# ENTRY POINT
# ============================================================================


def normalize_target(raw: str) -> str:
    target = raw.strip().strip("/")
    if target == "" or target == ".":
        return ""
    if any(ch in target for ch in ("\x00", "\n", "\r")):
        raise argparse.ArgumentTypeError("--target must be a relative subdirectory")
    normalized = target.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise argparse.ArgumentTypeError("--target must stay inside the project root")
    return str(path)


def main():
    """Entry point for testing workflow."""
    parser = argparse.ArgumentParser(
        description="Testing - Adversarial coverage improvement workflow",
        epilog=(
            "Steps: detect (1) -> green (2) -> red (3) -> verify (4) "
            "-> sandbox (5) -> blue (6) -> QR (7) -> final (8) -> present (9). "
            "Steps 7 and 8 loop back to 6 on FAIL (max 2 retries)."
        ),
    )
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--target", type=normalize_target, default="",
                        help="Subdirectory to scope analysis to (e.g., backend/)")
    parser.add_argument("--attempt", type=int, default=1,
                        help="Retry attempt number (default: 1, max useful: 3)")
    parser.add_argument("--state-dir", type=str, default=DEFAULT_STATE_DIR,
                        help="Directory for handoff files (default: .testing-skill)")

    args = parser.parse_args()

    if args.step < 1 or args.step > 9:
        sys.exit("ERROR: --step must be 1-9")

    Path(args.state_dir).mkdir(parents=True, exist_ok=True)

    print(format_output(args.step, args.target, args.attempt, args.state_dir))


if __name__ == "__main__":
    main()
