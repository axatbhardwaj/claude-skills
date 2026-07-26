---
name: authoring-workflows
description: Binds whenever a plan owes its execution workflow — any T2/T3 planning
  brief where the madhyastha is about to write the Workflow section. Load before
  writing any `export const meta` line. Not a Workflow-tool tutorial; whether a
  script is owed at all is CLAUDE.md §5's decision, not this skill's.
---

# Authoring Workflows

## The contract

The plan's Workflow section **is the emitted script**. There is no later translation
step where a station can disappear or a control-flow edge can change.

The contract binds both sides:

1. The planner emits a complete runnable script, not pseudocode or a prose station table.
2. The chair runs that script verbatim or returns it. Any chair edit is a plan revision
   and routes back to the author.

Put rationale in script comments; the lane-assignment comment block near the top of
`/home/xzat/.claude/workflows/pr-review.js` is the model. Never duplicate the graph
as a parallel prose station table: that creates a second translation surface, and
it will drift from the script.

## Delivery format

Precede one fenced `js` block with exactly:

- the proposed filename; and
- the exact invocation `Workflow({name, args: {...}})`, listing every required arg,
  its type, and whether it is baked into the script or chair-supplied at runtime.
  Dates, seeds, and other replay-sensitive values are chair-supplied.

A script needing a mid-run human decision is mis-scoped. End it at the decision,
then emit the next script's shape for use after the answer. Prefer a chain of short
scripts; only the planner can cut the graph at the decision boundary.

Tell the chair to syntax-check by stripping `export `, wrapping the body in
`async function f(){ ... }`, and running `node --check`. That wrapper is the **only**
invocation that validates anything.

Bare `node --check` on the raw `.js` file is **positional**: it exits 0 for any error
after the first module-syntax token (for example, `export`). The CommonJS parse aborts
at that token and Node discards the error, so nothing after `export const meta` is ever
parsed. Verified on Node v26.4.0:
`export const meta = { a: 1 }` followed by `@@@ ### not javascript (((` exits 0, while
the same garbage placed *before* the `export` exits 1. Every emitted workflow script
puts that token on line 1 as `export const meta`, so in practice a pass is **zero
evidence** — a null check, not a weak one.

Renaming to `.mjs` swings the other way: it parses the whole file but rejects the
top-level `return` the runtime requires (`SyntaxError: Illegal return statement`),
reporting failure on a correct script. Use neither. Never mutilate a correct workflow
to satisfy the wrong checker.

## Skeleton

This is an illustrative, deliberately incomplete skeleton, not a standalone example:

```js
export const meta = { // PURE LITERAL: statically extracted before the body runs.
  name: 'workflow-name',
  description: 'What this workflow does.',
  whenToUse: 'When this graph is the right execution shape.',
  phases: [{ title: 'X', detail: 'Build the spine' }],
} // A variable, call, spread, or template expression here fails parse.

const a = args || {}
if (!a.today) throw new Error(
  'args.today required (YYYY-MM-DD). Scripts cannot call Date.now(), new Date(), or Math.random() — ' +
  'replay on resume would diverge. The chair passes time and randomness in.',
)
// Define constants and derived paths.

phase('X')
const spine = await agent(brief, {
  label: 'spine',
  model: 'sonnet',
  schema: SPINE_SCHEMA, // Claude station: schema is allowed.
})
if (!spine) throw new Error(
  'spine station failed — refusing to continue without it.',
)

const results = await pipeline(
  UNITS,
  (u) => agent(codexBrief(u), {
    label: `find:${u.key}`,
    agentType: 'codex-wrapper', // NEVER pass schema to this station.
  }),
  (raw, u) => raw
    ? agent(extractAndJudge(raw), {
        label: `verify:${u.key}`, model: 'opus', schema: RESULT_SCHEMA,
      }).then((v) => ({ u, v }))
    : { u, v: null },
)

const gaps = [] // Pair every filter(Boolean) with gap accounting below.
// Aggregate; log() every dropped, filtered, or skipped result and why.
const review = await workflow('review-station', {
  paths, request, author, tier,
})
return { ...summary, coverageGaps: gaps, review } // Verdict rides the return.
```

