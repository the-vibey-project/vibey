# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign review runner, declared in the tree and installed from it (12.c).

Three halves, each held here: the `[runners]` table that declares the runner, the
installer that renders its LaunchAgent and supervisor from that table, and the
supervisor's own refusal to start on any credential but the dedicated, file-based one.
The supervisor is bash, so its refusals are driven through a harness of fake binaries
on `PATH`, the same way `test_templates.py` drives the workflow steps.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from vibey_gh import cli
from vibey_gh.cli import main
from vibey_gh.config import (
    GhConfig,
    PlatformConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    RunnersConfig,
    load_config,
)
from vibey_gh.doctor import _check_unknown_keys
from vibey_gh.interfaces import RunnersConfigInterface
from vibey_gh.interfaces.sovereign_runner_interface import (
    LaunchAgentUnitInterface,
    RunnerFileInterface,
    RunnerPlanInterface,
    SovereignRunnerInterface,
)
from vibey_gh.sovereign_runner import (
    TEMPLATES,
    LaunchAgentUnit,
    RunnerFile,
    RunnerPlan,
    SovereignRunner,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
SUPERVISOR = TEMPLATES / "vibey-runner.sh"
SECRET = "github_pat_NEVERPRINTME0123456789"
UID = 501


def _cfg(tmp_path: Path, **runners: object) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        platform=PlatformConfig(kind="github"),
        runners=RunnersConfig(**{"repository": "o/r", **runners}),  # type: ignore[arg-type]
        pr_automation=PrAutomationConfig(
            fallback=PrAutomationFallbackConfig(runner_label="vibey-local-r")
        ),
    )


class _Launchctl:
    """Records every launchctl argv and answers from a table keyed on the subcommand."""

    def __init__(self, answers: dict[str, tuple[int, str]] | None = None) -> None:
        self.calls: list[tuple[str, ...]] = []
        self.answers = answers or {}

    def __call__(self, argv: tuple[str, ...]) -> tuple[int, str]:
        self.calls.append(argv)
        return self.answers.get(argv[1], (0, ""))


def _runner(tmp_path: Path, cfg: GhConfig | None = None, launchctl=None) -> SovereignRunner:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return SovereignRunner(
        cfg or _cfg(tmp_path), home=home, uid=UID, launchctl=launchctl or _Launchctl()
    )


def _plan(runner: SovereignRunner) -> RunnerPlan:
    plan, problem = runner.render()
    assert problem == "" and plan is not None
    return plan


def _login(home: Path, *, token: bool = True, mode: int = 0o600) -> Path:
    directory = home / ".config" / "gh-runner"
    directory.mkdir(parents=True, exist_ok=True)
    hosts = directory / "hosts.yml"
    body = "github.com:\n    users:\n        bot:\n"
    if token:
        body += f"            oauth_token: {SECRET}\n    oauth_token: {SECRET}\n"
    hosts.write_text(body + "    user: bot\n", encoding="utf-8")
    hosts.chmod(mode)
    return directory


# --- the declared table ------------------------------------------------------------------


def test_runners_table_defaults():
    runners = RunnersConfig()
    assert runners.repository == ""
    assert runners.unit_prefix == "org.vibey.runner"
    assert runners.install_dir == "~/.local/share/vibey-runner"
    assert runners.gh_config_dir == "~/.config/gh-runner"
    assert runners.launch_agents_dir == "~/Library/LaunchAgents"
    assert runners.require_ac is True
    assert runners.throttle_seconds == 120
    assert isinstance(runners, RunnersConfigInterface)


