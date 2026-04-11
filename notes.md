# Notes

## MCP Servers (Model Context Protocol)

MCP stands for Model Context Protocol — an open standard that lets Claude connect to external tools and data sources, acting like a plugin system.

By default Claude Code can read files, run bash commands, search code, etc. MCP servers extend that with new capabilities.

**What we used:** The Playwright MCP server gave Claude browser control tools — `browser_navigate`, `browser_take_screenshot`, and `browser_evaluate` — allowing Claude to interact with a live browser directly instead of asking the user to describe what they see.

**Other examples of MCP servers:**
- Gmail — read/send emails
- Google Calendar — check/create events
- Databases — query Postgres or SQLite
- Slack — post messages

**How they work:**
1. An MCP server runs as a separate process on your machine (or remotely)
2. Claude Code connects to it via the `/mcp` command or settings
3. The server exposes tools that Claude can call just like any built-in tool

## Setting Up a Custom Skill (/log command)

Custom slash commands in Claude Code are called **skills** and must follow a specific folder structure to be recognized.

**Correct structure:**
```
.claude/skills/<skill-name>/SKILL.md
```

**SKILL.md requires two parts:**
1. YAML frontmatter (between `---` markers) with fields like `name`, `description`, and `disable-model-invocation: true` to only trigger on explicit use
2. Markdown instructions telling Claude what to do when the skill is invoked

**What didn't work:**
- `.claude/commands/log.md` — the old format, no longer supported

**Important:** Claude Code only scans for skills on startup — a full restart is required after creating a new skill for it to be recognized.
