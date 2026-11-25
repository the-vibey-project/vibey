# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An engine session's own client to the hub: `vibey search` and `vibey fetch` inside a session
(SP-LOOPS Phase 6, Task 4; R1).

A session never searches or fetches in its own process. It asks the hub, which holds the search
backends and the Brave key, charges the session's own `[web]` cap and the agent's hourly bucket
(R2), and records the use on the ledger. What the session holds is two names in its environment:
`VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` (`session.py`). The rules, in the order they apply:

1. **Loopback only.** The hub's address must be `http(s)://<loopback>:<port>` with nothing else
   in it (no user, path, query or fragment), and the connection goes to the loopback literal
   `HUB_TARGETS` reads it as, never to a name resolved again -- the rule `vibey mcp`'s gateway
   follows (`mcp/hub_gateway.py`, point 6). Anything else is refused before the token file is
   read or anything is sent. An `https` hub is trusted by its own certificate alone, read from
   the person's own `[hub]` state folder as the gateway reads it.
2. **The token is read from its file on every call**, through the store that wrote it
   (`SessionTokenStore.read`: owner-only, never through a link), and is never kept: a rotated
   or revoked token is what the next call presents. A missing, empty or unreadable file is
   `unconfigured`, named by its path.
3. **Built as the hub's own tools are**: `HOST_TOOL_CATALOG.build_call` makes the request from
   the `vibey_search` and `vibey_fetch` tools the MCP clients use, so a query or a URL the hub
   would refuse is refused here (`refused`) before anything is sent. `send` takes a call built
   that way already: `vibey mcp --scope web` builds its calls with the same catalog (Task 6).
4. **Sent once.** A call to the open web is never repeated: a request that may have arrived
   could spend twice. A hub that does not answer is `unreachable`, said in one line.
