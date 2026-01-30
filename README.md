# Claude Skills

Custom Claude Code skills for personal use.

## Skills

| Skill | Description |
|-------|-------------|
| `testing` | Run tests and validate coverage gaps |

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
    "https://github.com/axatbhardwaj/claude-skills.git",
    "https://github.com/solatis/claude-config.git"
  ]
}
```

Then sync skills:

```bash
haoshoku --skills
```

### Option 2: Manual Copy (All Platforms)

Clone this repo and copy the skills to your Claude config:

```bash
git clone https://github.com/axatbhardwaj/claude-skills.git
cp -r claude-skills/skills/* ~/.claude/skills/
```

## License

MIT
