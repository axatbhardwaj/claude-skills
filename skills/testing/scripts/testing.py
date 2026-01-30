#!/usr/bin/env python3
"""Testing Skill - Run tests and validate coverage gaps.

Four-step workflow:
  1. Discover   - Find test files and import skill modules
  2. Validate   - Compare registry workflows against test coverage
  3. Execute    - Run pytest subprocess
  4. Report     - Aggregate results and coverage gaps
"""

import argparse
import subprocess
import sys
from pathlib import Path

from skills.lib.workflow.core import (
    Outcome,
    StepContext,
    StepDef,
    Workflow,
    register_workflow,
    get_workflow_registry,
)
from skills.lib.workflow.ast import W, XMLRenderer, render, TextNode


MODULE_PATH = "skills.testing.testing"

# Skills directory resolution supports invocation from any working directory
SKILLS_DIR = Path(__file__).resolve().parent.parent.parent
TESTS_DIR = SKILLS_DIR / "tests"


def _discover(ctx: StepContext) -> tuple[Outcome, dict]:
    """Discover test files and import skill modules to populate registry."""
    if not TESTS_DIR.exists():
        return Outcome.FAIL, {"error": f"Tests directory not found: {TESTS_DIR}"}

    test_files = sorted(TESTS_DIR.glob("test_*.py"))

    # Workflow pattern requires all skills imported before registry query
    from tests.conftest import import_all_skills
    failures = import_all_skills()
    if failures:
        return Outcome.FAIL, {
            "import_failures": failures,
            "error": f"Failed to import {len(failures)} skill modules"
        }

    registry = get_workflow_registry()

    return Outcome.OK, {
        "test_files": [str(f.relative_to(SKILLS_DIR)) for f in test_files],
        "registry_count": len(registry),
    }


def _build_expected_coverage(registry) -> dict:
    """Build map of workflow:step -> False for all registered steps."""
    expected = {}
    for name, workflow in registry.items():
        for step_id in workflow.steps:
            expected[f"{name}:{step_id}"] = False
    return expected


def _scan_test_coverage(test_files, registry) -> tuple[bool, dict]:
    """Scan test files to mark covered workflow steps.

    Returns:
        (success, coverage_dict) or (False, {"error": message})
    """
    coverage = {}
    for test_file in test_files:
        try:
            content = test_file.read_text()
        except (OSError, UnicodeDecodeError) as e:
            return False, {"error": f"Failed to read {test_file.name}: {e}"}

        for name in registry:
            if name in content:
                for step_id in registry[name].steps:
                    coverage[f"{name}:{step_id}"] = True
    return True, coverage


def _validate(ctx: StepContext) -> tuple[Outcome, dict]:
    """Compare registry workflows against test files to find coverage gaps."""
    registry = get_workflow_registry()
    test_files = list(TESTS_DIR.glob("test_*.py"))

    expected = _build_expected_coverage(registry)
    success, result = _scan_test_coverage(test_files, registry)
    if not success:
        return Outcome.FAIL, result

    expected.update(result)
    gaps = [k for k, covered in expected.items() if not covered]

    return Outcome.OK, {
        "total_steps": len(expected),
        "covered_steps": sum(1 for v in expected.values() if v),
        "coverage_gaps": gaps,
    }


def _execute(ctx: StepContext) -> tuple[Outcome, dict]:
    """Run pytest subprocess with timeout."""
    try:
        # Single pytest invocation; 30s timeout from conftest.py pattern
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(TESTS_DIR)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=SKILLS_DIR,
        )

        return Outcome.OK, {
            "exit_code": result.returncode,
            "stdout": result.stdout[:1000],  # Truncate for XML
            "stderr": result.stderr[:1000],
        }
    except subprocess.TimeoutExpired:
        return Outcome.FAIL, {
            "exit_code": -1,
            "error": "Timeout (30s)",
        }
    except (subprocess.SubprocessError, OSError) as e:
        return Outcome.FAIL, {
            "exit_code": -1,
            "error": str(e)[:200],
        }