@pytest.mark.parametrize(
    ("runners", "platform", "expected"),
    [
        (
            {"repository": "a/b"},
            PlatformConfig(kind="github"),
            ("a/b", "https://github.com/a/b", ""),
        ),
        (
            {},
            PlatformConfig(kind="github", repository="o/r"),
            ("o/r", "https://github.com/o/r", ""),
        ),
        (
            {},
            PlatformConfig(kind="github", host="ghe.example", repository="o/r"),
            ("o/r", "https://ghe.example/o/r", ""),
        ),
        (
            {},
            PlatformConfig(kind="github"),
            (
                "",
                "",
                "runners.repository is empty and [platform] names no repository to derive it from",
            ),
        ),
        (
            {"repository": "a/b"},
            PlatformConfig(kind="forgejo"),
            (
                "",
                "",
                "the sovereign runner is a GitHub Actions runner; [platform] kind is forgejo",
            ),
        ),
    ],
)
def test_runners_registration_is_declared_or_derived(runners, platform, expected):
    assert RunnersConfig(**runners).registration(platform) == expected


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repository", "not-a-slug"),
        ("repository", "o/r/extra"),
        ("unit_prefix", ""),
        ("unit_prefix", "has space"),
        ("install_dir", ""),
        ("install_dir", "relative/path"),
        ("gh_config_dir", "~/.config/gh"),
        ("gh_config_dir", "~/.config/gh/"),
        ("launch_agents_dir", ""),
        ("log_dir", "logs"),
        ("image", ""),
        ("runner_version", "latest"),
        ("container_model_url", "host.docker.internal:11434"),
        ("throttle_seconds", 5),
        ("throttle_seconds", 3601),
        ("max_failures", 0),
        ("path", ""),
    ],
)
def test_runners_invalid_fields_are_refused(field, value):
    with pytest.raises(ValueError, match=rf"^runners\.{field} "):
        RunnersConfig(**{field: value})


def test_a_toml_runners_table_loads(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[runners]\n"
        'repository = "x/y"\n'
        'unit_prefix = "com.example.runner"\n'
        "require_ac = false\n"
        "throttle_seconds = 60\n",
        encoding="utf-8",
    )
    runners = load_config(tmp_path).runners
    assert (runners.repository, runners.unit_prefix) == ("x/y", "com.example.runner")
    assert (runners.require_ac, runners.throttle_seconds) == (False, 60)
    assert _check_unknown_keys(tmp_path) == []


