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
- **One deadline in all** (`[web] timeout_seconds`), fail closed: the fetch runs on its own
  daemon thread and the caller waits at most that long. Every step inside -- the resolution (on
  its own bounded thread), each connection, the request, the response and every receive, across
  every redirect -- is given only the time left of that one deadline, never a fresh timeout. When
  the caller gives up, the fetch is marked cancelled under a lock and its live socket shut: from
  then on nothing is resolved, connected, sent or read, a connection made after the cancel is
  closed the moment it is handed over, and the thread ends.

Errors name the cause by exception type, never the URL; each carries the hosts reached, for the
record. Declared by `interfaces/guarded_fetch_interface.py`; the port it fills is the application's
`WebFetchPortInterface`.
"""

from __future__ import annotations

import asyncio
import codecs
import contextlib
import http.client
import ipaddress
import re
import socket
import threading
import time
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
_SHOWN_TYPE_CHARS: Final = 64
"""The longest server-chosen content type a refusal repeats (it reaches the ledger)."""
TITLE_CHARS: Final = 300
"""The longest page title kept (and never more than `[web] max_chars`)."""
TEXT_CODECS: Final = frozenset(
    {
        "utf-8",
        "ascii",
        "latin-1",
        *(f"iso8859-{n}" for n in (*range(1, 12), *range(13, 17))),
        *(f"cp{n}" for n in range(1250, 1259)),
        "utf-16",
        "utf-32",
        "gbk",
        "gb18030",
        "big5",
        "shift_jis",
        "euc_jp",
        "euc_kr",
        "koi8-r",
        "koi8-u",
    }
)
"""The text codecs a page may name, as `codecs.lookup(...).name` spells them; any other falls
back to UTF-8."""
_CHUNK: Final = 64 * 1024
"""The most bytes one receive asks for."""

type Resolve = Callable[[str, int], Sequence[str]]
type Connect = Callable[[str, str, int, str, float], Any]


class _Cancelled(Exception):
    """The caller's deadline passed: the fetch's thread stops where it is and sends nothing."""


class _Live:
    """What the fetch's thread holds, shared with the caller under one lock: its connection, the
    hosts it has reached, the one deadline every step is measured against, and whether the caller
    has given up (`cancel`). Once cancelled, nothing more is resolved, connected, sent or read: a
    connection made after the cancel is closed the moment it is handed over."""

    def __init__(self, deadline: float, clock: Callable[[], float]) -> None:
        self.hosts: list[str] = []
        self._deadline = deadline
        self._clock = clock
        self._lock = threading.Lock()
        self._cancelled = False
        self._connection: Any = None

    def cancel(self) -> None:
        """Give up: mark the fetch cancelled and shut the live socket, so a read blocked on it
        returns at once."""
        with self._lock:
            self._cancelled = True
            connection, self._connection = self._connection, None
        if connection is not None:
            self._shut(connection)

    def check(self) -> float:
        """The seconds left before the deadline; raises when the caller gave up or none are."""
        with self._lock:
            if self._cancelled:
                raise _Cancelled
        left = self._deadline - self._clock()
        if left <= 0:
            raise _Cancelled
        return left

    def adopt(self, connection: Any) -> Any:
        """`connection`, held as the live one; or, when the caller gave up while it was being
        made, closed at once, and the fetch stops."""
        with self._lock:
            if not self._cancelled:
                self._connection = connection
                return connection
        self._shut(connection)
        raise _Cancelled

    def bound(self, connection: Any) -> None:
        """Bound the next blocking step on `connection`'s socket by the time left in all."""
        left = self.check()
        connection.timeout = left
        sock = getattr(connection, "sock", None)
        if sock is not None:
            sock.settimeout(left)

    @staticmethod
    def _shut(connection: Any) -> None:
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
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._policy = policy
        self._resolve = resolve if resolve is not None else self.system_addresses
        self._connect = connect
        self._clock = clock

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
        timeout = settings.timeout_seconds
        live = _Live(self._clock() + timeout, self._clock)

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
            except _Cancelled:
                outcome: tuple[WebPage | None, BaseException | None] = (
                    None,
                    WebToolFailed(self._late(timeout), hosts=tuple(live.hosts)),
                )
            except BaseException as exc:  # noqa: BLE001 - handed to the waiting caller as is
                outcome = (None, exc)
            else:
                outcome = (page, None)
            try:
                loop.call_soon_threadsafe(settle, *outcome)
            except RuntimeError:
                return  # the loop has closed: the caller went away long ago

        threading.Thread(target=run, name="vibey-web-fetch", daemon=True).start()
        try:
            return await asyncio.wait_for(done, timeout=timeout)
        except TimeoutError:
            live.cancel()
            raise WebToolFailed(self._late(timeout), hosts=tuple(live.hosts)) from None

    @staticmethod
    def _late(timeout: float) -> str:
        return f"the page did not finish answering within {timeout:g}s"

    def _fetch(self, target: WebTarget, settings: WebToolSettings, live: _Live) -> WebPage:
        current = target
        for _ in range(settings.max_redirects + 1):
            live.hosts.append(current.host)
            hosts = tuple(live.hosts)
            address = self._address(current, hosts, live)
            left = live.check()
            connection = live.adopt(
                self._connect(current.scheme, current.host, current.port, address, left)
            )
            try:
                # Connect now, not lazily inside `request`: a cancel that lands while the
                # connection is being made is then seen before one byte is sent.
                opened = getattr(connection, "connect", None)
                if opened is not None:
                    opened()
                live.bound(connection)
                connection.request("GET", current.target, headers=dict(HEADERS))
                live.bound(connection)
                response = connection.getresponse()
                location = response.getheader("Location")
                if response.status in _REDIRECTS and location:
                    current = self._follow(current, location, settings, hosts)
                    continue
                return self._page(current, response, settings, hosts, live, connection)
            except (OSError, http.client.HTTPException) as exc:
                live.check()  # a socket shut by the caller's cancel is the deadline, not a fault
                raise WebToolFailed(
                    f"the page could not be fetched ({type(exc).__name__})", hosts=hosts
                ) from None
            finally:
                connection.close()
        raise WebToolFailed(
            f"stopped after {settings.max_redirects} redirects", hosts=tuple(live.hosts)
        )

    @staticmethod
    def decoded(raw: bytes, header: str) -> str:
        """`raw` as text in the page's declared charset when that is one of `TEXT_CODECS`, else
        UTF-8; an undecodable byte is a replacement character. Never raises: the page's server
        chooses the charset, and a codec that is not text (`idna`, `punycode`, `undefined`,
        `rot13`) must never decide whether the fetch is recorded."""
        found = _CHARSET.search(header)
        try:
            name = codecs.lookup(found.group(1)).name if found else "utf-8"
        except LookupError:
            name = "utf-8"
        if name not in TEXT_CODECS:
            name = "utf-8"
        try:
            return raw.decode(name, "replace")
        except (LookupError, UnicodeError, ValueError):
            return raw.decode("utf-8", "replace")

    def _follow(
        self, current: WebTarget, location: str, settings: WebToolSettings, hosts: tuple[str, ...]
    ) -> WebTarget:
        try:
            return self._policy.follow(current, location, settings)
        except WebToolRefused as refused:
            raise WebToolRefused(str(refused), hosts=hosts) from None

    def _address(self, target: WebTarget, hosts: tuple[str, ...], live: _Live) -> str:
        """The checked address to connect to: the literal itself, or the first of the name's
        addresses once every one of them is public. A name is resolved within the time left, on
        its own daemon thread, so a resolver that hangs never holds the fetch past its deadline,
        and its late answer is never used."""
        try:
            addresses: Sequence[str] = [str(ipaddress.ip_address(target.host))]
        except ValueError:
            addresses = self._resolved(target, live)
        if not addresses:
            raise WebToolFailed("the page's host could not be resolved", hosts=hosts)
        for address in addresses:
            problem = self._policy.address_problem(address)
            if problem is not None:
                raise WebToolRefused(f"refused: {problem}", hosts=hosts)
        return addresses[0]

    def _resolved(self, target: WebTarget, live: _Live) -> list[str]:
        left = live.check()
        answer: list[list[str]] = []

        def resolve() -> None:
            # Any failure of the resolver is no address: the caller says the host did not resolve.
            with contextlib.suppress(Exception):
                answer.append(list(self._resolve(target.host, target.port)))

        worker = threading.Thread(target=resolve, name="vibey-web-resolve", daemon=True)
        worker.start()
        worker.join(left)
        live.check()  # the deadline, or the caller's cancel, came first: its answer is not used
        return answer[0] if answer else []

    @staticmethod
    def _page(
        target: WebTarget,
        response: Any,
        settings: WebToolSettings,
        hosts: tuple[str, ...],
        live: _Live,
        connection: Any,
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
            # The server chose this text: shown only when short and plainly a type, never more.
            shown = (
                kind
                if _TYPE.match(kind) and len(kind) <= _SHOWN_TYPE_CHARS
                else "an unreadable type"
                if kind
                else ""
            )
            raise WebToolRefused(
                f"refused: not a page vibey reads ({shown or 'no content type'}): PDF, images "
                "and other binary types are refused, never extracted",
                hosts=hosts,
            )
        raw = bytearray()
        read = getattr(response, "read1", None) or response.read
        while len(raw) <= settings.max_bytes:
            # One receive at a time, each bounded by what is left of the one deadline: a page
            # that trickles a byte just inside every timeout still stops when the time is up.
            live.bound(connection)
            chunk = read(min(_CHUNK, settings.max_bytes + 1 - len(raw)))
            if not chunk:
                break
            raw += chunk
        clipped = len(raw) > settings.max_bytes
        body = GuardedPageFetch.decoded(bytes(raw[: settings.max_bytes]), header)
        title, text = html_to_text(body) if kind in _HTML else ("", body.strip())
        title, text = UntrustedText.clean(title), UntrustedText.clean(text)
        return WebPage(
            url=target.url,
            hosts=hosts,
            title=title[: min(settings.max_chars, TITLE_CHARS)],
            text=text[: settings.max_chars],
            truncated=clipped or len(text) > settings.max_chars,
            content_type=kind,
        )
