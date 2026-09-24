# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The heartbeat timer, stood up from the tree: launchd on macOS, a systemd user timer on Linux,
pushing from a clone of its own whose gate is asked about a heartbeat before anything runs.

Nothing here touches a real service manager or installs anything on the machine running the
suite: every unit and every clone is made under a scratch home in pytest's `tmp_path`, git
runs with no global or system configuration, and launchctl, systemctl and loginctl are a seam
that records what it was asked. The clone's gate is a seam too, except where a test says it
runs the real hook.
"""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

import pytest

from vibey_gh.config import (
    GhConfig,
    PlatformConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    RunnersConfig,
)
from vibey_gh.heartbeat_clone import GATE_PASSED
from vibey_gh.heartbeat_timer import LAUNCHD, SYSTEMD, BeatRecord, HeartbeatPlan, HeartbeatTimer
from vibey_gh.interfaces.heartbeat_timer_interface import (
    BeatRecordInterface,
    HeartbeatPlanInterface,
    HeartbeatTimerInterface,
)

UID = 501
PYTHON = "/opt/vibey-tool/bin/python"
ORIGIN = "/opt/vibey-tool/lib/python3.12/site-packages/vibey_gh"
LABEL = "org.vibey.runner-heartbeat-r"
SOURCE = '[platform]\nkind = "github"\n\n[runners]\nrepository = "o/r"\n'


@pytest.fixture(autouse=True)
def _hermetic_git(monkeypatch):
    """git as the clone's default seam runs it, minus whatever this machine's own
    configuration or an enclosing hook would add."""
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


class _Service:
    """Records every service-manager argv and answers from a table keyed on the argv."""

    def __init__(self, answers: dict[str, tuple[int, str]] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.answers = {"loginctl": (0, "Linger=yes"), **(answers or {})}

    def __call__(self, argv: tuple[str, ...]) -> tuple[int, str]:
        self.calls.append(argv)
        for key, answer in self.answers.items():
            if key in argv:
                return answer
        return 0, ""

    def managed(self) -> list[tuple[str, ...]]:
        """Every call but the linger read, which only reads."""
        return [argv for argv in self.calls if argv[0] != "loginctl"]


class _Hook:
    """The clone's gate: records what it was handed and answers as told."""

    def __init__(self, code: int = 0, said: str = f"{GATE_PASSED}\n") -> None:
        self.code, self.said = code, said
        self.calls: list[tuple[tuple[str, ...], Path, str, dict[str, str]]] = []

    def __call__(self, argv, cwd, stdin, env) -> tuple[int, str]:
        self.calls.append((tuple(argv), cwd, stdin, dict(env)))
        return self.code, self.said


class _Timer(HeartbeatTimer):
    """No temporary directory counts as temporary: the scratch tree the suite writes into
    usually IS one, and the refusal is tested on its own below."""

    @staticmethod
    def temp_roots() -> tuple[Path, ...]:
        return ()


def _cfg(tmp_path: Path, fallback: dict | None = None, **runners: object) -> GhConfig:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    (repo / ".vibey-gh.toml").write_text(SOURCE, encoding="utf-8")
    home = tmp_path / "home"
    return GhConfig(
        root=repo,
        platform=PlatformConfig(kind="github"),
        runners=RunnersConfig(
            **{  # type: ignore[arg-type]
                "repository": "o/r",
                "launch_agents_dir": str(home / "Library/LaunchAgents"),
                "log_dir": str(home / "Library/Logs"),
                "install_dir": str(home / ".local/share/vibey-runner"),
                "gh_config_dir": str(home / ".config/gh-runner"),
                "systemd_user_dir": str(home / ".config/systemd/user"),
                "heartbeat_python": "",
                **runners,
            }
        ),
        pr_automation=PrAutomationConfig(
            fallback=PrAutomationFallbackConfig(
                **{"runner_label": "vibey-local-r", **(fallback or {})}
            )
        ),
    )


def _timer(
    tmp_path: Path,
    cfg: GhConfig | None = None,
    *,
    platform: str = "darwin",
    python: str = PYTHON,
    service: _Service | None = None,
    origin: str | None = ORIGIN,
    clock: float = 10_000.0,
    kind: type[HeartbeatTimer] = _Timer,
    hook: _Hook | None = None,
) -> HeartbeatTimer:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return kind(
        cfg or _cfg(tmp_path),
        home=home,
        uid=UID,
        platform=platform,
        python=python,
        service=service or _Service(),
        origin=lambda interpreter, cwd: origin,
        clock=lambda: clock,
        hook=hook or _Hook(),
    )


def _plan(timer: HeartbeatTimer, python: str | None = None) -> HeartbeatPlan:
    plan, problem = timer.render(python)
    assert problem == "" and plan is not None
    return plan


def _clone(tmp_path: Path) -> Path:
    return tmp_path / "home/.local/share/vibey-runner/heartbeat-r"


# --- rendering ---------------------------------------------------------------------------