def _report(ctx: StepContext) -> tuple[Outcome, dict]:
    """Aggregate results and coverage gaps into XML structure.

    Runs even if execution fails to capture partial results.
    """
    test_files = ctx.workflow_params.get("test_files", [])
    coverage_gaps = ctx.workflow_params.get("coverage_gaps", [])
    exit_code = ctx.workflow_params.get("exit_code", -1)

    return Outcome.OK, {
        "test_count": len(test_files),
        "gap_count": len(coverage_gaps),
        "passed": exit_code == 0,
    }


# Step definitions
STEPS = {
    1: {
        "title": "Discover",
        "brief": "Find test files and import skill modules",
        "actions": [
            "GLOB test files in scripts/tests/ directory",
            "IMPORT all skill modules to populate workflow registry",
            "COUNT workflows and test files",
        ],
    },
    2: {
        "title": "Validate",
        "brief": "Compare registry workflows against test coverage",
        "actions": [
            "BUILD expected coverage map from workflow registry",
            "SCAN test files for workflow invocations",
            "IDENTIFY coverage gaps: steps without ANY test coverage",
        ],
    },
    3: {
        "title": "Execute",
        "brief": "Run pytest subprocess",
        "actions": [
            "INVOKE pytest on tests directory",
            "CAPTURE stdout, stderr, exit code",
            "HANDLE timeout (30s) and exceptions",
        ],
    },
    4: {
        "title": "Report",
        "brief": "Aggregate results and coverage gaps",
        "actions": [
            "COLLECT data from all previous steps",
            "FORMAT XML report with test results and coverage gaps",
            "RUNS even if execution fails",
        ],
    },
}


# Workflow definition
WORKFLOW = Workflow(
    "testing",
    StepDef(
        id="discover",
        title="Discover",
        actions=STEPS[1]["actions"],
        handler=_discover,
        next={Outcome.OK: "validate", Outcome.FAIL: None},
    ),
    StepDef(
        id="validate",
        title="Validate",
        actions=STEPS[2]["actions"],
        handler=_validate,
        next={Outcome.OK: "execute", Outcome.FAIL: None},
    ),
    StepDef(
        id="execute",
        title="Execute",
        actions=STEPS[3]["actions"],
        handler=_execute,
        next={Outcome.OK: "report", Outcome.FAIL: "report"},
    ),
    StepDef(
        id="report",
        title="Report",
        actions=STEPS[4]["actions"],
        handler=_report,
        next={Outcome.OK: None},
    ),
    description="Run tests and validate coverage gaps",
)

register_workflow(WORKFLOW)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Testing Skill")
    parser.add_argument("--step", type=int, required=True)
    parser.add_argument("--total-steps", type=int, required=True)
    return parser.parse_args()


def validate_step_bounds(step, total):
    """Validate step number is within bounds.

    Raises:
        ValueError: If step is out of bounds or invalid.
    """
    if step < 1 or step > total:
        raise ValueError(f"--step must be between 1 and {total}")
    if step not in STEPS:
        raise ValueError(f"Invalid step {step}")


def format_step_output(step, total, step_info):
    """Format step guidance as XML string."""
    next_step = step + 1 if step < total else None
    next_cmd = f'<invoke working-dir=".claude/skills/scripts" cmd="python3 -m {MODULE_PATH} --step {next_step} --total-steps {total}" />' if next_step else None

    return render(W.text_output(
        step=step,
        total=total,
        title=f"TESTING - {step_info['title']}",
        actions=step_info["actions"],
        invoke_after=next_cmd
    ).build(), XMLRenderer())


def main():
    """Entry point: coordinate argparse, validation, and output formatting."""
    args = parse_args()
    try:
        validate_step_bounds(args.step, args.total_steps)
    except ValueError as e:
        sys.exit(f"ERROR: {e}")

    step_info = STEPS[args.step]
    output = format_step_output(args.step, args.total_steps, step_info)
    print(output)


if __name__ == "__main__":
    main()
