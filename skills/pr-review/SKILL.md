---
name: pr-review
description: Full PR review procedure for any repo — local canonical HTML review file, GitHub posting shape and approval rules, round-2 refinement, and post-editing mechanics. Invoke whenever reviewing a pull request or preparing/posting review feedback to GitHub. The never-auto-post rule also lives in global CLAUDE.md; this skill holds everything else.
---

# PR Reviews

Applies to any PR review, any repo. The local review file is the canonical deliverable; the GitHub review is a notification surface.

## Posting rules

- **Never auto-post.** Posting anything to a PR (review body, top-level comment, inline comment, subagent posts) requires explicit per-session user approval — and even then, confirm the *form* (full / medium / specific finding) before posting. If a post happens without approval, delete it rather than edit it.
- **Reviewer models are read-only.** A Codex-lane review runs with `--sandbox read-only`; a Claude review subagent gets no Edit/Write.

## Local file — the canonical deliverable

- Author as dark self-contained HTML via the `html-deliverables` skill: verdict, filterable severity table, strengths, collapsible issues with `file:line` refs + suggested fixes, ground-truth verification appendix.
- Round 2+: append a dated round section to the same file.
- Location: per-repo convention from that repo's project CLAUDE.md (defi-com repos: `~/defi/CLAUDE.md`). No convention yet → confirm a location with the user once, then stay consistent.
- Pre-June-2026 `.md` reviews stay as they are; don't convert.

## GitHub medium shape (when approved to post)

Render from the local file — never paste the whole local review into the GitHub body:
- Verdict + severity table + strengths (3–5 condensed bullets) + issues (one short paragraph per finding: `file:line`, 2–3 sentences, suggested fix as prose) + recommendation.
- Skip: verification appendix, file-read inventory, "couldn't verify" section, multi-line suggested-fix code blocks.
- **No footer link to the local file** — it's gitignored and unreachable by the PR author. If the full review should be shared, attach or publish it through an approved mechanism the user names; otherwise omit any reference to it.
- Single finding needing a verbatim code-block patch → targeted inline review comment on that file/line, not an expanded top-level body.

## Editing after the fact

Trim a posted body with `gh api -X PUT repos/{owner}/{repo}/pulls/{n}/reviews/{review_id}` and a `{body: …}` payload — review state (APPROVED / COMMENT / CHANGES_REQUESTED) survives edits.