def test_the_timer_and_its_plan_satisfy_their_interfaces(tmp_path):
    timer = _timer(tmp_path)
    assert isinstance(timer, HeartbeatTimerInterface)
    assert isinstance(_plan(timer), HeartbeatPlanInterface)
    assert isinstance(BeatRecord(1.0, True, "ok"), BeatRecordInterface)


def test_on_macos_it_renders_a_launch_agent_that_beats_from_its_own_clone(tmp_path):
    plan = _plan(_timer(tmp_path))
    assert plan.scheduler == LAUNCHD and plan.label == LABEL
    assert plan.clone == _clone(tmp_path) and plan.remote_url == "https://github.com/o/r"
    _hook, _config, unit = plan.files
    assert unit.path == tmp_path / "home/Library/LaunchAgents" / f"{LABEL}.plist"
    agent = plistlib.loads(unit.text.encode("utf-8"))
    record = tmp_path / "home/Library/Logs" / f"{LABEL}.last.json"
    assert agent["Label"] == LABEL
    assert agent["ProgramArguments"] == [
        PYTHON,
        "-m",
        "vibey_gh.cli",
        "sovereign",
        "--beat",
        "--record",
        str(record),
    ]
    # It runs in the clone the timer owns, never in the checkout it was installed from.
    assert agent["WorkingDirectory"] == str(_clone(tmp_path))
    # The default trust window is 15 minutes, so a beat every 7: one missed beat never
    # stales the lane.
    assert agent["StartInterval"] == 7 * 60 and plan.interval_minutes == 7
    assert agent["EnvironmentVariables"]["PYTHONSAFEPATH"] == "1"
    assert agent["StandardOutPath"] == str(tmp_path / "home/Library/Logs" / f"{LABEL}.log")
    assert "--no-verify" not in unit.text


def test_the_clone_gets_its_own_gate_and_the_declared_configuration(tmp_path):
    """The gate asks the timer's own interpreter for the scope decision, and the clone reads
    the lane the checkout declares, byte for byte."""
    plan = _plan(_timer(tmp_path, python="/opt/a b/python"))
    hook, config, _unit = plan.files
    assert hook.path == _clone(tmp_path) / ".git/hooks/pre-push" and hook.executable
    assert "PYTHONSAFEPATH=1 '/opt/a b/python' -m vibey_gh.cli push-scope" in hook.text
    assert 'if [ "$scope" = "carries-no-code" ]; then' in hook.text
    assert "--no-verify" not in hook.text.split("set -e", 1)[1]
    assert config.path == _clone(tmp_path) / ".vibey-gh.toml" and config.text == SOURCE
    assert not config.executable


def test_on_linux_it_renders_a_systemd_user_service_and_timer(tmp_path):
    cfg = _cfg(tmp_path, heartbeat_log_dir="", path="/usr/bin:/bin:$HOME/bin")
    plan = _plan(_timer(tmp_path, cfg, platform="linux"))
    assert plan.scheduler == SYSTEMD
    _hook, _config, service, timer = plan.files
    units = tmp_path / "home/.config/systemd/user"
    assert (service.path, timer.path) == (units / f"{LABEL}.service", units / f"{LABEL}.timer")
    # The Linux default keeps the log and the record out of ~/Library.
    record = tmp_path / "home/.local/state/vibey-gh" / f"{LABEL}.last.json"
    assert plan.record == record
    assert (
        f'ExecStart="{PYTHON}" "-m" "vibey_gh.cli" "sovereign" "--beat" "--record" "{record}"'
        in service.text
    )
    assert f"WorkingDirectory={_clone(tmp_path)}" in service.text
    assert "Type=oneshot" in service.text and "Environment=PYTHONSAFEPATH=1" in service.text
    # An assignment is not a command line: systemd expands no `$` in it, so none is doubled.
    assert 'Environment="PATH=/usr/bin:/bin:$HOME/bin"' in service.text
    # A user manager has no network-online.target to wait for.
    assert "network-online" not in service.text.split("[Unit]", 1)[1]
    assert "OnUnitActiveSec=7min" in timer.text and f"Unit={LABEL}.service" in timer.text
    assert "WantedBy=timers.target" in timer.text
    assert "--no-verify" not in service.text + timer.text


def test_systemd_values_are_quoted_not_spliced(tmp_path):
    word = HeartbeatTimer._unit_word('a b"c\\d$e%f')
    assert word == '"a b\\"c\\\\d$$e%%f"'
    assert HeartbeatTimer._env_word('P=a b"c\\d$e%f') == '"P=a b\\"c\\\\d$e%%f"'
    assert HeartbeatTimer._unit_text("50%") == "50%%"


@pytest.mark.parametrize(
    "platform, declared, expected",
    [
        ("darwin", "", LAUNCHD),
        ("linux", "", SYSTEMD),
        ("win32", "systemd", SYSTEMD),
        ("linux", "launchd", LAUNCHD),
    ],
)
def test_the_scheduler_follows_the_platform_unless_declared(tmp_path, platform, declared, expected):
    cfg = _cfg(tmp_path, heartbeat_scheduler=declared)
    assert _plan(_timer(tmp_path, cfg, platform=platform)).scheduler == expected


