# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's guarded fetch of one page a principal named (ADR-0102, SP-ACP Task 9b).

The domain policy (`domain/web_tools.py`) has already read the URL as a public http(s) target
inside the person's `[web]` host lists. This adapter does what needs a network, and nothing more:

- **Every address checked, and the one checked is the one connected to.** A name is resolved
  once per hop and every address it answers must be public (`address_problem`); the connection
  is pinned to the first of them (`fetch.pinned_connect`), so a DNS answer that changes between
  the check and the connection (rebinding) cannot steer it inward. Nothing is cached between
  hops: a name asked again is checked again.
- **Every redirect is a new target**, read and checked by the policy (no step from https down to
  http, no host the person denies), at most `[web] max_redirects` of them.
- **Fixed headers, and only these:** a fixed User-Agent, an Accept, and `Accept-Encoding:
  identity`. No cookie is kept or sent, no credential, no header the caller chose.
- **Nothing is ever decompressed.** An answer with any `Content-Encoding` but identity is
  refused before one byte of its body is read, so no compressed bomb can expand here.
- **Only the person's content types** (`[web] content_types`; PDF, images and other binary
  types are refused, never extracted), at most `max_bytes` read and `max_chars` returned, as
  plain text cleaned of terminal control (`UntrustedText`).
- **One deadline in all** (`[web] timeout_seconds`): the fetch runs on its own daemon thread and
  the caller waits at most that long; when it passes, the live socket is shut so the thread
  ends too, rather than living until a trickling server lets it go.

Errors name the cause by exception type, never the URL; each carries the hosts reached, for the
record. Declared by `interfaces/guarded_fetch_interface.py`; the port it fills is the application's
`WebFetchPortInterface`.
"""

from __future__ import annotations

import asyncio
import contextlib
import http.client
import ipaddress
import re
import socket
import threading
from collections.abc import Callable, Sequence
from typing import Any, Final

from vibey.application.dto import WebPage
from vibey.domain.interfaces.web_tools_interface import WebToolPolicyInterface
from vibey.domain.web_tools import (
    WEB_TOOL_POLICY,
    WebTarget,
    WebToolFailed,
    WebToolRefused,
    WebToolSettings,
)
from vibey.infrastructure.web.fetch import USER_AGENT as USER_AGENT
from vibey.infrastructure.web.fetch import html_to_text, pinned_connect
from vibey.infrastructure.web.untrusted_text import UntrustedText

HEADERS: Final[dict[str, str]] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
    "Accept-Encoding": "identity",
}
"""Every header a fetch sends; the caller adds none."""
_REDIRECTS: Final = frozenset({301, 302, 303, 307, 308})
_HTML: Final = frozenset({"text/html", "application/xhtml+xml"})
_TYPE: Final = re.compile(r"^[a-z0-9][a-z0-9!#$&^_.+-]*/[a-z0-9][a-z0-9!#$&^_.+-]*$")
_CHARSET: Final = re.compile(r"charset=([\w-]+)")

type Resolve = Callable[[str, int], Sequence[str]]
type Connect = Callable[[str, str, int, str, float], Any]


class _Live:
    """What the fetch's thread holds right now: its connection, and the hosts it has reached."""

    def __init__(self) -> None:
        self.connection: Any = None
        self.hosts: list[str] = []

    def shut(self) -> None:
        """Shut the live socket, so a read blocked on it returns at once, then close it."""
        connection = self.connection
        if connection is None:
            return
        sock = getattr(connection, "sock", None)
        if sock is not None:
            # Already gone is fine: the close below is all that is left to do.
            with contextlib.suppress(OSError):
                sock.shutdown(socket.SHUT_RDWR)
        connection.close()


