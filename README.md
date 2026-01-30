# Claude Skills

Custom Claude Code skills for personal use.

## Skills

| Skill | Description |
|-------|-------------|
| `testing` | Run tests and validate coverage gaps |

## Usage

Add this repo to `~/.haoshoku.json`:

```json
{
  "skillSources": [
    "https://github.com/xzat/claude-skills.git",
    "https://github.com/solatis/claude-config.git"
  ]
}
```

Then run `haoshoku --skills` to sync skills.
