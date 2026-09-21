# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Webhook publisher with HMAC-SHA256 signing."""

import asyncio
import hashlib
import hmac
import ipaddress
import json
import socket
from collections.abc import Callable
from contextlib import suppress
from urllib import request
from urllib.parse import urlsplit

from vibey.infrastructure.notify.events import NotificationEvent


class _NoRedirectHandler(request.HTTPRedirectHandler):
    """Keep a webhook delivery on the address the operator configured."""

    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


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
        if not self._is_public_http_url(url):
            return False
        with suppress(Exception):
            req = request.Request(url, data=payload_bytes, headers=headers, method="POST")
            opener = request.build_opener(_NoRedirectHandler())
            with opener.open(req, timeout=timeout_seconds) as response:  # nosec B310
                return int(response.status) in {200, 201, 202, 204}
        return False

    @staticmethod
    def _is_public_http_url(url: str) -> bool:
        """Reject local, private, and redirectable webhook destinations.

        Webhook URLs are copied from repository configuration, so a project
        author must not be able to turn an opt-in notification into a request
        to loopback, cloud metadata, or another private network.  DNS is
        resolved immediately before the request and every returned address
        must be globally routable.  Redirects are disabled by the opener
        above, so a public endpoint cannot bounce the request into a private
        one after validation.
        """
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
                return False
            if parsed.username is not None or parsed.password is not None:
                return False
            port = parsed.port
        except ValueError:
            return False

        hostname = parsed.hostname.rstrip(".").lower()
        if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
            (".localhost", ".local", ".internal", ".home.arpa")
        ):
            return False

        try:
            addresses = socket.getaddrinfo(
                hostname,
                port or (443 if parsed.scheme.lower() == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except OSError:
            return False
        if not addresses:
            return False

        for address in addresses:
            try:
                ip = ipaddress.ip_address(address[4][0])
            except (IndexError, ValueError):
                return False
            if not ip.is_global:
                return False
        return True
