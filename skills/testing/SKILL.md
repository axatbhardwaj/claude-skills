---
name: testing
description: Invoke IMMEDIATELY via python script for adversarial test coverage improvement. Do NOT analyze first - the script orchestrates the red/blue/green team workflow.
---

# Testing

When this skill activates, IMMEDIATELY invoke the script. The script IS the workflow.

## Invocation

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.testing.testing --step 1" />

If the user specifies a subdirectory to scope to (e.g., "only test the backend"):

<invoke working-dir=".claude/skills/scripts" cmd="python3 -m skills.testing.testing --step 1 --target '<subdirectory>'" />

| Argument   | Required | Description                                      |
| ---------- | -------- | ------------------------------------------------ |
| `--step`   | Yes      | Current step (1-8)                               |
| `--target` | No       | Subdirectory to scope analysis to (e.g., backend) |

Do NOT explore or analyze first. Run the script and follow its output.

## Install

This skill dispatches work to custom agent types (`architect`, `adversarial-analyst`, `developer`, `quality-reviewer`). Copy the files from `agents/` to your `~/.claude/agents/` directory:

```sh
cp agents/*.md ~/.claude/agents/
```