def test_a_stray_runners_key_is_named_by_doctor(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text('[runners]\nrepo = "x/y"\n', encoding="utf-8")
    assert [f.message for f in _check_unknown_keys(tmp_path)] == [
        "[runners] repo is not a key vibey-gh reads; it is silently ignored"
    ]


def test_repository_declares_its_runner_registration():
    cfg = load_config(REPO_ROOT)
    slug, url, problem = cfg.runners.registration(cfg.platform)
    assert (slug, url, problem) == (
        "the-vibey-project/vibey",
        "https://github.com/the-vibey-project/vibey",
        "",
    )
    # The unit keeps the name the operator's LaunchAgent already has, so an install
    # replaces it in place rather than standing a second supervisor up beside it.
    assert cfg.runners.unit_prefix == "com.adammatthewsteinberger.vibey-runner"
    assert not [f for f in _check_unknown_keys(REPO_ROOT) if "[runners]" in f.message]


# --- rendering ---------------------------------------------------------------------------


def test_the_plan_renders_the_supervisor_and_a_launch_agent_from_config(tmp_path):
    runner = _runner(tmp_path)
    plan = _plan(runner)
    home = tmp_path / "home"
    assert plan.label == "org.vibey.runner-r"
    assert (plan.repository, plan.repo_url) == ("o/r", "https://github.com/o/r")
    assert plan.plist == home / "Library/LaunchAgents/org.vibey.runner-r.plist"
    install = home / ".local/share/vibey-runner"
    assert [f.path for f in plan.files] == [
        plan.plist,
        install / "Dockerfile",
        install / "entrypoint.sh",
        install / "vibey-runner.sh",
    ]
    assert [f.executable for f in plan.files] == [False, False, True, True]
    agent = plistlib.loads(plan.files[0].text.encode("utf-8"))
    assert agent["Label"] == "org.vibey.runner-r"
    assert agent["ProgramArguments"] == [str(install / "vibey-runner.sh")]
    assert agent["WorkingDirectory"] == str(install)
    assert agent["EnvironmentVariables"] == {
        "VIBEY_REPO_URL": "https://github.com/o/r",
        "VIBEY_RUNNER_LABEL": "vibey-local-r",
        "VIBEY_RUNNER_IMAGE": "vibey-runner:latest",
        "VIBEY_OLLAMA_URL": "http://127.0.0.1:11434",
        "VIBEY_CONTAINER_OLLAMA_URL": "http://host.docker.internal:11434",
        "VIBEY_REQUIRE_AC": "1",
        "VIBEY_MAX_FAILURES": "5",
        "GH_CONFIG_DIR": str(home / ".config/gh-runner"),
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    }
    assert agent["RunAtLoad"] is True and agent["KeepAlive"] is True
    assert agent["ThrottleInterval"] == 120
    assert agent["StandardOutPath"] == str(home / "Library/Logs/org.vibey.runner-r.log")
    assert agent["StandardErrorPath"] == agent["StandardOutPath"]
    for rendered in plan.files:
        assert not re.search(r"__[A-Z_]+__", rendered.text), rendered.path
    assert isinstance(plan, RunnerPlanInterface)
    assert isinstance(plan.files[0], RunnerFileInterface)


def test_values_are_escaped_into_the_plist_not_spliced(tmp_path):
    cfg = _cfg(tmp_path, image="reg.example/a&b<c>:1", require_ac=False)
    agent = plistlib.loads(_plan(_runner(tmp_path, cfg)).files[0].text.encode("utf-8"))
    assert agent["EnvironmentVariables"]["VIBEY_RUNNER_IMAGE"] == "reg.example/a&b<c>:1"
    assert agent["EnvironmentVariables"]["VIBEY_REQUIRE_AC"] == "0"


def test_absolute_paths_are_kept_as_declared(tmp_path):
    cfg = _cfg(tmp_path, install_dir=str(tmp_path / "opt"), launch_agents_dir=str(tmp_path / "la"))
    plan = _plan(_runner(tmp_path, cfg))
    assert plan.plist == tmp_path / "la/org.vibey.runner-r.plist"
    assert plan.files[-1].path == tmp_path / "opt/vibey-runner.sh"


def test_the_repository_s_own_plan_names_the_live_repository(tmp_path):
    plan = _plan(_runner(tmp_path, load_config(REPO_ROOT)))
    assert plan.label == "com.adammatthewsteinberger.vibey-runner-vibey"
    agent = plistlib.loads(plan.files[0].text.encode("utf-8"))
    env = agent["EnvironmentVariables"]
    assert env["VIBEY_REPO_URL"] == "https://github.com/the-vibey-project/vibey"
    assert env["VIBEY_RUNNER_LABEL"] == "vibey-local-vibey"


@pytest.mark.parametrize(
    ("cfg", "problem"),
    [
        (
            GhConfig(root=Path("."), platform=PlatformConfig(kind="github")),
            "runners.repository is empty and [platform] names no repository to derive it from",
        ),
        (
            GhConfig(
                root=Path("."),
                runners=RunnersConfig(repository="o/r"),
                pr_automation=PrAutomationConfig(
                    fallback=PrAutomationFallbackConfig(enabled=False)
                ),
                platform=PlatformConfig(kind="github"),
            ),
            (
                "[pr_automation.fallback] is disabled, so no workflow schedules onto a"
                " sovereign runner; enable it before installing one"
            ),
        ),
    ],
)
def test_an_underivable_plan_is_refused_with_its_reason(tmp_path, cfg, problem):
    assert _runner(tmp_path, cfg).render() == (None, problem)


def test_the_dockerfile_takes_its_runner_version_from_the_build_not_a_default():
    dockerfile = (TEMPLATES / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r"^ARG RUNNER_VERSION$", dockerfile, re.MULTILINE)
    assert "2.328.0" not in dockerfile


def test_no_template_names_a_repository_or_a_person():
    """Nothing hard-coded (12.c): the supervisor reads everything from its unit."""
    for template in TEMPLATES.iterdir():
        text = template.read_text(encoding="utf-8")
        body = "\n".join(text.splitlines()[2:])  # past the shebang and provenance line
        assert "adammatthewsteinberger" not in body, template.name
        assert "the-vibey-project" not in body, template.name


# --- install, check, next steps ----------------------------------------------------------


def test_install_writes_every_file_and_loads_nothing(tmp_path):
    launchctl = _Launchctl()
    runner = _runner(tmp_path, launchctl=launchctl)
    plan = _plan(runner)
    lines = runner.install(plan, load=False)
    assert lines == [f"wrote {f.path}" for f in plan.files]
    for rendered in plan.files:
        assert rendered.path.read_text(encoding="utf-8") == rendered.text
        assert bool(rendered.path.stat().st_mode & 0o111) is rendered.executable
    assert launchctl.calls == []


def test_install_with_load_replaces_the_running_agent(tmp_path):
    launchctl = _Launchctl({"bootout": (3, "No such process")})
    runner = _runner(tmp_path, launchctl=launchctl)
    plan = _plan(runner)
    lines = runner.install(plan, load=True)
    assert launchctl.calls == [
        ("launchctl", "bootout", f"gui/{UID}/org.vibey.runner-r"),
        ("launchctl", "bootstrap", f"gui/{UID}", str(plan.plist)),
    ]
    assert lines[-1] == f"loaded org.vibey.runner-r from {plan.plist}"


def test_install_reports_a_load_that_launchd_refuses(tmp_path):
    launchctl = _Launchctl({"bootstrap": (5, "Input/output error")})
    runner = _runner(tmp_path, launchctl=launchctl)
    lines = runner.install(_plan(runner), load=True)
    assert lines[-1] == "launchctl bootstrap failed (exit 5): Input/output error"


def test_next_steps_are_the_exact_commands_in_order(tmp_path):
    runner = _runner(tmp_path)
    plan = _plan(runner)
    home = tmp_path / "home"
    steps = runner.next_steps(plan)
    gh_dir = home / ".config/gh-runner"
    login = (
        f"env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR={gh_dir}"
        " gh auth login --hostname github.com --with-token --insecure-storage"
    )
    assert steps == [
        f"mkdir -m 700 -p {gh_dir}",
        login,
        (
            "docker build --build-arg RUNNER_VERSION=2.337.0 -t vibey-runner:latest"
            f" {home / '.local/share/vibey-runner'}"
        ),
        (
            f"launchctl bootout gui/{UID}/org.vibey.runner-r 2>/dev/null;"
            f" launchctl bootstrap gui/{UID} {plan.plist}"
        ),
        "vibey-gh runner check",
        (
            f"env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR={gh_dir} gh api"
            " repos/o/r/actions/runners --jq"
            " '.runners[] | {name, status, busy, labels: [.labels[].name]}'"
        ),
    ]


def test_check_reports_missing_drift_and_the_credential_then_passes(tmp_path):
    runner = _runner(tmp_path)
    plan = _plan(runner)
    home = tmp_path / "home"
    gh_dir = home / ".config/gh-runner"
    missing = runner.check(plan)
    assert [f"missing: {f.path}" for f in plan.files] == missing[:-1]
    assert missing[-1].startswith(f"credential: {gh_dir} does not exist")
    runner.install(plan, load=False)
    _login(home)
    assert runner.check(plan) == []
    plan.files[0].path.write_text(plan.files[0].text + " ", encoding="utf-8")
    plan.files[-1].path.chmod(0o644)
    assert runner.check(plan) == [
        f"drift: {plan.files[0].path}",
        f"not executable: {plan.files[-1].path}",
    ]


@pytest.mark.parametrize(
    ("setup", "expected"),
    [
        ("no-hosts", "holds no gh login"),
        ("keyring", "the macOS keyring, which a LaunchAgent cannot read"),
        ("readable", "is readable by other users"),
    ],
)
def test_the_credential_check_names_what_is_wrong_and_never_the_token(tmp_path, setup, expected):
    runner = _runner(tmp_path)
    home = tmp_path / "home"
    if setup == "no-hosts":
        (home / ".config/gh-runner").mkdir(parents=True)
    else:
        _login(home, token=setup != "keyring", mode=0o644 if setup == "readable" else 0o600)
    (problem,) = runner.credential_problems()
    assert expected in problem
    assert SECRET not in problem


# --- cleanup and uninstall ---------------------------------------------------------------


def _agent(directory: Path, name: str, label: str | None, url: str | None) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    body: dict[str, object] = {}
    if label is not None:
        body["Label"] = label
    if url is not None:
        body["EnvironmentVariables"] = {"VIBEY_REPO_URL": url}
    path = directory / name
    path.write_bytes(plistlib.dumps(body))
    return path


def test_cleanup_lists_exactly_the_undeclared_agents_under_the_prefix(tmp_path):
    runner = _runner(tmp_path)
    plan = _plan(runner)
    agents = plan.plist.parent
    _agent(agents, plan.plist.name, plan.label, "https://github.com/o/r")
    old = _agent(agents, "org.vibey.runner-gone.plist", "org.vibey.runner-gone", "https://x/gone")
    base = _agent(agents, "org.vibey.runner.plist", "org.vibey.runner", None)
    _agent(agents, "org.vibey.runnerish.plist", "org.vibey.runnerish", None)
    _agent(agents, "org.vibey.local-authority.plist", "org.vibey.local-authority", None)
    (agents / "org.vibey.runner-broken.plist").write_text("not a plist", encoding="utf-8")
    (agents / "org.vibey.runner-notes.txt").write_text("", encoding="utf-8")
    strays = runner.strays(plan)
    assert strays == (
        LaunchAgentUnit(agents / "org.vibey.runner-broken.plist", "org.vibey.runner-broken", ""),
        LaunchAgentUnit(old, "org.vibey.runner-gone", "https://x/gone"),
        LaunchAgentUnit(base, "org.vibey.runner", ""),
    )
    assert isinstance(strays[0], LaunchAgentUnitInterface)


def test_cleanup_is_a_dry_run_unless_applied(tmp_path):
    launchctl = _Launchctl()
    runner = _runner(tmp_path, launchctl=launchctl)
    plan = _plan(runner)
    old = _agent(plan.plist.parent, "org.vibey.runner-gone.plist", "org.vibey.runner-gone", "u")
    retired = tmp_path / "home/.local/share/vibey-runner/retired-units"
    lines = runner.remove(runner.strays(plan), apply=False)
    assert lines == [
        (
            f"would unload org.vibey.runner-gone (launchctl bootout gui/{UID}/org.vibey.runner-gone)"
            f" and move {old} to {retired / old.name} [serves u]"
        )
    ]
    assert old.exists() and launchctl.calls == []


def test_cleanup_applied_unloads_and_moves_aside_never_deletes(tmp_path):
    launchctl = _Launchctl({"bootout": (3, "Boot-out failed: 3: No such process")})
    runner = _runner(tmp_path, launchctl=launchctl)
    plan = _plan(runner)
    old = _agent(plan.plist.parent, "org.vibey.runner-gone.plist", "org.vibey.runner-gone", None)
    retired = tmp_path / "home/.local/share/vibey-runner/retired-units"
    lines = runner.remove(runner.strays(plan), apply=True)
    assert launchctl.calls == [("launchctl", "bootout", f"gui/{UID}/org.vibey.runner-gone")]
    assert lines == [
        "org.vibey.runner-gone was not loaded (launchctl: Boot-out failed: 3: No such process)",
        f"moved {old} to {retired / old.name}",
    ]
    assert not old.exists() and (retired / old.name).is_file()


def test_nothing_to_clean_says_so(tmp_path):
    runner = _runner(tmp_path)
    assert runner.remove((), apply=True) == ["nothing to remove"]


def test_uninstall_removes_the_declared_unit_and_only_the_files_it_wrote(tmp_path):
    launchctl = _Launchctl()
    runner = _runner(tmp_path, launchctl=launchctl)
    plan = _plan(runner)
    runner.install(plan, load=False)
    keep = plan.files[-1].path.parent / "heartbeat-r"
    keep.write_text("", encoding="utf-8")
    dry = runner.uninstall(plan, apply=False)
    assert dry[0].startswith("would unload org.vibey.runner-r")
    assert dry[1:] == [f"would delete {f.path}" for f in plan.files[1:]]
    assert all(f.path.exists() for f in plan.files)
    runner.uninstall(plan, apply=True)
    assert not any(f.path.exists() for f in plan.files)
    assert keep.exists()
    assert launchctl.calls == [("launchctl", "bootout", f"gui/{UID}/org.vibey.runner-r")]


def test_uninstall_of_nothing_installed_says_so(tmp_path):
    runner = _runner(tmp_path)
    assert runner.uninstall(_plan(runner), apply=True) == ["nothing to remove"]


def test_the_default_launchctl_runs_the_real_binary_without_a_shell(tmp_path):
    runner = SovereignRunner(_cfg(tmp_path), home=tmp_path, uid=UID)
    code, output = runner._launchctl(("/nonexistent/launchctl-for-test", "list"))
    assert code == 127 and "No such file" in output
    code, output = runner._launchctl(("sh", "-c", "echo out; echo err >&2; exit 4"))
    assert (code, output) == (4, "out\nerr")


def test_the_runner_satisfies_its_interface(tmp_path):
    assert isinstance(_runner(tmp_path), SovereignRunnerInterface)
    assert isinstance(RunnerFile(Path("x"), ""), RunnerFileInterface)


# --- the command line --------------------------------------------------------------------


def _repo(tmp_path: Path, monkeypatch, extra: str = "") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\n\n[runners]\nrepository = "o/r"\n' + extra,
        encoding="utf-8",
    )
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)
    return home


