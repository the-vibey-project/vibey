# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redis Cache adapter implementing the Cache port (ADR-0042).

Self-hosted Redis over a minimal stdlib-socket RESP client: GET, SET with an
optional EX expiry, DEL, plus AUTH and SELECT when the URL carries them. No
third-party client -- the port's surface is four commands, and a socket plus
twenty lines of RESP is the whole protocol those commands need.
"""

from __future__ import annotations

import asyncio
import socket
import urllib.parse
from typing import Any

from vibey.application.interfaces.cache import CachePort


class RedisError(RuntimeError):
    """The server answered with an error reply, or the socket failed."""


def _encode(*parts: bytes) -> bytes:
    return b"*%d\r\n" % len(parts) + b"".join(b"$%d\r\n%s\r\n" % (len(p), p) for p in parts)


class _RespReader:
    def __init__(self, sock: socket.socket) -> None:
        self._file = sock.makefile("rb")

    def read(self) -> Any:
        line = self._file.readline().decode("utf-8")
        if not line:
            raise RedisError("redis closed the connection")
        kind, rest = line[0], line[1:].rstrip("\r\n")
        if kind == "+":
            return rest
        if kind == "-":
            raise RedisError(f"redis error: {rest}")
        if kind == ":":
            return int(rest)
        if kind == "$":
            length = int(rest)
            if length < 0:
                return None
            data = self._file.read(length)
            self._file.read(2)
            return data.decode("utf-8")
        raise RedisError(f"unexpected redis reply: {line!r}")


class RedisCacheAdapter(CachePort):
    def __init__(self, *, url: str, timeout: int = 5) -> None:
        parts = urllib.parse.urlsplit(url.strip())
        if parts.scheme != "redis" or not parts.hostname:
            raise ValueError(f"cache url must be a redis:// URL with a host, got {url!r}")
        self._host = parts.hostname
        self._port = parts.port or 6379
        self._password = urllib.parse.unquote(parts.password) if parts.password else None
        self._db = int(parts.path.lstrip("/") or 0) if parts.path else 0
        self._timeout = timeout

    def _roundtrip(self, *parts: bytes) -> Any:
        try:
            with socket.create_connection((self._host, self._port), timeout=self._timeout) as sock:
                sock.settimeout(self._timeout)
                reader = _RespReader(sock)
                if self._password is not None:
                    sock.sendall(_encode(b"AUTH", self._password.encode()))
                    reader.read()
                if self._db:
                    sock.sendall(_encode(b"SELECT", str(self._db).encode()))
                    reader.read()
                sock.sendall(_encode(*parts))
                return reader.read()
        except OSError as exc:
            raise RedisError(f"redis roundtrip failed: {exc}") from exc

    async def get(self, key: str) -> str | None:
        result = await asyncio.to_thread(self._roundtrip, b"GET", key.encode())
        return None if result is None else str(result)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        parts: tuple[bytes, ...] = (b"SET", key.encode(), value.encode())
        if ttl_seconds is not None:
            parts += (b"EX", str(ttl_seconds).encode())
        await asyncio.to_thread(self._roundtrip, *parts)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._roundtrip, b"DEL", key.encode())
