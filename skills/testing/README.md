# Testing Skill

Run tests and validate coverage gaps across workflow-based skills.

## Purpose

Orchestrates a four-step workflow that discovers skill modules, validates test coverage, runs pytest, and produces a structured report. Uses the instruction-based pattern where each step emits prompts that direct the LLM to perform actions using its tools.

## Architecture

Instruction-based workflow using `format_step()`:
- Step 1 (Discover): LLM globs for test files and skill modules
- Step 2 (Validate): LLM greps test files for workflow references, builds coverage table
- Step 3 (Execute): LLM runs `pytest tests/ -v` via bash
- Step 4 (Report): LLM aggregates results into structured report

Each step outputs instructions via `format_step(body, next_cmd, title)`. The script contains no execution logic — all work is done by the LLM following the emitted instructions.

## Workflow

1. **Discover**: Glob test files from `scripts/tests/`, glob skill modules from `scripts/skills/`, list discovered files
2. **Validate**: Grep test files for workflow name references, build coverage summary table, identify gaps
3. **Execute**: Run pytest subprocess, capture output and exit code
4. **Report**: Combine all results into structured report with recommendations (runs even if execution encountered errors)

## Coverage Algorithm

Coverage detection uses the LLM's search tools:
- Skill modules discovered by globbing `scripts/skills/*/[!_]*.py`
- Test coverage determined by grepping test files for workflow names
- Gap reported when a skill has ZERO test file references

## When to Use

Invoke when:
- User requests test execution
- Validating skill implementation completeness
- Checking for untested workflow steps

## Why This Structure

Follows the instruction-based workflow pattern used by `deepthink/`, `planner/`, and other skills:
- `format_step()` as sole output assembler
- `StepDef` / `Workflow` metadata for discovery
- CLI step invocation via `python3 -m skills.testing.testing --step N`
- No execution engine, no handlers — the LLM does the work

## Invariants

- All four steps always use `format_step()` for output
- Step 4 (Report) always runs regardless of Step 3 outcome
- Invalid step numbers produce an error via `sys.exit()`
- `WORKFLOW` metadata matches the step registry for introspection consistency
