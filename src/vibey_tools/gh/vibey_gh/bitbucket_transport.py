# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Bitbucket forge transport: direct HTTP calls to the Bitbucket Cloud REST API (#298).

This transport implements `vibey_gh.interfaces.forge_transport_interface`. It uses
`urllib.request` to keep vibey-gh at zero runtime dependencies, and it has the shape of
`forgejo_transport.py` and `gitlab_transport.py`: `survey` takes a path, then optionally a method
and a JSON body, and answers the decoded value and a problem.

Two things differ from those transports, both because Bitbucket's API differs:

- **Authentication.** A token with a colon in it is a `username:app-password` pair and is sent as
  HTTP Basic; any other token is a repository, project or workspace access token and is sent as a
  Bearer token. An empty token sends no `Authorization` header, which is what a public
  repository needs.
- **Pagination.** A listing is `{"values": [...], "next": "<url>"}`. A GET that answers one is
  followed to its last page and returned as the list of every value, so a caller never sees a
  page. The `next` link is followed only when it stays on this transport's own host over HTTPS,
  because the next request carries the credential: a link that leaves the host ends the walk
  with a problem rather than sending the token somewhere else.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface, WorkingDirectory

# A listing longer than this many pages is a loop or a runaway, not a repository: the walk stops
# with a problem naming the cap rather than returning a partial list as though it were whole.
MAX_PAGES = 100


@dataclass(frozen=True)
class BitbucketTransport(ForgeTransportInterface):
    """Talks to Bitbucket via HTTP.

    `host` is the API host (Bitbucket Cloud's is 'api.bitbucket.org'; a self-managed
    instance is named here too).
    `token` is an access token, or `username:app-password`.
    """

    host: str = "api.bitbucket.org"
    token: str = ""
    timeout: float = 30.0
    opener: Callable[..., Any] = field(default=urllib.request.urlopen, repr=False, compare=False)

    @property
    def executable(self) -> str:
        return "http (bitbucket)"

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[bool, str]:
        return False, "BitbucketTransport.run is not implemented for direct API calls"

    def survey(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[list[Any] | dict[str, Any], str]:
        if not args:
            return [], "No API path provided"

        path = args[0]
        method = args[1].upper() if len(args) > 1 else "GET"
        body = args[2] if len(args) > 2 else ""
        data = body.encode("utf-8") if body else None

        value, problem = self._call(f"https://{self.host}/2.0/{path}", method, data)
        if problem or method != "GET":
            return value, problem
        return self._paged(value)

    def _paged(self, first: list[Any] | dict[str, Any]) -> tuple[list[Any] | dict[str, Any], str]:
        """Follow `next` links from a listing's first page, or return a non-listing as it is."""
        if not isinstance(first, dict) or not isinstance(first.get("values"), list):
            return first, ""
        page: dict[str, Any] = first
        collected: list[Any] = list(page["values"])
        for _ in range(MAX_PAGES - 1):
            link = page.get("next")
            if not link:
                return collected, ""
            parts = urlsplit(str(link))
            if parts.scheme != "https" or parts.netloc != self.host:
                return [], f"Bitbucket paging link leaves {self.host}; not following it"
            following, problem = self._call(str(link), "GET", None)
            if problem:
                return [], problem
            if not isinstance(following, dict) or not isinstance(following.get("values"), list):
                return [], "Bitbucket API returned a page that is not a listing"
            page = following
            collected.extend(page["values"])
        if page.get("next"):
            return [], f"Bitbucket listing runs past {MAX_PAGES} pages; stopped"
        return collected, ""

    def _call(
        self, url: str, method: str, data: bytes | None
    ) -> tuple[list[Any] | dict[str, Any], str]:
        req = urllib.request.Request(url, data=data, method=method)
        authorization = self._authorization()
        if authorization:
            req.add_header("Authorization", authorization)
        if data is not None:
            req.add_header("Content-Type", "application/json")

        try:
            with self.opener(req, timeout=self.timeout) as resp:
                text = resp.read().decode("utf-8")
                if not text.strip():
                    return {}, ""
                value = json.loads(text)
                if isinstance(value, (list, dict)):
                    return value, ""
                return [], "Bitbucket API returned JSON that is neither a list nor an object"
        except urllib.error.HTTPError as e:
            return [], f"Bitbucket API error {e.code}: {e.reason}{self._detail(e)}"
        except (OSError, TimeoutError, ValueError) as error:
            return [], f"Bitbucket transport failure: {error!s}"

    def _authorization(self) -> str:
        if not self.token:
            return ""
        if ":" in self.token:
            return "Basic " + base64.b64encode(self.token.encode("utf-8")).decode("ascii")
        return f"Bearer {self.token}"

    @staticmethod
    def _detail(error: urllib.error.HTTPError) -> str:
        """Bitbucket's own sentence for a failure (`{"error": {"message": ...}}`), if it gave one."""
        try:
            message = json.loads(error.read().decode("utf-8"))["error"]["message"]
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return ""
        return f": {message}" if isinstance(message, str) and message else ""
