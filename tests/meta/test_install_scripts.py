# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The install and uninstall scripts name exactly what the source builds and ships.

`scripts/uninstall-krypton.sh` hard-codes identifiers so it can run on a machine with no
repository: the app id, the editor extension id, the Python package, the binary and the four
files the Ubuntu tarball installs. Each is checked here against the place it comes from, so a
rename in the source fails CI instead of leaving an uninstaller that silently misses its target.
And neither script may ever uninstall vibey-engine.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
UNINSTALL = (REPO / "scripts" / "uninstall-krypton.sh").read_text(encoding="utf-8")
INSTALL = (REPO / "scripts" / "install.sh").read_text(encoding="utf-8")


def default(name: str, text: str = UNINSTALL) -> str:
    found = re.search(rf'^{name}="\$\{{[A-Z_]+:-([^}}]+)\}}"', text, re.MULTILINE)
    assert found, name
    return found[1]


def test_the_app_id_is_the_flatpak_and_desktop_id() -> None:
    manifest = (REPO / "clients/desktop/packaging/flatpak").glob("*.yml")
    ids = {re.search(r"^app-id:\s*(\S+)", p.read_text(), re.MULTILINE)[1] for p in manifest}  # type: ignore[index]
    assert ids == {default("APP_ID")}
    data = REPO / "clients/desktop/data"
    assert (data / f"{default('APP_ID')}.desktop.in").is_file()
    assert (data / f"{default('APP_ID')}.metainfo.xml.in").is_file()


def test_the_extension_and_package_names_are_the_shipped_ones() -> None:
    vscode = json.loads((REPO / "clients/vscode/package.json").read_text())
    assert default("EXTENSION_ID") == f"{vscode['publisher']}.{vscode['name']}"
    apps = tomllib.loads((REPO / "clients/krypton-app/pyproject.toml").read_text())
    assert default("PYTHON_PACKAGE") == apps["project"]["name"]
    assert default("APPS", INSTALL) == apps["project"]["name"]
    engine = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert default("ENGINE", INSTALL) == engine["project"]["name"]


def test_the_tarball_binary_is_the_one_the_release_checks() -> None:
    release = (REPO / ".github/workflows/release-binaries.yml").read_text()
    assert 'test -x "$stage/usr/bin/krypton-desktop"' in release
    assert "/usr/bin/krypton-desktop" in UNINSTALL


def test_nothing_ever_uninstalls_vibey_engine() -> None:
    for text in (UNINSTALL, INSTALL):
        assert not re.search(r"uninstall[^\n]*vibey-engine", text)
        assert not re.search(r"uninstall[^\n]*\$ENGINE", text)


FULL_STEP = re.compile(
    r'^\s*(?:capture_)?step (\S+) "[^"]*" vibey (\S+)((?: --?[a-z][a-z-]*)*)', re.MULTILINE
)


def test_every_full_step_is_a_command_and_option_vibey_ships() -> None:
    """`--full` runs vibey's own commands, never a reimplementation, so each one it names
    must exist with each option it passes: a renamed command or flag fails here, not on a
    person's fresh machine."""
    import typer.main

    from vibey.cli.main import app

    cli = typer.main.get_command(app)
    steps = FULL_STEP.findall(INSTALL)
    assert [name for name, _, _ in steps] == ["postgres", "database", "migrate", "model", "connect"]
    for _, command, options in steps:
        shipped = cli.commands[command]  # type: ignore[attr-defined]
        known = {opt for param in shipped.params for opt in param.opts}
        assert set(options.split()) <= known, (command, options)
    connect = cli.commands["connect"]  # type: ignore[attr-defined]
    assert "--client" in {opt for param in connect.params for opt in param.opts}
    models = cli.commands["models"]  # type: ignore[attr-defined]
    assert "vibey models --default-tag" in INSTALL
    assert "--default-tag" in {opt for param in models.params for opt in param.opts}


def test_the_line_full_reads_is_the_line_vibey_install_database_prints() -> None:
    """The script keeps the `export VIBEY_PG_URL=...` line `vibey install --database` prints;
    that command printing it differently would leave the doctor and the closing lines without it."""
    from vibey.cli import local_install

    printed = (REPO / "src/vibey/cli/local_install.py").read_text(encoding="utf-8")
    assert 'f"  export VIBEY_PG_URL={names.app_dsn}"' in printed, local_install.__file__
    assert "s/^ *\\(export VIBEY_PG_URL=[^ ]*\\)$/\\1/p" in INSTALL


def test_the_engine_is_installed_with_the_extras_the_hub_needs() -> None:
    """`vibey serve`, `vibey hub` and the hub `vibey mcp` starts import FastAPI, which is only
    in vibey-engine's `hub` extra; krypton-app asks for the same extra."""
    engine = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert "hub" in engine["project"]["optional-dependencies"]
    assert 'EXTRAS="${VIBEY_ENGINE_EXTRAS-hub}"' in INSTALL
    apps = tomllib.loads((REPO / "clients/krypton-app/pyproject.toml").read_text())
    assert f"{engine['project']['name']}[hub]" in apps["project"]["dependencies"]


def test_full_reads_the_owner_dsn_vibey_migrate_reads() -> None:
    from vibey.infrastructure.db.ledger_guard import DatabaseEndpoints

    assert f"${{{DatabaseEndpoints.MIGRATE_ENV}:-}}" in INSTALL
