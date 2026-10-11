# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Publishes a finished project to GitHub with `git` and `gh`, and nothing wider.

Declared by `application/interfaces/publish.py::PublisherInterface`. What it does:

- A project whose checkout has a remote: push the integration branch to it (never forced, never
  to the base branch) and open a pull request, as a draft unless the plan says otherwise.
- A project with no remote, or one whose remote is empty because an earlier attempt created it
  and did not get to push: create the repository (`gh repo create`, private unless the plan says
  public) when there is none, and push the branch to it as the base branch.

Because this is the one place vibey's work leaves the machine, it checks the repository first.
An engine session works in a linked worktree and can write the repository's shared config, and
a push runs whatever that config names. So before anything is pushed it refuses a repository
whose own config sets a command git would run (`core.sshCommand`, `core.gitProxy`,
`core.askPass`, a credential helper) and a remote that is not an https or ssh address
(`ext::`, a local path), and it runs git with hooks off, as vibey's other git calls do.
It does not decide *where* the work goes: the plan names the remote, and the interview shows
its address.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Final

from vibey.domain.publish import (
    PublishFailed,
    PublishKind,
    PublishPlan,
    PublishResult,
    PublishTarget,
)
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.publish.command_runner import ProgramRunner
from vibey.infrastructure.publish.interfaces import ProgramRunnerInterface

_NEUTRAL: Final = ("-c", f"core.hooksPath={os.devnull}", "-c", "core.fsmonitor=false")
_ALLOWED_REMOTE: Final = re.compile(r"^(https://|ssh://|[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:)\S+$")
_DENIED_CONFIG: Final = re.compile(
    r"^(core\.(sshcommand|gitproxy|askpass|pager|editor|hookspath|fsmonitor)"
    r"|credential(\..+)?\.helper"
    r"|remote\..+\.(receivepack|uploadpack|vcs))=",
    re.IGNORECASE,
)
_MESSAGE_LIMIT: Final = 600


def _said(result: CommandResult) -> str:
    text = (result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}")[
        :_MESSAGE_LIMIT
    ]
    return text.replace("\n", " ")


