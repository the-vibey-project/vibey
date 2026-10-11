# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What publishing a finished project proposes, and how a person's answer changes it.

The last step of a delivered project is getting its work off the machine: a project whose
checkout has a remote gets its work pushed and a pull request opened; one with no remote gets a
new GitHub repository. Both leave the machine and neither is easily taken back, so this module
is where the proposal is made explicit, and the only place an answer can change it.

Pure: no git, no network. The proposal is derived from the project's name and spec, its
`[publish]` settings (`PublishConfig`) and what the checkout looks like (`PublishTarget`); a
`publish_interview` answer is parsed into a decision here, with every field validated, because
it ends up as an argument to `git` and `gh`.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final

from vibey.domain.config import PUBLISH_VISIBILITIES, PublishConfig

TITLE_LIMIT: Final = 72
"""A pull request title that fits a line of a log."""

DESCRIPTION_LIMIT: Final = 300
"""GitHub's repository description limit is 350."""

BODY_LIMIT: Final = 20_000

CHOICES: Final = ("accept_defaults", "custom", "skip")
"""The options of a `publish_interview` gate. `skip` finishes the project locally."""

_REPO_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
_CUSTOM_KEYS: Final = frozenset(
    {"choice", "title", "body", "base", "draft", "visibility", "repo", "owner", "description"}
)


class PublishKind(StrEnum):
    """What publishing does for this project."""

    PULL_REQUEST = "pull_request"
    NEW_REPOSITORY = "new_repository"


class PublishAnswerError(ValueError):
    """A `publish_interview` answer that cannot be used; the message says what to fix."""


class PublishFailed(RuntimeError):
    """Publishing could not be done; the message says what git or gh said, trimmed."""


@dataclass(frozen=True, slots=True)
class PublishResult:
    """Where the work now is. `already_there` is true when a retry found it published."""

    url: str
    kind: "PublishKind"
    already_there: bool = False


@dataclass(frozen=True, slots=True)
class PublishTarget:
    """What the project's checkout looks like to a publisher.

    `remote_url` is None when the checkout has no remote of the configured name: that is what
    makes a project new. `default_branch` is the remote's, when it could be read, and
    `remote_empty` says the remote has no branches at all: a repository an earlier attempt
    created and did not get to push to, which is finished by pushing, not by a pull request.
    """

    branch: str
    remote: str
    remote_url: str | None
    default_branch: str | None
    repo_path: str
    remote_empty: bool = False

    @property
    def has_remote(self) -> bool:
        return self.remote_url is not None


@dataclass(frozen=True, slots=True)
class PublishPlan:
    """Exactly what publishing will do. Shown to the person before it happens."""

    kind: PublishKind
    branch: str
    remote: str
    base: str
    title: str
    body: str
    draft: bool
    repo_name: str
    owner: str | None
    visibility: str
    description: str
    existing_remote: str | None = None
    """The empty remote an earlier attempt created: nothing is created, the branch is pushed."""

    def summary(self) -> str:
        """The plan as the interview prompt prints it."""
        if self.kind is PublishKind.PULL_REQUEST:
            state = "a draft pull request" if self.draft else "a pull request ready for review"
            return (
                f"Push branch {self.branch} to {self.remote} and open {state} into "
                f"{self.base}.\nTitle: {self.title}"
            )
        if self.existing_remote is not None:
            return (
                f"Push branch {self.branch} to the empty repository at {self.existing_remote} "
                f"as {self.base}."
            )
        owner = f"{self.owner}/" if self.owner else ""
        return (
            f"Create the {self.visibility} GitHub repository {owner}{self.repo_name} and push "
            f"branch {self.branch} to it as {self.base}.\nDescription: {self.description}"
        )


@dataclass(frozen=True, slots=True)
class PublishDecision:
    """What a person's answer settled: publish this plan, or do not."""

    plan: PublishPlan | None
    reason: str = ""

    @property
    def skipped(self) -> bool:
        return self.plan is None


