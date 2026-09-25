# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sovereign readiness (doctrine 8.a): the probe that makes preferring free safe, and the
heartbeat that feeds it -- published only when the lane can serve, only through a gate,
never past one.

Every repository here -- the timer's clone, its bare remote -- is made under pytest's
`tmp_path`; nothing touches the repository the suite runs in."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from vibey_gh import cli, sovereign
from vibey_gh.cli import main
from vibey_gh.config import IssueAutomationConfig, PrAutomationFallbackConfig, load_config
from vibey_gh.heartbeat_clone import HOOK_TEMPLATE, HeartbeatClone
from vibey_gh.interfaces.sovereign_interface import SovereignHeartbeatInterface
from vibey_gh.sovereign import TIMED_OUT, SovereignHeartbeat, beat, probe
from vibey_gh.sovereign_lane import LaneState
from vibey_gh.sovereign_runner import TEMPLATES as RUNNER_TEMPLATES

REF = "refs/vibey-gh/sovereign-heartbeat"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


class _Lane:
    """A lane whose readiness is exactly what the test says, and which counts the asking."""

    def __init__(self, serving: bool = True, reason: str = "1 runner online; m answers") -> None:
        self.state = LaneState(serving, reason)
        self.asked = 0

    def assess(self) -> LaneState:
        self.asked += 1
        return self.state


class _BrokenLane:
    """A readiness that raises instead of answering."""

    def assess(self) -> LaneState:
        raise RuntimeError("the runners API returned a page nobody expected")


SERVING = _Lane()


@pytest.fixture
def gate(tmp_path: Path) -> Path:
    """An executable pre-push hook for the faked repository to name as its gate."""
    hook = tmp_path / "hooks" / "pre-push"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    hook.chmod(0o755)
    return hook


@pytest.fixture
def fake(monkeypatch, gate):
    """Drive `_run` from a table keyed on a word of the git argv. The repository's gate is
    `gate` unless the table answers `rev-parse` itself; every call is recorded, and the
    push is the one call made with `stderr=True`."""

    def install(script: dict[str, tuple[int, str]]) -> list[tuple[str, ...]]:
        calls: list[tuple[str, ...]] = []
        table = {"rev-parse": (0, str(gate)), **script}

        def run(*cmd: str, cwd=None, stderr=False):
            calls.append(cmd)
            assert stderr == ("push" in cmd), cmd
            for key, result in table.items():
                if key in cmd:
                    return result
            return (0, "")

        monkeypatch.setattr(sovereign, "_run", run)
        return calls

    return install


def test_the_heartbeat_honours_its_interface():
    assert isinstance(SovereignHeartbeat(REF), SovereignHeartbeatInterface)


def test_the_sovereign_lane_is_offered_only_while_the_heartbeat_is_fresh(fake):
    fake({"log": (0, "1000")})
    assert probe(REF, max_age_minutes=15, now=1300.0).ready
    verdict = probe(REF, max_age_minutes=15, now=1300.0)
    assert verdict.age_seconds == 300 and "300s old" in verdict.reason


def test_a_stale_heartbeat_treats_the_runner_as_offline(fake):
    """The whole point: a machine that has stopped saying it is up is not up. Offering
    the lane anyway queues a job forever against a runner nobody is running."""
    fake({"log": (0, "1000")})
    verdict = probe(REF, max_age_minutes=15, now=1000.0 + 16 * 60)
    assert not verdict.ready
    assert "16m old" in verdict.reason and "treating the runner as offline" in verdict.reason


def test_a_missing_heartbeat_is_a_fact_not_a_failure(fake):
    fake({"fetch": (1, "")})
    verdict = probe(REF, max_age_minutes=15)
    assert not verdict.ready and verdict.age_seconds is None
    assert "no sovereign heartbeat" in verdict.reason


@pytest.mark.parametrize("raw", [(1, "1000"), (0, "not-a-timestamp"), (0, "")])
def test_an_unreadable_heartbeat_never_reports_ready(fake, raw):
    fake({"log": raw})
    assert not probe(REF, max_age_minutes=15).ready


