---
name: "defi-worktree-setup"
description: "Use when setting up a defi-com monorepo git worktree — for Monday.com item/ticket (feature) work from a monday.com pulse/board URL, for GitHub PR review (single or multiple PRs), or for branch-based prep."
---

# DeFi Worktree Setup

## Overview

Set up defi-com `monorepo` review and ticket worktrees consistently: correct base branch, Monday.com/GitHub context, env copy, dependency install, bounded baseline, and local handoff notes.

This skill layers repo-specific convention on top of generic worktree discipline. If available, invoke `superpowers:using-git-worktrees` first.

## Workflow

1. Start from `/home/xzat/defi/monorepo` unless the user explicitly names another repo.
2. Read current branch/worktree state:
   - `git status --short --branch`
   - `git worktree list --porcelain`
   - relevant `git branch --list ...`
3. Gather context before creating anything:
   - PR review: fetch/read the GitHub PR metadata and PR head.
   - Monday.com item: from the item URL (`https://<org>.monday.com/boards/<boardId>/pulses/<pulseId>`) take the pulse ID (to fetch the item) and board ID. Read the item via the Monday.com MCP (`mcp__claude_ai_monday_com__*`, e.g. `all_monday_api` with GraphQL `items(ids:[<pulseId>]){ name column_values { id text } }`) and pull its **EDEF/TDEF/STDEF item key** from the custom-key column (Epic→EDEF, Task→TDEF, Sub-task→STDEF), plus name, status, parent/subitems, and any requested base branch. That key — not the pulse ID — is what worktrees are named after (below). If the key column shows a bare number instead of an `EDEF/TDEF/STDEF-<n>` key, the board's Item-ID column hasn't been switched from ID-number to Custom-key in the UI — flag that rather than naming with the raw pulse ID. Monday has no git-branch field — derive the branch from the convention below.
   - Multi-PR review: fetch each PR head into `refs/remotes/origin/pr/<num>`.
4. Choose names using local convention:
   - Single PR review path: `/home/xzat/defi/monorepo-pr-<num>-review`
   - Multi-PR review path: `/home/xzat/defi/monorepo-prs-<nums>-review`
   - Monday item path: `/home/xzat/defi/monorepo-<key>` — `<key>` is the lowercased EDEF/TDEF/STDEF item key (e.g. `monorepo-edef-12`, `monorepo-tdef-345`, `monorepo-stdef-6789`)
   - PR branch: `review/pr-<num>` or `review/prs-<nums>`
   - Ticket branch: `feature/<key>` (e.g. `feature/tdef-345`)
5. Create the worktree from the requested base:
   - PR review usually starts from the PR head or fresh `origin/dev`, depending on the review goal.
   - Ticket work starts from the ticket branch if it exists, otherwise from the requested base branch.
   - If the base branch moves during setup and the new branch has no work yet, move/rebase the setup branch to the new base. Never reset user work.
6. Copy local env files from the source/base worktree, preserving relative paths:
   - `.env`, `.env.local`, `.envrc`, `.env.keys`
   - search below the repo while excluding `.git` and `node_modules`.
7. Run `bun install`.
   - If Bun only adds `"configVersion": 0` to `bun.lock`, remove that setup-only noise.
8. Run a bounded baseline:
   - `timeout --kill-after=10s 180s bash -lc 'TURBO_UI=false bun run test'`
   - Known baseline caveat: `@deficom/decentralised-icons:test` is a live E2E/Vitest suite and may hang or time out after other packages pass. Do not call the baseline passing if this happens.
   - Always verify no leftover `turbo`, `vitest`, or `bun run test` process remains for the worktree.
9. Record handoff state:
   - `BRANCH-NOTES.md` in the worktree root.
   - `~/ACTIVE-WORK.md` with one line for the worktree, branch, and current status.

## Review Guardrails

For PR reviews in defi-com repos, local markdown is the canonical deliverable. Use `~/defi/misc/reviews/review-PR-<num>.md` unless instructed otherwise. Never post GitHub review bodies or comments without explicit per-session approval and agreed posting shape.

## Common Checks

- Confirm `BRANCH-NOTES.md` and `/superpowers/` are ignored before relying on them.
- Confirm Git identity uses a verified email: `axatbhardwaj@outlook.com` or `axatbhardwaj@gmail.com`.
- Report exact SHAs for the base branch and fetched PR heads.
- If validation is blocked by the known E2E timeout, say that plainly and preserve the clean worktree.
