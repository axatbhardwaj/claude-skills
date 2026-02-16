#!/usr/bin/env python3
"""Testing Skill - Run tests and validate coverage gaps.

Four-step workflow:
  1. Discover  - Find test files and list them
  2. Validate  - Grep test files for workflow names, identify gaps
  3. Execute   - Run pytest tests/ -v via bash
  4. Report    - Summarize pass/fail results and coverage gaps
"""

import argparse
import sys

from skills.lib.workflow.core import StepDef, Workflow
from skills.lib.workflow.prompts import format_step


MODULE_PATH = "skills.testing.testing"
TOTAL_STEPS = 4


# ============================================================================
# STEP INSTRUCTIONS
# ============================================================================

DISCOVER_INSTRUCTIONS = (
    "Find all test files and skill modules in this repository.\n"
    "\n"
    "ACTIONS:\n"
    "  1. GLOB for test files: scripts/tests/test_*.py\n"
    "  2. GLOB for skill modules: scripts/skills/*/[!_]*.py\n"
    "     (exclude __init__.py and lib/ directory)\n"
    "  3. LIST each test file and each skill module found\n"
    "  4. NOTE any skill modules that appear to lack corresponding test files\n"
    "\n"
    "OUTPUT FORMAT:\n"
    "  Test files found:\n"
    "    - tests/test_foo.py\n"
    "    - tests/test_bar.py\n"
    "  Skill modules found:\n"
    "    - skills/deepthink/think.py\n"
    "    - skills/planner/orchestrator/planner.py\n"
    "  Preliminary gaps:\n"
    "    - skills/testing/testing.py (no test_testing.py found)"
)

VALIDATE_INSTRUCTIONS = (
    "Validate test coverage by checking which skill workflows are referenced "
    "in test files.\n"
    "\n"
    "ACTIONS:\n"
    "  1. For EACH skill module found in Step 1:\n"
    "     a. GREP test files for the workflow name or module import\n"
    "     b. Record whether ANY test file references this skill\n"
    "  2. Build a coverage summary table:\n"
    "     | Skill Module | Workflow Name | Covered? | Test File(s) |\n"
    "  3. IDENTIFY coverage gaps: skills with ZERO test references\n"
    "\n"
    "OUTPUT FORMAT:\n"
    "  Coverage summary:\n"
    "    [table as above]\n"
    "  Coverage gaps:\n"
    "    - list of uncovered skills\n"
    "  Coverage ratio: X/Y skills have test coverage"
)

EXECUTE_INSTRUCTIONS = (
    "Run the test suite using pytest.\n"
    "\n"
    "ACTIONS:\n"
    "  1. RUN: python3 -m pytest tests/ -v\n"
    "     Working directory: the scripts/ directory (where this skill runs)\n"
    "  2. CAPTURE the full output including pass/fail per test\n"
    "  3. NOTE the exit code (0 = all passed, non-zero = failures)\n"
    "\n"
    "If pytest fails to run (e.g., import errors), report the error and "
    "continue to the next step.\n"
    "\n"
    "OUTPUT FORMAT:\n"
    "  Paste the pytest output verbatim, then summarize:\n"
    "    Total: X tests\n"
    "    Passed: Y\n"
    "    Failed: Z\n"
    "    Errors: W"
)

REPORT_INSTRUCTIONS = (
    "Aggregate all results from previous steps into a final report.\n"
    "\n"
    "ACTIONS:\n"
    "  1. COMBINE results from all previous steps\n"
    "  2. PRODUCE a structured report with these sections:\n"
    "\n"
    "REPORT FORMAT:\n"
    "  ## Test Execution Results\n"
    "  - Total tests: X\n"
    "  - Passed: Y / Failed: Z / Errors: W\n"
    "  - Status: PASS or FAIL\n"
    "\n"
    "  ## Coverage Analysis\n"
    "  - Skills with tests: X/Y\n"
    "  - Coverage gaps:\n"
    "    - [list uncovered skills]\n"
    "\n"
    "  ## Recommendations\n"
    "  - [actionable items to improve coverage]\n"
    "\n"
    "This step always runs even if Step 3 (Execute) encountered errors, "
    "to capture partial results."
)


# ============================================================================
# STEP REGISTRY
# ============================================================================

STATIC_STEPS = {
    1: ("Discover", DISCOVER_INSTRUCTIONS),
    2: ("Validate", VALIDATE_INSTRUCTIONS),
    3: ("Execute", EXECUTE_INSTRUCTIONS),
    4: ("Report", REPORT_INSTRUCTIONS),
}


# ============================================================================
# WORKFLOW METADATA (for discovery/introspection)
# ============================================================================

WORKFLOW = Workflow(
    "testing",
    StepDef(
        id="discover",
        title="Discover",
        actions=[
            "GLOB test files in scripts/tests/ directory",
            "GLOB skill modules in scripts/skills/",
            "LIST all discovered files",
        ],
    ),
    StepDef(
        id="validate",
        title="Validate",
        actions=[
            "GREP test files for workflow name references",
            "BUILD coverage summary table",
            "IDENTIFY coverage gaps",
        ],
    ),
    StepDef(
        id="execute",
        title="Execute",
        actions=[
            "RUN pytest tests/ -v",
            "CAPTURE output and exit code",
            "NOTE failures and errors",
        ],
    ),
    StepDef(
        id="report",
        title="Report",
        actions=[
            "COMBINE results from all steps",
            "PRODUCE structured report",
            "LIST recommendations",
        ],
    ),
    description="Run tests and validate coverage gaps",
)


# ============================================================================
# OUTPUT FORMATTING
# ============================================================================

def build_next_command(step: int) -> str:
    """Build the command for the next step, or empty string if done."""
    if step < TOTAL_STEPS:
        return f"python3 -m {MODULE_PATH} --step {step + 1}"
    return ""


def format_output(step: int) -> str:
    """Format output for the given step."""
    if step not in STATIC_STEPS:
        sys.exit(f"ERROR: --step must be between 1 and {TOTAL_STEPS}")

    title, instructions = STATIC_STEPS[step]
    next_cmd = build_next_command(step)
    return format_step(instructions, next_cmd, title=f"TESTING - {title}")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Testing Skill")
    parser.add_argument("--step", type=int, required=True,
                        help=f"Current step (1-{TOTAL_STEPS})")
    args = parser.parse_args()

    print(format_output(args.step))


if __name__ == "__main__":
    main()
