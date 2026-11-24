# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/install.sh` and `scripts/uninstall-krypton.sh`, run for real against stub tools.

Each test puts stub commands (uv, pipx, code, flatpak, git, vibey, ...) first on PATH; every
stub appends the command line it was given to a log and answers as declared. So the tests see
exactly what the scripts would run, and nothing on this machine is touched. The invariant
they hold above all: nothing either script runs ever removes vibey-engine.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UNINSTALL = REPO / "scripts" / "uninstall-krypton.sh"
INSTALL = REPO / "scripts" / "install.sh"
APP_ID = "io.github.the_vibey_project.krypton"


class Machine:
    """A temporary HOME, root and PATH of recording stubs."""

    def __init__(self, tmp: Path) -> None:
        self.home = tmp / "home"
        self.root = tmp / "root"
        self.bin = tmp / "bin"
        self.log = tmp / "calls.log"
        for d in (self.home, self.root, self.bin):
            d.mkdir(parents=True)
        self.log.write_text("")

    def stub(self, name: str, script: str = "exit 0", where: Path | None = None) -> None:
        path = (where or self.bin) / name
        path.write_text(f'#!/bin/sh\necho "{name} $*" >> "{self.log}"\n{script}\n')
        path.chmod(0o755)

    def environment(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        return {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "KRYPTON_ROOT": str(self.root),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            **(extra or {}),
        }

    def run(
        self, script: Path, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(script), *args],
            env=self.environment(env),
            capture_output=True,
            text=True,
            check=False,
        )

    def piped(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        """The script read from stdin, as `curl ... | sh -s -- ARGS` runs it: `$0` is no file."""
        return subprocess.run(
            ["sh", "-s", "--", *args],
            input=script.read_text(encoding="utf-8"),
            env=self.environment(),
            capture_output=True,
            text=True,
            check=False,
        )

    def calls(self) -> list[str]:
        return [line for line in self.log.read_text().splitlines() if line]


def never_touches_the_engine(machine: Machine) -> None:
    """No command either script ran removes vibey-engine (the core is never uninstalled)."""
    for call in machine.calls():
        assert not ("uninstall" in call and "vibey-engine" in call), call


# ------------------------------------------------------------------ the uninstaller


def test_a_clean_machine_is_reported_and_nothing_changes(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    done = m.run(UNINSTALL)
    assert done.returncode == 0, done.stderr
    assert "Dry run" in done.stdout and "Nothing was changed" in done.stdout
    assert done.stdout.count("not installed") == 3
    assert m.calls() == []


def test_a_dry_run_lists_without_removing(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    m.stub(
        "uv",
        'case "$*" in "tool list") echo "krypton-app v0.1.0"; echo "vibey-engine v3.4.0";; esac',
    )
    done = m.run(UNINSTALL)
    assert "would remove: krypton-app (uv tool)" in done.stdout
    assert not any("uninstall" in c for c in m.calls())


def test_the_krypton_command_is_removed_with_the_tool_that_installed_it(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    m.stub(
        "uv",
        'case "$*" in "tool list") echo "krypton-app v0.1.0"; echo "vibey-engine v3.4.0";; esac',
    )
    done = m.run(UNINSTALL, "--yes")
    assert done.returncode == 0, done.stdout
    assert "uv tool uninstall krypton-app" in m.calls()
    assert "vibey-engine was not touched" in done.stdout
    never_touches_the_engine(m)


def test_pipx_and_pip_installs_are_found_too(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    m.stub("pipx", 'case "$*" in "list --short") echo "krypton-app 0.1.0";; esac')
    m.run(UNINSTALL, "--yes")
    assert "pipx uninstall krypton-app" in m.calls()
    m2 = Machine(tmp_path / "pip")
    m2.stub("python3", 'case "$*" in "-m pip show krypton-app") exit 0;; esac')
    m2.run(UNINSTALL, "--yes")
    assert "python3 -m pip uninstall -y krypton-app" in m2.calls()


def test_the_extension_is_removed_from_every_editor_that_has_it(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    listing = 'case "$*" in "--list-extensions") echo "the-vibey-project.krypton";; esac'
    m.stub("code", listing)
    m.stub("cursor", listing)
    m.stub("codium", 'case "$*" in "--list-extensions") echo "some.other";; esac')
    m.run(UNINSTALL, "--yes")
    calls = m.calls()
    assert "code --uninstall-extension the-vibey-project.krypton" in calls
    assert "cursor --uninstall-extension the-vibey-project.krypton" in calls
    assert not any(c.startswith("codium --uninstall") for c in calls)


def test_the_flatpak_is_removed_and_its_data_only_with_purge(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    m.stub(
        "flatpak",
        f'case "$*" in "info --user {APP_ID}") exit 0;; "info --system {APP_ID}") exit 1;; esac',
    )
    m.run(UNINSTALL, "--yes")
    assert f"flatpak uninstall --user -y {APP_ID}" in m.calls()
    m2 = Machine(tmp_path / "purge")
    m2.stub(
        "flatpak",
        f'case "$*" in "info --user {APP_ID}") exit 0;; "info --system {APP_ID}") exit 1;; esac',
    )
    m2.run(UNINSTALL, "--yes", "--purge")
    assert f"flatpak uninstall --user -y --delete-data {APP_ID}" in m2.calls()


def test_the_tarball_files_needing_root_are_printed_as_a_sudo_command(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    for rel in ("usr/bin/krypton-desktop", f"usr/share/applications/{APP_ID}.desktop"):
        f = m.root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    done = m.run(UNINSTALL, "--yes")
    if os.geteuid() == 0:  # pragma: no cover -- CI runs unprivileged
        assert not (m.root / "usr/bin/krypton-desktop").exists()
    else:
        assert "sudo rm -f" in done.stdout and "krypton-desktop" in done.stdout
        assert (m.root / "usr/bin/krypton-desktop").exists()  # never escalated by itself


def write_app(path: Path, bundle_id: str) -> None:
    contents = path / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_text(
        f"<plist><dict>\n<key>CFBundleIdentifier</key>\n<string>{bundle_id}</string>\n</dict></plist>\n"
    )


def test_only_krypton_s_own_mac_app_is_removed(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    write_app(m.home / "Applications" / "krypton.app", APP_ID)
    m.run(UNINSTALL, "--yes")
    assert not (m.home / "Applications" / "krypton.app").exists()
    m2 = Machine(tmp_path / "other")
    write_app(m2.home / "Applications" / "krypton.app", "com.someone.else.krypton")
    done = m2.run(UNINSTALL, "--yes")
    assert (m2.home / "Applications" / "krypton.app").exists()
    assert "left alone" in done.stdout


def test_settings_are_kept_unless_purged_and_the_hub_is_told_to_forget_the_device(
    tmp_path: Path,
) -> None:
    m = Machine(tmp_path)
    settings = m.home / ".config" / "krypton"
    settings.mkdir(parents=True)
    (settings / "paired-hub.ini").write_text("[hub]\nhost=h\n[device]\nid=dev-123\nkey=secret\n")
    done = m.run(UNINSTALL, "--yes")
    assert settings.exists() and "kept:" in done.stdout
    assert "vibey hub revoke dev-123" in done.stdout
    assert "secret" not in done.stdout  # the device key is never printed
    m.run(UNINSTALL, "--yes", "--purge")
    assert not settings.exists()


def test_a_failed_removal_is_reported_and_fails_the_run(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    m.stub(
        "uv",
        'case "$*" in "tool list") echo "krypton-app v0.1.0";; "tool uninstall krypton-app") exit 1;; esac',
    )
    done = m.run(UNINSTALL, "--yes")
    assert done.returncode == 1
    assert "could not remove: krypton-app (uv tool)" in done.stdout


def test_an_unknown_option_is_refused(tmp_path: Path) -> None:
    assert Machine(tmp_path).run(UNINSTALL, "--everything").returncode == 2


# ------------------------------------------------------------------ the installer


def installer_machine(tmp: Path) -> Machine:
    m = Machine(tmp)
    m.stub("uv")
    m.stub("vibey")
    m.stub("git", 'if [ "$1" = clone ]; then mkdir -p "$3"; fi')
    return m


def test_install_is_a_reinstall_of_the_engine_and_checks_itself(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    done = m.run(INSTALL)
    assert done.returncode == 0, done.stderr
    assert m.calls() == ["uv tool install --reinstall vibey-engine", "vibey doctor"]


def test_install_with_krypton_adds_the_apps(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    m.run(INSTALL, "--with-krypton")
    assert "uv tool install --reinstall krypton-app" in m.calls()


def test_from_source_clones_once_then_updates_the_same_copy(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    copy = tmp_path / "copy"
    m.run(INSTALL, "--from-source", str(copy))
    assert any(
        c.startswith("git clone https://github.com/the-vibey-project/vibey.git") for c in m.calls()
    )
    assert "uv sync --extra dev" in m.calls()
    assert f"uv tool install --reinstall --editable {copy}" in m.calls()
    (copy / ".git").mkdir(parents=True)
    m.log.write_text("")
    m.run(INSTALL, "--from-source", str(copy))
    assert f"git -C {copy} pull --ff-only" in m.calls()
    assert not any(c.startswith("git clone") for c in m.calls())


def test_a_doctor_finding_does_not_fail_the_install(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    m.stub("vibey", "exit 3")
    assert m.run(INSTALL).returncode == 0


def test_the_installer_refuses_unknown_options_and_a_bare_from_source(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    assert m.run(INSTALL, "--everything").returncode == 2
    assert m.run(INSTALL, "--from-source").returncode == 2


def test_the_closing_line_names_no_file_a_piped_install_lacks(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    plain = m.run(INSTALL)
    assert "uninstall-krypton.sh" not in plain.stdout
    assert "krypton" not in plain.stdout  # nothing about apps that were not installed
    with_apps = m.run(INSTALL, "--with-krypton")
    assert "uv tool uninstall krypton-app" in with_apps.stdout
    assert "sh scripts/uninstall-krypton.sh" not in with_apps.stdout


# ------------------------------------------------------------------ help, piped or not


def test_help_works_when_the_script_is_piped(tmp_path: Path) -> None:
    m = installer_machine(tmp_path)
    for done in (m.piped(INSTALL, "--help"), m.run(INSTALL, "--help")):
        assert done.returncode == 0, done.stderr
        assert "--with-krypton" in done.stdout and "--from-source" in done.stdout
        assert "--full" in done.stdout
    assert m.calls() == []  # help installs nothing


# ------------------------------------------------------------------ vibey not on PATH


def test_vibey_missing_from_path_fails_with_the_line_to_add(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    tools = tmp_path / "uv-bin"
    tools.mkdir()
    m.stub("uv", f'case "$*" in "tool dir --bin") echo "{tools}";; esac')
    done = m.run(INSTALL)
    assert done.returncode != 0
    assert f'export PATH="{tools}:$PATH"' in done.stderr
    assert "vibey is installed" not in done.stdout
    assert not any(c.startswith("vibey ") for c in m.calls())


def test_vibey_in_uv_s_bin_dir_is_found_and_the_path_line_is_printed(tmp_path: Path) -> None:
    m = Machine(tmp_path)
    tools = tmp_path / "uv-bin"
    tools.mkdir()
    m.stub("uv", f'case "$*" in "tool dir --bin") echo "{tools}";; esac')
    m.stub("vibey", where=tools)
    done = m.run(INSTALL)
    assert done.returncode == 0, done.stderr
    assert "vibey doctor" in m.calls()
    assert f'export PATH="{tools}:$PATH"' in done.stdout


# ------------------------------------------------------------------ --full


FULL_STEPS = ["vibey install --postgres", "vibey migrate", "vibey connect --yes"]
OWNER_DSN = {"VIBEY_PG_MIGRATE_URL": "postgresql://owner@localhost:5432/vibey"}


def full_machine(tmp: Path) -> Machine:
    """An installer machine where PostgreSQL comes from Homebrew, so no step needs sudo."""
    m = installer_machine(tmp)
    m.stub("brew")
    m.stub("sudo", "exit 1")
    return m


def test_full_runs_vibey_s_own_setup_commands_in_order(tmp_path: Path) -> None:
    m = full_machine(tmp_path)
    done = m.run(INSTALL, "--full", env=OWNER_DSN)
    assert done.returncode == 0, done.stderr
    assert m.calls() == ["uv tool install --reinstall vibey-engine", *FULL_STEPS, "vibey doctor"]
    said = done.stdout
    positions = [said.index(cmd) for cmd in FULL_STEPS]  # each step says what it will run
    assert positions == sorted(positions)
    never_touches_the_engine(m)


def test_a_failing_full_step_stops_the_run_and_names_it(tmp_path: Path) -> None:
    m = full_machine(tmp_path)
    m.stub("vibey", 'case "$1" in migrate) exit 1;; esac')
    done = m.run(INSTALL, "--full", env=OWNER_DSN)
    assert done.returncode != 0
    assert "migrate" in done.stderr and "vibey migrate" in done.stderr
    assert "vibey connect --yes" not in m.calls() and "vibey doctor" not in m.calls()
    assert "vibey is installed" not in done.stdout


def test_full_is_safe_to_run_again(tmp_path: Path) -> None:
    m = full_machine(tmp_path)
    first = m.run(INSTALL, "--full", env=OWNER_DSN)
    m.log.write_text("")
    again = m.run(INSTALL, "--full", env=OWNER_DSN)
    assert first.returncode == 0 and again.returncode == 0, again.stderr
    assert m.calls() == ["uv tool install --reinstall vibey-engine", *FULL_STEPS, "vibey doctor"]


def test_each_full_step_has_its_own_switch(tmp_path: Path) -> None:
    for switch, command in zip(
        ("VIBEY_FULL_POSTGRES", "VIBEY_FULL_MIGRATE", "VIBEY_FULL_CONNECT"), FULL_STEPS, strict=True
    ):
        m = full_machine(tmp_path / switch)
        done = m.run(INSTALL, "--full", env={**OWNER_DSN, switch: "0"})
        assert done.returncode == 0, done.stderr
        assert command not in m.calls()
        assert [c for c in FULL_STEPS if c != command] == [c for c in m.calls() if c in FULL_STEPS]


def test_full_connects_only_the_clients_it_is_given(tmp_path: Path) -> None:
    m = full_machine(tmp_path)
    m.run(INSTALL, "--full", env={**OWNER_DSN, "VIBEY_FULL_CONNECT_CLIENTS": "codex,zed"})
    assert "vibey connect --yes --client codex --client zed" in m.calls()


def test_without_full_no_setup_step_runs(tmp_path: Path) -> None:
    m = full_machine(tmp_path)
    m.run(INSTALL, env=OWNER_DSN)
    assert not any(c in m.calls() for c in FULL_STEPS)


def test_full_without_an_owner_dsn_skips_the_migration_and_says_what_to_run(
    tmp_path: Path,
) -> None:
    m = full_machine(tmp_path)
    done = m.run(INSTALL, "--full")
    assert done.returncode == 0, done.stderr
    assert "vibey migrate" not in m.calls()
    assert "vibey connect --yes" in m.calls()
    assert "VIBEY_PG_MIGRATE_URL" in done.stdout and "vibey migrate" in done.stdout
    assert "ollama pull" in done.stdout  # the model is named as the person's step, not run


def test_full_says_before_postgres_that_sudo_may_ask_for_a_password(tmp_path: Path) -> None:
    if os.geteuid() == 0:  # pragma: no cover -- CI runs unprivileged
        return
    m = installer_machine(tmp_path)
    m.stub("apt-get")
    m.stub("sudo", "exit 1")
    terminal = tmp_path / "tty"
    terminal.write_text("")
    done = m.run(INSTALL, "--full", env={**OWNER_DSN, "VIBEY_TTY": str(terminal)})
    assert done.returncode == 0, done.stderr
    assert done.stdout.index("password") < done.stdout.index("vibey install --postgres")
    assert "vibey install --postgres" in m.calls()
    assert not any(c.startswith("apt-get") for c in m.calls())  # vibey runs it, not the script


def test_full_refuses_a_sudo_step_with_no_terminal_to_ask_on(tmp_path: Path) -> None:
    if os.geteuid() == 0:  # pragma: no cover -- CI runs unprivileged
        return
    m = installer_machine(tmp_path)
    m.stub("apt-get")
    m.stub("sudo", "exit 1")
    done = m.run(INSTALL, "--full", env={**OWNER_DSN, "VIBEY_TTY": str(tmp_path / "no-tty")})
    assert done.returncode != 0
    assert "terminal" in done.stderr and "vibey install --postgres" in done.stderr
    assert "VIBEY_FULL_POSTGRES=0" in done.stderr
    assert "vibey install --postgres" not in m.calls()
