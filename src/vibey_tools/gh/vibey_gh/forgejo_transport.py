# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Forgejo forge transport: direct HTTP calls to the Forgejo/Gitea REST API.

This transport implements `vibey_gh.interfaces.forge_transport_interface`. It uses
`urllib.request` to maintain zero runtime dependencies. Authentication is handled
via a private token passed in the `Authorization: token <token>` header.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface, WorkingDirectory


@dataclass(frozen=True)
class ForgejoTransport(ForgeTransportInterface):
    """Talks to Forgejo via HTTP.

    `host` is the Forgejo instance URL (e.g., 'forgejo.local').
    `token` is the private access token.
    """

    host: str = "forgejo.local"
    token: str = ""

    @property
    def executable(self) -> str:
        return "http (forgejo)"

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[bool, str]:
        return False, "ForgejoTransport.run is not implemented for direct API calls"

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
        url = f"https://{self.host}/api/v1/{path}"

        req = urllib.request.Request(url)
        req.add_header("Authorization", f"token {self.token}")

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read().decode("utf-8")
                value = json.loads(data)
                if isinstance(value, (list, dict)):
                    return value, ""
                return [], "Forgejo API returned JSON that is neither a list nor an object"
        except urllib.error.HTTPError as e:
            return [], f"Forgejo API error {e.code}: {e.reason}"
        except (OSError, TimeoutError, ValueError) as error:
            return [], f"Forgejo transport failure: {error!s}"