class GitHubPublisher:
    """Publishes through `git` and `gh`, run by an injected `ProgramRunnerInterface`."""

    def __init__(self, runner: ProgramRunnerInterface | None = None) -> None:
        self._runner = ProgramRunner() if runner is None else runner

    async def problem(self) -> str | None:
        if (await self._runner.run(("git", "--version"))).returncode != 0:
            return "git is not installed"
        if (await self._runner.run(("gh", "--version"))).returncode != 0:
            return "the GitHub CLI (gh) is not installed (https://cli.github.com)"
        if (await self._runner.run(("gh", "auth", "status"))).returncode != 0:
            return "gh is not logged in: run `gh auth login`"
        return None

    async def inspect(self, repo_path: Path, *, branch: str, remote: str) -> PublishTarget:
        branch_ref = await self._git(
            repo_path, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False
        )
        if branch_ref.returncode != 0:
            raise PublishFailed(
                f"branch {branch} does not exist in {repo_path}: nothing was integrated to publish"
            )
        await self._refuse_dangerous_config(repo_path)
        found = await self._git(repo_path, "remote", "get-url", "--push", remote, check=False)
        url = found.stdout.strip() if found.returncode == 0 and found.stdout.strip() else None
        default_branch: str | None = None
        empty = False
        if url is not None:
            if not _ALLOWED_REMOTE.fullmatch(url):
                raise PublishFailed(
                    f"the {remote} remote ({url}) is not an https or ssh address, so nothing "
                    "is pushed to it"
                )
            listing = await self._git(repo_path, "ls-remote", "--symref", remote, "HEAD")
            default_branch, empty = self._default_branch(listing.stdout)
        return PublishTarget(
            branch=branch,
            remote=remote,
            remote_url=url,
            default_branch=default_branch,
            repo_path=str(repo_path),
            remote_empty=empty,
        )

    async def publish(self, plan: PublishPlan, *, repo_path: Path) -> PublishResult:
        await self._refuse_dangerous_config(repo_path)
        if plan.kind is PublishKind.PULL_REQUEST:
            return await self._pull_request(plan, repo_path)
        return await self._new_repository(plan, repo_path)

    # -- the two things publishing does ---------------------------------------------------

    async def _pull_request(self, plan: PublishPlan, repo_path: Path) -> PublishResult:
        if plan.branch == plan.base:
            raise PublishFailed(
                f"the branch to publish ({plan.branch}) is the base branch: nothing is pushed to it"
            )
        await self._push(repo_path, plan.remote, f"{plan.branch}:refs/heads/{plan.branch}")
        listed = await self._gh(
            repo_path,
            "pr", "list", "--head", plan.branch, "--base", plan.base,
            "--state", "open", "--json", "url", "--limit", "1",
        )  # fmt: skip
        existing = self._first_url(listed.stdout)
        if existing:
            return PublishResult(existing, PublishKind.PULL_REQUEST, already_there=True)
        with tempfile.TemporaryDirectory(prefix="vibey-publish-") as scratch:
            body = Path(scratch) / "body.md"
            body.write_text(plan.body, encoding="utf-8")
            argv = [
                "pr", "create", "--base", plan.base, "--head", plan.branch,
                "--title", plan.title, "--body-file", str(body),
            ]  # fmt: skip
            if plan.draft:
                argv.append("--draft")
            created = await self._gh(repo_path, *argv)
        return PublishResult(self._url_line(created.stdout), PublishKind.PULL_REQUEST)

    async def _new_repository(self, plan: PublishPlan, repo_path: Path) -> PublishResult:
        url = plan.existing_remote
        if url is None:
            slug = f"{plan.owner}/{plan.repo_name}" if plan.owner else plan.repo_name
            created = await self._gh(
                repo_path,
                "repo", "create", slug,
                "--public" if plan.visibility == "public" else "--private",
                "--description", plan.description,
                "--source", str(repo_path), "--remote", plan.remote,
            )  # fmt: skip
            url = self._url_line(created.stdout)
        await self._push(repo_path, plan.remote, f"{plan.branch}:refs/heads/{plan.base}")
        return PublishResult(
            url, PublishKind.NEW_REPOSITORY, already_there=plan.existing_remote is not None
        )

    # -- helpers --------------------------------------------------------------------------

    async def _push(self, repo_path: Path, remote: str, refspec: str) -> None:
        # No `--force`, and the refspec has no leading `+`: a push that is not a fast-forward
        # is refused by the remote and reported, never made to succeed.
        await self._git(repo_path, "push", "--set-upstream", remote, refspec)

    async def _git(self, repo_path: Path, *args: str, check: bool = True) -> CommandResult:
        result = await self._runner.run(("git", *_NEUTRAL, "-C", str(repo_path), *args))
        if check and result.returncode != 0:
            raise PublishFailed(f"git {args[0]} failed: {_said(result)}")
        return result

    async def _gh(self, repo_path: Path, *args: str) -> CommandResult:
        result = await self._runner.run(("gh", *args), cwd=repo_path)
        if result.returncode != 0:
            raise PublishFailed(f"gh {' '.join(args[:2])} failed: {_said(result)}")
        return result

    async def _refuse_dangerous_config(self, repo_path: Path) -> None:
        for scope in ("--local", "--worktree"):
            listed = await self._git(repo_path, "config", scope, "--list", check=False)
            if listed.returncode != 0:
                continue  # no such scope in this repository
            for line in listed.stdout.splitlines():
                if _DENIED_CONFIG.match(line):
                    key = line.split("=", 1)[0]
                    raise PublishFailed(
                        f"the repository's own git config sets {key}, a command git would run "
                        "when pushing. A work item can write that file, so vibey will not push "
                        "from this repository until it is removed (git config --unset "
                        f"{key})"
                    )

    @staticmethod
    def _default_branch(listing: str) -> tuple[str | None, bool]:
        """The remote's default branch from `ls-remote --symref`, and whether it is empty."""
        if not listing.strip():
            return None, True
        match = re.search(r"^ref: refs/heads/(\S+)\s+HEAD$", listing, re.MULTILINE)
        return (match.group(1) if match else None), False

    @staticmethod
    def _first_url(raw: str) -> str | None:
        try:
            items = json.loads(raw or "[]")
        except ValueError:
            return None
        if isinstance(items, list) and items and isinstance(items[0], dict):
            url = items[0].get("url")
            return url if isinstance(url, str) and url else None
        return None

    @staticmethod
    def _url_line(output: str) -> str:
        for line in reversed(output.splitlines()):
            if line.strip().startswith("https://"):
                return line.strip()
        raise PublishFailed(f"gh did not say where it was published: {output.strip()[:200]!r}")
