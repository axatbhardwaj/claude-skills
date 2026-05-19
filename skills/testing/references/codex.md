# Codex Adapter

Use this adapter when the testing skill runs inside Codex.

## Dispatch

Use subagents only when current Codex instructions permit delegation. Leave the
model unset so subagents inherit the active model. If delegation is unavailable
or disallowed, complete the step locally.

Recommended roles when available:

| Step | Preferred role |
| --- | --- |
| 2 Coverage analysis | read-only explorer |
| 3 Attack hypotheses | read-only explorer |
| 4 Verify findings | read-only explorer |
| 5 Runtime probes | local execution or read-only analysis plus explicit probes |
| 6 Write tests | worker with ownership limited to test files |
| 7 Test quality review | read-only reviewer/explorer |
| 8 Final review | read-only reviewer/explorer |

## State Handoff

Write each step's final answer to the state file printed by the orchestrator.
Read the listed input state files before running the next step.

## Safety

Do not run destructive git commands. Do not commit. Do not modify production
code during this skill unless the user explicitly approves a separate fix pass.
For Step 6, keep the worker write scope to test files and test fixtures.
