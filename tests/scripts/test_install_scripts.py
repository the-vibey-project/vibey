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

    def stub(self, name: str, script: str = "exit 0") -> None:
        path = self.bin / name
        path.write_text(f'#!/bin/sh\necho "{name} $*" >> "{self.log}"\n{script}\n')
        path.chmod(0o755)

    def run(self, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "KRYPTON_ROOT": str(self.root),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
        }
        return subprocess.run(
            ["sh", str(script), *args], env=env, capture_output=True, text=True, check=False
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
