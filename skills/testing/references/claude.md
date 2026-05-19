# Claude Code Adapter

Use this adapter when the testing skill runs inside Claude Code.

## Dispatch

For Steps 2-8, prefer the custom agent named by the orchestrator output:

| Step | Agent |
| --- | --- |
| 2 Coverage analysis | `architect` |
| 3 Attack hypotheses | `adversarial-analyst` |
| 4 Verify findings | `architect` |
| 5 Runtime probes | `sandbox-executor` |
| 6 Write tests | `developer` |
| 7 Test quality review | `quality-reviewer` |
| 8 Final review | `architect` |

Keep `run_in_background` unset or false so the main workflow receives only the
agent's final answer. Include the required state-file contents in the prompt.

## State Handoff

After every step, write the final answer to the state file printed by the
orchestrator. Do not summarize while saving; downstream steps depend on the
exact findings, evidence, and verdict labels.

## Safety

Steps 2-5 and 7-8 do not edit project source or test files. Step 5 may execute
diagnostic probes in `/tmp`. Step 6 may create or edit test files only.
Production-code fixes require a separate explicit user approval after Step 9.
