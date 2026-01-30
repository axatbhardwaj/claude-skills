# Testing Skill

Run tests and validate coverage gaps across workflow-based skills.

## Purpose

Executes pytest test suite while detecting coverage gaps by comparing workflow registry against test files. Reports both test execution results and untested workflow steps.

## Architecture

Four-step workflow with data flow:
- Step 1 (Discover): Produces `workflow_registry` and `test_files[]`
- Step 2 (Validate): Consumes `workflow_registry`, produces `coverage_gaps[]`
- Step 3 (Execute): Produces `pytest_result` (exit_code, stdout, stderr)
- Step 4 (Report): Consumes `coverage_gaps[]` and `pytest_result`, aggregates into XML

Step 4 always runs even if Step 3 fails to capture partial results.

## Workflow

Four-step process ensures comprehensive validation:

1. **Discover**: Glob test files from `scripts/tests/`, import all skill modules to populate workflow registry
2. **Validate**: Build expected coverage map from registry, scan test files for workflow invocations, identify steps without ANY test coverage
3. **Execute**: Invoke pytest subprocess with 30s timeout, capture stdout/stderr/exit code
4. **Report**: Aggregate test results and coverage gaps into XML output (runs even if execution fails)

## Coverage Algorithm

Coverage detection uses static analysis:
- Expected coverage derived from `get_workflow_registry()` after importing all skills
- Actual coverage determined by scanning test file content for workflow names
- Parametrized tests counted as single coverage entry
- Gap reported only when step has ZERO test coverage (not partial)

## When to Use

Invoke when:
- User requests test execution
- Validating skill implementation completeness
- Checking for untested workflow steps

## Why This Structure

Follows Workflow pattern like `refactor/` and `planner/` skills. Deviation would require modifying test infrastructure which expects:
- Single entry point with `Workflow` registration at module load
- Frozen `StepDef` dataclasses with explicit handlers
- XML output via `XMLRenderer` for QR agent compatibility
- Path resolution supports invocation from any directory

## Invariants

- All skill modules imported before registry query (Step 1 guarantee)
- Test file discovery uses same paths as pytest.ini `testpaths`
- Report step always executes regardless of prior failures
- Coverage gaps computed before test execution (static analysis)

## Tradeoffs

- **Static coverage only**: Simpler than runtime but misses dynamic discovery
- **No test generation**: Focused scope but requires manual test authoring
- **Single pytest invocation**: Cannot parallelize but simpler error handling
