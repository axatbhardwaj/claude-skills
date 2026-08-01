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
The harness delivers `args` as a JSON string to top-level `Workflow({name, args})`
invocations, while nested `workflow()` calls pass a real object, so scripts must tolerate both.

```js
export const meta = { // PURE LITERAL: statically extracted before the body runs.
  name: 'workflow-name',
  description: 'What this workflow does.',
  whenToUse: 'When this graph is the right execution shape.',
  phases: [{ title: 'X', detail: 'Build the spine' }],
} // A variable, call, spread, or template expression here fails parse.

let a = args || {}
if (typeof a === 'string') {
  try {
    a = JSON.parse(a)
  } catch (e) {
    throw new Error(
      `args arrived as a non-JSON string (the harness marshals args to a string): ${e.message}`,
    )
  }
}
if (a === null || typeof a !== 'object' || Array.isArray(a)) {
  throw new Error(
    `args resolved to ${a === null ? 'null' : Array.isArray(a) ? 'an array' : typeof a}, not an object — the harness must pass object-shaped args`,
  )
}
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

Parallel write stations still require isolated worktrees or serial execution;
disjoint file scopes alone are insufficient, but the reason has changed. For
`--mode implementation`, the launcher takes a per-workspace `flock`. A second
concurrent dispatch into the same workspace is refused with
`blocked_concurrent_dispatch` (exit 4) and never runs at all. A fanned-out write
station that collides on a workspace therefore no longer gets corrupted attribution;
it loses that unit of work outright unless the chair reads the blocked status and
redispatches. That is a different failure mode to design around, not a non-issue.

Serial implementation dispatches may start from a dirty tree. After the lock is
acquired, the launcher fingerprints the pre-run worktree contents and index entries,
reports that starting state as `pre_existing_dirty_state`, and subtracts unchanged
baseline paths from `actual_changes`. A stream therefore no longer needs a committed
baseline before it can be dispatched.

The lock and baseline subtraction do not make `actual_changes` trustworthy under
concurrency in general. Any writer the lock does not cover—a review-mode (read-only)
dispatch running concurrently, the chair writing under a §4 carve-out, a human
editor, or a build process—can still be folded into the running dispatch's attributed
`actual_changes`. Only concurrent implementation dispatches into the same workspace
are mutually exclusive under the lock; other concurrent writers are not covered.
Use worktrees or serialization, without exception. Refuse “our files don't overlap”:
it may be true of the bytes, but it is still insufficient.

## Executor roster

Treat the Codex executor roster as capacity to allocate while designing the graph.
Choose the lane by task shape:

- **sol** — high-uncertainty implementation and every code review.
- **terra** — bounded implementation whose shape is already specified.
- **luna** — read-only scouting, reports, and exploration. Editing and implementation
  are not currently available to luna.

This is only the planner's lane-selection view. CLAUDE.md §6 and `codex-wrapper.md`
are authoritative for the launcher's complete model allowlist, effort tokens, and
related mechanics.

Name the executor for each Codex station in addition to following the Pin every
station rule. A reviewer must be able to count planned stations by lane from the
emitted graph; station pinning fixes how each dispatch runs.

The launcher's workspace-keyed implementation lock is real; this section describes
its shape without hard-coding a runtime ceiling. A second implementation dispatch
into the same checkout is refused regardless of which executor it uses. Parallel
writes need distinct worktrees or the launcher's worktree-on-contention option. The
Workflow tool also caps concurrent agents; consult its runtime documentation for the
current limit. This makes the roster a resource constraint on the graph, not a choice
among labels.

## Parallelism: scope-driven concurrency

**Two stations may run concurrently only when their write scopes are disjoint.**
After that scope test, apply the separate workspace and launcher requirements in
the earlier Write parallelism section; this section does not weaken them.

A plan that serializes independent streams is a defective plan, not a property of
the work. Plan review already occurs on the relevant tiers, so fan-out is reviewable:
a reviewer may reject a sequential plan when its declared write scopes are disjoint.

For example:

> Station A writes `src/account.js` and tests `tests/account.test.js`.
> Station B writes `src/wallet.js` and tests `tests/wallet.test.js`.
> These scopes are disjoint, so they may run in parallel.
>
> But Station C writes `tests/` for all test fixtures. Stations A and B also write
> test files under `tests/`, so A–C and B–C collide even though A and B do not. The
> fact that their production files are disjoint is insufficient.

A shared test directory is itself a collision until the plan narrows the scope to
specific files. Do that narrowing before using the pipeline or a fan-out to express
the resulting independent streams.

## Feasibility spikes

A feasibility spike is a fourth move available to the planner when reading cannot
settle a premise: whether a file can be replaced safely while in use, whether an
interface accepts a given shape, or whether a guard fires when the thing it guards
breaks. It is a bounded, throwaway investigation with these rules:

- **Output is evidence, not code.** Its acceptance is an answer with proof, never a
  merged change.
- **Write scope is scratch only.** It never touches the repository, which makes it
  parallel-safe by construction because its scope is disjoint from all production
  work.
- **Code is discarded.** A spike whose code gets merged has smuggled unreviewed work
  into the tree.
- **Executor follows probe shape.** A spike is bounded and throwaway; it does not
  need sol. Use terra when the probe writes scratch; use luna only for read-only
  scouting, reports, or exploration.
- **It blocks only its dependents.** A spike blocks the stream that needs its answer,
  not the full plan.

The plan states in advance what each possible answer changes. A spike whose result
would not alter the plan is not worth running.

For example, a spike can test whether a test asserts an intermediate value rather
than the final one. It copies the program under test into scratch, breaks exactly one
line, and runs the suite against that copy to see whether the failure is detected.
The pass-or-fail answer determines whether the test needs refactoring; the copied
program is discarded after the answer. Route only that dependent test stream through
the result, using the existing control-flow rules for everything else.

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
- [ ] Light dispatches name only the chair-owned flags (`--mode`, `--model`, `--workspace`, optional `--tier`, and—when continuing the standing session—`--persist`, `--resume`, or `--resume-from-pointer`) and never add `--effort`.
- [ ] Concurrent cold dispatches say why they do not race a standing session.
- [ ] Same-repo concurrent implementation writes use separate worktrees.
- [ ] Every `parallel()` has a one-line approved barrier justification.
- [ ] Every failed fan-out member and every filtered or skipped result is logged and returned as coverage gap/debt.
- [ ] Every spine failure throws instead of degrading.
- [ ] The review-station tail is present, with truthful `author` and its verdict in the return.
- [ ] Claude stations pin `model`, Codex stations name their executor, and workflow stations name the nested workflow.
- [ ] Every station states its write scope.
- [ ] Independent streams are actually parallel — a sequential plan over disjoint scopes is a defect.
- [ ] Spikes write only to scratch, and their output is discarded.

## Boundaries

- Workflow-tool API signatures belong to the runtime documentation.
- Launcher modes, tier values, allowlists, effort, and tokens belong to CLAUDE.md §6
  and `~/.claude/agents/codex-wrapper.md`; this skill names the chair-owned flags,
  including the persistence flags when continuing a standing session.
- Whether a script is owed and tier routing belong to CLAUDE.md §2/§5.
- Review-station internals belong to `/home/xzat/.claude/workflows/review-station.js`.
- Superpowers skill-to-task mapping belongs to CLAUDE.md §6; briefs only name `SKILL:`.
- Sandbox and baseline-attribution facts belong to `codex-wrapper.md`; consult them when
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

Write parallelism is no longer taken on trust; it is settled by experiment. Two Codex
implementation dispatches ran concurrently in one git repository with disjoint
declared write scopes, one owning `a.txt` and one owning `b.txt`. The bytes were
perfect: each file received exactly its owner's line, with no interleaving, so
file-level disjointness is safe for the writes themselves. But both reports'
`actual_changes` named both files—bidirectional attribution corruption—and both
wrapper reports manufactured a scope-violation finding against workers that provably
stayed in scope: each worker's own session diff contained only its file. The cause is
tree-wide `actual_changes` computed at run end plus a start-time-only clean-tree gate,
a TOCTOU race. A few seconds' difference in start time would instead have produced
`blocked_dirty_tree`, so concurrent implementation dispatches into one tree land on a
coin flip between corrupted attribution and a spurious but loud, safer block.

**VERIFIED by subsequent re-probe against the current launcher:** the per-workspace
`flock` now holds. A second concurrent implementation dispatch into the same
workspace is refused with `blocked_concurrent_dispatch` rather than racing, so the
earlier coin-flip-between-corruption-and-block outcome no longer applies to two
concurrent implementation dispatches. It may still apply across dispatch modes and
to review-mode, chair, editor, or build writers that the implementation lock does
not cover, as described under Write parallelism.

Write parallelism is no longer taken on trust; it is settled by experiment. The
current launcher permits implementation dispatches against a dirty tree, fingerprints
the pre-run worktree and index state, reports that state separately, and subtracts
unchanged baseline paths from `actual_changes`. A stream therefore does not need a
committed baseline before dispatch.

The per-workspace `flock` also holds. A second concurrent implementation dispatch
into the same workspace is refused with `blocked_concurrent_dispatch` rather than
racing. Concurrent writers outside that lock may still affect attribution, as
described under Write parallelism.

The incomplete skeleton will still anchor authors. Treat its idioms as canonical
and update them whenever either live drift-check script changes.
