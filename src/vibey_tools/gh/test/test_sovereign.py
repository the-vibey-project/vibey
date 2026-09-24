# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sovereign readiness (doctrine 8.a): the probe that makes preferring free safe, and the
heartbeat that feeds it -- published only when the lane can serve, never past the gate."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from vibey_gh import cli, sovereign
from vibey_gh.cli import main
from vibey_gh.config import GhConfig, IssueAutomationConfig, PrAutomationFallbackConfig, load_config
from vibey_gh.install import TEMPLATES, render_hook
from vibey_gh.interfaces.sovereign_interface import SovereignHeartbeatInterface
from vibey_gh.sovereign import SovereignHeartbeat, beat, probe
from vibey_gh.sovereign_lane import LaneState

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


SERVING = _Lane()


def _fake(monkeypatch, script):
    """Drive `_run` from a table keyed on the git subcommand."""
    calls: list[tuple[str, ...]] = []

    def run(*cmd: str, cwd=None):
        calls.append(cmd)
        for key, result in script.items():
            if key in cmd:
                return result
        return (0, "")

    monkeypatch.setattr(sovereign, "_run", run)
    return calls


def test_the_heartbeat_honours_its_interface():
    assert isinstance(SovereignHeartbeat(REF), SovereignHeartbeatInterface)


def test_the_sovereign_lane_is_offered_only_while_the_heartbeat_is_fresh(monkeypatch):
    _fake(monkeypatch, {"log": (0, "1000")})
    assert probe(REF, max_age_minutes=15, now=1300.0).ready
    verdict = probe(REF, max_age_minutes=15, now=1300.0)
    assert verdict.age_seconds == 300 and "300s old" in verdict.reason


def test_a_stale_heartbeat_treats_the_runner_as_offline(monkeypatch):
    """The whole point: a machine that has stopped saying it is up is not up. Offering
    the lane anyway queues a job forever against a runner nobody is running."""
    _fake(monkeypatch, {"log": (0, "1000")})
    verdict = probe(REF, max_age_minutes=15, now=1000.0 + 16 * 60)
    assert not verdict.ready
    assert "16m old" in verdict.reason and "treating the runner as offline" in verdict.reason


def test_a_missing_heartbeat_is_a_fact_not_a_failure(monkeypatch):
    _fake(monkeypatch, {"fetch": (1, "")})
    verdict = probe(REF, max_age_minutes=15)
    assert not verdict.ready and verdict.age_seconds is None
    assert "no sovereign heartbeat" in verdict.reason


@pytest.mark.parametrize("raw", [(1, "1000"), (0, "not-a-timestamp"), (0, "")])
def test_an_unreadable_heartbeat_never_reports_ready(monkeypatch, raw):
    _fake(monkeypatch, {"log": raw})
    assert not probe(REF, max_age_minutes=15).ready


def test_a_future_dated_heartbeat_is_refused(monkeypatch):
    """Clock skew must not be able to manufacture readiness."""
    _fake(monkeypatch, {"log": (0, "9000")})
    verdict = probe(REF, max_age_minutes=15, now=1000.0)
    assert not verdict.ready and "dated in the future" in verdict.reason


# --- publishing: honest, and through the gate ---------------------------------------------


def test_a_heartbeat_is_an_empty_commit_on_a_ref_that_is_not_a_branch(monkeypatch):
    calls = _fake(monkeypatch, {"hash-object": (0, "tree1"), "commit-tree": (0, "c0ffee")})
    result = beat(REF, readiness=SERVING)
    assert result.ready and result.age_seconds == 0
    assert result.reason.endswith(": 1 runner online; m answers")
    pushed = next(c for c in calls if "push" in c)
    # A compare-and-swap on a ref that does not exist yet: an empty lease means "absent".
    assert pushed == ("git", "push", f"--force-with-lease={REF}:", "origin", f"c0ffee:{REF}")
    assert "refs/heads/" not in pushed[-1]