def test_a_platform_with_neither_scheduler_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, platform="win32").render()
    assert plan is None and "set [runners] heartbeat_scheduler" in problem


@pytest.mark.parametrize(
    "window, interval, expected",
    [(15, 0, 7), (15, 5, 5), (60, 30, 30), (2, 0, 1)],
)
def test_the_interval_is_at_most_half_the_trust_window(tmp_path, window, interval, expected):
    cfg = _cfg(
        tmp_path,
        fallback={"heartbeat_max_age_minutes": window},
        heartbeat_interval_minutes=interval,
    )
    assert _timer(tmp_path, cfg).interval_minutes() == (expected, "")


@pytest.mark.parametrize("window, interval", [(15, 8), (1, 0), (10, 6)])
def test_an_interval_that_could_stale_the_lane_is_refused(tmp_path, window, interval):
    cfg = _cfg(
        tmp_path,
        fallback={"heartbeat_max_age_minutes": window},
        heartbeat_interval_minutes=interval,
    )
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "at most half the window" in problem


def test_a_declared_interpreter_is_used_and_expanded(tmp_path):
    cfg = _cfg(tmp_path, heartbeat_python="~/.local/share/uv/tools/vibey/bin/python")
    plan = _plan(_timer(tmp_path, cfg))
    assert plan.python == str(tmp_path / "home/.local/share/uv/tools/vibey/bin/python")
    # An explicit one (what status passes: the interpreter the installed unit runs) wins.
    assert _plan(_timer(tmp_path, cfg), "/usr/bin/python3").python == "/usr/bin/python3"


def test_the_default_interpreter_is_the_uv_tool_install(tmp_path):
    """Not the interpreter running the install, which under `uv run` in a checkout is that
    checkout's own .venv -- the one place the timer must never run from."""
    assert RunnersConfig().heartbeat_python == "~/.local/share/uv/tools/vibey/bin/python"
    cfg = _cfg(tmp_path, heartbeat_python=RunnersConfig().heartbeat_python)
    plan = _plan(_timer(tmp_path, cfg, python="/somewhere/in/a/checkout/.venv/bin/python"))
    assert plan.python == str(tmp_path / "home/.local/share/uv/tools/vibey/bin/python")


# A clone directory outside every temporary root, for the tests that run the real roots
# while the suite's own scratch tree sits under one of them. Render never creates it.
DURABLE_CLONE = "/nonexistent-durable/heartbeat-r"


def test_an_interpreter_under_a_temporary_directory_is_refused(tmp_path):
    timer = _timer(
        tmp_path,
        _cfg(tmp_path, heartbeat_clone_dir=DURABLE_CLONE),
        python=str(Path(os.path.realpath("/tmp")) / "venv/bin/python"),
        kind=HeartbeatTimer,
    )
    plan, problem = timer.render()
    assert plan is None and "which a reboot empties" in problem
    assert "[runners] heartbeat_python" in problem


class _SecondRootIsTemporary(HeartbeatTimer):
    """Two temporary roots, in a fixed order: the first can never match, the second holds
    the test's own scratch tree."""

    scratch = Path("/nonexistent")

    @classmethod
    def temp_roots(cls) -> tuple[Path, ...]:
        return (Path("/nonexistent"), cls.scratch)


def test_a_refusal_names_the_temporary_root_that_holds_the_path(tmp_path):
    """Deterministic on every platform: the first root does not hold the interpreter, so the
    search moves on and the refusal names the second."""
    _SecondRootIsTemporary.scratch = Path(os.path.realpath(tmp_path))
    interpreter = Path(os.path.realpath(tmp_path)) / "venv/bin/python"
    cfg = _cfg(tmp_path, heartbeat_clone_dir=DURABLE_CLONE)
    plan, problem = _timer(
        tmp_path, cfg, python=str(interpreter), kind=_SecondRootIsTemporary
    ).render()
    assert plan is None and problem.startswith(f"the heartbeat interpreter {interpreter} is")
    assert f"is under the temporary directory {os.path.realpath(tmp_path)}," in problem
    assert "/nonexistent," not in problem


def test_the_default_temporary_roots_are_this_machines_own_and_sorted():
    import tempfile

    roots = HeartbeatTimer.temp_roots()
    assert Path(os.path.realpath(tempfile.gettempdir())) in roots
    assert list(roots) == sorted(set(roots))


def test_an_interpreter_inside_a_git_work_tree_is_refused(tmp_path):
    clone = tmp_path / "checkout"
    (clone / ".git").mkdir(parents=True)
    plan, problem = _timer(tmp_path, python=str(clone / ".venv/bin/python")).render()
    assert plan is None and f"inside the git work tree {clone}" in problem
    assert "uv tool install" in problem