def test_cli_install_writes_files_and_prints_the_next_commands(tmp_path, monkeypatch, capsys):
    home = _repo(tmp_path, monkeypatch)
    assert main(["runner", "install"]) == 0
    out = capsys.readouterr().out
    plist = home / "Library/LaunchAgents/org.vibey.runner-r.plist"
    assert f"wrote {plist}" in out
    assert "nothing was loaded" in out
    assert "gh auth login --hostname github.com --with-token --insecure-storage" in out
    assert f"launchctl bootstrap gui/{os.getuid()} {plist}" in out
    assert "Administration: Read and write" in out
    assert plist.is_file()


def test_cli_check_passes_after_install_and_login_then_catches_drift(tmp_path, monkeypatch, capsys):
    home = _repo(tmp_path, monkeypatch)
    assert main(["runner", "check"]) == 1
    main(["runner", "install"])
    _login(home)
    capsys.readouterr()
    assert main(["runner", "check"]) == 0
    assert "vibey-gh runner: org.vibey.runner-r matches the tree" in capsys.readouterr().out
    plist = home / "Library/LaunchAgents/org.vibey.runner-r.plist"
    plist.write_text(plist.read_text(encoding="utf-8").replace("120", "121"), encoding="utf-8")
    assert main(["runner", "check"]) == 1
    assert f"drift: {plist}" in capsys.readouterr().err