class GuardedPageFetch:
    """Declared by `interfaces/guarded_fetch_interface.py::GuardedPageFetchInterface`."""

    def __init__(
        self,
        *,
        policy: WebToolPolicyInterface = WEB_TOOL_POLICY,
        resolve: Resolve | None = None,
        connect: Connect = pinned_connect,
    ) -> None:
        self._policy = policy
        self._resolve = resolve if resolve is not None else self.system_addresses
        self._connect = connect

    @staticmethod
    def system_addresses(host: str, port: int) -> list[str]:
        """Every address the system resolves `host` to; none when the lookup fails."""
        try:
            infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError:
            return []
        return [str(info[4][0]) for info in infos]

    async def fetch(self, target: WebTarget, settings: WebToolSettings) -> WebPage:
        loop = asyncio.get_running_loop()
        done: asyncio.Future[WebPage] = loop.create_future()
        live = _Live()

        def settle(result: WebPage | None, error: BaseException | None) -> None:
            if done.done():
                return  # the deadline passed first: nobody is waiting for this any more
            if error is not None:
                done.set_exception(error)
            else:
                done.set_result(result)  # type: ignore[arg-type]

        def run() -> None:
            try:
                page = self._fetch(target, settings, live)
            except BaseException as exc:  # noqa: BLE001 - handed to the waiting caller as is
                outcome: tuple[WebPage | None, BaseException | None] = (None, exc)
            else:
                outcome = (page, None)
            try:
                loop.call_soon_threadsafe(settle, *outcome)
            except RuntimeError:
                return  # the loop has closed: the caller went away long ago

        threading.Thread(target=run, name="vibey-web-fetch", daemon=True).start()
        try:
            return await asyncio.wait_for(done, timeout=settings.timeout_seconds)
        except TimeoutError:
            live.shut()
            raise WebToolFailed(
                f"the page did not finish answering within {settings.timeout_seconds:g}s",
                hosts=tuple(live.hosts),
            ) from None

    def _fetch(self, target: WebTarget, settings: WebToolSettings, live: _Live) -> WebPage:
        current = target
        for _ in range(settings.max_redirects + 1):
            live.hosts.append(current.host)
            hosts = tuple(live.hosts)
            address = self._address(current, hosts)
            connection = self._connect(
                current.scheme, current.host, current.port, address, settings.timeout_seconds
            )
            live.connection = connection
            try:
                connection.request("GET", current.target, headers=dict(HEADERS))
                response = connection.getresponse()
                location = response.getheader("Location")
                if response.status in _REDIRECTS and location:
                    current = self._follow(current, location, settings, hosts)
                    continue
                return self._page(current, response, settings, hosts)
            except (OSError, http.client.HTTPException) as exc:
                raise WebToolFailed(
                    f"the page could not be fetched ({type(exc).__name__})", hosts=hosts
                ) from None
            finally:
                connection.close()
        raise WebToolFailed(
            f"stopped after {settings.max_redirects} redirects", hosts=tuple(live.hosts)
        )

    def _follow(
        self, current: WebTarget, location: str, settings: WebToolSettings, hosts: tuple[str, ...]
    ) -> WebTarget:
        try:
            return self._policy.follow(current, location, settings)
        except WebToolRefused as refused:
            raise WebToolRefused(str(refused), hosts=hosts) from None

    def _address(self, target: WebTarget, hosts: tuple[str, ...]) -> str:
        """The checked address to connect to: the literal itself, or the first of the name's
        addresses once every one of them is public."""
        try:
            addresses: Sequence[str] = [str(ipaddress.ip_address(target.host))]
        except ValueError:
            addresses = list(self._resolve(target.host, target.port))
        if not addresses:
            raise WebToolFailed("the page's host could not be resolved", hosts=hosts)
        for address in addresses:
            problem = self._policy.address_problem(address)
            if problem is not None:
                raise WebToolRefused(f"refused: {problem}", hosts=hosts)
        return addresses[0]

    @staticmethod
    def _page(
        target: WebTarget, response: Any, settings: WebToolSettings, hosts: tuple[str, ...]
    ) -> WebPage:
        if response.status != 200:
            raise WebToolFailed(f"the page answered HTTP {response.status}", hosts=hosts)
        encoding = (response.getheader("Content-Encoding") or "").strip().lower()
        if encoding not in {"", "identity"}:
            raise WebToolRefused(
                "refused: the page came compressed; vibey asks for, and reads, only uncompressed "
                "pages",
                hosts=hosts,
            )
        header = response.getheader("Content-Type") or ""
        kind = header.split(";")[0].strip().lower()
        if kind not in settings.content_types:
            shown = kind if _TYPE.match(kind) else "an unreadable type" if kind else ""
            raise WebToolRefused(
                f"refused: not a page vibey reads ({shown or 'no content type'}): PDF, images "
                "and other binary types are refused, never extracted",
                hosts=hosts,
            )
        raw = response.read(settings.max_bytes + 1)
        clipped = len(raw) > settings.max_bytes
        charset = _CHARSET.search(header)
        try:
            body = raw[: settings.max_bytes].decode(
                charset.group(1) if charset else "utf-8", "replace"
            )
        except LookupError:
            body = raw[: settings.max_bytes].decode("utf-8", "replace")
        title, text = html_to_text(body) if kind in _HTML else ("", body.strip())
        title, text = UntrustedText.clean(title), UntrustedText.clean(text)
        return WebPage(
            url=target.url,
            hosts=hosts,
            title=title,
            text=text[: settings.max_chars],
            truncated=clipped or len(text) > settings.max_chars,
            content_type=kind,
        )
