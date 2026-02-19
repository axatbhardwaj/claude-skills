#!/usr/bin/env python3
"""
Testing — Adversarial Coverage Improvement.

Seven-step workflow:
  1:   DETECT - Identify test framework, conventions, directory structure
  2:   GREEN: COVERAGE - Analyze coverage gaps and rank by severity
  3:   RED: BREAK IT - Find edge cases, boundary conditions, error handling gaps
  4:   GREEN: VERIFY - Verify Red's claims, filter false positives
  5:   BLUE: WRITE TESTS - Write test cases for confirmed issues
  6:   GREEN: FINAL REVIEW - Review test quality, propose fix plans
  7:   PRESENT RESULTS - Summarize findings to user

Adversarial red/blue/green team model:
  - Green (architect): analyzes, verifies, reviews
  - Red (general-purpose): attacks, finds vulnerabilities
  - Blue (developer): writes tests for confirmed issues
"""

import argparse
import sys

from skills.lib.workflow.prompts import format_step, subagent_dispatch


# ============================================================================
# CONFIGURATION
# ============================================================================

MODULE_PATH = "skills.testing.testing"


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

# --- STEP 3: RED - BREAK IT ------------------------------------------------

RED_INSTRUCTIONS = (
    "You are RED TEAM (adversarial attacker role).\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT and COVERAGE_GAPS in your "
    "prompt.\n"
    "\n"
    "Your task:\n"
    "- Target the untested areas Green identified\n"
    "- Find edge cases, boundary conditions, error handling gaps\n"
    "- Try invalid inputs, type confusion, missing validation, race "
    "conditions\n"
    "- Use Bash to run code in sandbox where possible — attempt actual "
    "crashes, panics, unhandled exceptions\n"
    "- For each finding, provide concrete reproduction steps (exact inputs, "
    "commands, expected vs actual behavior)\n"
    "- Output a numbered vulnerability list, each with: description, "
    "severity, reproduction steps, affected code location\n"
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
    "- Evaluate each of Red's claims architecturally\n"
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

# --- STEP 5: BLUE - WRITE TESTS --------------------------------------------

BLUE_INSTRUCTIONS = (
    "You are BLUE TEAM (developer role) writing tests.\n"
    "\n"
    "The orchestrator will pass PROJECT_CONTEXT, CONFIRMED_ISSUES, and test "
    "conventions from Step 1 in your prompt.\n"
    "\n"
    "Your task:\n"
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
    "The orchestrator will save your output as TEST_RESULTS."
)

# --- STEP 6: GREEN - FINAL REVIEW ------------------------------------------

REVIEW_INSTRUCTIONS = (
    "You are GREEN TEAM (architect role) performing final review.\n"
    "\n"
    "The orchestrator will pass CONFIRMED_ISSUES and TEST_RESULTS in your "
    "prompt.\n"
    "\n"
    "Your task:\n"
    "- Review the quality of Blue's tests — are they meaningful? Do they "
    "actually test the confirmed issue?\n"
    "- For each confirmed bug, propose a fix plan: what to change, where, "
    "and why (do NOT implement fixes)\n"
    "- Assess overall test suite improvement from this run\n"
    "- Output a final report with: confirmed issues summary, test quality "
    "assessment, and proposed fix plans\n"
    "\n"
    "The orchestrator will save your output as FINAL_REPORT."
)

# --- STEP 7: PRESENT RESULTS -----------------------------------------------

PRESENT_INSTRUCTIONS = (
    "Summarize the full adversarial testing pipeline results to the user:\n"
    "\n"
    "1. **Coverage gaps found**: count from Step 2 (COVERAGE_GAPS)\n"
    "2. **Red team findings**: count from Step 3 (RED_FINDINGS)\n"
    "3. **Confirmed after verification**: count from Step 4 — note how many "
    "false positives were filtered\n"
    "4. **Tests written**: file paths from Step 5, with pass/fail status\n"
    "5. **Proposed fixes**: from Step 6, for user approval before "
    "implementing\n"
    "\n"
    "Present this as a clear, actionable summary. The user decides what to "
    "fix next."
)


# ============================================================================
# MESSAGE BUILDERS
# ============================================================================


def build_next_command(step: int) -> str | None:
    """Build invoke command for next step."""
    base = f"python3 -m {MODULE_PATH}"
    if step == 1:
        return f"{base} --step 2"
    elif step == 2:
        return f"{base} --step 3"
    elif step == 3:
        return f"{base} --step 4"
    elif step == 4:
        # Conditional: depends on whether Green found confirmed issues
        return None  # handled specially in format_output
    elif step == 5:
        return f"{base} --step 6"
    elif step == 6:
        return f"{base} --step 7"
    elif step == 7:
        return None
    return None


# ============================================================================
# STEP DEFINITIONS
# ============================================================================

# Static steps: (title, instructions) tuples for steps with constant content
STATIC_STEPS = {
    1: ("Detect", DETECT_INSTRUCTIONS),
    7: ("Present Results", PRESENT_INSTRUCTIONS),
}

# Dynamic steps: functions/dispatchers that compute (title, body) based on parameters
# Steps 2-6 use subagent_dispatch, producing dispatch blocks as body content
DYNAMIC_STEPS = {
    2: ("Green: Coverage Analysis", "architect", "opus", COVERAGE_INSTRUCTIONS),
    3: ("Red: Break It", "general-purpose", "sonnet", RED_INSTRUCTIONS),
    4: ("Green: Verify", "architect", "opus", VERIFY_INSTRUCTIONS),
    5: ("Blue: Write Tests", "developer", "sonnet", BLUE_INSTRUCTIONS),
    6: ("Green: Final Review", "architect", "opus", REVIEW_INSTRUCTIONS),
}


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================


def format_output(step: int) -> str:
    """Format output for the given step.

    Static steps use format_step directly.
    Dynamic steps wrap subagent_dispatch output in format_step.
    Step 4 uses conditional branching (if_pass/if_fail).
    """
    base = f"python3 -m {MODULE_PATH}"

    if step in STATIC_STEPS:
        title, instructions = STATIC_STEPS[step]
        next_cmd = build_next_command(step)
        return format_step(
            instructions, next_cmd or "", title=f"TESTING - {title}"
        )

    elif step in DYNAMIC_STEPS:
        title, agent_type, model, instructions = DYNAMIC_STEPS[step]
        body = subagent_dispatch(
            agent_type=agent_type,
            command="",
            prompt=instructions,
            model=model,
        )

        if step == 4:
            # Conditional branching: skip to step 6 if no confirmed issues
            return format_step(
                body,
                title=f"TESTING - {title}",
                if_pass=f"{base} --step 6",
                if_fail=f"{base} --step 5",
            )
        else:
            next_cmd = build_next_command(step)
            return format_step(
                body, next_cmd or "", title=f"TESTING - {title}"
            )

    else:
        return f"ERROR: Invalid step {step}"


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    """Entry point for testing workflow."""
    parser = argparse.ArgumentParser(
        description="Testing - Adversarial coverage improvement workflow",
        epilog="Steps: detect (1) -> green (2) -> red (3) -> green (4) -> blue (5) -> green (6) -> present (7)",
    )
    parser.add_argument("--step", type=int, required=True)

    args = parser.parse_args()

    if args.step < 1 or args.step > 7:
        sys.exit("ERROR: --step must be 1-7")

    print(format_output(args.step))


if __name__ == "__main__":
    main()
