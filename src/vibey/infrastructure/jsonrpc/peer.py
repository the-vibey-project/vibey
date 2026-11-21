# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A bidirectional, line-delimited JSON-RPC 2.0 peer on asyncio streams (stdlib only).

The peer never touches stdout itself: every outbound line goes through the injected
`write_line`, and every diagnostic goes to stderr, so a caller that owns stdout for a protocol
(ACP) cannot be corrupted by the peer.
"""

from __future__ import annotations

import asyncio
import itertools
import sys
import traceback
from collections.abc import Awaitable, Callable, Coroutine, Mapping
from dataclasses import dataclass
from typing import Any

from vibey.infrastructure.jsonrpc.errors import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    PARSE_ERROR,
    PeerCancelled,
    PeerClosed,
    RpcError,
)
from vibey.infrastructure.jsonrpc.interfaces.codec_interface import JsonRpcCodecInterface
from vibey.infrastructure.jsonrpc.interfaces.peer_interface import (
    NotificationHandler,
    RequestHandler,
)


@dataclass(frozen=True)
class _Pending:
    """One outbound request awaiting its reply."""

    method: str
    params: Mapping[str, Any]
    future: asyncio.Future[Mapping[str, Any]]


class JsonRpcPeer:
    """Serves inbound requests and notifications, and issues outbound ones, over one stream pair.

    Declared by `interfaces/peer_interface.py::JsonRpcPeerInterface`. Each inbound message is
    handled in its own task, started in arrival order, so a notification (a cancel) is read and
    acted on while an earlier request is still running. One lock makes every outbound write one
    whole line. Lines passed to `write_line` are complete frames, trailing newline included.
    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        write_line: Callable[[str], Awaitable[None]],
        *,
        on_request: RequestHandler,
        on_notification: NotificationHandler,
        codec: JsonRpcCodecInterface,
        id_prefix: str = "vibey",
        max_message_bytes: int = 16_777_216,
    ) -> None:
        self._reader = reader
        self._write_line = write_line
        self._on_request = on_request
        self._on_notification = on_notification
        self._codec = codec
        self._id_prefix = id_prefix
        self._max_message_bytes = max_message_bytes
        self._counter = itertools.count(1)
        self._write_lock = asyncio.Lock()
        self._pending: dict[str, _Pending] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    async def run(self) -> None:
        try:
            while True:
                framed = await self._next_line()
                if framed is None:
                    return
                line, oversized = framed
                if oversized:
                    await self._write(
                        self._codec.error(
                            None,
                            INVALID_REQUEST,
                            f"Invalid Request: message exceeds {self._max_message_bytes} bytes",
                        )
                    )
                    continue
                await self._take(line)
        finally:
            await self._shutdown()

    async def request(
        self, method: str, params: Mapping[str, Any], *, timeout: float | None = None
    ) -> Mapping[str, Any]:
        if self._closed:
            raise PeerClosed("the peer's input has ended")
        msg_id = f"{self._id_prefix}-{next(self._counter)}"
        future: asyncio.Future[Mapping[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[msg_id] = _Pending(method, params, future)
        try:
            await self._write(
                {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": dict(params)}
            )
            return await asyncio.wait_for(future, timeout)
        finally:
            self._pending.pop(msg_id, None)

    async def notify(self, method: str, params: Mapping[str, Any]) -> None:
        await self._write({"jsonrpc": "2.0", "method": method, "params": dict(params)})

    def cancel_outbound(
        self, predicate: Callable[[str, Mapping[str, Any]], bool]
    ) -> tuple[str, ...]:
        cancelled: list[str] = []
        for msg_id, pending in list(self._pending.items()):
            if not pending.future.done() and predicate(pending.method, pending.params):
                pending.future.set_exception(PeerCancelled(f"request {msg_id} cancelled"))
                cancelled.append(msg_id)
        return tuple(cancelled)

    # -- reading --------------------------------------------------------------------------

    async def _next_line(self) -> tuple[bytes, bool] | None:
        """The next line and whether it was oversized, or None at a clean EOF.

        An oversized line is drained to its newline and reported once, so the stream continues
        at the next line. The bound is enforced here as well as by the caller's reader limit.
        """
        oversized = False
        while True:
            try:
                line = await self._reader.readuntil(b"\n")
            except asyncio.IncompleteReadError as exc:
                if not exc.partial and not oversized:
                    return None
                return exc.partial, oversized or len(exc.partial) > self._max_message_bytes
            except asyncio.LimitOverrunError as exc:
                await self._reader.readexactly(exc.consumed)
                oversized = True
                continue
            return line, oversized or len(line) > self._max_message_bytes

    async def _take(self, raw: bytes) -> None:
        try:
            line = raw.decode("utf-8")
        except UnicodeDecodeError:
            await self._write(self._codec.error(None, PARSE_ERROR, "Parse error: invalid UTF-8"))
            return
        if self._codec.is_blank(line):
            return
        try:
            message = self._codec.decode(line)
        except RpcError as exc:
            await self._write(self._codec.error(None, exc.code, exc.message))
            return
        problem = self._codec.validate(message, allow_response=True)
        if problem is not None:
            await self._write(problem)
            return
        if isinstance(message.get("method"), str):
            self._spawn(self._serve(message))
        else:
            self._resolve(message)

    # -- handling -------------------------------------------------------------------------

    def _spawn(self, coroutine: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coroutine)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _serve(self, message: Mapping[str, Any]) -> None:
        method: str = message["method"]
        params = message.get("params")
        is_request = "id" in message
        msg_id = message.get("id")
        if params is not None and not isinstance(params, Mapping):
            if is_request:
                await self._write_quietly(
                    self._codec.error(
                        msg_id, INVALID_PARAMS, "Invalid params: expected JSON object"
                    )
                )
            else:
                self._log(f"dropped notification {method!r}: params is not a JSON object")
            return
        params_map: Mapping[str, Any] = params if isinstance(params, Mapping) else {}
        if is_request:
            await self._serve_request(msg_id, method, params_map)
        else:
            await self._serve_notification(method, params_map)

    async def _serve_request(self, msg_id: Any, method: str, params: Mapping[str, Any]) -> None:
        try:
            result = await self._on_request(method, params)
            reply = self._codec.ok(msg_id, result)
        except RpcError as exc:
            reply = self._codec.error(msg_id, exc.code, exc.message, exc.data)
        except Exception as exc:
            self._log(f"handler for {method!r} failed:\n{traceback.format_exc()}")
            reply = self._codec.error(
                msg_id, INTERNAL_ERROR, f"Internal error: {type(exc).__name__}"
            )
        await self._write_quietly(reply)

    async def _serve_notification(self, method: str, params: Mapping[str, Any]) -> None:
        try:
            await self._on_notification(method, params)
        except Exception:
            self._log(f"notification handler for {method!r} failed:\n{traceback.format_exc()}")

    def _resolve(self, message: Mapping[str, Any]) -> None:
        response_id = message.get("id")
        pending = self._pending.get(response_id) if isinstance(response_id, str) else None
        if pending is None:
            self._log(f"dropped response with unknown id {response_id!r}")
            return
        if pending.future.done():
            return
        if "error" in message:
            raw = message["error"]
            detail: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
            code = detail.get("code")
            text = detail.get("message")
            pending.future.set_exception(
                RpcError(
                    code if isinstance(code, int) else INTERNAL_ERROR,
                    text if isinstance(text, str) else "malformed error response",
                    detail.get("data"),
                )
            )
            return
        result = message.get("result")
        pending.future.set_result(result if isinstance(result, Mapping) else {})

    # -- writing and teardown -------------------------------------------------------------

    async def _write(self, message: Mapping[str, Any]) -> None:
        line = self._codec.encode(message) + "\n"
        async with self._write_lock:
            await self._write_line(line)

    async def _write_quietly(self, message: Mapping[str, Any]) -> None:
        """Write from a handler task: a dead stream or unserialisable reply is logged, not raised."""
        try:
            await self._write(message)
        except Exception as exc:
            self._log(f"could not write a reply: {type(exc).__name__}: {exc}")

    async def _shutdown(self) -> None:
        self._closed = True
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_exception(PeerClosed("the peer's input has ended"))
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _log(text: str) -> None:
        sys.stderr.write(f"vibey jsonrpc: {text}\n")
        sys.stderr.flush()
