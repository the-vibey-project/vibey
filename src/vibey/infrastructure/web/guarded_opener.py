# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How a search backend opens its requests.

`urllib`'s default opener follows any redirect to any host and carries every header but the
content ones along, so a SearXNG answering `302 Location: https://elsewhere/` would send the
query there, and a redirect from Brave would send the `X-Subscription-Token` key with it. This
opener follows a redirect only to the same scheme, host and port; any other is refused, which
the backend reports as the `3xx` it was.

A SearXNG on a loopback address is reached directly, never through `HTTP_PROXY` or
`ALL_PROXY`: a proxy would see every query, and the local SearXNG is local so that nothing
does. A backend elsewhere (an operator's remote SearXNG, Brave) uses the environment's proxy
settings as any other request would.

Declared by `interfaces/guarded_opener_interface.py` (ADR-0016).
"""

from __future__ import annotations

import ipaddress
import urllib.parse
import urllib.request
from http.client import HTTPMessage
from typing import IO, Any

_LOCAL_NAMES = frozenset({"localhost"})


class _SameOriginRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only within the origin it started from."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        here = urllib.parse.urlsplit(req.full_url)
        there = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
        if (here.scheme, here.netloc) != (there.scheme, there.netloc):
            # None makes urllib raise the redirect as the HTTPError it was.
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GuardedOpener:
    """Declared by `interfaces/guarded_opener_interface.py::GuardedOpenerInterface`."""

    def __init__(self, base_url: str) -> None:
        self.direct = self.is_loopback(base_url)
        handlers: list[urllib.request.BaseHandler] = [_SameOriginRedirects()]
        if self.direct:
            handlers.append(urllib.request.ProxyHandler({}))
        self._director = urllib.request.build_opener(*handlers)

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        return self._director.open(request, timeout=timeout)

    @staticmethod
    def is_loopback(url: str) -> bool:
        """Whether `url` names this machine: `localhost` or a loopback address."""
        host = (urllib.parse.urlsplit(url).hostname or "").lower()
        if host in _LOCAL_NAMES:
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False
