# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The GitLab forge transport: direct HTTP calls to the GitLab REST API.

This transport implements `vibey_gh.interfaces.forge_transport_interface`. It uses
`urllib.request` to maintain zero runtime dependencies. Authentication is handled
via a private token passed in the `PRIVATE-TOKEN` header.
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
class GitLabTransport(ForgeTransportInterface):
    """Talks to GitLab via HTTP.

    `host` is the GitLab instance URL (e.g., 'gitlab.com').
    `token` is the private access token.
    """

    host: str = "gitlab.com"
    token: str = ""

    @property
    def executable(self) -> str:
        return "http (gitlab)"

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[bool, str]:
        # Since we are not running a CLI, we simulate the return value.
        # In reality, this would be used to run a `git` command or similar.
        # For #138, the primary interaction is through `survey`.
        return False, "GitLabTransport.run is not implemented for direct API calls"

    def survey(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[list[Any] | dict[str, Any], str]:
        # GitLab adapter will pass the API path as the first argument in `args`.
        # Example: args = ["projects/123/merge_requests"]
        if not args:
            return [], "No API path provided"

        path = args[0]
        method = args[1].upper() if len(args) > 1 else "GET"
        body = args[2] if len(args) > 2 else ""
        data = body.encode("utf-8") if body else None
        url = f"https://{self.host}/api/v4/{path}"

        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("PRIVATE-TOKEN", self.token)
        if data is not None:
            req.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read().decode("utf-8")
                value = json.loads(data)
                if isinstance(value, (list, dict)):
                    return value, ""
                return [], "GitLab API returned JSON that is neither a list nor an object"
        except urllib.error.HTTPError as e:
            return [], f"GitLab API error {e.code}: {e.reason}"
        except (OSError, TimeoutError, ValueError) as error:
            return [], f"GitLab transport failure: {error!s}"