def slug(name: str) -> str:
    """A repository name from a project name: lower case, runs of anything else become '-'."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower()).strip("-._")
    return cleaned[:100] or "project"


def _one_line(text: str, limit: int) -> str:
    line = " ".join(text.split())
    return line if len(line) <= limit else line[: limit - 1].rstrip() + "\u2026"


def default_plan(
    *,
    project_name: str,
    objective: str,
    criteria: Sequence[str],
    cycle: int,
    target: PublishTarget,
    config: PublishConfig,
) -> PublishPlan:
    """The proposal: private and a draft unless the project's settings say otherwise."""
    is_new = not target.has_remote or target.remote_empty
    kind = PublishKind.NEW_REPOSITORY if is_new else PublishKind.PULL_REQUEST
    summary = _one_line(objective, 400) or project_name
    listed = ", ".join(criteria) if criteria else "none recorded"
    body = (
        f"## Summary\n\n{objective.strip() or project_name}\n\n"
        f"## Acceptance criteria\n\n{listed}\n\n"
        f"## How this was built\n\n"
        f"Built by vibey as project `{project_name}`, cycle {cycle}. Each work item passed its "
        f"verification gates before it was merged into this branch, and the review was "
        f"accepted. Review it as you would any pull request.\n"
    )
    return PublishPlan(
        kind=kind,
        branch=target.branch,
        remote=target.remote,
        base=config.base or target.default_branch or "main",
        title=_one_line(f"feat: {summary}", TITLE_LIMIT),
        body=body,
        draft=config.draft,
        repo_name=slug(project_name),
        owner=config.owner,
        visibility=config.visibility,
        description=_one_line(summary, DESCRIPTION_LIMIT),
        existing_remote=target.remote_url if target.remote_empty else None,
    )


def decide(plan: PublishPlan, answer: Mapping[str, object] | None) -> PublishDecision:
    """Apply a `publish_interview` answer to the proposal.

    `{"choice": "accept_defaults"}` (or no choice) publishes as proposed; `skip` does not
    publish; `custom` changes only the fields it names. Anything else is refused, naming the
    problem, so a typo cannot publish something nobody looked at.
    """
    given = dict(answer or {})
    choice = str(given.get("choice") or "accept_defaults").lower()
    if choice == "skip":
        return PublishDecision(None, "the operator chose not to publish")
    if choice == "accept_defaults":
        return PublishDecision(plan)
    if choice != "custom":
        raise PublishAnswerError(f"choice must be one of {', '.join(CHOICES)}, got {choice!r}")
    unknown = sorted(set(given) - _CUSTOM_KEYS)
    if unknown:
        raise PublishAnswerError(
            f"{unknown[0]!r} is not a field (fields: {', '.join(sorted(_CUSTOM_KEYS - {'choice'}))})"
        )
    return PublishDecision(_customised(plan, given))


def _customised(plan: PublishPlan, given: Mapping[str, object]) -> PublishPlan:
    changes: dict[str, object] = {}
    if "title" in given:
        changes["title"] = _text(given["title"], "title", TITLE_LIMIT, one_line=True)
    if "body" in given:
        changes["body"] = _text(given["body"], "body", BODY_LIMIT)
    if "description" in given:
        changes["description"] = _text(
            given["description"], "description", DESCRIPTION_LIMIT, one_line=True
        )
    if "base" in given:
        changes["base"] = _name(given["base"], "base")
    if "owner" in given:
        changes["owner"] = _name(given["owner"], "owner")
    if "repo" in given:
        repo = given["repo"]
        if not isinstance(repo, str) or not _REPO_NAME.fullmatch(repo) or repo in {".", ".."}:
            raise PublishAnswerError("repo must be a plain repository name")
        changes["repo_name"] = repo
    if "draft" in given:
        if not isinstance(given["draft"], bool):
            raise PublishAnswerError("draft must be true or false")
        changes["draft"] = given["draft"]
    if "visibility" in given:
        if given["visibility"] not in PUBLISH_VISIBILITIES:
            raise PublishAnswerError(f"visibility must be one of {PUBLISH_VISIBILITIES}")
        changes["visibility"] = given["visibility"]
    return replace(plan, **changes)  # type: ignore[arg-type]


def _text(value: object, field: str, limit: int, *, one_line: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublishAnswerError(f"{field} must be some text")
    if len(value) > limit:
        raise PublishAnswerError(f"{field} is {len(value)} characters; the limit is {limit}")
    if one_line and "\n" in value:
        raise PublishAnswerError(f"{field} must be one line")
    return value.strip()


def _name(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise PublishAnswerError(f"{field} must be a plain name, not an option")
    return value