def test_a_vibey_gh_imported_from_a_checkout_is_refused(tmp_path):
    clone = tmp_path / "checkout"
    (clone / ".git").mkdir(parents=True)
    plan, problem = _timer(tmp_path, origin=str(clone / "src/vibey_gh")).render()
    assert plan is None and "the vibey_gh it runs" in problem


def test_an_interpreter_that_cannot_import_vibey_gh_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, origin=None).render()
    assert plan is None and "cannot import vibey_gh" in problem
    assert "uv tool install --force --from . vibey" in problem


def test_a_relative_interpreter_is_refused(tmp_path):
    plan, problem = _timer(tmp_path, python="python3").render()
    assert plan is None and "absolute path" in problem


def test_a_log_directory_inside_a_git_work_tree_is_refused(tmp_path):
    clone = tmp_path / "checkout"
    (clone / ".git").mkdir(parents=True)
    cfg = _cfg(tmp_path, heartbeat_log_dir=str(clone / "logs"))
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "the heartbeat log directory" in problem
    assert "[runners] heartbeat_log_dir" in problem


def test_the_clone_may_not_live_inside_a_checkout(tmp_path):
    """The clone IS a git repository, so only what is above it is judged -- and a checkout
    above it is one `git clean` or one finished lane away from taking it."""
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    cfg = _cfg(tmp_path, heartbeat_clone_dir=str(checkout / ".heartbeat"))
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "the heartbeat's clone" in problem
    assert f"inside the git work tree {checkout}" in problem
    assert "[runners] heartbeat_clone_dir" in problem


def test_the_clone_may_not_live_under_a_temporary_directory(tmp_path):
    cfg = _cfg(tmp_path, heartbeat_clone_dir=str(Path(os.path.realpath("/tmp")) / "hb"))
    plan, problem = _timer(tmp_path, cfg, kind=HeartbeatTimer).render()
    assert plan is None and "the heartbeat's clone" in problem
    assert "which a reboot empties" in problem


def test_a_declared_clone_directory_is_used_and_its_own_git_is_not_held_against_it(tmp_path):
    where = tmp_path / "durable/heartbeat"
    (where / ".git").mkdir(parents=True)
    cfg = _cfg(tmp_path, heartbeat_clone_dir=str(where))
    timer = _timer(tmp_path, cfg)
    assert _plan(timer).clone == where
    assert timer.clone_dir() == (where, "")


def test_where_the_beat_pushes_from_needs_only_a_declared_repository(tmp_path):
    assert _timer(tmp_path).clone_dir() == (_clone(tmp_path), "")
    path, problem = _timer(tmp_path, _cfg(tmp_path, repository="")).clone_dir()
    assert path is None and "runners.repository is empty" in problem


def test_there_must_be_a_declared_lane_to_give_the_clone(tmp_path):
    cfg = _cfg(tmp_path)
    (cfg.root / ".vibey-gh.toml").unlink()
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "no declared lane to give the clone" in problem


def test_a_linked_worktree_may_install_the_timer_it_no_longer_runs_from(tmp_path):
    """The timer runs from its own clone, so the checkout it was installed from may be a
    lane's worktree: nothing depends on that worktree once the install is done."""
    cfg = _cfg(tmp_path)
    (cfg.root / ".git").rmdir()
    (cfg.root / ".git").write_text("gitdir: /elsewhere/.git/worktrees/lane\n", encoding="utf-8")
    assert _plan(_timer(tmp_path, cfg)).clone == _clone(tmp_path)


def test_no_timer_without_a_sovereign_lane_or_a_repository(tmp_path):
    plan, problem = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).render()
    assert plan is None and "[pr_automation.fallback] is disabled" in problem
    cfg = _cfg(tmp_path, repository="")
    plan, problem = _timer(tmp_path, cfg).render()
    assert plan is None and "runners.repository is empty" in problem


# --- install ------------------------------------------------------------------------------


def test_install_makes_the_clone_asks_its_gate_and_loads_nothing_unasked(tmp_path):
    service, hook = _Service(), _Hook()
    timer = _timer(tmp_path, service=service, hook=hook)
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=False)
    clone = _clone(tmp_path)
    assert ok, lines
    assert lines == [
        f"created the heartbeat's clone at {clone}",
        f"set remote.origin.url in {clone}",
        f"set core.hooksPath in {clone}",
        f"set credential.helper in {clone}",
        f"wrote {clone / '.git/hooks/pre-push'}",
        f"wrote {clone / '.vibey-gh.toml'}",
        "the clone's own pre-push gate lets a heartbeat through: carries-no-code",
        f"wrote {plan.files[-1].path}",
    ]
    for rendered in plan.files:
        assert rendered.path.read_text(encoding="utf-8") == rendered.text
    assert os.access(clone / ".git/hooks/pre-push", os.X_OK)
    assert plan.log.parent.is_dir()
    assert service.calls == []
    # The gate was handed one synthetic heartbeat, exactly as a push would hand it.
    ((argv, cwd, stdin, env),) = hook.calls
    assert argv == (str(clone / ".git/hooks/pre-push"), "origin", "https://github.com/o/r")
    assert cwd == clone
    local, sha, ref, old = stdin.split()
    assert local == sha and ref == "refs/vibey-gh/sovereign-heartbeat" and not old.strip("0")
    assert env["PATH"] == RunnersConfig().path