def test_cli_refuses_an_underivable_runner(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".vibey-gh.toml").write_text('[platform]\nkind = "github"\n', encoding="utf-8")
    monkeypatch.chdir(repo)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert main(["runner", "install"]) == 1
    assert "runners.repository is empty" in capsys.readouterr().err


def test_cli_cleanup_and_uninstall_are_dry_runs_by_default(tmp_path, monkeypatch, capsys):
    home = _repo(tmp_path, monkeypatch)
    agents = home / "Library/LaunchAgents"
    old = _agent(agents, "org.vibey.runner-gone.plist", "org.vibey.runner-gone", "u")
    assert main(["runner", "cleanup"]) == 0
    out = capsys.readouterr().out
    assert "would unload org.vibey.runner-gone" in out
    assert "dry run: nothing was changed; pass --apply to do it" in out
    assert old.exists()
    main(["runner", "install"])
    capsys.readouterr()
    assert main(["runner", "uninstall"]) == 0
    assert "would delete" in capsys.readouterr().out


def test_cli_apply_goes_through_the_launchctl_seam(tmp_path, monkeypatch, capsys):
    home = _repo(tmp_path, monkeypatch)
    old = _agent(home / "Library/LaunchAgents", "org.vibey.runner-gone.plist", "x", None)
    launchctl = _Launchctl()
    args = argparse.Namespace(action="cleanup", apply=True, load=False)
    assert cli._runner(args, launchctl=launchctl) == 0
    assert launchctl.calls == [("launchctl", "bootout", f"gui/{os.getuid()}/x")]
    assert not old.exists()
    args = argparse.Namespace(action="install", apply=False, load=True)
    assert cli._runner(args, launchctl=launchctl) == 0
    assert "loaded org.vibey.runner-r" in capsys.readouterr().out


