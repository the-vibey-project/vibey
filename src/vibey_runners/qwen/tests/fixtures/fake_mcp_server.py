# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A stdio MCP server for tests: newline-delimited JSON-RPC, behaviour chosen by argv[1]."""

import json
import sys

mode = sys.argv[1] if len(sys.argv) > 1 else "ok"


def send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


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
        send({"jsonrpc": "2.0", "id": 999, "result": {}})
        send(["not", "an", "object"])
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": request_id, "result": {"capabilities": {}}})
    elif method == "tools/list":
        tools = [{"name": "echo", "description": "Echo.", "inputSchema": {"type": "object"}}, 7]
        send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}})
    elif method == "tools/call":
        name, arguments = request["params"]["name"], request["params"]["arguments"]
        if name == "boom":
            send({"jsonrpc": "2.0", "id": request_id, "error": {"message": "exploded"}})
        elif name == "bare":
            send({"jsonrpc": "2.0", "id": request_id, "error": "plain"})
        elif name == "fail":
            content = [{"type": "text", "text": "it failed"}]
            send(
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"content": content, "isError": True},
                }
            )
        elif name == "silent-fail":
            send({"jsonrpc": "2.0", "id": request_id, "result": {"content": [], "isError": True}})
        elif name == "weird":
            send({"jsonrpc": "2.0", "id": request_id, "result": "not an object"})
        else:
            content = [{"type": "text", "text": f"echo {arguments}"}, {"type": "image"}, 3]
            send({"jsonrpc": "2.0", "id": request_id, "result": {"content": content}})
