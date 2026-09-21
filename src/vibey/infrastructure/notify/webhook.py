# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Webhook publisher with HMAC-SHA256 signing and IP-pinned delivery.

DNS is resolved and validated once, then the TCP connection is pinned to the
validated IP so a DNS rebinding between validation and connection cannot
steer the request to a private address.  The ``Host`` header and TLS SNI
keep the original hostname because the connection class inherits from
``http.client.HTTPConnection``; only the socket target is pinned.
"""

import asyncio
import hashlib
import hmac
import http.client
import ipaddress
import json
import socket
from collections.abc import Callable
from urllib.parse import urlsplit

from vibey.infrastructure.notify.events import NotificationEvent

_DEFAULT_HTTPS_PORT = 443
_DEFAULT_HTTP_PORT = 80


def _pinned_connection_class(
    base: type[http.client.HTTPConnection], ip: str
) -> type[http.client.HTTPConnection]:
    """Build a subclass whose socket always connects to ``ip``, not the hostname.

    ``base.__init__`` still stores the original hostname in ``self.host``,
    which becomes the TLS SNI / ``Host`` header; the DNS bypass lives in
    ``_create_connection``.
    """

    def _create(
        address: tuple[str, int],
        timeout: float | None,
        socket_options: object = None,
        source_address: tuple[str, int] | None = None,
    ) -> socket.socket:
        _ = address[0]
        return socket.create_connection(
            (ip, address[1]),
            timeout=timeout,
            source_address=source_address,
        )

    class _PinnedConnection(base):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            self._create_connection = _create

    return _PinnedConnection


def _resolve_safe_target(url: str) -> tuple[str, int, str] | None:
    """Validate and resolve the URL to a globally routable IP, or None.

    Every address returned by the name resolver must be public; a single
    private or malformed entry rejects the URL.  The connection uses the
    first validated address directly, closing the TOCTOU gap between
    validation and connection.
    """
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        port = parsed.port
    except ValueError:
        return None

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
        (".localhost", ".local", ".internal", ".home.arpa")
    ):
        return None

    is_https = parsed.scheme.lower() == "https"
    port = port or (_DEFAULT_HTTPS_PORT if is_https else _DEFAULT_HTTP_PORT)

    try:
        addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except OSError:
        return None
    if not addresses:
        return None

    for entry in addresses:
        try:
            ip = ipaddress.ip_address(entry[4][0])
        except (IndexError, ValueError):
            return None
        if not ip.is_global:
            return None
    return hostname, port, str(ipaddress.ip_address(addresses[0][4][0]))


class WebhookPublisher:
    def __init__(
        self,
        *,
        http_post_fn: Callable[[str, bytes, dict[str, str]], bool] | None = None,
    ) -> None:
        self._http_post_fn = http_post_fn

    def compute_signature(self, payload_bytes: bytes, secret: str) -> str:
        digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    async def publish(
        self,
        event: NotificationEvent,
        url: str,
        secret: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> bool:
        payload_bytes = json.dumps(event.to_dict(), sort_keys=True).encode("utf-8")
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "vibey-notifier/1.0",
        }
        if secret:
            headers["X-Vibey-Signature"] = self.compute_signature(payload_bytes, secret)

        if self._http_post_fn is not None:
            return self._http_post_fn(url, payload_bytes, headers)

        return await asyncio.to_thread(
            self._sync_post, url, payload_bytes, headers, timeout_seconds
        )

    def _sync_post(
        self,
        url: str,
        payload_bytes: bytes,
        headers: dict[str, str],
        timeout_seconds: float,
    ) -> bool:
        target = _resolve_safe_target(url)
        if target is None:
            return False
        host, port, resolved_ip = target

        parsed = urlsplit(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        base = (
            http.client.HTTPSConnection
            if parsed.scheme.lower() == "https"
            else http.client.HTTPConnection
        )
        conn: http.client.HTTPConnection | None = None
        try:
            conn = _pinned_connection_class(base, resolved_ip)(host, port, timeout=timeout_seconds)
            request_headers = dict(headers)
            request_headers.setdefault("Host", host)
            conn.request("POST", path, body=payload_bytes, headers=request_headers)
            response = conn.getresponse()
            return response.status in {200, 201, 202, 204}
        except Exception:
            return False
        finally:
            if conn is not None:
                conn.close()