# --- the supervisor's refusals, driven through fake binaries -----------------------------

_FAKE = r"""#!/usr/bin/env bash
# Records the call and the credential-bearing environment it saw, then answers from files.
printf '%s|GH_CONFIG_DIR=%s|GH_TOKEN=%s|GITHUB_TOKEN=%s\n' "$(basename "$0") $*" \
  "${GH_CONFIG_DIR:-}" "${GH_TOKEN:-}" "${GITHUB_TOKEN:-}" >> "$FAKE_DIR/calls"
name=$(basename "$0")
case "$name $1" in
  "gh auth") exit "$(cat "$FAKE_DIR/auth_rc" 2>/dev/null || echo 0)" ;;
  "gh api")
    case "$*" in
      *registration-token*) cat "$FAKE_DIR/token" 2>/dev/null ;;
    esac
    exit 0 ;;
  "docker info") exit "$(cat "$FAKE_DIR/docker_rc" 2>/dev/null || echo 0)" ;;
  "docker image") exit 0 ;;
  "docker ps") exit 0 ;;
  "docker run") printf 'RUNNER_TOKEN=%s\n' "${RUNNER_TOKEN:-}" >> "$FAKE_DIR/calls"; exit 1 ;;
  "pmset -g") echo "Now drawing from 'AC Power'" ;;
esac
exit 0
"""