def test_a_second_install_changes_nothing_that_already_holds(tmp_path):
    timer = _timer(tmp_path)
    plan = _plan(timer)
    timer.install(plan, load=False)
    lines, ok = timer.install(plan, load=False)
    assert ok and not any(line.startswith(("created", "set ")) for line in lines)


def test_install_refuses_a_clone_whose_gate_refuses_a_heartbeat(tmp_path):
    """No unit that could never publish is written, let alone loaded."""
    said = (
        "\x1b[0;31m✖ push refused: this repository publishes only the sovereign heartbeat.\x1b[0m\n"
    )
    service = _Service()
    timer = _timer(tmp_path, service=service, hook=_Hook(1, said))
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=True)
    assert not ok
    assert lines[-1].startswith("refused: the clone's own pre-push gate did not let a synthetic")
    assert "(exit 1): ✖ push refused: this repository publishes only" in lines[-1]
    assert "uv tool install --force --from . vibey" in lines[-1]
    assert lines[-1].endswith("The timer was not written.")
    assert not plan.files[-1].path.exists()
    assert service.calls == []


def test_install_stops_at_a_clone_it_cannot_create(tmp_path):
    timer = HeartbeatTimer(
        _cfg(tmp_path),
        home=tmp_path / "home",
        uid=UID,
        platform="darwin",
        python=PYTHON,
        origin=lambda interpreter, cwd: ORIGIN,
        git=lambda args, cwd: (128, ""),
        hook=_Hook(),
        service=_Service(),
    )
    timer.temp_roots = lambda: ()  # type: ignore[method-assign]
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=False)
    assert not ok and lines == [
        f"could not create the heartbeat's clone at {_clone(tmp_path)} (git init exited 128)"
    ]
    assert not any(rendered.path.exists() for rendered in plan.files)


def test_install_with_load_replaces_the_running_launch_agent(tmp_path):
    service = _Service({"bootout": (3, "not loaded")})
    timer = _timer(tmp_path, service=service)
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=True)
    assert ok and lines[-1] == f"loaded {LABEL}: a beat every 7m"
    assert service.managed() == [
        ("launchctl", "bootout", f"gui/{UID}/{LABEL}"),
        ("launchctl", "bootstrap", f"gui/{UID}", str(plan.files[-1].path)),
    ]


def test_install_with_load_enables_and_restarts_the_systemd_timer(tmp_path):
    service = _Service()
    timer = _timer(tmp_path, platform="linux", service=service)
    lines, ok = timer.install(_plan(timer), load=True)
    assert ok and lines[-1] == f"loaded {LABEL}: a beat every 7m"
    assert service.calls == [
        ("systemctl", "--user", "daemon-reload"),
        ("systemctl", "--user", "enable", "--now", f"{LABEL}.timer"),
        # A re-install takes effect: `enable --now` leaves a running timer as it was.
        ("systemctl", "--user", "restart", f"{LABEL}.timer"),
        ("loginctl", "show-user", str(UID), "-p", "Linger"),
    ]


@pytest.mark.parametrize(
    "answer, expected",
    [
        ((0, "Linger=no"), f"lingering is off for uid {UID}"),
        ((1, "Failed to get user"), "could not read whether lingering is on"),
    ],
)
def test_a_load_without_lingering_prints_the_step_that_keeps_it_running(tmp_path, answer, expected):
    timer = _timer(tmp_path, platform="linux", service=_Service({"loginctl": answer}))
    lines, ok = timer.install(_plan(timer), load=True)
    assert ok
    assert expected in lines[-1] and lines[-1].endswith('next: loginctl enable-linger "$USER"')


def test_a_refused_load_is_reported(tmp_path):
    timer = _timer(tmp_path, service=_Service({"bootstrap": (5, "Input/output error")}))
    lines, ok = timer.install(_plan(timer), load=True)
    assert not ok and lines[-1] == "launchctl bootstrap failed (exit 5): Input/output error"


def test_next_steps_are_the_exact_commands(tmp_path):
    timer = _timer(tmp_path)
    plan = _plan(timer)
    assert timer.next_steps(plan) == [
        (
            f"launchctl bootout gui/{UID}/{LABEL} 2>/dev/null;"
            f" launchctl bootstrap gui/{UID} {plan.files[-1].path}"
        ),
        "vibey-gh heartbeat status",
    ]
    linux = _timer(tmp_path, platform="linux")
    steps = linux.next_steps(_plan(linux))
    assert steps[1] == (
        f"systemctl --user enable --now {LABEL}.timer && systemctl --user restart {LABEL}.timer"
    )
    assert steps[2].startswith('loginctl enable-linger "$USER"')


# --- status -------------------------------------------------------------------------------


