# vibey-runners-common

Shared `application/interfaces` and `application/usecases` for the AI
coding-agent session-runner family: `claudeloop` (the original), and its
retarget `codexloop`.

Only the protocols and use-case orchestrations that genuinely converge
across the family live here. Each runner still owns its own domain layer,
its own vendor-specific concrete implementations (in `infrastructure/`),
and any interface or use case whose actual shape diverges enough between
runners that forcing a shared version would misrepresent one of them —
those stay local to the runner that needs them. See each runner's own
`application/interfaces/` and `application/usecases/` packages, and the
monorepo-merge extraction notes, for what was and wasn't pulled in here
and why.

## `jsonrpc/`

A stdlib JSON-RPC 2.0 implementation: the line codec (`codec.py`,
`JsonRpcCodec` and its `CODEC` singleton), the error vocabulary
(`errors.py`: the standard codes, `RpcError`, `PeerClosed`,
`PeerCancelled`) and a bidirectional asyncio peer (`peer.py`,
`JsonRpcPeer`), each with its interface under `jsonrpc/interfaces/`.

It is shared because more than one speaker of the wire format lives in the
family: vibey's MCP server (`vibey mcp`) and its Agent Client Protocol agent
(`vibey acp`), and the local runner's MCP client (SP-LOOPS Phase 5). One
implementation keeps their bytes from drifting apart; vibey holds no copy of
its own (`tests/meta/test_one_jsonrpc_peer.py`). Like the rest of this
package it imports nothing outside the standard library, so vibey's
application layer may import `errors` (ADR-0017), and the package's
`__init__.py` is empty so that doing so pulls in no `asyncio`.

## `mcp/`

A stdlib MCP client over that peer (SP-LOOPS Phase 5). `McpSession` speaks
MCP to one server through a transport; `StdioTransport` starts a `local`
server as a child that leads its own process group, and closing it closes
the server's stdin, waits a grace period, then kills the whole group.
`McpSessionPool` holds one session per server for a run: it starts each on
first use, restarts a dead one a bounded number of times, keeps each remote
server's call budget, and closes them all when the run ends without ever
raising. `protocol.py` holds the protocol versions, which vibey's own MCP
server imports, so both ends speak from one list. A `local` server's argv
comes from `capabilities/scrubbed_launch.py` (`ScrubbedLaunch`), which
claudeloop's MCP config uses too.
