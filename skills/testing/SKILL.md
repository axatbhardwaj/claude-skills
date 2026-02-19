---
name: testing
description: Invoke IMMEDIATELY via python script for adversarial test coverage improvement. Do NOT analyze first - the script orchestrates the red/blue/green team workflow.
---

# Testing

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.testing.testing --step 1" />

| Argument | Required | Description             |
| -------- | -------- | ----------------------- |
| `--step` | Yes      | Current step (1-7)      |

Do NOT explore or analyze first. Run the script and follow its output.
