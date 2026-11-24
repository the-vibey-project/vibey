# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stdio MCP server for the client's tests: newline-delimited JSON-RPC, behaviour by argv[1].

- `ok`: answers `initialize` with the version it was offered, lists one tool (`echo`) and echoes
  a call's arguments back as text.
- `hang`: never answers anything, `initialize` included, and ignores the end of its input.
- `exit`: exits with code 3 before reading anything.
- `error`: as `ok`, but every `tools/call` is answered with a JSON-RPC error.
- `paged`: `tools/list` comes in two pages, `a` then `b`, joined by `nextCursor`.
- `old-protocol`: answers `initialize` with `2024-11-05`, the oldest supported version.
- `unknown-protocol`: answers `initialize` with `1999-01-01`, a version nobody speaks.
- `spawns-child`: starts a child that sleeps, both holding the inherited descriptor named by
  argv[2], so the test sees the end of that pipe only once both have exited. A call to `pid`
  answers the child's pid. At the end of its input it keeps running, so only the process-group
  kill ends either.
- `echo-env`: as `ok`, but a call answers the names in its environment, sorted, one per line.
  Never a value.

Not collected by pytest: the name does not start with `test_`.
"""

import json
import os
import subprocess
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "ok"


def send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def answer(request_id: object, result: dict) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "result": result})


if mode == "exit":
    sys.exit(3)

child = None
if mode == "spawns-child":
    inherited = int(sys.argv[2])
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(600)"],
        pass_fds=(inherited,),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

for raw in sys.stdin:
    request = json.loads(raw)
    method, request_id = request.get("method"), request.get("id")
    if request_id is None or mode == "hang":
        continue
    params = request.get("params") or {}
    if method == "initialize":
        offered = params.get("protocolVersion")
        version = {"old-protocol": "2024-11-05", "unknown-protocol": "1999-01-01"}.get(
            mode, offered
        )
        answer(request_id, {"protocolVersion": version, "capabilities": {"tools": {}}})
    elif method == "tools/list":
        if mode == "paged":
            if params.get("cursor") == "page-2":
                answer(request_id, {"tools": [{"name": "b", "inputSchema": {"type": "object"}}]})
            else:
                tools = [{"name": "a", "inputSchema": {"type": "object"}}]
                answer(request_id, {"tools": tools, "nextCursor": "page-2"})
        else:
            tools = [{"name": "echo", "description": "Echo.", "inputSchema": {"type": "object"}}]
            answer(request_id, {"tools": tools})
    elif method == "tools/call":
        if mode == "error":
            error = {"code": -32000, "message": "exploded"}
            send({"jsonrpc": "2.0", "id": request_id, "error": error})
        elif mode == "echo-env":
            names = "\n".join(sorted(os.environ))
            answer(request_id, {"content": [{"type": "text", "text": names}]})
        elif mode == "spawns-child" and child is not None:
            answer(request_id, {"content": [{"type": "text", "text": str(child.pid)}]})
        else:
            text = json.dumps(params.get("arguments"), sort_keys=True)
            answer(request_id, {"content": [{"type": "text", "text": text}]})

if mode in {"hang", "spawns-child"}:
    time.sleep(600)
