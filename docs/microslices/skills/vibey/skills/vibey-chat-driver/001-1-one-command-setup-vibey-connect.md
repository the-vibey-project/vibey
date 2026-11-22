---
id: skill-1-one-command-setup-vibey-connect-9fa75fbd59
purpose: 1 one command setup vibey connect
source: src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver/SKILL.md
requires: []
links: ["skill-2-security-boundary-the-scoped-agent-principal-046fb6537a"]
---

## 1. One-Command Setup (`vibey connect`)

Register `vibey mcp` with your host clients:

```bash
vibey connect          # shows the plan (create / update / unchanged), backs up existing files, merges idempotently
vibey connect --yes    # non-interactive approval
vibey connect --list   # list supported client IDs (claude_code, claude_desktop, codex, cursor, vscode, gemini_cli, zed)
```

Every entry runs the running install's own `vibey` by absolute path, never one found on `PATH`. In the person's own user-level configs an existing `vibey` entry keeps their `env`, other keys and extra flags; in a project's `.mcp.json` or `.vscode/mcp.json` (the repository's file) only the exact canonical entry counts, and anything else is replaced whole. After the plan, `vibey connect` lists the surfaces of the clients it planned, and `vibey doctor` (its `llm-tooling` section) those of every installed client -- `acp-agent`, `mcp-server`, `skill`, `plugin` -- as present, missing (with the exact command that fixes it) or not applicable.

Or install via the Claude Code plugin marketplace:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install vibey@vibey
```

 When the first MCP tool call runs, `vibey mcp` connects to the local hub (`<state_dir>/serving.json`) and automatically runs `vibey hub start` if no hub is serving yet.

---
