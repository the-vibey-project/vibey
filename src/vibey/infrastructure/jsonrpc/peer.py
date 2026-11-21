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

_UNSERIALISABLE = "Internal error: unserialisable result"


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
    At EOF in-flight handlers get `eof_grace_seconds` to finish before they are cancelled.
    A failed write of a reader-loop reply (parse error, oversize) raises out of `run`; a failed
    write of a handler's reply is logged to stderr and the peer carries on.
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
        eof_grace_seconds: float = 5.0,
    ) -> None:
        self._reader = reader
        self._write_line = write_line
        self._on_request = on_request
        self._on_notification = on_notification
        self._codec = codec
        self._id_prefix = id_prefix
        self._max_message_bytes = max_message_bytes
        self._eof_grace_seconds = eof_grace_seconds
        self._counter = itertools.count(1)
        self._write_lock = asyncio.Lock()
        self._pending: dict[str, _Pending] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._closed = False

    async def run(self) -> None:
        at_eof = False
        try:
            while True:
                framed = await self._next_line()
                if framed is None:
                    at_eof = True
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
            await self._shutdown(drain=at_eof)

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
            if pending.future.done():
                continue
            try:
                matches = predicate(pending.method, pending.params)
            except Exception as exc:
                self._log(f"cancel_outbound predicate failed for {msg_id}: {exc!r}")
                continue
            if matches:
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
                return exc.partial, oversized or self._too_long(exc.partial)
            except asyncio.LimitOverrunError as exc:
                await self._reader.readexactly(exc.consumed)
                oversized = True
                continue
            return line, oversized or self._too_long(line)

    def _too_long(self, line: bytes) -> bool:
        """Whether the message, not counting its terminating newline, exceeds the bound."""
        return len(line.removesuffix(b"\n")) > self._max_message_bytes

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
                await self._send_quietly(
                    self._error_line(msg_id, INVALID_PARAMS, "Invalid params: expected JSON object")
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
            line = self._ok_line(msg_id, method, result)
        except RpcError as exc:
            line = self._error_line(msg_id, exc.code, exc.message, exc.data)
        except Exception as exc:
            self._log(f"handler for {method!r} failed:\n{traceback.format_exc()}")
            line = self._error_line(msg_id, INTERNAL_ERROR, f"Internal error: {type(exc).__name__}")
        await self._send_quietly(line)

    def _ok_line(self, msg_id: Any, method: str, result: Mapping[str, Any]) -> str:
        try:
            return self._frame(self._codec.ok(msg_id, result))
        except (TypeError, ValueError):
            self._log(f"reply to {method!r} is not serialisable:\n{traceback.format_exc()}")
            return self._error_line(msg_id, INTERNAL_ERROR, _UNSERIALISABLE)

    def _error_line(self, msg_id: Any, code: int, message: str, data: Any = None) -> str:
        """An error frame that always encodes.

        A peer-supplied id can be NaN (`json.loads` accepts it) and a handler's `data` can be
        anything, so the frame is retried without the offending part: first with a null id, then
        with the generic unserialisable-result error, last with both. Every degraded reply is logged.
        """
        attempts = (
            (msg_id, code, message, data),
            (None, code, message, data),
            (msg_id, INTERNAL_ERROR, _UNSERIALISABLE, None),
        )
        for attempt_id, attempt_code, attempt_message, attempt_data in attempts:
            try:
                return self._frame(
                    self._codec.error(attempt_id, attempt_code, attempt_message, attempt_data)
                )
            except (TypeError, ValueError):
                self._log(f"error reply {code} is not serialisable; degrading it")
        return self._frame(self._codec.error(None, INTERNAL_ERROR, _UNSERIALISABLE))

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

    def _frame(self, message: Mapping[str, Any]) -> str:
        """One complete line. Strict JSON: NaN and Infinity are refused, never put on the wire."""
        return self._codec.encode_strict(message) + "\n"

    async def _send(self, line: str) -> None:
        async with self._write_lock:
            await self._write_line(line)

    async def _write(self, message: Mapping[str, Any]) -> None:
        await self._send(self._frame(message))

    async def _send_quietly(self, line: str) -> None:
        """Send from a handler task: a dead output stream is logged, not raised."""
        try:
            await self._send(line)
        except Exception as exc:
            self._log(f"could not write a reply: {type(exc).__name__}: {exc}")

    async def _shutdown(self, *, drain: bool) -> None:
        self._closed = True
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_exception(PeerClosed("the peer's input has ended"))
        tasks = list(self._tasks)
        try:
            if drain and tasks:
                await asyncio.wait(tasks, timeout=self._eof_grace_seconds)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _log(text: str) -> None:
        sys.stderr.write(f"vibey jsonrpc: {text}\n")
        sys.stderr.flush()