def _installed(tmp_path: Path, **kwargs: object) -> tuple[HeartbeatTimer, HeartbeatPlan]:
    timer = _timer(tmp_path, **kwargs)  # type: ignore[arg-type]
    plan = _plan(timer)
    lines, ok = timer.install(plan, load=False)
    assert ok, lines
    return timer, plan


def test_status_of_nothing_installed_says_what_is_missing(tmp_path):
    lines, healthy = _timer(tmp_path).status()
    assert not healthy
    assert lines[0] == f"missing: {tmp_path / 'home/Library/LaunchAgents' / f'{LABEL}.plist'}"
    assert lines[-1] == "last beat: none recorded"


def test_status_is_healthy_only_after_a_fresh_published_beat(tmp_path):
    hook = _Hook()
    timer, plan = _installed(tmp_path, clock=10_000.0, hook=hook)
    BeatRecord(10_000.0 - 125, True, "heartbeat published to refs/x at T: 1 runner").write(
        plan.record
    )
    lines, healthy = timer.status()
    assert healthy, lines
    assert "the clone's own pre-push gate lets a heartbeat through: carries-no-code" in lines
    assert f"{LABEL}: loaded (launchd)" in lines
    assert "last beat: 2m05s ago, published: heartbeat published to refs/x at T: 1 runner" in lines
    # Status asked the gate again rather than trusting the install's answer.
    assert len(hook.calls) == 2


def test_status_reads_the_interpreter_the_installed_unit_runs(tmp_path):
    """Drift is judged against what is on the host: `status` run from a checkout's own
    virtualenv must not call a timer installed with a tool interpreter drifted."""
    _, plan = _installed(tmp_path)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    other = _timer(tmp_path, python="/somewhere/else/python")
    assert other.status()[1] is True


@pytest.mark.parametrize(
    "record, expected",
    [
        (
            BeatRecord(10_000.0 - 60, False, "heartbeat withheld: no runner"),
            "withheld: heartbeat withheld",
        ),
        (BeatRecord(10_000.0 - 16 * 60, True, "ok"), "older than the 15m window"),
        (BeatRecord(10_000.0 + 90, True, "ok"), "recorded 90s in the future"),
    ],
)
def test_status_is_unhealthy_after_a_withheld_stale_or_impossible_beat(tmp_path, record, expected):
    timer, plan = _installed(tmp_path)
    record.write(plan.record)
    lines, healthy = timer.status()
    assert not healthy and any(expected in line for line in lines), lines


def test_status_names_drift_and_a_timer_that_is_not_loaded(tmp_path):
    timer, plan = _installed(tmp_path, service=_Service({"print": (113, "")}))
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    unit = plan.files[-1].path
    unit.write_text(unit.read_text(encoding="utf-8").replace("420", "421"), encoding="utf-8")
    lines, healthy = timer.status()
    assert not healthy
    assert f"drift: {unit}" in lines and f"{LABEL}: not loaded (launchd)" in lines


def test_status_names_a_clone_that_drifted_from_the_tree(tmp_path):
    timer, plan = _installed(tmp_path)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    hook = plan.files[0].path
    hook.chmod(0o644)
    (plan.clone / ".vibey-gh.toml").write_text("# an older lane\n", encoding="utf-8")
    import subprocess

    subprocess.run(
        ["git", "config", "--local", "remote.origin.url", "https://example.invalid/fork"],
        cwd=plan.clone,
        check=True,
    )
    lines, healthy = timer.status()
    assert not healthy
    assert f"not executable: {hook}" in lines
    assert f"drift: {plan.clone / '.vibey-gh.toml'}" in lines
    assert any(line.startswith("drift: remote.origin.url") for line in lines), lines


def test_status_reports_a_gate_that_refuses_a_heartbeat(tmp_path):
    _, plan = _installed(tmp_path)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    refusing = _timer(tmp_path, hook=_Hook(1, "vibey-gh: error: invalid choice: 'push-scope'\n"))
    lines, healthy = refusing.status()
    assert not healthy
    gate = next(line for line in lines if line.startswith("the clone's gate: "))
    assert "invalid choice: 'push-scope'" in gate and "uv tool install" in gate


def test_status_does_not_ask_a_gate_that_is_not_there(tmp_path):
    hook = _Hook()
    timer, plan = _installed(tmp_path, hook=hook)
    plan.files[0].path.unlink()
    lines, healthy = timer.status()
    assert not healthy and f"missing: {plan.files[0].path}" in lines
    assert len(hook.calls) == 1  # the install's own check, and no other


@pytest.mark.parametrize(
    "linger, healthy_expected, expected",
    [
        ((0, "Linger=yes"), True, f"lingering is on for uid {UID}"),
        (
            (0, "Linger=no"),
            False,
            'so the timer stops when you log out: loginctl enable-linger "$USER"',
        ),
        ((1, ""), False, "could not read whether lingering is on"),
    ],
)
def test_status_on_linux_asks_systemd_and_whether_it_lingers(
    tmp_path, linger, healthy_expected, expected
):
    service = _Service({"loginctl": linger})
    timer, plan = _installed(tmp_path, platform="linux", service=service)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    lines, healthy = timer.status()
    assert healthy is healthy_expected, lines
    assert any(expected in line for line in lines), lines
    assert ("systemctl", "--user", "is-active", "--quiet", f"{LABEL}.timer") in service.calls
    assert ("loginctl", "show-user", str(UID), "-p", "Linger") in service.calls


