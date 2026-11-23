# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey inputs` group and the `[inputs]` table are documented as the code states them
(SP-LOOPS Phase 3, Task 8).

The CLI reference is written by hand, so the help text the code prints is checked word for word
against the page: a flag or a sentence changed in one place and not the other is a reader told
something the command no longer says. The `[inputs]` keys and their defaults are read from
`RunInputsSettings` itself, so a key added or a default changed in code fails here until the
configuration reference says so too (ADR-0018: each limit a key; ADR-0104). The store keys
are `InputStoreLocation`'s fields, its `kind` written as the key `store` (ADR-0105).
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import typer.main

from vibey.cli.inputs import inputs_app
from vibey.domain.run_input import InputStoreLocation, RunInputsSettings

DOCS = Path(__file__).resolve().parents[2] / "docs" / "reference"
CLI_DOC = DOCS / "cli.md"
CONFIG_DOC = DOCS / "configuration.md"


def _section(path: Path, heading: str) -> str:
    """The text of the `## ` section whose heading starts with `heading`, up to the next one."""
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    assert len(starts) == 1, f"{path.name}: expected one section headed {heading!r}, not {starts}"
    body: list[str] = []
    for line in lines[starts[0] + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body)


def _help_texts() -> list[str]:
    """Every help string `vibey inputs --help` and its commands' `--help` print."""
    group = typer.main.get_command(inputs_app)
    commands = getattr(group, "commands", {})  # a group: typer's own Group subclass
    assert set(commands) == {"add", "list"}, commands
    texts = [str(group.help)]
    for command in commands.values():
        texts.append(str(command.help))
        texts.extend(str(p.help) for p in command.params if getattr(p, "help", None))
    return texts


def test_the_cli_reference_has_the_inputs_group() -> None:
    section = _section(CLI_DOC, "## `vibey inputs")
    assert "vibey inputs add" in section
    assert "vibey inputs list" in section


def test_the_cli_reference_carries_the_codes_own_help_text() -> None:
    section = " ".join(_section(CLI_DOC, "## `vibey inputs").split())
    missing = [text for text in _help_texts() if " ".join(text.split()) not in section]
    assert not missing, f"docs/reference/cli.md's `vibey inputs` section lacks {missing}"


def _inputs_rows() -> dict[str, str]:
    """`[inputs]`'s table in the configuration reference: each key and its default cell."""
    rows: dict[str, str] = {}
    for line in _section(CONFIG_DOC, "## `[inputs]`").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0].startswith("`") and cells[0].endswith("`"):
            rows[cells[0].strip("`")] = cells[1]
    return rows


def _keys_and_defaults() -> dict[str, object]:
    """Every `[inputs]` key and its default, from the code: the limits, then the store keys."""
    limits = RunInputsSettings()
    store = InputStoreLocation()
    keys: dict[str, object] = {
        f.name: getattr(limits, f.name) for f in fields(RunInputsSettings) if f.name != "store"
    }
    for f in fields(InputStoreLocation):
        keys["store" if f.name == "kind" else f.name] = getattr(store, f.name)
    return keys


def test_the_configuration_reference_names_every_inputs_key() -> None:
    assert set(_inputs_rows()) == set(_keys_and_defaults())


def test_the_configuration_reference_states_each_default() -> None:
    rows = _inputs_rows()
    wrong = {
        key: rows.get(key)
        for key, default in _keys_and_defaults().items()
        if ("unset" if default is None else f"`{default}`") not in rows.get(key, "")
    }
    assert not wrong, f"docs/reference/configuration.md's [inputs] defaults differ: {wrong}"


def test_the_cli_reference_gives_exit_69_in_both_exit_tables() -> None:
    """Phase 3c Task 8 (fix round 1, review I6): `vibey inputs` exits 69 when the store does not
    answer, and both the global table and the command's own list say so."""
    from vibey.cli.inputs import EXIT_UNAVAILABLE

    assert EXIT_UNAVAILABLE == 69
    exits = _section(CLI_DOC, "## Exit codes and errors")
    assert "| `69` |" in exits and "vibey inputs" in exits
    inputs = " ".join(_section(CLI_DOC, "## `vibey inputs").split())
    assert "`69` the store did not answer" in inputs


def test_the_cli_reference_describes_the_run_inputs_doctor_line() -> None:
    from vibey.cli.run_inputs_doctor import NAME

    text = CLI_DOC.read_text(encoding="utf-8")
    assert f"The `{NAME}` line" in text
    for phrase in ("reachable; credentials from", "is not set", "made on the first add"):
        assert phrase in " ".join(text.split()), phrase


def test_the_cli_reference_no_longer_says_a_handed_off_run_gets_no_section() -> None:
    inputs = " ".join(_section(CLI_DOC, "## `vibey inputs").split())
    assert "a known gap, ADR-0104" not in inputs
    assert "Inputs stay on this machine" not in inputs
    assert "is given exactly the inputs the run it replaces was given" in inputs
    assert 'store = "seaweedfs"' in inputs