def test_a_heartbeat_never_skips_the_pre_push_gate(monkeypatch):
    """12.d forbids `--no-verify`, with no exceptions: the heartbeat goes through the gate,
    and the gate lets it through by its own rule (`vibey_gh.push_scope`). Nor is it a bare
    `--force`: only the exact value that was read is ever replaced."""
    calls = _fake(monkeypatch, {"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert beat(REF, readiness=SERVING).ready
    argv = [arg for call in calls for arg in call]
    assert "--no-verify" not in argv and "--force" not in argv and "-f" not in argv
    assert not any(arg.startswith("+") for arg in argv)


def test_a_lane_that_cannot_serve_publishes_nothing_at_all(monkeypatch):
    """A heartbeat is a claim that a job will be taken. Withheld, it goes stale on its own
    and the gate falls back to asking a human, which is the honest answer."""
    calls = _fake(monkeypatch, {})
    lane = _Lane(False, "no runner labelled vibey-local-r is online for o/r (none registered)")
    result = beat(REF, readiness=lane)
    assert not result.ready and lane.asked == 1
    assert result.reason == (
        "heartbeat withheld: no runner labelled vibey-local-r is online for o/r (none registered)"
    )
    assert calls == []


def test_an_earlier_heartbeat_is_replaced_by_compare_and_swap(monkeypatch):
    old = "a" * 40
    calls = _fake(
        monkeypatch,
        {
            "ls-remote": (0, f"{old}\t{REF}"),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\nauthor x\n\nsovereign heartbeat"),
        },
    )
    assert beat(REF, readiness=SERVING).ready
    assert next(c for c in calls if "push" in c)[2] == f"--force-with-lease={REF}:{old}"
    assert not any("fetch" in c for c in calls)  # the object was already here


def test_an_earlier_heartbeat_missing_locally_is_fetched_before_it_is_judged(monkeypatch):
    old = "a" * 40
    calls = _fake(
        monkeypatch,
        {
            "ls-remote": (0, f"{old}\t{REF}\n{'b' * 40}\trefs/other/{REF}"),
            "-e": (1, ""),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\n\nsovereign heartbeat"),
        },
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
def test_every_heartbeat_failure_is_reported_rather_than_raised(monkeypatch, script, expected):
    calls = _fake(monkeypatch, script)
    result = beat(REF, readiness=SERVING)
    assert not result.ready and expected in result.reason
    if expected != "could not push":
        assert not any("push" in c for c in calls)


def test_a_ref_holding_something_that_is_not_a_heartbeat_is_never_replaced(monkeypatch):
    foreign = "d" * 40
    calls = _fake(
        monkeypatch,
        {
            "ls-remote": (0, f"{foreign}\t{REF}"),
            "hash-object": (0, EMPTY_TREE),
            "commit-tree": (0, "c"),
            "-t": (0, "commit"),
            "commit": (0, f"tree {EMPTY_TREE}\nparent {'e' * 40}\n\nsomeone else's"),
        },
    )
    result = beat(REF, readiness=SERVING)
    assert not result.ready
    assert f"holds {foreign}, which is not a heartbeat" in result.reason
    assert "has a parent" in result.reason and "nothing was pushed" in result.reason
    assert not any("push" in c for c in calls)


def test_run_survives_a_missing_or_hanging_git(monkeypatch):
    def boom(*a, **k):
        raise OSError("no git here")

    monkeypatch.setattr(sovereign.subprocess, "run", boom)
    assert sovereign._run("git", "status") == (1, "")

    class Failed:
        returncode = 2
        stdout = " out \n"

    monkeypatch.setattr(sovereign.subprocess, "run", lambda *a, **k: Failed())
    assert sovereign._run("git", "status") == (2, "out")


# --- end to end: a real remote, the real hook, a heavy stage that would refuse ----------

STUB_VIBEY_GH = """#!/bin/sh
case "$1" in
  trailer-key) echo "Made-With"; exit 0 ;;
  check) exit 0 ;;
  push-scope) PYTHONPATH="{tenant}" exec "{python}" -m vibey_gh.cli "$@" ;;
esac
exit 0
"""


@pytest.fixture
def checkout(tmp_path: Path):
    """A clone whose pre-push stage REFUSES everything it judges, pushing to a bare remote.

    If the heartbeat reached that stage the push would fail; it succeeds only because the
    gate recognises, by its own rule, that there is nothing to judge."""
    import sys

    tenant = Path(__file__).resolve().parent.parent
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "vibey-gh").write_text(STUB_VIBEY_GH.format(tenant=tenant, python=sys.executable))
    (bin_dir / "vibey-gh").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("_VIBEY_GH_SELF", None)
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
    )
    root, remote = tmp_path / "work", tmp_path / "remote.git"
    root.mkdir()

    def git(*args: str, cwd: Path = root) -> tuple[int, str]:
        done = subprocess.run(
            ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False
        )
        return done.returncode, done.stdout.strip()

    assert git("init", "-q", "--bare", str(remote), cwd=tmp_path)[0] == 0
    for args in (
        ("init", "-q", "-b", "main"),
        ("config", "user.name", "test_sovereign"),
        ("config", "user.email", "beat@example.invalid"),
        ("config", "commit.gpgsign", "false"),
        ("remote", "add", "origin", str(remote)),
        ("config", "core.hooksPath", "hooks"),
    ):
        assert git(*args)[0] == 0, args
    hooks = root / "hooks"
    hooks.mkdir()
    (hooks / "pre-push").write_text(render_hook(TEMPLATES / "pre-push", GhConfig(root=root)))
    (hooks / "pre-push").chmod(0o755)
    (hooks / "pre-push.local").write_text("#!/bin/sh\ncat >/dev/null\nexit 1\n")
    (hooks / "pre-push.local").chmod(0o755)
    return git


def test_a_real_heartbeat_passes_a_refusing_gate_by_the_gates_own_rule(checkout):
    # Two beats a minute apart, as the timer makes them: each commit is its own.
    instants = iter((1_800_000_000.0, 1_800_000_060.0))
    heartbeat = SovereignHeartbeat(REF, git=checkout, clock=lambda: next(instants))
    first = heartbeat.beat(SERVING)
    assert first.ready, first.reason
    code, listed = checkout("ls-remote", "origin", REF)
    assert code == 0 and listed
    # The next beat replaces the first by compare-and-swap, still through the gate.
    second = heartbeat.beat(SERVING)
    assert second.ready, second.reason
    assert checkout("ls-remote", "origin", REF)[1] != listed


def test_a_real_ref_holding_code_is_neither_replaced_nor_pushed_past_the_gate(checkout):
    (Path(checkout("rev-parse", "--show-toplevel")[1]) / "f.txt").write_text("code\n")
    checkout("add", "f.txt")
    checkout("commit", "-q", "-m", "feat: code")
    # Put code on the heartbeat ref the only way the refusing gate allows: not at all.
    code, _ = checkout("push", "origin", f"HEAD:{REF}")
    assert code != 0  # the gate judged it, and refused
    assert checkout("ls-remote", "origin", REF)[1] == ""


# --- the command line ---------------------------------------------------------------------


def test_the_probe_publishes_its_verdict_to_the_job_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    out = tmp_path / "gh-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    _fake(monkeypatch, {"log": (0, "1000")})
    monkeypatch.setattr(sovereign.time, "time", lambda: 1100.0)
    assert main(["sovereign"]) == 0
    assert "ready=true" in out.read_text(encoding="utf-8")

    assert "reason=sovereign runner heartbeat is 100s old" in out.read_text(encoding="utf-8")

    _fake(monkeypatch, {"fetch": (1, "")})
    assert main(["sovereign"]) == 0  # not available is not an error
    assert "ready=false" in out.read_text(encoding="utf-8")
    assert "no sovereign heartbeat" in capsys.readouterr().out
    # The reason travels too: with no paid review declared (8.b), "needs a human review"
    # has to say WHY the sovereign lane was not offered, in the gate a person reads.
    assert out.read_text(encoding="utf-8").splitlines()[-1] == (
        "reason=no sovereign heartbeat at refs/vibey-gh/sovereign-heartbeat"
        " — the local lane is not offered"
    )


def test_the_probe_runs_outside_actions_without_a_job_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    _fake(monkeypatch, {"fetch": (1, "")})
    assert main(["sovereign"]) == 0
    assert "vibey-gh sovereign:" in capsys.readouterr().out


def test_publishing_a_heartbeat_reports_failure_to_the_operator(monkeypatch, tmp_path, capsys):
    """`--beat` is the one form that exits non-zero: the timer calling it needs to know its
    heartbeat never landed, or it will believe the lane is offered when it is not."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    _fake(monkeypatch, {"hash-object": (0, "t"), "commit-tree": (0, "c")})
    assert main(["sovereign", "--beat"]) == 0
    _fake(monkeypatch, {"hash-object": (1, "")})
    assert main(["sovereign", "--beat"]) == 1
    assert "empty tree" in capsys.readouterr().out


def test_a_withheld_beat_exits_non_zero_and_records_why(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: _Lane(False, "no runner online"))
    calls = _fake(monkeypatch, {})
    record = tmp_path / "logs" / "beat.last.json"
    assert main(["sovereign", "--beat", "--record", str(record)]) == 1
    assert "heartbeat withheld: no runner online" in capsys.readouterr().out
    body = json.loads(record.read_text(encoding="utf-8"))
    assert body["published"] is False and body["reason"] == "heartbeat withheld: no runner online"
    assert calls == []
    monkeypatch.setattr(cli, "_lane_readiness", lambda cfg: SERVING)
    _fake(monkeypatch, {"hash-object": (0, "t"), "commit-tree": (0, "c")})
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
