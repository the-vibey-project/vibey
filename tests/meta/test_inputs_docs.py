# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey inputs` group and the `[inputs]` table are documented as the code states them
(SP-LOOPS Phase 3, Task 8).

The CLI reference is written by hand, so the help text the code prints is checked word for word
against the page: a flag or a sentence changed in one place and not the other is a reader told
something the command no longer says. The `[inputs]` keys and their defaults are read from
`RunInputsSettings` itself, so a key added or a default changed in code fails here until the
configuration reference says so too (ADR-0018: each limit a key; ADR-0104).
"""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import typer.main

from vibey.cli.inputs import inputs_app
from vibey.domain.run_input import RunInputsSettings

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


def test_the_configuration_reference_names_every_inputs_key() -> None:
    assert set(_inputs_rows()) == {f.name for f in fields(RunInputsSettings)}


def test_the_configuration_reference_states_each_default() -> None:
    defaults = RunInputsSettings()
    rows = _inputs_rows()
    wrong = {
        f.name: rows.get(f.name)
        for f in fields(RunInputsSettings)
        if f"`{getattr(defaults, f.name)}`" not in rows.get(f.name, "")
    }
    assert not wrong, f"docs/reference/configuration.md's [inputs] defaults differ: {wrong}"
