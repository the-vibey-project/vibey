# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The forge-neutral nouns: what vibey-gh talks about, whichever forge it is talking to.

Everything above a forge adapter speaks in these, and never in a platform's own words. A
GitHub pull request, a GitLab merge request and a Forgejo pull request are each a
`ChangeRequest` here; a GitHub ruleset and a GitLab protected branch are each a
`ProtectedRef`. The adapter translates, in both directions, and is the only code that
knows which forge it is (#138, and this package's ADR 0001, which records the vocabulary
as proposed until the operator ratifies it).

Pure data: no I/O, no clock, nothing imported from this package. A seam may therefore
name these the way it names `vibey_gh.config`, which is declaring and not consuming.

Each record carries its identity and nothing a verb has not needed yet. A field is added by
the first verb that reads it from a real forge, never ahead of one, so the vocabulary never
promises a shape no adapter has had to produce. `ForgeRelease` is the one a verb returns
today; the rest name what the platform abstraction is about to need (#136, #145).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ChangeRequest",
    "CheckResult",
    "ForgeComment",
    "ForgeKind",
    "ForgeLabel",
    "ForgeRelease",
    "ForgeRepository",
    "ProtectedRef",
]


class ForgeKind(StrEnum):
    """Every forge the standard names. Naming one is not the same as having an adapter for
    it: which kinds `[platform] kind` accepts today is configuration's to say."""

    GITHUB = "github"
    GITLAB = "gitlab"
    FORGEJO = "forgejo"


@dataclass(frozen=True)
class ForgeRepository:
    """One repository on one forge. `owner` is the whole namespace, so a GitLab project in
    a nested group is `group/subgroup`, and `full_name` is what every forge's client takes."""

    kind: ForgeKind
    host: str
    owner: str
    name: str

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class ChangeRequest:
    """A proposed change: a pull request on GitHub and Forgejo, a merge request on GitLab.

    `head_sha` is part of its identity, not decoration. A verdict binds to the commit it
    judged, never to the change request's moving head, and a record without the SHA could
    not say which commit it is about.
    """

    number: int
    head_ref: str
    head_sha: str
    base_ref: str


@dataclass(frozen=True)
class ForgeComment:
    """A comment on a change request or an issue. `id` is the forge's own identifier, kept
    opaque: GitHub alone has two (a database id and a node id) and each API wants one."""

    id: str
    author: str
    body: str


@dataclass(frozen=True)
class CheckResult:
    """One check's result on one exact commit. `conclusion` is empty while the check has not
    finished, so an unfinished check is never mistaken for a passing one."""

    name: str
    head_sha: str
    conclusion: str = ""


@dataclass(frozen=True)
class ForgeRelease:
    """A published or draft release. `tag` is the tag it is cut from, `name` its title.

    A forge may return a release without a tag (GitHub's untagged drafts), so either may be
    empty and `label` is the one a person would recognise.
    """

    tag: str
    name: str = ""
    draft: bool = False

    @property
    def label(self) -> str:
        return self.tag or self.name


@dataclass(frozen=True)
class ForgeLabel:
    """A label as a forge attaches it to a change request or an issue."""

    name: str


@dataclass(frozen=True)
class ProtectedRef:
    """A branch the forge refuses to let anyone rewrite: a GitHub ruleset or branch
    protection, a GitLab or Forgejo protected branch. `ref` is the branch name."""

    ref: str