def test_a_future_dated_heartbeat_is_refused(fake):
    """Clock skew must not be able to manufacture readiness."""
    fake({"log": (0, "9000")})
    verdict = probe(REF, max_age_minutes=15, now=1000.0)
    assert not verdict.ready and "dated in the future" in verdict.reason


# --- publishing: honest, and through the gate ---------------------------------------------


def test_a_heartbeat_is_an_empty_commit_on_a_ref_that_is_not_a_branch(fake):
    calls = fake({"hash-object": (0, "tree1"), "commit-tree": (0, "c0ffee")})
    result = beat(REF, readiness=SERVING)
    assert result.ready and result.age_seconds == 0
    assert result.reason.endswith(": 1 runner online; m answers")
    pushed = next(c for c in calls if "push" in c)
    # A compare-and-swap on a ref that does not exist yet: an empty lease means "absent".
    assert pushed == ("git", "push", f"--force-with-lease={REF}:", "origin", f"c0ffee:{REF}")
    assert "refs/heads/" not in pushed[-1]


def test_a_heartbeat_never_skips_the_pre_push_gate(fake):
    """12.d forbids `--no-verify`, with no exceptions: the heartbeat goes through the gate,
    and the gate lets it through by its own rule (`vibey_gh.push_scope`). Nor is it a bare
    `--force`: only the exact value that was read is ever replaced."""
    calls = fake({"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert beat(REF, readiness=SERVING).ready
    argv = [arg for call in calls for arg in call]
    assert "--no-verify" not in argv and "--force" not in argv and "-f" not in argv
    assert not any(arg.startswith("+") for arg in argv)


def test_the_gate_is_found_where_git_would_run_it(fake, gate):
    """`core.hooksPath` honoured: the hook's path is asked of git, not assumed."""
    calls = fake({"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert beat(REF, readiness=SERVING).ready
    assert calls[0] == (
        "git",
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "hooks/pre-push",
    )


@pytest.mark.parametrize(
    "setup, expected",
    [
        (lambda gate, tmp: ({}, str(tmp / "no-such-clone")), "does not exist"),
        (lambda gate, tmp: ({"rev-parse": (128, "")}, None), "is not a git repository"),
        (lambda gate, tmp: ({"rev-parse": (0, str(tmp / "absent"))}, None), "no executable"),
        (lambda gate, tmp: (gate.chmod(0o644) or {}, None), "no executable pre-push gate"),
    ],
)
def test_no_heartbeat_is_published_without_a_repository_and_its_gate(
    fake, gate, tmp_path, setup, expected
):
    """A heartbeat is only ever pushed through a gate: a missing clone, a directory that is
    no repository, a missing hook or one git cannot run all withhold it, before the lane is
    even asked, and nothing else runs."""
    script, cwd = setup(gate, tmp_path)
    calls = fake(script)
    lane = _Lane()
    result = beat(REF, readiness=lane, cwd=cwd)
    assert not result.ready and result.reason.startswith("heartbeat withheld: ")
    assert expected in result.reason and "vibey-gh heartbeat install" in result.reason
    assert lane.asked == 0
    assert not any("push" in call for call in calls)


def test_a_lane_that_cannot_serve_publishes_nothing_at_all(fake):
    """A heartbeat is a claim that a job will be taken. Withheld, it goes stale on its own
    and the gate falls back to asking a human, which is the honest answer."""
    calls = fake({})
    lane = _Lane(False, "no runner labelled vibey-local-r is online for o/r (none registered)")
    result = beat(REF, readiness=lane)
    assert not result.ready and lane.asked == 1
    assert result.reason == (
        "heartbeat withheld: no runner labelled vibey-local-r is online for o/r (none registered)"
    )
    assert [call[1] for call in calls] == ["rev-parse"]


def test_a_readiness_that_raises_withholds_the_beat_and_never_raises(fake):
    calls = fake({})
    result = beat(REF, readiness=_BrokenLane())
    assert not result.ready
    assert result.reason == (
        "heartbeat withheld: the lane's readiness could not be read (RuntimeError: the"
        " runners API returned a page nobody expected)"
    )
    assert not any("push" in call for call in calls)


def test_an_earlier_heartbeat_is_replaced_by_compare_and_swap(fake):
    old = "a" * 40
    calls = fake(
        {
            "ls-remote": (0, f"{old}\t{REF}"),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\nauthor x\n\nsovereign heartbeat"),
            "rev-list": (0, f"{old}\n{EMPTY_TREE}"),
        }
    )
    assert beat(REF, readiness=SERVING).ready
    assert next(c for c in calls if "push" in c)[2] == f"--force-with-lease={REF}:{old}"
    assert not any("fetch" in c for c in calls)  # the object was already here
    # The lease's value is read as the push would send it, replacements refused.
    assert ("git", "--no-replace-objects", "cat-file", "-e", old) in calls
    assert any(c[:3] == ("git", "--no-replace-objects", "rev-list") for c in calls)


def test_an_earlier_heartbeat_missing_locally_is_fetched_before_it_is_judged(fake):
    old = "a" * 40
    calls = fake(
        {
            "ls-remote": (0, f"{old}\t{REF}\n{'b' * 40}\trefs/other/{REF}"),
            "-e": (1, ""),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\n\nsovereign heartbeat"),
            "rev-list": (0, f"{old}\n{EMPTY_TREE}"),
        }
    )
    assert beat(REF, readiness=SERVING).ready
    fetched = next(c for c in calls if "fetch" in c)
    assert fetched == ("git", "fetch", "--no-tags", "--no-write-fetch-head", "origin", REF)


@pytest.mark.parametrize(
    "script, expected",
    [
        ({"hash-object": (1, "")}, "empty tree"),
        ({"hash-object": (0, "t"), "commit-tree": (0, "")}, "heartbeat commit"),
        (
            {"hash-object": (0, "t"), "commit-tree": (0, "c"), "ls-remote": (2, "")},
            "nothing to lease against",
        ),
        (
            {
                "hash-object": (0, "t"),
                "commit-tree": (0, "c"),
                "ls-remote": (0, f"{'a' * 40}\t{REF}"),
                "-e": (1, ""),
                "fetch": (1, ""),
            },
            "could not fetch what",
        ),
        ({"hash-object": (0, "t"), "commit-tree": (0, "c"), "push": (1, "")}, "could not push"),
    ],
)
def test_every_heartbeat_failure_is_reported_rather_than_raised(fake, script, expected):
    calls = fake(script)
    result = beat(REF, readiness=SERVING)
    assert not result.ready and expected in result.reason
    if expected != "could not push":
        assert not any("push" in c for c in calls)


def test_a_refused_push_carries_what_git_said_with_its_credentials_scrubbed(fake):
    """A reason is evidence (10.f): the tail of git's own words, on one line, colour codes
    dropped, and no URL userinfo or token in it."""
    said = (
        "Enumerating objects: 1, done.\n"
        "remote: Permission to o/r.git denied to vibey-runner.\n"
        "fatal: unable to access 'https://x-access-token:ghs_abcdefghijklmnopqrstuvwxyz"
        "@github.com/o/r.git/': The requested URL returned error: 403\n"
        "\x1b[0;31m✖ push refused: this repository publishes only the sovereign heartbeat.\x1b[0m\n"
        "error: failed to push some refs to"
        " 'https://github_pat_ABCDEFGHIJKLMNOPQRSTUV@github.com/o/r'"
    )
    fake({"hash-object": (0, "t"), "commit-tree": (0, "c"), "push": (1, said)})
    reason = beat(REF, readiness=SERVING).reason
    assert reason.startswith(f"could not push the heartbeat to origin {REF} (exit 1:")
    assert "Permission to o/r.git denied" in reason
    assert "✖ push refused: this repository publishes only" in reason
    assert "https://github.com/o/r.git/" in reason
    for secret in ("x-access-token", "ghs_abc", "github_pat_ABC", "\x1b["):
        assert secret not in reason, secret
    assert "Enumerating objects" not in reason  # a tail, not the whole transcript


def test_a_push_that_times_out_says_so_and_nothing_more(fake):
    fake({"hash-object": (0, "t"), "commit-tree": (0, "c"), "push": (TIMED_OUT, "")})
    reason = beat(REF, readiness=SERVING).reason
    assert f"timed out after 60s (exit {TIMED_OUT})" in reason
    assert "whether it landed is unknown" in reason


def test_a_ref_holding_something_that_is_not_a_heartbeat_is_never_replaced(fake):
    foreign = "d" * 40
    calls = fake(
        {
            "ls-remote": (0, f"{foreign}\t{REF}"),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\nparent {'e' * 40}\n\nsomeone else's"),
        }
    )
    result = beat(REF, readiness=SERVING)
    assert not result.ready
    assert f"holds {foreign}, which is not a heartbeat" in result.reason
    assert "has a parent" in result.reason and "nothing was pushed" in result.reason
    assert not any("push" in c for c in calls)


def test_run_reports_a_hung_or_missing_git_by_distinct_codes(monkeypatch):
    def missing(*a, **k):
        raise OSError("no git here")

    monkeypatch.setattr(sovereign.subprocess, "run", missing)
    assert sovereign._run("git", "status") == (127, "")

    def hung(*a, **k):
        raise subprocess.TimeoutExpired("git", 60)

    monkeypatch.setattr(sovereign.subprocess, "run", hung)
    assert sovereign._run("git", "push") == (TIMED_OUT, "")

    class Failed:
        returncode = 2
        stdout = " out \n"
        stderr = " refused \n"

    monkeypatch.setattr(sovereign.subprocess, "run", lambda *a, **k: Failed())
    assert sovereign._run("git", "status") == (2, "out")
    assert sovereign._run("git", "push", stderr=True) == (2, "refused")


# --- end to end: the timer's own clone, its real gate, a bare remote ------------------------


def _git_env() -> dict[str, str]:
    """No inherited repository, no global or system configuration, and an identity for the
    heartbeat commits, which on the operator's machine comes from their own git config."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="test_sovereign",
        GIT_AUTHOR_EMAIL="beat@example.invalid",
        GIT_COMMITTER_NAME="test_sovereign",
        GIT_COMMITTER_EMAIL="beat@example.invalid",
    )
    return env


class Clone:
    """The heartbeat's clone as `heartbeat install` makes it -- `HeartbeatClone.ensure()` and
    the real hook template -- pushing to a bare remote. The interpreter its gate runs logs
    every call and then runs the real vibey_gh, so a test can count the gate's decisions."""

    def __init__(self, tmp_path: Path) -> None:
        self.env = _git_env()
        self.remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], env=self.env, check=True)
        self.log = tmp_path / "scope.log"
        python = tmp_path / "tool" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.write_text(
            f'#!/bin/sh\necho "$*" >> "{self.log}"\nexec "{sys.executable}" "$@"\n',
            encoding="utf-8",
        )
        python.chmod(0o755)
        self.path = tmp_path / "heartbeat-r"
        self.clone = HeartbeatClone(
            self.path,
            remote_url=str(self.remote),
            gh_config_dir=tmp_path / "gh-runner",
            heartbeat_ref=REF,
            path_env=self.env["PATH"],
            git=lambda args, cwd: self.run(*args, cwd=cwd),
        )
        _lines, problem = self.clone.ensure()
        assert problem == "", problem
        hook = (RUNNER_TEMPLATES / HOOK_TEMPLATE).read_text(encoding="utf-8")
        self.clone.hook_path.write_text(
            hook.replace("__PYTHON__", shlex.quote(str(python))), encoding="utf-8"
        )
        self.clone.hook_path.chmod(0o755)

    def run(self, *args: str, cwd: Path | None = None, stderr: bool = False) -> tuple[int, str]:
        done = subprocess.run(
            ["git", *args],
            cwd=cwd or self.path,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, (done.stderr if stderr else done.stdout).strip()

    def git(self, *args: str, stderr: bool = False) -> tuple[int, str]:
        """The heartbeat's seam: git in the clone."""
        return self.run(*args, stderr=stderr)

    def remote_holds(self) -> str:
        return self.run("--git-dir", str(self.remote), "rev-parse", "--verify", "-q", REF)[1]

    def scope_calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def code_commit(self, where: Path) -> str:
        """A commit carrying one file, made directly in the repository at `where`."""
        identity = ("-c", "user.name=t", "-c", "user.email=t@example.invalid")
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=where,
            env=self.env,
            input="code\n",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "mktree"],
            cwd=where,
            env=self.env,
            input=f"100644 blob {blob}\tf.txt\n",
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        code, commit = self.run(*identity, "commit-tree", tree, "-m", "code", cwd=where)
        assert code == 0
        return commit


@pytest.fixture
def clone(tmp_path: Path) -> Clone:
    return Clone(tmp_path)


def test_a_real_heartbeat_passes_the_clones_gate_by_the_gates_own_rule(clone):
    """No `--no-verify` anywhere: each beat reaches the remote only because the clone's own
    gate asked the scope rule and was told the push carries no code -- once per beat."""
    instants = iter((1_800_000_000.0, 1_800_000_060.0))
    heartbeat = SovereignHeartbeat(
        REF, cwd=str(clone.path), git=clone.git, clock=lambda: next(instants)
    )
    first = heartbeat.beat(SERVING)
    assert first.ready, first.reason
    assert clone.scope_calls() == ["-m vibey_gh.cli push-scope"]
    published = clone.remote_holds()
    assert published
    # The next beat replaces the first by compare-and-swap, still through the gate.
    second = heartbeat.beat(SERVING)
    assert second.ready, second.reason
    assert len(clone.scope_calls()) == 2
    assert clone.remote_holds() not in ("", published)


def test_the_clones_gate_refuses_anything_that_is_not_a_heartbeat(clone):
    """The clone has no working tree and exists to publish one thing, so a push that is not
    a heartbeat is refused outright -- here, a commit carrying a file, on the heartbeat ref."""
    commit = clone.code_commit(clone.path)
    code, said = clone.git("push", "origin", f"{commit}:{REF}", stderr=True)
    assert code != 0
    assert "publishes only the sovereign heartbeat" in said
    assert clone.remote_holds() == ""
    assert clone.scope_calls() == ["-m vibey_gh.cli push-scope"]


def test_a_real_ref_holding_code_is_never_replaced_by_a_beat(clone):
    """Code already on the heartbeat ref -- put there by something other than this timer --
    is read, fetched, found not to be a heartbeat, and left exactly as it was. Nothing is
    pushed, so the gate is never even asked."""
    foreign = clone.code_commit(clone.remote)
    assert clone.run("--git-dir", str(clone.remote), "update-ref", REF, foreign)[0] == 0
    result = SovereignHeartbeat(REF, cwd=str(clone.path), git=clone.git).beat(SERVING)
    assert not result.ready
    assert f"holds {foreign}, which is not a heartbeat" in result.reason
    assert "carries a tree" in result.reason and "nothing was pushed" in result.reason
    assert clone.remote_holds() == foreign
    assert clone.scope_calls() == []


def test_a_clone_whose_gate_is_gone_publishes_nothing(clone):
    clone.clone.hook_path.unlink()
    result = SovereignHeartbeat(REF, cwd=str(clone.path), git=clone.git).beat(SERVING)
    assert not result.ready
    assert "has no executable pre-push gate" in result.reason
    assert str(clone.clone.hook_path) in result.reason
    assert clone.remote_holds() == ""


# --- the command line ---------------------------------------------------------------------


def test_the_probe_publishes_its_verdict_to_the_job_output(fake, monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    out = tmp_path / "gh-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    fake({"log": (0, "1000")})
    monkeypatch.setattr(sovereign.time, "time", lambda: 1100.0)
    assert main(["sovereign"]) == 0
    assert "ready=true" in out.read_text(encoding="utf-8")

    assert "reason=sovereign runner heartbeat is 100s old" in out.read_text(encoding="utf-8")

    fake({"fetch": (1, "")})
    assert main(["sovereign"]) == 0  # not available is not an error
    assert "ready=false" in out.read_text(encoding="utf-8")
    assert "no sovereign heartbeat" in capsys.readouterr().out
    # The reason travels too: with no paid review declared (8.b), "needs a human review"
    # has to say WHY the sovereign lane was not offered, in the gate a person reads.
    assert out.read_text(encoding="utf-8").splitlines()[-1] == (
        "reason=no sovereign heartbeat at refs/vibey-gh/sovereign-heartbeat"
        " — the local lane is not offered"
    )


def test_the_probe_runs_outside_actions_without_a_job_output(fake, monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    fake({"fetch": (1, "")})
    assert main(["sovereign"]) == 0
    assert "vibey-gh sovereign:" in capsys.readouterr().out


def _beat_repo(tmp_path: Path, monkeypatch, *, clone: bool = True) -> Path:
    """A checkout declaring a runner for o/r, a home to expand `~/` in, and -- unless asked
    not to -- the timer's clone where `[runners]` puts it by default."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\n\n[runners]\nrepository = "o/r"\n', encoding="utf-8"
    )
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)
    where = home / ".local/share/vibey-runner/heartbeat-r"
    if clone:
        where.mkdir(parents=True)
    return where


def test_publishing_a_heartbeat_reports_failure_to_the_operator(
    fake, monkeypatch, tmp_path, capsys
):
    """`--beat` is the one form that exits non-zero: the timer calling it needs to know its
    heartbeat never landed, or it will believe the lane is offered when it is not."""
    where = _beat_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    calls = fake({"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert main(["sovereign", "--beat"]) == 0
    assert all(call[0] == "git" for call in calls)
    fake({"hash-object": (1, "")})
    assert main(["sovereign", "--beat"]) == 1
    assert "empty tree" in capsys.readouterr().out
    assert where.is_dir()


def test_the_beat_pushes_from_the_timers_clone_and_nowhere_else(fake, monkeypatch, tmp_path):
    where = _beat_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    seen: list[str | None] = []
    fake({"hash-object": (0, "t"), "commit-tree": (0, "c")})
    real_run = sovereign._run

    def run(*cmd, cwd=None, stderr=False):
        seen.append(cwd)
        return real_run(*cmd, cwd=cwd, stderr=stderr)

    monkeypatch.setattr(sovereign, "_run", run)
    assert main(["sovereign", "--beat"]) == 0
    assert seen and set(seen) == {str(where)}


def test_a_beat_without_its_clone_is_withheld_and_recorded(fake, monkeypatch, tmp_path, capsys):
    _beat_repo(tmp_path, monkeypatch, clone=False)
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    calls = fake({})
    record = tmp_path / "logs" / "beat.last.json"
    assert main(["sovereign", "--beat", "--record", str(record)]) == 1
    body = json.loads(record.read_text(encoding="utf-8"))
    assert body["published"] is False
    assert "heartbeat-r, does not exist" in body["reason"]
    assert "vibey-gh heartbeat install" in capsys.readouterr().out
    assert calls == []


def test_a_beat_with_no_declared_repository_is_withheld(fake, monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text('[platform]\nkind = "github"\n', encoding="utf-8")
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    calls = fake({})
    assert main(["sovereign", "--beat"]) == 1
    assert "heartbeat withheld: runners.repository is empty" in capsys.readouterr().out
    assert calls == []


def test_a_withheld_beat_exits_non_zero_and_records_why(fake, monkeypatch, tmp_path, capsys):
    _beat_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: _Lane(False, "no runner online"))
    calls = fake({})
    record = tmp_path / "logs" / "beat.last.json"
    assert main(["sovereign", "--beat", "--record", str(record)]) == 1
    assert "heartbeat withheld: no runner online" in capsys.readouterr().out
    body = json.loads(record.read_text(encoding="utf-8"))
    assert body["published"] is False and body["reason"] == "heartbeat withheld: no runner online"
    assert not any("push" in call for call in calls)
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    fake({"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert main(["sovereign", "--beat", "--record", str(record)]) == 0
    assert json.loads(record.read_text(encoding="utf-8"))["published"] is True


def test_the_command_line_reads_the_lane_from_the_declared_runner_and_model(tmp_path):
    """The real readiness: the runner `[runners]` declares, read with its own credential,
    and the model `[pr_automation.fallback]` names, read through the fit's sampler."""
    from vibey_gh.fit import OllamaModelSampler
    from vibey_gh.sovereign_lane import SovereignLaneReadiness

    readiness = cli._lane_readiness(load_config(tmp_path))
    assert isinstance(readiness, SovereignLaneReadiness)
    assert isinstance(readiness._model, OllamaModelSampler)
    assert readiness._model.base_url == PrAutomationFallbackConfig().base_url


# --- configuration --------------------------------------------------------------------------


def test_the_sovereign_lane_is_available_by_default_now(monkeypatch):
    """8.a: the sovereign path is the preference, so it may not be the one that has to
    be opted into while the paid lane runs automatically. Safe because the probe gates
    scheduling — a repository with no heartbeat simply never offers the lane."""
    assert PrAutomationFallbackConfig().enabled is True
    assert PrAutomationFallbackConfig().heartbeat_max_age_minutes == 15


def test_the_documented_fallback_defaults_are_the_code_defaults(tmp_path):
    """#277 turned BOTH local fallbacks on; the issue path's config comment and its
    configuration.md row went on saying "off by default" (#264). The dataclass and the
    loader spell the default separately, so both are asserted, and so is the docs row."""
    issue_default = IssueAutomationConfig().fallback_enabled
    assert issue_default is True
    assert load_config(tmp_path).issue_automation.fallback_enabled is issue_default
    docs = Path(__file__).resolve().parent.parent / "docs" / "configuration.md"
    lines = docs.read_text(encoding="utf-8").splitlines()
    issue_row = next(line for line in lines if line.startswith("| `fallback_enabled` |"))
    pr_row = next(
        line for line in lines if line.startswith("| `enabled` |") and "fallback job" in line
    )
    for row in (issue_row, pr_row):
        assert row.split("|")[2].strip() == "boolean / `true`", row


def test_the_docs_name_the_runner_label_key_not_one_repositorys_value():
    """Five pages said the lane runs on `[self-hosted, vibey-local-gh]` -- the label
    vibey-gh's OWN .vibey-gh.toml sets -- while `runner_label` defaults to `vibey-local`
    (#264). A literal runs-on in prose may only be the placeholder or the default."""
    tenant = Path(__file__).resolve().parent.parent
    allowed = {"<runner_label>", PrAutomationFallbackConfig().runner_label}
    for page in [tenant / "README.md", *sorted((tenant / "docs").glob("*.md"))]:
        for label in re.findall(r"\[self-hosted, ([^\]]+)\]", page.read_text(encoding="utf-8")):
            assert label in allowed, f"{page.name} names runner label {label!r}"


@pytest.mark.parametrize(
    "field, value, expected",
    [
        ("heartbeat_ref", "sovereign-heartbeat", "must be a full refs/ path"),
        ("heartbeat_ref", "refs/heads/heartbeat", "must not be a branch"),
        ("heartbeat_ref", "refs/tags/heartbeat", "must not be a tag"),
        ("heartbeat_max_age_minutes", 0, "between 1 and 1440"),
        ("heartbeat_max_age_minutes", 1441, "between 1 and 1440"),
    ],
)
def test_a_heartbeat_that_would_pollute_or_never_expire_is_refused(field, value, expected):
    with pytest.raises(ValueError, match=expected):
        PrAutomationFallbackConfig(**{field: value})


def test_a_toml_block_overrides_the_heartbeat_defaults(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.fallback]\n"
        'heartbeat_ref = "refs/vibey/pulse"\n'
        "heartbeat_max_age_minutes = 60\n",
        encoding="utf-8",
    )
    fallback = load_config(tmp_path).pr_automation.fallback
    assert fallback.heartbeat_ref == "refs/vibey/pulse"
    assert fallback.heartbeat_max_age_minutes == 60