Pattern map: meta literal → the exported `meta` object at the top of `pr-review.js`;
args throw → the required-input validation below its Inputs comment; lane-rationale
comments → the lane-assignment comment block after the review-file constants;
pipeline-not-parallel reasoning → the comment immediately before the review
pipeline; light dispatch → the Codex lens prompt in the pipeline's first stage; gap
accounting → the confirmed/dropped/gaps aggregation and `COVERAGE GAP` logging before
Render; reviewer routing → the family-disjointness author-routing comment near the
top of `review-station.js`.

**Copying warning:** `pr-review.js` has no review-station tail because it is the sole
fixed-graph member. The script being emitted is not; it always ends with the tail.

## Station rules

### Pin every station

Every Claude `agent()` call pins `model`; every Codex call pins
`agentType: 'codex-wrapper'`. Do not rely on ambient defaults.

### Codex wrapper: prose out, Claude structure next

NEVER pass a `schema` to a codex-wrapper station. “I need structure and the schema
is small” is not an exception: schema kills the wrapper mid-supervision. Codex
returns prose; the adjacent Claude station extracts it. Fold extraction and judgment
into that station when Claude already follows, as the verify station does in
the second stage of `pr-review.js`'s review pipeline. Add a dedicated structurer only
when no Claude station already follows.

A light dispatch names the chair-owned launcher flags: `--mode`, `--model`,
`--workspace`, and optionally `--tier`. When the dispatch is meant to continue the
standing session, it also names the persistence flags `--persist`, `--resume`, and
`--resume-from-pointer`. Do **not** add `--effort`; the launcher derives it. Point to
CLAUDE.md §6 and `~/.claude/agents/codex-wrapper.md` for launcher semantics rather
than copying their tables.

Each Codex brief is self-contained. “Per the plan” and “as discussed” are dead
references because Codex has no plan. Paste the governing content into the brief.
Use these named slots, in order:

```text
OBJECTIVE:
WORKSPACE + PATHS:
WRITE SCOPE:
PROHIBITIONS:
CONSTRAINTS:
VERIFICATION:
SKILL: <named superpowers skill>
```

The objective states the goal; workspace and write scope state the box; verification
contains a mechanically checkable acceptance criterion. If no criterion can be made
writable, make the station an investigation whose acceptance is a findings brief.
The dispatch does not prescribe implementation steps: the worker owns the approach
inside the box. Prescribe the HOW only where it is load-bearing—an integration
landmine, an existing convention, or required sequencing—and say why that HOW is
load-bearing.
Inside a fan-out, a brief that needs a sibling's output is not a fan-out unit; it is
the next pipeline stage.

Every Codex brief contains this sentence verbatim:

> If you find a contradiction — between this brief and the code, between two requirements, or between the brief and observed behavior — STOP and report it in your result. Do not resolve it, even when the resolution seems obvious. A reported contradiction is a successful outcome of this dispatch.

Concurrent Codex stations against one workspace are deliberately cold: racing a
standing session corrupts it, as the no-persist/no-resume warning in `pr-review.js`'s
Codex lens prompt explains. Say why in a comment.

### Write parallelism

The launcher snapshots the whole tree, not each station's file list. Therefore the
disjointness unit is the tree: concurrent implementation dispatches in the same repo
use worktrees, without exception. “Our files don't overlap” is not sufficient;
non-overlapping file lists still corrupt attribution when the snapshot unit is the
repository tree.

## Control flow

`pipeline()` is the default: each item flows through its stages independently,
without waiting for its siblings. Use `parallel()` only for one genuine cross-item
need: deduplication across the full set, early exit when the full-set count is zero,
or comparison of findings against one another.

Every `parallel()` carries a one-line comment naming which of those three applies.
If that comment cannot be written, use a pipeline. Flattening or mapping results is
not a barrier reason; do it inside a stage.

Failure handling follows station role. A spine station, whose output every later
station consumes, throws on failure. A fan-out member degrades into explicit gap
accounting. Never degrade a spine into a coverage gap.

## Failure visibility

Null-check every station result. Every `filter(Boolean)` is paired with a companion
loop that names what fell out, logs it as a `COVERAGE GAP`, and carries it into the
return value. A bare filter turns a dead lens into apparently clean coverage.