def test_status_on_linux_names_a_timer_that_is_not_active(tmp_path):
    service = _Service({"is-active": (3, "")})
    timer, plan = _installed(tmp_path, platform="linux", service=service)
    BeatRecord(10_000.0, True, "ok").write(plan.record)
    lines, healthy = timer.status()
    assert not healthy and f"{LABEL}: not loaded (systemd)" in lines


def test_status_of_a_unit_it_cannot_parse_or_render(tmp_path):
    _, plan = _installed(tmp_path)
    plan.files[-1].path.write_text("not a plist", encoding="utf-8")
    lines, healthy = _timer(tmp_path, origin=None).status()
    assert not healthy and any("cannot render" in line for line in lines)
    assert f"drift: {plan.files[-1].path}" in _timer(tmp_path).status()[0]


def test_status_without_a_lane_says_why(tmp_path):
    lines, healthy = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).status()
    assert not healthy and "is disabled" in lines[0]


def test_the_installed_interpreter_is_read_back_from_either_unit(tmp_path):
    timer, plan = _installed(tmp_path, platform="linux", python="/opt/a b/python")
    service = plan.files[2].path
    assert timer._installed_python(service, SYSTEMD) == "/opt/a b/python"
    service.write_text("[Service]\n", encoding="utf-8")
    assert timer._installed_python(service, SYSTEMD) is None
    assert timer._installed_python(tmp_path / "absent.plist", LAUNCHD) is None


# --- uninstall ----------------------------------------------------------------------------


def test_uninstall_is_a_dry_run_unless_applied_and_moves_units_and_clone_aside(tmp_path):
    service = _Service()
    timer, plan = _installed(tmp_path, service=service)
    unit = plan.files[-1].path
    retired = tmp_path / "home/.local/share/vibey-runner/retired-units"
    assert timer.uninstall(apply=False) == [
        f"would run: launchctl bootout gui/{UID}/{LABEL}",
        f"would move {unit} to {retired / unit.name}",
        f"would move {plan.clone} to {retired / plan.clone.name}",
    ]
    assert unit.exists() and plan.clone.is_dir() and service.calls == []
    assert timer.uninstall(apply=True) == [
        f"unloaded {LABEL}",
        f"moved {unit} to {retired / unit.name}",
        f"moved {plan.clone} to {retired / plan.clone.name}",
    ]
    assert (retired / unit.name).is_file() and (retired / plan.clone.name / ".git").is_dir()
    assert not unit.exists() and not plan.clone.exists()
    assert timer.uninstall(apply=True) == ["no heartbeat timer is installed"]


def test_uninstall_retires_a_clone_left_without_its_units(tmp_path):
    service = _Service()
    timer, plan = _installed(tmp_path, service=service)
    plan.files[-1].path.unlink()
    lines = timer.uninstall(apply=True)
    assert lines == [
        f"moved {plan.clone} to {plan.clone.parent / 'retired-units' / plan.clone.name}"
    ]
    assert service.calls == []


def test_uninstall_on_linux_disables_the_timer_and_reloads(tmp_path):
    service = _Service({"disable": (1, "Unit not loaded")})
    timer, plan = _installed(tmp_path, platform="linux", service=service)
    lines = timer.uninstall(apply=True)
    assert lines[0] == f"{LABEL} was not loaded (Unit not loaded)"
    assert service.calls[-1] == ("systemctl", "--user", "daemon-reload")
    assert not any(rendered.path.exists() for rendered in plan.files)


def test_uninstall_without_a_lane_says_why(tmp_path):
    lines = _timer(tmp_path, _cfg(tmp_path, fallback={"enabled": False})).uninstall(apply=True)
    assert "is disabled" in lines[0]


# --- the beat record and the default seams ------------------------------------------------


def test_a_beat_record_round_trips_and_a_bad_one_reads_as_none(tmp_path):
    path = tmp_path / "logs" / "beat.last.json"
    BeatRecord(12.5, False, "heartbeat withheld: x").write(path)
    assert BeatRecord.read(path) == BeatRecord(12.5, False, "heartbeat withheld: x")
    assert not list(path.parent.glob(".*partial"))
    path.write_text("{", encoding="utf-8")
    assert BeatRecord.read(path) is None
    assert BeatRecord.read(tmp_path / "absent.json") is None


def test_the_default_service_seam_runs_without_a_shell(tmp_path):
    assert HeartbeatTimer._run((sys.executable, "-c", "print('ok')")) == (0, "ok")
    assert HeartbeatTimer._run((str(tmp_path / "no-such-binary"),))[0] == 127


