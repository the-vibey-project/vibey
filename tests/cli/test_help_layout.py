# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey --help` command list: grouped by what a person came to do (#1665).

A newcomer met thirty-four commands in registration order, each printing a paragraph. These
tests hold the replacement to what makes it worth having: every command has a place in it,
every summary fits on a line, no example names a command that does not exist, and a command
added tomorrow without a place fails here instead of landing at the bottom unexplained.
"""

from __future__ import annotations

import re
from pathlib import Path

import click
import pytest
import typer
from typer.testing import CliRunner

from vibey.cli.help_layout import EPILOG, PANELS, Entry, HelpLayout, Panel
from vibey.cli.interfaces.help_layout_interface import HelpLayoutInterface
from vibey.cli.main import app

REPO = Path(__file__).resolve().parents[2]
runner = CliRunner()
WIDE = {"COLUMNS": "120", "NO_COLOR": "1"}


def _help(*args: str) -> str:
    """The help as a person reads it, without the styling codes typer adds when the terminal
    is forced (GitHub Actions forces it, whatever `NO_COLOR` says). Those codes split an option
    name such as `--json` into pieces, so a search of the raw bytes fails there and passes on a
    laptop; develop went red on that (#1724)."""
    return click.unstyle(runner.invoke(app, list(args), env=WIDE).output)


def _registered() -> set[str]:
    layout = HelpLayout()
    return set(layout._command_names(app))  # noqa: SLF001 - the names the app registers


def test_the_layout_satisfies_its_interface() -> None:
    assert isinstance(HelpLayout(), HelpLayoutInterface)


def test_every_command_the_root_app_registers_has_a_place_in_the_list() -> None:
    """The guard: a new command with no entry in `PANELS` is named here, not left under an
    anonymous heading for a confused user to find."""
    assert HelpLayout().unplaced(app) == []


def test_no_entry_names_a_command_that_is_not_registered() -> None:
    placed = {entry.name for panel in PANELS for entry in panel.entries}
    assert placed - _registered() == set()


def test_a_name_is_placed_once() -> None:
    names = [entry.name for panel in PANELS for entry in panel.entries]
    assert len(names) == len(set(names))


@pytest.mark.parametrize(
    "entry", [e for panel in PANELS for e in panel.entries], ids=lambda e: e.name
)
def test_a_summary_is_one_short_line_with_no_full_stop(entry: Entry) -> None:
    assert "\n" not in entry.summary and entry.summary == entry.summary.strip()
    assert len(entry.summary) <= 60, entry.summary
    assert not entry.summary.endswith("."), entry.summary


def test_the_list_shows_every_panel_in_reading_order_with_each_summary() -> None:
    assert runner.invoke(app, ["--help"], env=WIDE).exit_code == 0
    out = _help("--help")
    positions = [out.index(panel.title) for panel in PANELS]
    assert positions == sorted(positions), "the panels must print in the order PANELS lists them"
    for panel in PANELS:
        for entry in panel.entries:
            assert entry.summary in out, entry.name


def test_a_commands_own_help_keeps_its_full_text() -> None:
    """Only the list is shortened: `vibey abandon --help` still says what it does in full."""
    out = " ".join(_help("abandon", "--help").split())
    assert "its jobs are cancelled, its gates withdrawn" in out


def test_the_examples_name_only_commands_that_exist() -> None:
    examples = re.findall(r"^  vibey (\S+)", EPILOG, re.MULTILINE)
    assert examples, "the footer lost its examples"
    assert set(examples) <= _registered()


def test_the_help_ends_with_the_examples() -> None:
    out = _help("--help")
    assert "Examples:" in out and "vibey new my-app" in out


@pytest.mark.parametrize(
    "command", ["projects", "gates", "status", "loops", "models", "engines", "cost", "doctor"]
)
def test_a_command_the_footer_says_takes_json_does_take_it(command: str) -> None:
    claim = re.search(r"([a-z, ]+) take --json", EPILOG)
    assert claim is not None and command in claim.group(1)
    assert "--json" in _help(command, "--help")


def _small_app() -> typer.Typer:
    small = typer.Typer(name="demo")
    sub = typer.Typer(name="tools")

    @small.command("alpha")
    def alpha() -> None: ...

    @small.command()
    def beta_two() -> None: ...

    @small.command("stray")
    def stray() -> None: ...

    @sub.command("noop")
    def noop() -> None: ...

    small.add_typer(sub)
    small.add_typer(typer.Typer(name="named"), name="named")
    return small


LAYOUT = HelpLayout(
    (
        Panel("First", (Entry("beta-two", "Second by name"), Entry("tools", "A sub-app"))),
        Panel("Second", (Entry("alpha", "Placed later"), Entry("named", "An explicit name"))),
    ),
    epilog="demo epilog",
)


def test_names_come_from_the_callback_the_sub_app_or_the_explicit_name() -> None:
    assert LAYOUT._command_names(_small_app()) == [  # noqa: SLF001
        "alpha",
        "beta-two",
        "stray",
        "tools",
        "named",
    ]


def test_a_name_with_no_place_is_reported_and_left_where_it_was() -> None:
    small = _small_app()
    assert LAYOUT.unplaced(small) == ["stray"]
    stray = next(c for c in small.registered_commands if c.name == "stray")
    before = (stray.rich_help_panel, stray.short_help)
    LAYOUT.apply(small)
    assert (stray.rich_help_panel, stray.short_help) == before


def test_applying_orders_places_summarises_and_sets_the_epilog() -> None:
    small = _small_app()
    LAYOUT.apply(small)
    assert [c.name or c.callback.__name__ for c in small.registered_commands] == [  # type: ignore[union-attr]
        "beta_two",
        "alpha",
        "stray",
    ]
    assert [g.name or g.typer_instance.info.name for g in small.registered_groups] == [
        "tools",
        "named",
    ]
    alpha = next(c for c in small.registered_commands if c.name == "alpha")
    assert (alpha.rich_help_panel, alpha.short_help) == ("Second", "Placed later")
    tools = small.registered_groups[0]
    assert (tools.rich_help_panel, tools.short_help) == ("First", "A sub-app")
    assert small.info.epilog == "demo epilog"


def test_the_cli_reference_lists_the_same_panels_in_the_same_order() -> None:
    """`docs/reference/cli.md` is written by hand; this holds its panel list to `PANELS`."""
    page = (REPO / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    listed = re.findall(r"^- \*\*([^*]+):\*\* (.+)$", page, re.MULTILINE)
    expected = [(panel.title, [entry.name for entry in panel.entries]) for panel in PANELS]
    documented = [
        (title, [name.rstrip("…") for name in re.findall(r"`([a-z]+)`…?", names)])
        for title, names in listed
        if title in {panel.title for panel in PANELS}
    ]
    assert documented == expected