5. **Refusals by kind**: 401 `ended` (the session finished, was revoked or expired), 403
   `forbidden`, 429 `budget` (the hub's own words, which name the budget), anything else
   `failed`, with the hub's `detail` cleaned to one printable line.

The token is never in an error, a `repr` or a log line: errors are built from statuses, paths
and exception class names, and this module logs nothing. Declared by
`interfaces/session_hub_client_interface.py::SessionHubClientInterface`.
"""

from __future__ import annotations

import ssl
import urllib.parse
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Final, Literal

import httpx

from vibey.application.dto import WebHit, WebSearchAnswer
from vibey.application.interfaces.session_web_principals_interface import (
    SessionTokenFilesInterface,
)
from vibey.application.session_token_lookup import SessionTokenLookup
from vibey.domain.config import ConfigError
from vibey.domain.errors import SessionGrantRefused, VibeyError
from vibey.domain.host_tools import HOST_TOOL_CATALOG, HostToolError, HubCall
from vibey.domain.hub_target import HUB_TARGETS
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.domain.session_web_state import HUB_URL_VARIABLE
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.hub.session_token_store import SessionTokenStore
from vibey.infrastructure.hub.settings import HUB_SETTINGS
from vibey.infrastructure.hub.tls import HubCertificate
from vibey.infrastructure.mcp.hub_gateway import WEB_TIMEOUT_MARGIN, personal_config
from vibey.infrastructure.web.fetch import FetchedPage
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.page_fetcher import own_web_settings
from vibey.infrastructure.web.search import DEFAULT_TIMEOUT_SECONDS
from vibey.infrastructure.web.untrusted_text import UntrustedText

type SessionHubFailure = Literal[
    "unconfigured", "refused", "ended", "forbidden", "budget", "unreachable", "failed"
]
type ClientFactory = Callable[..., httpx.Client]

REQUEST_ID: Final = "session"
"""What `build_call` is given as a request id: neither web tool sends one."""
_UNREADABLE: Final = "the hub's answer could not be read"


class SessionHubError(VibeyError):
    """The hub could not be asked, or refused. `kind` says which; the message never carries the
    token."""

    def __init__(self, message: str, *, kind: SessionHubFailure) -> None:
        super().__init__(message)
        self.kind: SessionHubFailure = kind


class SessionHubClient:
    """Declared by `interfaces/session_hub_client_interface.py::SessionHubClientInterface`."""

    def __init__(
        self,
        hub_url: str,
        token_file: Path,
        *,
        tokens: SessionTokenFilesInterface | None = None,
        client: ClientFactory = httpx.Client,
        certificate: Callable[[], ssl.SSLContext] | None = None,
        web_settings: Callable[[], WebToolSettings] | None = None,
        tools: HostToolsInterface = HOST_TOOL_CATALOG,
    ) -> None:
        self._hub_url = hub_url
        self._token_file = token_file
        self._tokens = tokens if tokens is not None else SessionTokenStore()
        self._client = client
        self._certificate = certificate or SessionHubClient.own_certificate
        self._web_settings = web_settings or (lambda: own_web_settings())
        self._tools = tools

    def __repr__(self) -> str:
        return f"SessionHubClient(hub={self._hub_url!r}, token_file={str(self._token_file)!r})"

    @classmethod
    def for_access(cls, access: SessionWebAccessInterface) -> SessionHubClient:
        """The client a session's environment names. Only for `mode == "hub"`."""
        if access.mode != "hub" or access.token_file is None:
            raise ValueError("no hub to reach: the session's environment names none")
        return cls(access.hub_url, access.token_file)

    @staticmethod
    def own_certificate() -> ssl.SSLContext:
        """A TLS context trusting the person's own hub's certificate and nothing else: the
        state folder is their own `[hub]`'s, narrowed by the current folder's, as `vibey mcp`
        reads it."""
        settings = HUB_SETTINGS.load_trusted(personal_config(), Path.cwd() / "vibey.toml")
        return HubCertificate(settings.state_dir).client_context()

    def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        arguments: dict[str, object] = {"query": query}
        if limit is not None:
            arguments["limit"] = limit
        document = self._post("vibey_search", arguments, "search the web")
        backend, results, notice = (
            document.get("backend"),
            document.get("results"),
            document.get("notice"),
        )
        if not (
            isinstance(backend, str)
            and isinstance(results, list)
            and (notice is None or isinstance(notice, str))
            and all(self._is_hit(result) for result in results)
        ):
            raise SessionHubError(_UNREADABLE, kind="failed")
        return WebSearchAnswer(
            hits=tuple(WebHit(r["title"], r["url"], r["snippet"]) for r in results),
            backend=backend,
            notice=notice,
        )

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        document = self._post("vibey_fetch", {"url": url}, "fetch a web page")
        where, truncated, text = (
            document.get("url"),
            document.get("truncated"),
            document.get("text"),
        )
        if not (isinstance(where, str) and isinstance(truncated, bool) and isinstance(text, str)):
            raise SessionHubError(_UNREADABLE, kind="failed")
        if max_chars is not None:
            text, cut = self._cut(text, max_chars)
            truncated = truncated or cut
        # The hub keeps the page's title inside its marked block, with the page's other words.
        return FetchedPage(url=where, title="", text=text, truncated=truncated)

    @staticmethod
    def _is_hit(result: object) -> bool:
        return isinstance(result, dict) and all(
            isinstance(result.get(key), str) for key in ("title", "url", "snippet")
        )

    @staticmethod
    def _cut(text: str, max_chars: int) -> tuple[str, bool]:
        """The page's own words cut to `max_chars` inside the hub's nonce-marked block, whose
        two marker lines are kept whole; and whether anything was cut."""
        opening, _, rest = text.partition("\n")
        body, newline, closing = rest.rpartition("\n")
        if not newline:
            raise SessionHubError(_UNREADABLE, kind="failed")
        if len(body) <= max_chars:
            return text, False
        return f"{opening}\n{body[:max_chars]}\n{closing}", True

    def _post(self, tool: str, arguments: Mapping[str, object], what: str) -> dict[str, Any]:
        try:
            call = self._tools.build_call(tool, arguments, request_id=REQUEST_ID)
        except HostToolError as exc:
            raise SessionHubError(str(exc), kind="refused") from None
        return self.send(call, what)

    def send(self, call: HubCall, what: str) -> dict[str, Any]:
        base = self._base()
        verify: ssl.SSLContext | bool = self._verify(base)
        token = self._token()
        try:
            with self._client(
                base_url=base,
                headers={"authorization": f"Bearer {token}"},
                verify=verify,
                timeout=self._deadline(),
            ) as http:
                response = http.request(call.method, call.route, json=call.body)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise SessionHubError(
                f"no hub answered at {base} ({type(exc).__name__}); it may have stopped",
                kind="unreachable",
            ) from None
        except httpx.HTTPError as exc:
            raise SessionHubError(
                f"the hub at {base} did not answer in time ({type(exc).__name__}); the request "
                "may have reached it, so it is not sent again",
                kind="unreachable",
            ) from None
        return self._answer(response, what)

    def _base(self) -> str:
        """`scheme://<loopback literal>:<port>` for the hub, or `unconfigured`."""
        refused = SessionHubError(
            f"{HUB_URL_VARIABLE} must name a hub on this computer's loopback, as "
            "http://127.0.0.1:<port>; nothing was sent",
            kind="unconfigured",
        )
        parts = urllib.parse.urlsplit(self._hub_url)
        try:
            port = parts.port
        except ValueError:
            raise refused from None
        if (
            parts.scheme not in {"http", "https"}
            or not port
            or parts.username is not None
            or parts.password is not None
            or parts.path not in {"", "/"}
            or parts.query
            or parts.fragment
        ):
            raise refused
        host = HUB_TARGETS.loopback_address(parts.hostname or "")
        if host is None:
            raise refused
        shown = f"[{host}]" if ":" in host else host
        return f"{parts.scheme}://{shown}:{port}"

    def _verify(self, base: str) -> ssl.SSLContext | bool:
        if not base.startswith("https://"):
            return True
        try:
            return self._certificate()
        except (OSError, ValueError, ConfigError) as exc:
            raise SessionHubError(
                f"the hub's certificate could not be read ({type(exc).__name__}); nothing was sent",
                kind="unconfigured",
            ) from None

    def _token(self) -> str:
        """The session's token, read from its file now: never kept between calls."""
        path = self._token_file
        try:
            token = self._tokens.read(path)
        except FileNotFoundError:
            raise SessionHubError(
                f"{path} does not exist: this session's web token is missing", kind="unconfigured"
            ) from None
        except SessionGrantRefused as exc:
            raise SessionHubError(str(exc), kind="unconfigured") from None
        except (OSError, ValueError):
            raise SessionHubError(f"{path} holds no usable token", kind="unconfigured") from None
        if not SessionTokenLookup.usable(token):
            raise SessionHubError(f"{path} holds no usable token", kind="unconfigured")
        return token

    def _deadline(self) -> float:
        """Longer than the hub's own longest web deadline, so the hub always answers first: its
        `[web]` fetch deadline, or three search timeouts (SearXNG's identity check, SearXNG and
        the Brave backup), plus `WEB_TIMEOUT_MARGIN`, as `vibey mcp` waits."""
        try:
            deadline = self._web_settings().timeout_seconds
        except ConfigError:
            deadline = WebToolSettings().timeout_seconds
        return max(deadline, 3 * DEFAULT_TIMEOUT_SECONDS) + WEB_TIMEOUT_MARGIN

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        """The hub's `detail`, as one clean line, or "" when it sent none to read."""
        try:
            document = response.json()
        except ValueError:
            return ""
        detail = document.get("detail") if isinstance(document, dict) else None
        if not isinstance(detail, str):
            return ""
        return " ".join(UntrustedText.clean(detail).split())

    def _answer(self, response: httpx.Response, what: str) -> dict[str, Any]:
        status = response.status_code
        if status == 200:
            try:
                document = response.json()
            except ValueError:
                document = None
            if not isinstance(document, dict):
                raise SessionHubError(_UNREADABLE, kind="failed")
            return document
        detail = self._detail(response)
        said = f": {detail}" if detail else ""
        if status == 401:
            raise SessionHubError(
                "the hub refused this session's token: this session's web access has ended "
                "(the session finished, or its token was revoked or expired)",
                kind="ended",
            )
        if status == 403:
            raise SessionHubError(
                f"the hub does not let this session {what} (HTTP 403){said}", kind="forbidden"
            )
        if status == 429:
            raise SessionHubError(
                detail or "the hub is limiting this session's requests (HTTP 429)", kind="budget"
            )
        raise SessionHubError(f"the hub could not {what} (HTTP {status}){said}", kind="failed")