def test_the_default_origin_asks_the_interpreter_itself(tmp_path):
    origin = HeartbeatTimer._module_origin(sys.executable, tmp_path)
    assert origin is not None and origin.endswith("vibey_gh")
    assert HeartbeatTimer._module_origin(str(tmp_path / "no-python"), tmp_path) is None


def test_the_defaults_are_the_running_platform_and_interpreter(tmp_path):
    timer = HeartbeatTimer(_cfg(tmp_path), home=tmp_path, uid=UID)
    assert timer._platform == sys.platform and timer._python == sys.executable


# --- the command line ---------------------------------------------------------------------


def _fake_python(tmp_path: Path, *, knows_push_scope: bool = True) -> Path:
    """An 'interpreter' outside any checkout: it answers the origin probe, and -- unless it
    stands for a vibey-gh too old to know it -- the clone's gate's `push-scope` with the
    token, so the real hook installed in the clone lets a heartbeat through."""
    python = tmp_path / "tool" / "bin" / "python"
    python.parent.mkdir(parents=True)
    scope = "echo carries-no-code" if knows_push_scope else "echo 'invalid choice' >&2; exit 2"
    python.write_text(
        f'#!/bin/sh\ncase "$*" in\n  *push-scope*) cat >/dev/null; {scope} ;;\n'
        f"  *) echo {ORIGIN} ;;\nesac\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    return python


def _toml_repo(tmp_path: Path, monkeypatch, *, knows_push_scope: bool = True) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    python = _fake_python(tmp_path, knows_push_scope=knows_push_scope)
    (repo / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\n\n[runners]\nrepository = "o/r"\n'
        f'heartbeat_scheduler = "launchd"\nheartbeat_python = "{python}"\n',
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)
    monkeypatch.setattr(HeartbeatTimer, "temp_roots", staticmethod(lambda: ()))
    return home


def test_cli_heartbeat_install_writes_and_prints_the_next_commands(tmp_path, monkeypatch, capsys):
    """End to end through the real hook in a real clone: the gate the install tests is the
    one it wrote."""
    from vibey_gh.cli import main

    home = _toml_repo(tmp_path, monkeypatch)
    assert main(["heartbeat", "install"]) == 0
    out = capsys.readouterr().out
    plist = home / "Library/LaunchAgents" / f"{LABEL}.plist"
    assert f"wrote {plist}" in out and plist.is_file()
    assert "the clone's own pre-push gate lets a heartbeat through: carries-no-code" in out
    assert "the heartbeat timer was not loaded" in out
    assert f"launchctl bootstrap gui/{os.getuid()} {plist}" in out


def test_cli_heartbeat_install_refuses_a_gate_that_refuses(tmp_path, monkeypatch, capsys):
    from vibey_gh.cli import main

    home = _toml_repo(tmp_path, monkeypatch, knows_push_scope=False)
    assert main(["heartbeat", "install"]) == 1
    out = capsys.readouterr().out
    assert "refused: the clone's own pre-push gate did not let a synthetic heartbeat" in out
    assert "invalid choice" in out
    assert not (home / "Library/LaunchAgents" / f"{LABEL}.plist").exists()


def test_cli_heartbeat_refuses_what_it_cannot_render(tmp_path, monkeypatch, capsys):
    from vibey_gh.cli import main

    _toml_repo(tmp_path, monkeypatch)
    monkeypatch.setattr(HeartbeatTimer, "temp_roots", staticmethod(lambda: (tmp_path,)))
    assert main(["heartbeat", "install"]) == 1
    assert "which a reboot empties" in capsys.readouterr().err


def test_cli_heartbeat_status_and_uninstall_go_through_the_service_seam(
    tmp_path, monkeypatch, capsys
):
    import argparse

    from vibey_gh import cli

    home = _toml_repo(tmp_path, monkeypatch)
    service = _Service()
    install = argparse.Namespace(action="install", load=True, apply=False)
    assert cli._heartbeat(install, service=service) == 0
    assert f"loaded {LABEL}: a beat every 7m" in capsys.readouterr().out
    status = argparse.Namespace(action="status", load=False, apply=False)
    assert cli._heartbeat(status, service=service) == 1  # no beat recorded yet
    assert "last beat: none recorded" in capsys.readouterr().out
    record = home / "Library/Logs" / f"{LABEL}.last.json"
    BeatRecord(__import__("time").time(), True, "published").write(record)
    assert cli._heartbeat(status, service=service) == 0
    refused = _Service({"bootstrap": (5, "denied")})
    assert cli._heartbeat(install, service=refused) == 1
    dry = argparse.Namespace(action="uninstall", load=False, apply=False)
    assert cli._heartbeat(dry, service=service) == 0
    assert "dry run: nothing was changed" in capsys.readouterr().out
    applied = argparse.Namespace(action="uninstall", load=False, apply=True)
    assert cli._heartbeat(applied, service=service) == 0
    assert not (home / "Library/LaunchAgents" / f"{LABEL}.plist").exists()
    assert not (home / ".local/share/vibey-runner/heartbeat-r").exists()
