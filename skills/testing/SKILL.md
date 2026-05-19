---
name: testing
description: Use when auditing or improving test coverage, adding regression tests after bugs, finding missing edge-case tests, or running adversarial test-gap analysis.
---

# Testing

Portable adversarial test coverage workflow for Claude Code and Codex.

## Start

Run the orchestrator from the target project root:

```bash
python3 <skill-dir>/scripts/testing.py --step 1
```

For scoped analysis:

```bash
python3 <skill-dir>/scripts/testing.py --step 1 --target backend
```

Use `--state-dir <dir>` to choose the handoff directory. The default is
`.testing-skill/`; add it to `.gitignore` or use a temporary directory if the
run should leave no repo-local state.

## Workflow Contract

The script prints the next instruction block. Follow it literally:

1. Complete the current step in the target project root.
2. Save the exact step output to the printed state file.
3. Run the printed next command.
4. Continue until Step 9 presents results.

Do not write tests until Step 6. Steps 2-5 are read-only analysis and
verification. Step 6 may edit tests only, unless the user explicitly approves a
production-code fix.

## Platform Adapters

Claude Code: use the custom agents from this repo when available:
`architect`, `adversarial-analyst`, `sandbox-executor`, `developer`, and
`quality-reviewer`. See `references/claude.md`.

Codex: use inherited-model subagents only when current instructions allow them.
Use read-only/explorer-style work for analysis and a worker only for Step 6.
See `references/codex.md`.

If the platform cannot dispatch subagents, do the step locally and still use the
same state files.

## Borrowed From clawpatch

This skill deliberately borrows the strongest parts of `clawpatch`:

- bounded feature/test context instead of whole-repo guessing
- persisted state handoffs instead of relying on conversation memory
- evidence-backed findings with file paths and line references
- explicit test-writing and revalidation phases
- no implicit commits, branch switches, or destructive git commands

For broader automated review or patch management, prefer `clawpatch` directly.
Use this skill when the goal is specifically adversarial test-gap discovery and
focused regression-test generation.
