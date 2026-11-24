# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stdlib MCP client over the shared JSON-RPC peer (SP-LOOPS Phase 5, R2).

`McpSession` speaks MCP to one server through a transport (`StdioTransport` for a `local`
server). `McpSessionPool` holds one session per server for one run: it starts each on first use,
restarts a dead one a bounded number of times, keeps the remote call budget and closes them all
when the run ends. `protocol` holds the protocol versions, shared with vibey's own MCP server so
both ends speak from one list. Deliberately free of imports: each module is imported by its own
name.
"""
