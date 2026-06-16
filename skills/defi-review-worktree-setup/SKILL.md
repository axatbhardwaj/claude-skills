---
name: "defi-review-worktree-setup"
description: "Use when setting up a defi-com monorepo worktree for GitHub PR review, multiple PR review, Monday.com item/ticket work (monday.com pulse/board URL), or branch-based review prep."
---

# DeFi Review Worktree Setup

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
   - Monday.com item: from the item URL (`https://<org>.monday.com/boards/<boardId>/pulses/<pulseId>`) take the pulse/item ID for naming and the board ID for context. Read the item via the Monday.com MCP (`mcp__claude_ai_monday_com__*`, e.g. `all_monday_api` with GraphQL `items(ids:[<pulseId>])`): name, status, parent/subitems, and any requested base branch. Monday has no git-branch field — derive the branch from the convention below.
   - Multi-PR review: fetch each PR head into `refs/remotes/origin/pr/<num>`.
4. Choose names using local convention:
   - Single PR review path: `/home/xzat/defi/monorepo-pr-<num>-review`
   - Multi-PR review path: `/home/xzat/defi/monorepo-prs-<nums>-review`
   - Monday item path: `/home/xzat/defi/monorepo-mon-<pulseId>` (pulse/item ID from the item URL, e.g. `monorepo-mon-2995186593`)
   - PR branch: `review/pr-<num>` or `review/prs-<nums>`
   - Ticket branch: `feature/mon-<pulseId>` (e.g. `feature/mon-2995186593`)
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
