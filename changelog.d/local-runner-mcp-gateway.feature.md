* **The local runner can use your MCP servers:** `gptossloop` and `qwenloop` gain `mcp_list` and `mcp_call`, two
  gateway tools over the stdio servers in `~/.claude.json` and `QWENLOOP_MCP_CONFIG`, never the worktree's `.mcp.json`.
  Two tools rather than every server's own, because a 32k-context model misuses a long tool list. Each call starts
  and stops its server, and every answer is marked untrusted. ADR-0092, #1666.