_ENV = {
    "VIBEY_REPO_URL": "https://github.com/o/r",
    "VIBEY_RUNNER_LABEL": "vibey-local-r",
    "VIBEY_RUNNER_IMAGE": "vibey-runner:test",
    "VIBEY_OLLAMA_URL": "http://127.0.0.1:1",
    "VIBEY_CONTAINER_OLLAMA_URL": "http://host.docker.internal:1",
    "VIBEY_REQUIRE_AC": "1",
    "VIBEY_MAX_FAILURES": "1",
    "VIBEY_CAFFEINATED": "1",
}


def _supervise(tmp_path: Path, *, gh_dir: Path | None, **env: str):
    if shutil.which("bash") is None:  # pragma: no cover - every supported host has bash
        pytest.skip("the supervisor is a bash script")
    fake = tmp_path / "fake"
    fake.mkdir(exist_ok=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    for name in ("gh", "docker", "curl", "pmset"):
        (bin_dir / name).write_text(_FAKE, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    base = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "FAKE_DIR": str(fake),
        "GH_TOKEN": "env-token-must-be-ignored",
        "GITHUB_TOKEN": "env-token-must-be-ignored",
        **_ENV,
    }
    if gh_dir is not None:
        base["GH_CONFIG_DIR"] = str(gh_dir)
    base.update(env)
    done = subprocess.run(
        ["bash", str(SUPERVISOR)],
        env=base,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,  # the exit status IS the assertion
    )
    calls = (fake / "calls").read_text(encoding="utf-8") if (fake / "calls").exists() else ""
    return done.returncode, done.stdout + done.stderr, calls, fake


def test_the_supervisor_refuses_without_a_dedicated_config_dir(tmp_path):
    code, out, calls, _ = _supervise(tmp_path, gh_dir=None)
    assert code == 1
    assert "REFUSING TO START: GH_CONFIG_DIR is not set" in out
    assert "gh " not in calls  # never asked gh anything, so never reached the keyring


def test_the_supervisor_refuses_a_missing_config_dir_with_the_command_to_make_it(tmp_path):
    gh_dir = tmp_path / "nope"
    code, out, calls, _ = _supervise(tmp_path, gh_dir=gh_dir)
    assert code == 1
    assert f"{gh_dir} does not exist" in out
    assert f"GH_CONFIG_DIR={gh_dir} gh auth login --hostname github.com" in out
    assert "--with-token --insecure-storage" in out
    assert "gh " not in calls


@pytest.mark.parametrize(
    ("token", "mode", "expected"),
    [
        (False, 0o600, "the macOS keyring, which a LaunchAgent cannot read"),
        (True, 0o644, "is readable by other users"),
        (True, 0o640, "is readable by other users"),
    ],
)
def test_the_supervisor_refuses_a_credential_launchd_cannot_use(tmp_path, token, mode, expected):
    gh_dir = _login(tmp_path, token=token, mode=mode)
    code, out, calls, _ = _supervise(tmp_path, gh_dir=gh_dir)
    assert code == 1 and expected in out
    assert SECRET not in out
    assert "gh " not in calls


def test_the_supervisor_refuses_a_rejected_token(tmp_path):
    gh_dir = _login(tmp_path)
    (tmp_path / "fake").mkdir()
    (tmp_path / "fake/auth_rc").write_text("1", encoding="utf-8")
    code, out, calls, _ = _supervise(tmp_path, gh_dir=gh_dir)
    assert code == 1
    assert f"the token in {gh_dir} is not accepted by github.com" in out
    assert SECRET not in out
    # gh saw only the dedicated directory, and none of the ambient tokens.
    (auth,) = [line for line in calls.splitlines() if line.startswith("gh auth")]
    assert (
        auth
        == f"gh auth status --hostname github.com|GH_CONFIG_DIR={gh_dir}|GH_TOKEN=|GITHUB_TOKEN="
    )


def test_the_supervisor_refuses_to_start_without_docker(tmp_path):
    gh_dir = _login(tmp_path)
    (tmp_path / "fake").mkdir()
    (tmp_path / "fake/docker_rc").write_text("1", encoding="utf-8")
    code, out, _, _ = _supervise(tmp_path, gh_dir=gh_dir)
    assert code == 1 and "docker is not running" in out


def test_the_supervisor_refuses_a_missing_setting(tmp_path):
    code, out, calls, _ = _supervise(tmp_path, gh_dir=None, VIBEY_RUNNER_LABEL="")
    assert code == 1 and "VIBEY_RUNNER_LABEL is not set" in out
    assert calls == ""


def test_the_supervisor_stays_down_on_battery(tmp_path):
    # The shared fake pmset reports AC; an earlier directory on PATH overrides it here.
    battery = tmp_path / "battery"
    battery.mkdir()
    (battery / "pmset").write_text("#!/bin/sh\necho \"Now drawing from 'Battery Power'\"\n")
    (battery / "pmset").chmod(0o755)
    code, out, calls, _ = _supervise(
        tmp_path, gh_dir=_login(tmp_path), PATH=f"{battery}:{tmp_path / 'bin'}:/usr/bin:/bin"
    )
    assert code == 0 and "on battery power" in out
    assert "gh " not in calls


def test_the_supervisor_registers_with_the_dedicated_credential_only(tmp_path):
    gh_dir = _login(tmp_path)
    (tmp_path / "fake").mkdir()
    (tmp_path / "fake/token").write_text("REGTOKEN123\n", encoding="utf-8")
    code, out, calls, _ = _supervise(tmp_path, gh_dir=gh_dir)
    # The fake runner exits non-zero once, and VIBEY_MAX_FAILURES=1 stops the loop.
    assert code == 1 and "1 consecutive failures -- stopping" in out
    mint = [line for line in calls.splitlines() if "registration-token" in line]
    assert mint == [
        (
            "gh api -X POST repos/o/r/actions/runners/registration-token --jq .token"
            f"|GH_CONFIG_DIR={gh_dir}|GH_TOKEN=|GITHUB_TOKEN="
        )
    ]
    (run,) = [line for line in calls.splitlines() if line.startswith("docker run")]
    assert "REGTOKEN123" not in run  # handed over by environment, not on the argv
    assert "--url" not in run and "RUNNER_REPOSITORY_URL=https://github.com/o/r" in run
    assert "RUNNER_TOKEN=REGTOKEN123" in calls
    assert "REGTOKEN123" not in out and SECRET not in out


def test_the_supervisor_names_the_permission_when_it_cannot_mint(tmp_path):
    code, out, _, _ = _supervise(tmp_path, gh_dir=_login(tmp_path))
    assert code == 1
    assert "Administration: Read and write" in out


def test_every_runners_key_is_documented_with_its_default():
    """The configuration page's `[runners]` table names every field the code reads."""
    import dataclasses

    docs = (Path(__file__).resolve().parent.parent / "docs" / "configuration.md").read_text(
        encoding="utf-8"
    )
    section = docs.split("## `[runners]`", 1)[1].split("\n## ", 1)[0]
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", section, re.MULTILINE))
    assert documented == {field.name for field in dataclasses.fields(RunnersConfig)}
    assert '`"~/.config/gh-runner"`' in section and "Administration: Read and write" in section


def test_the_runbook_and_the_code_name_the_same_permission():
    from vibey_gh.sovereign_runner import PAT_PERMISSION

    runbook = REPO_ROOT / "docs" / "runbooks" / "sovereign-review-runner.md"
    if not runbook.is_file():  # pragma: no cover - the tenant tested outside the monorepo
        pytest.skip("the runbook lives in the vibey repository")
    text = runbook.read_text(encoding="utf-8")
    assert PAT_PERMISSION in text and PAT_PERMISSION in SUPERVISOR.read_text(encoding="utf-8")
    assert f"RUNNER_VERSION={RunnersConfig().runner_version}" in text
