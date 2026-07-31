---
name: html-deliverables
description: Use when creating any HTML file for a human to read — a report, explainer, spec, plan, review, audit, research write-up, or status page. Applies to every HTML deliverable regardless of project or topic.
---

# HTML Deliverables — the house format

Every HTML file uses dark ground, a role-colored duel palette, mono machine
words, diagrams, and an argument that lands cold. Copy `template.html`; do not
restyle from scratch.

## The contract

Every page IS, in order:

1. `<title>` + the `dvandva-artifact-meta` JSON script block (schema, type, title, date, basis).
2. The `:root` token block from the template, **verbatim** — including the
   literal `color-scheme: dark;` declaration.
3. An orientation `<section>` immediately after `<header>` and before any
   verdict section; follow the Content contract.
4. Sections, each opened by an `.eyebrow` mono label + an `h2` thesis.
5. At least one `figure` per structural idea: hand-authored SVG + `figcaption`.
   Anything you would sketch on a whiteboard is drawn, not listed.
6. Prose in system sans at ≤68ch; every state name, command, field, and exit
   code in mono (`code` or `.st`).
7. A `.foot` stamp line: what the page reflects and as-of what version/commit.

## Tokens (never improvise replacements)

| Token | Hex | Role |
|---|---|---|
| `--ground` | `#0b0f14` | page (blue-biased near-black) |
| `--panel` / `--panel2` | `#121821` / `#182130` | cards, figures |
| `--line` | `#26303e` | borders |
| `--ink` / `--dim` / `--faint` | `#dce4ee` / `#8a97a8` / `#5c6774` | text tiers |
| `--vadi` | `#34d399` | actor A / primary accent |
| `--prat` | `#a78bfa` | actor B / opposing accent |
| `--team` | `#5ca9ff` | shared / both |
| `--human` | `#e0a63d` | the human, pauses |
| `--seal` | `#46c26a` | success, gates, done |
| `--stop` | `#ff6a5e` | failure, dead ends |

Map the subject's opposition onto `--vadi`/`--prat` (writer/reviewer,
client/server, before/after). Semantic colors never decorate. `--vadi` is
lighter/cooler than `--seal`; keep gates as `--seal`-stroked rects so the
greens never share a shape.

## Components (all defined in the template)

`.eyebrow` section label · `.chip` fact strip · `.cards` grid of `.card` ·
`.lane` (route/option card with colored dot + mono `.route` line) ·
`figure > svg + figcaption` · `.source` evidence line · sticky `nav` only when
the page exceeds ~3 screens · `.baton-rail` only on editorial pages (behind
`prefers-reduced-motion`).

## Diagram rules

- Hand-authored SVG; geometric shapes only (rects, circles, lines, short
  paths). `svg text` is mono. Wide `viewBox`, `min-width` on the svg, and the
  `figure` scrolls (`overflow-x:auto`) — the page body never scrolls sideways.
- Node fill = owning actor's token. Dashed stroke = loop, optional, or
  fallback. `--seal`-stroked rect = gate/terminal.
- Multiple routes through shared stages → draw ONE comparative map: stages as
  columns, routes as horizontal lines stopping only at their stations
  (transit-map idiom). Don't draw N separate near-identical flowcharts.
- Label sparingly at 8.5–10px `--dim`/`--faint`; a legend when >2 encodings.

## Copy

Eyebrows are lowercase mono, ≤5 words. `h2`s state a thesis, not a topic
("Pick a profile: every path, one map", not "Profiles"). Captions add the one
insight the drawing can't say. Real content only — never lorem.

## Content contract

- The orientation section's first line names the reader and what they can be
  assumed to know. Gloss or cut every term outside that set.
- Its first 150 words state the situation, prompting problem, and what changes
  with the answer. The header `h1`/`.thesis` are a stance, not orientation, and
  do not satisfy item 3.
- Lead every paragraph with its claim; support it afterwards. Never open with
  evidence and arrive at the point last.
- Keep two registers apart. Prose carries the argument. Evidence — file:line
  refs, addresses, hashes, byte counts, commit SHAs — goes in `.source` lines,
  tables, and figcaptions. Paragraphs read aloud without citation stops.
- Gloss every term of art at first use, headings included.
- Order sections by the reader's questions: what is this, why now, what is the
  answer, what does it cost, what is still unknown — never by evidence category
  or work order.
- Every verdict callout or box stands alone: it makes sense when read alone.
- A correction round may not increase prose word count: after ≤ before.
  Put precision in `.source` lines or table cells; cut elsewhere first.
- Before writing, record target word count and section count in the template's
  orientation budget comment. Cut what the reader does not need—appendix,
  linked file, or gone; never shrink it. If it cannot fit, make two pages.

## Verify & publish

- Hand the file alone—no conversation, brief, or summary—to a no-context reader
  (a subagent given only its path). Ask: (1) what is this about? (2) what is the
  conclusion and what does it cost? (3) what happens next? Pass only if all
  three answers are correct; wrong answers are page defects, not the reader's.
- If `dvandva` 3.x is installed, `dvandva lint artifacts <file>` must pass.
  Otherwise keep the meta block + `color-scheme: dark;`.
- For claude.ai Artifacts, strip the doctype/html/head/body skeleton; keep
  `<title>`, style, and body content.

## Common mistakes

| Mistake | Fix |
|---|---|
| Ad-hoc palette ("looks dark enough") | Tokens verbatim; identity comes from the duel pair |
| Structure described in bullets | Draw it; prose annotates the figure |
| One accent color everywhere | Ownership/opposition mapped to `--vadi`/`--prat` |
| Figures without `figcaption` | Every figure carries its insight line |
| Page scrolls sideways on mobile | Wide content scrolls inside its own container |
| Prose written to survive review | Write for the reader; precision goes in the evidence register |
| Paragraph opens with citations and ends with the claim | Claim first, evidence after |
| "Looks great, couldn't follow it" | The cold read is not optional |