Use `log()` for every dropped, filtered, or skipped finding and include its reason.
Return `coverageGaps` or `debt` so a partial run cannot present a clean summary.
The confirmed/dropped/gaps aggregation and `COVERAGE GAP` logging before Render in
`pr-review.js` are the reference implementation. A failed station is never a pass.

## Review tail

End every emitted script with:

```js
const review = await workflow('review-station', {
  paths, request, author, tier,
})
return { ...summary, review }
```

Set `author: 'chair'` if any chair-authored write is in the reviewed set. Use
`author: 'codex'` only when the entire set is Codex-authored: `author` selects the
reviewer, and a false Codex attribution can let a lane approve its own work.

“The graph already has a Claude verify station” does not remove the tail. In-graph
verify stations are build stations; the tail is the cross-review edge. Only
human-curated fixed-graph members skip it, and this emitted script is not on that
list.

## Pre-emission checklist

- [ ] `meta` is a pure literal; no variable, call, spread, or template expression.
- [ ] `meta.phases` entries exactly match the `phase()` calls.
- [ ] Every required arg appears in the plan's invocation line with type and source.
- [ ] Replay-sensitive time and randomness enter through validated args; no `Date.now()`, `new Date()`, or `Math.random()`.
- [ ] The chair's syntax-check instruction wraps the body; it does not rewrite the script.
- [ ] Every Claude station pins `model`; every Codex station pins `agentType`.
- [ ] No codex-wrapper station receives `schema`; adjacent Claude extracts and judges.
- [ ] Every Codex brief is self-contained and has goal, box, prohibitions, constraints, verification, and skill.
- [ ] Every Codex brief contains the canonical contradiction clause verbatim.
- [ ] Light dispatches name only the four chair-owned flags and never add `--effort`.
- [ ] Concurrent cold dispatches say why they do not race a standing session.
- [ ] Same-repo concurrent implementation writes use separate worktrees.
- [ ] Every `parallel()` has a one-line approved barrier justification.
- [ ] Every failed fan-out member and every filtered or skipped result is logged and returned as coverage gap/debt.
- [ ] Every spine failure throws instead of degrading.
- [ ] The review-station tail is present, with truthful `author` and its verdict in the return.

## Boundaries

- Workflow-tool API signatures belong to the runtime documentation.
- Launcher modes, tier values, allowlists, effort, and tokens belong to CLAUDE.md §6
  and `~/.claude/agents/codex-wrapper.md`; this skill names only the four flags.
- Whether a script is owed and tier routing belong to CLAUDE.md §2/§5.
- Review-station internals belong to `/home/xzat/.claude/workflows/review-station.js`.
- Superpowers skill-to-task mapping belongs to CLAUDE.md §6; briefs only name `SKILL:`.
- Sandbox and clean-tree facts belong to `codex-wrapper.md`; consult them when
  assigning implementation lanes.
- Drift-check the skeleton against `/home/xzat/.claude/workflows/pr-review.js` and
  `/home/xzat/.claude/workflows/review-station.js`.

## Premises and risks

The design reports as verified: both live scripts and their idioms; the house skill
format; the current numbered CLAUDE.md §4–6; and no overlapping workflow-authoring
skill in this repository.

Taken on trust, because they were not verified against runtime source: meta static
extraction; schema killing codex-wrapper; and resume replay divergence under ambient
time. These agree with live-script comments and CLAUDE.md §5.

The raw-file `node --check` premise has now been wrong **twice**, in opposite
directions, and is settled above by experiment rather than reasoning. It was first
written as "fails by design" (false), then corrected to "passes under CommonJS rules,
so a weak check" (also false — the CJS parse never reaches the body). Ground truth,
probed on Node v26.4.0: the check exits 0 unconditionally for any file whose first
module-syntax token precedes the error, which is every workflow script.

Draw the general lesson from it. Claims about what a *tool* does are cheap to test and
expensive to reason about; two careful readers got this one wrong from first principles
before anyone ran it. Test tool behaviour, never derive it.

Also taken on trust is the load-bearing strict reading of write parallelism: file-level
disjointness within one repository still corrupts because the snapshot unit is the
tree. The rule above uses that reading because it is safe in both worlds, but the
chair should cheaply probe launcher behavior before this skill ships; the strict
reading forbids parallelism that a lax implementation might permit.

The incomplete skeleton will still anchor authors. Treat its idioms as canonical
and update them whenever either live drift-check script changes.
