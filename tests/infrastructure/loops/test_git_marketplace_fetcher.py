# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fetching a git marketplace: what git is asked, in what environment (SP-LOOPS Task 7).

No test runs git or touches the network: a fake runner records every command and plays git's part
in the staging folder.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from vibey.domain.marketplace_source import MARKETPLACE_SOURCE_RULE, MarketplaceSource
from vibey.infrastructure.loops.git_marketplace_fetcher import (
    ALLOWED_PROTOCOLS,
    GitMarketplaceFetcher,
)
from vibey.infrastructure.loops.interfaces.marketplace_fetcher_interface import (
    MarketplaceFetcherInterface,
)
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import FetchResult

COMMIT = "0123456789abcdef0123456789abcdef01234567"
HTTPS = MARKETPLACE_SOURCE_RULE.classify("https://example.test/acme.git")


class FakeGit:
    """Records each call; `init` makes `.git`, `checkout` writes the tree, `rev-parse` answers
    `commit`. `fail` names a verb that exits 128 with a remote's message on stderr."""

    def __init__(self, commit: str = COMMIT, fail: str | None = None) -> None:
        self.calls: list[tuple[list[str], dict[str, str], Path, float]] = []
        self._commit = commit
        self._fail = fail

    def __call__(
        self, argv: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        argv = list(argv)
        self.calls.append((argv, dict(env), cwd, timeout))
        verb = self.verb(argv)
        if verb == self._fail:
            return subprocess.CompletedProcess(
                argv, 128, "", "remote: \x1b[31mno such ref\x1b[0m\n"
            )
        if verb == "init":
            (cwd / ".git" / "hooks").mkdir(parents=True)
        elif verb == "checkout":
            (cwd / ".claude-plugin").mkdir()
            (cwd / ".claude-plugin" / "marketplace.json").write_text("{}", encoding="utf-8")
        stdout = f"{self._commit}\n" if verb == "rev-parse" else ""
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    @staticmethod
    def verb(argv: Sequence[str]) -> str:
        """The git subcommand: the first argument after the `-c name=value` pairs."""
        index = 1
        while argv[index] == "-c":
            index += 2
        return argv[index]

    def by_verb(self, verb: str) -> list[str]:
        return next(argv for argv, *_ in self.calls if self.verb(argv) == verb)


def _fetcher(git: FakeGit, **options: object) -> GitMarketplaceFetcher:
    options.setdefault("environ", {"PATH": "/usr/bin:/bin", "HOME": "/home/me"})
    return GitMarketplaceFetcher(runner=git, **options)  # type: ignore[arg-type]


def test_the_fetcher_satisfies_its_interface() -> None:
    assert isinstance(GitMarketplaceFetcher(), MarketplaceFetcherInterface)


def test_a_pinned_ref_is_fetched_shallow_checked_out_and_the_git_folder_removed(
    tmp_path: Path,
) -> None:
    git = FakeGit()
    into = tmp_path / "tree"
    result = _fetcher(git).fetch(HTTPS, "v1.2.0", into)
    assert result == FetchResult(COMMIT, ())
    assert [FakeGit.verb(argv) for argv, *_ in git.calls] == [
        "init",
        "fetch",
        "checkout",
        "rev-parse",
    ]
    fetch = git.by_verb("fetch")
    assert fetch[fetch.index("fetch") :] == [
        "fetch",
        "--quiet",
        "--depth=1",
        "--no-tags",
        "--no-recurse-submodules",
        "--",
        "https://example.test/acme.git",
        "v1.2.0",
    ]
    assert git.by_verb("init")[-2:] == ["--template=", "."]
    assert git.by_verb("checkout")[-3:] == ["--detach", "FETCH_HEAD", "--"]
    assert not (into / ".git").exists()
    assert (into / ".claude-plugin" / "marketplace.json").is_file()
    assert oct(into.stat().st_mode & 0o777) == oct(0o700)
    assert all(cwd == into for _, _, cwd, _ in git.calls)


def test_no_ref_fetches_the_default_branch(tmp_path: Path) -> None:
    git = FakeGit()
    _fetcher(git).fetch(HTTPS, None, tmp_path / "tree")
    assert git.by_verb("fetch")[-3:] == ["--", "https://example.test/acme.git", "HEAD"]


def test_every_git_call_runs_with_only_the_allowed_protocols_and_no_hooks(tmp_path: Path) -> None:
    git = FakeGit()
    _fetcher(git).fetch(HTTPS, None, tmp_path / "tree")
    for argv, env, _, _ in git.calls:
        pairs = {argv[i + 1] for i, arg in enumerate(argv) if arg == "-c"}
        assert "protocol.allow=never" in pairs
        assert {f"protocol.{name}.allow=always" for name in ALLOWED_PROTOCOLS} <= pairs
        assert f"core.hooksPath={os.devnull}" in pairs
        assert {"submodule.recurse=false", "fetch.recurseSubmodules=false"} <= pairs
        assert "core.fsmonitor=false" in pairs
        assert env["GIT_ALLOW_PROTOCOL"] == "https:ssh:git"
    assert ALLOWED_PROTOCOLS == ("https", "ssh", "git")


def test_git_sees_a_scrubbed_environment_with_its_own_configuration_neutralised(
    tmp_path: Path,
) -> None:
    git = FakeGit()
    environ = {
        "PATH": "/usr/bin",
        "HOME": "/home/me",
        "SSH_AUTH_SOCK": "/tmp/agent.sock",
        "GIT_SSH_COMMAND": "evil",
        "GIT_DIR": "/elsewhere",
        "GIT_EXEC_PATH": "/evil",
        "GIT_ASKPASS": "/evil/askpass",
        "VIBEY_HUB_TOKEN": "fake-hub-token",
        "BRAVE_API_KEY": "fake-brave-key",
    }
    _fetcher(git, environ=environ).fetch(HTTPS, None, tmp_path / "tree")
    env = git.calls[0][1]
    assert env == {
        "PATH": "/usr/bin",
        "HOME": "/home/me",
        "SSH_AUTH_SOCK": "/tmp/agent.sock",
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ALLOW_PROTOCOL": "https:ssh:git",
        "GIT_LFS_SKIP_SMUDGE": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
    }


def test_a_missing_path_or_home_is_not_invented(tmp_path: Path) -> None:
    git = FakeGit()
    _fetcher(git, environ={}).fetch(HTTPS, None, tmp_path / "tree")
    env = git.calls[0][1]
    assert env["PATH"] == os.defpath
    assert "HOME" not in env and "SSH_AUTH_SOCK" not in env


def test_the_calls_share_one_deadline(tmp_path: Path) -> None:
    git = FakeGit()
    now = iter([100.0, 100.0, 130.0, 160.0, 170.0])
    _fetcher(git, timeout_seconds=90.0, clock=lambda: next(now)).fetch(
        HTTPS, None, tmp_path / "tree"
    )
    assert [timeout for *_, timeout in git.calls] == [90.0, 60.0, 30.0, 20.0]


def test_a_deadline_already_spent_stops_before_the_next_call(tmp_path: Path) -> None:
    git = FakeGit()
    now = iter([0.0, 0.0, 400.0])
    with pytest.raises(MarketplaceFetchError, match="did not finish within 300 seconds"):
        _fetcher(git, clock=lambda: next(now)).fetch(HTTPS, None, tmp_path / "tree")
    assert len(git.calls) == 1


def test_a_git_timeout_is_a_fetch_error(tmp_path: Path) -> None:
    def slow(
        argv: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(list(argv), timeout)

    with pytest.raises(MarketplaceFetchError, match="did not finish within 300 seconds"):
        GitMarketplaceFetcher(runner=slow).fetch(HTTPS, None, tmp_path / "tree")


def test_no_git_installed_is_a_fetch_error(tmp_path: Path) -> None:
    def missing(
        argv: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(2, "No such file or directory", "git")

    with pytest.raises(MarketplaceFetchError, match="git is not installed"):
        GitMarketplaceFetcher(runner=missing).fetch(HTTPS, None, tmp_path / "tree")


def test_a_failing_git_names_the_step_and_its_last_words(tmp_path: Path) -> None:
    with pytest.raises(
        MarketplaceFetchError, match="git fetch failed .exit 128.: remote:"
    ) as error:
        _fetcher(FakeGit(fail="fetch")).fetch(HTTPS, "v9", tmp_path / "tree")
    assert "no such ref" in str(error.value)


def test_a_pinned_commit_must_be_the_commit_fetched(tmp_path: Path) -> None:
    other = "f" * 40
    with pytest.raises(MarketplaceFetchError, match=f"fetched {other}, not the pinned {COMMIT}"):
        _fetcher(FakeGit(commit=other)).fetch(HTTPS, COMMIT, tmp_path / "tree")
    assert _fetcher(FakeGit()).fetch(HTTPS, COMMIT, tmp_path / "ok").commit == COMMIT


@pytest.mark.parametrize("answer", ["", "not a commit\n", "zz" * 20 + "\n"])
def test_an_answer_that_is_not_a_commit_id_is_refused(tmp_path: Path, answer: str) -> None:
    git = FakeGit(commit=answer.strip())
    with pytest.raises(MarketplaceFetchError, match="not a commit id"):
        _fetcher(git).fetch(HTTPS, None, tmp_path / "tree")


def test_a_ref_that_could_be_an_option_or_refspec_never_reaches_git(tmp_path: Path) -> None:
    git = FakeGit()
    with pytest.raises(MarketplaceFetchError, match="ref"):
        _fetcher(git).fetch(HTTPS, "--upload-pack=x", tmp_path / "tree")
    assert git.calls == []


def test_a_local_source_is_not_this_fetchers(tmp_path: Path) -> None:
    git = FakeGit()
    local = MarketplaceSource("/srv/x", "local", "local")
    with pytest.raises(MarketplaceFetchError, match="not a git source"):
        _fetcher(git).fetch(local, None, tmp_path / "tree")
    assert git.calls == []


def test_a_staging_folder_that_already_exists_is_refused(tmp_path: Path) -> None:
    (tmp_path / "tree").mkdir()
    with pytest.raises(MarketplaceFetchError, match="already exists"):
        _fetcher(FakeGit()).fetch(HTTPS, None, tmp_path / "tree")


def test_the_real_runner_runs_a_command_with_no_stdin_and_a_timeout(tmp_path: Path) -> None:
    """The default runner, exercised with `true`/`printf` rather than git: no network."""
    result = GitMarketplaceFetcher.run_command(
        ["printf", "%s", "ok"], {"PATH": os.defpath}, tmp_path, 10.0
    )
    assert (result.returncode, result.stdout) == (0, "ok")
