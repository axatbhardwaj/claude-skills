# Claude Skills

Custom Claude Code skills for personal use.

## Skills

| Skill | Description |
|-------|-------------|
| `testing` | Adversarial test-gap analysis and focused regression-test workflow |
| `teaching-deep-understanding` | Teach a change or session for genuine, incremental understanding — mastery-gated, Socratic, with a dark-HTML understanding checklist |

## Usage

### Option 1: With Haoshoku

> **Note:** Haoshoku only supports CachyOS and Debian. For other distros, use Option 2.

Install [haoshoku](https://www.npmjs.com/package/haoshoku) and add this repo to `~/.haoshoku.json`:

```bash
npm install -g haoshoku
```

```json
{
  "skillSources": [
    "https://github.com/axatbhardwaj/claude-skills.git"
  ]
}
```

Then sync skills:

```bash
haoshoku --skills
```

### Option 2: Manual Copy for Claude Code

Clone this repo and copy the skills to your Claude config:

```bash
git clone https://github.com/axatbhardwaj/claude-skills.git
cp -r claude-skills/skills/* ~/.claude/skills/
mkdir -p ~/.claude/agents
cp claude-skills/agents/*.md ~/.claude/agents/
```

### Option 3: Manual Symlink for Codex

Codex reads Agent Skills from `~/.agents/skills` or `.agents/skills` in a repo.
Symlink the same skill directory:

```bash
mkdir -p ~/.agents/skills
ln -sfn "$(pwd)/claude-skills/skills/testing" ~/.agents/skills/testing
```

The skill includes `agents/openai.yaml` metadata for Codex and Claude-specific
adapter notes that Codex can ignore.

## Notes

The `testing` skill borrows ideas from
[clawpatch](https://github.com/openclaw/clawpatch): persisted state handoffs,
bounded context, evidence-backed findings, explicit test-writing, and
revalidation. Use clawpatch directly for broad automated review and patch
tracking; use this skill when the goal is specifically test-gap analysis.

## License

MIT
