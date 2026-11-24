# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two ways an MCP request fails (SP-LOOPS Phase 5, R6).

Neither ends a run: the tool dispatcher turns both into a tool error the model reads. Their
messages name the server and the method, never an argument, an argv tail or an environment
value. Exception types only (ADR-0016 exempts them from the interface rule).
"""


class McpUnavailable(RuntimeError):
    """The server cannot be reached: it would not start, spoke an unknown protocol version,
    closed its stream, did not answer in time, or is out of restarts or calls for this run.
    Its session is dead."""


class McpToolError(RuntimeError):
    """The server answered with a JSON-RPC error. Its session is still alive."""
