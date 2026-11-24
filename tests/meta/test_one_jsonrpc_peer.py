# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey holds no JSON-RPC peer of its own: the one peer lives in `vibey_runners.common.jsonrpc`.

The MCP server, the ACP agent and the local runner's MCP client speak through one codec, one
error vocabulary and one peer (SP-LOOPS Phase 5 R1). A second copy under `src/vibey` would be
two implementations of one wire format drifting apart, so this fails the moment one returns.
Module-level test functions rather than a class with an interface beside it (ADR-0016).
"""

import importlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VIBEY = REPO / "src" / "vibey"
PEER_CLASSES = re.compile(r"^class (JsonRpcPeer|JsonRpcCodec|RpcError)\b", re.MULTILINE)


def test_vibey_holds_no_second_jsonrpc_peer() -> None:
    assert not (VIBEY / "infrastructure" / "jsonrpc").exists(), (
        "src/vibey/infrastructure/jsonrpc is back; the peer lives in vibey_runners.common.jsonrpc"
    )
    defining = sorted(
        str(path.relative_to(REPO))
        for path in VIBEY.rglob("*.py")
        if PEER_CLASSES.search(path.read_text(encoding="utf-8"))
    )
    assert defining == [], f"src/vibey defines its own JSON-RPC peer classes: {defining}"
    peer = importlib.import_module("vibey_runners.common.jsonrpc.peer")
    assert peer.JsonRpcPeer.__name__ == "JsonRpcPeer"
