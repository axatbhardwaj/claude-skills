---
name: testing
description: Invoke IMMEDIATELY via python script to run tests and validate coverage gaps. Do NOT explore first - the script orchestrates test discovery, coverage validation, execution, and reporting.
---

# Testing

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.testing.testing --step 1" />

| Argument   | Required | Description                |
| ---------- | -------- | -------------------------- |
| `--step`   | Yes      | Current step (1-4)         |

Do NOT run pytest manually. Run the script and follow its output.

## Workflow Steps

1. **Discover** - Find test files and import skill modules
2. **Validate** - Compare registry workflows against test coverage
3. **Execute** - Run pytest subprocess
4. **Report** - Aggregate results and coverage gaps
