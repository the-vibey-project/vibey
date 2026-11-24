# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stdio MCP server for tests: newline-delimited JSON-RPC, behaviour chosen by argv[1].

Every id is answered as it was sent, so the client's string ids (`vibey-mcp-N`) come back
unchanged. `initialize` agrees to the version the client offers. When argv[2] names a file, one
line is appended to it each time the server starts, so a test can count starts.

Modes: `ok`; `exit` (ends at once); `hang` (reads two lines, never answers); `chatter` (noise
before every answer); `paged` (60 tools over three `nextCursor` pages); `slow-schema` (also
lists `huge`, whose input schema is far larger than any answer budget: the tool a model has to
call from its description). The `env-names` tool answers the names of its environment, never
the values, and `long` answers `chars` characters of text (each `fill`, when given).
"""

import json
import os
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "ok"
if len(sys.argv) > 2:
    with open(sys.argv[2], "a", encoding="utf-8") as starts:
        starts.write("started\n")


def send(message: object) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def text_result(request_id: object, text: str, *, is_error: bool = False) -> None:
    result: dict = {"content": [{"type": "text", "text": text}]}
    if is_error:
        result["isError"] = True
    send({"jsonrpc": "2.0", "id": request_id, "result": result})


def listing(params: dict) -> dict:
    if mode == "paged":
        cursor = int(params.get("cursor") or "0")
        page = [
            {"name": f"t{number:02d}", "description": f"Tool {number}.", "inputSchema": {}}
            for number in range(cursor * 20, cursor * 20 + 20)
        ]
        return {"tools": page, **({"nextCursor": str(cursor + 1)} if cursor < 2 else {})}
    tools: list[object] = [
        {"name": "echo", "description": "Echo.", "inputSchema": {"type": "object"}},
        7,
    ]
    if mode == "slow-schema":
        properties = {
            f"field_{n:04d}": {"type": "string", "description": "x" * 40} for n in range(800)
        }
        tools.append(
            {
                "name": "huge",
                "description": "A tool whose schema is too large to show.\n" + "More. " * 100,
                "inputSchema": {"type": "object", "properties": properties},
            }
        )
    return {"tools": tools}


if mode == "exit":
    sys.exit(0)
if mode == "hang":
    sys.stdin.readline()
    sys.stdin.readline()
    import time

    time.sleep(60)

for raw in sys.stdin:
    request = json.loads(raw)
    method, request_id = request.get("method"), request.get("id")
    if request_id is None:
        continue
    if mode == "chatter":
        sys.stdout.write("not json\n")
        send({"jsonrpc": "2.0", "id": "someone-else", "result": {}})
        send(["not", "an", "object"])
    params = request.get("params") or {}
    if method == "initialize":
        version = params.get("protocolVersion")
        send({"jsonrpc": "2.0", "id": request_id, "result": {"protocolVersion": version}})
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": request_id, "result": listing(params)})
    elif method == "tools/call":
        name, arguments = params["name"], params["arguments"]
        if name == "boom":
            error = {"code": -32000, "message": "exploded" + "!" * arguments.get("chars", 0)}
            send({"jsonrpc": "2.0", "id": request_id, "error": error})
        elif name == "fail":
            text_result(request_id, "it failed", is_error=True)
        elif name == "silent-fail":
            send({"jsonrpc": "2.0", "id": request_id, "result": {"content": [], "isError": True}})
        elif name == "weird":
            send({"jsonrpc": "2.0", "id": request_id, "result": "not an object"})
        elif name == "long":
            fill = arguments.get("fill")
            count = arguments["chars"]
            text_result(
                request_id,
                fill * count if fill else "".join(chr(97 + n % 26) for n in range(count)),
            )
        elif name == "env-names":
            text_result(request_id, " ".join(sorted(os.environ)))
        else:
            content = [{"type": "text", "text": f"echo {arguments}"}, {"type": "image"}, 3]
            send({"jsonrpc": "2.0", "id": request_id, "result": {"content": content}})
