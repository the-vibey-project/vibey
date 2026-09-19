# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The GitHub forge adapter: the forge-neutral verbs, spoken as `gh` command lines.

Implements `vibey_gh.interfaces.forge_adapter_interface` on the `gh` transport. Every
command line here is one that already ran before the adapter existed, moved rather than
rewritten, with the same argv and the same working directory: the adapter's job is to
translate the answer into `vibey_gh.forge` nouns, not to ask a different question. The
proof is in `test/test_forge_github.py`, which drives the code as it stood and the code as
it stands through one fake `gh` and requires the same invocations and the same report.

`gh` runs in the repository's clone, as it always has, so it finds the repository from the
clone's own remote rather than from anything this process tells it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vibey_gh.forge import ForgeRelease
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface, WorkingDirectory

# The host `gh` talks to when nothing names another. Naming it changes nothing, so a
# `[platform] host` equal to it is not exported to the client (see `GhTransport.host`).
GH_DEFAULT_HOST = "github.com"


@dataclass(frozen=True)
class GitHubForge(ForgeAdapterInterface):
    """One GitHub repository, reached through `gh` run in its clone at `root`."""

    root: WorkingDirectory
    transport: GhTransportInterface = field(default_factory=GhTransport)

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        pulls, problem = self._listing("pr", "list", "--json", "headRefName", "--limit", str(limit))
        heads = frozenset(
            head
            for pull in pulls
            if isinstance(pull, dict) and isinstance(head := pull.get("headRefName", ""), str)
        )
        return heads, problem

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        rows, problem = self._listing(
            "release", "list", "--json", "tagName,name,isDraft", "--limit", str(limit)
        )
        releases = tuple(
            ForgeRelease(
                tag=str(row.get("tagName") or ""),
                name=str(row.get("name") or ""),
                draft=bool(row.get("isDraft")),
            )
            for row in rows
            if isinstance(row, dict)
        )
        return releases, problem

    def _listing(self, *args: str) -> tuple[list[Any], str]:
        """Ask for a listing, and refuse to read anything else as one.

        The transport's `survey` answers for any JSON shape, because an endpoint may
        legitimately return an object. A listing may not. Iterating a dict yields its keys,
        so a caller handed one would enumerate field names, match none of them, and report
        an empty result with no problem: "could not look" wearing the face of "nothing
        there", which is the collapse the `(value, problem)` shape exists to prevent. `gh`
        exits zero with an error envelope such as `{"message": "Bad credentials"}` often
        enough that this is not hypothetical.
        """
        value, problem = self.transport.survey(args, cwd=self.root)
        if problem:
            return [], problem
        if not isinstance(value, list):
            label = " ".join((self.transport.executable, *args[:2]))
            return [], f"`{label}` returned a JSON object where a listing was expected"
        return value, ""
