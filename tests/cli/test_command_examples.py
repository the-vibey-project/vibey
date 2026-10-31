# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Six commands end their `--help` with worked examples a test still resolves (#1687).

An example is resolved against the real command tree with each command's own parser, without
calling its callback: the command exists, its flags exist, its arguments satisfy it. Nothing
runs and no database is needed.
"""

from __future__ import annotations

import typer
from typer.testing import CliRunner

from vibey.cli.command_examples import EXAMPLES, REQUIRED, CommandExamples, Example
from vibey.cli.help_layout import EPILOG
from vibey.cli.interfaces.command_examples_interface import CommandExamplesInterface
from vibey.cli.main import app

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1", "COLUMNS": "120", "NO_COLOR": "1"})


def _help(*args: str) -> str:
    done = runner.invoke(app, [*args, "--help"])
    assert done.exit_code == 0, done.output
    return done.output


def test_every_shipped_example_resolves_against_the_real_command_tree() -> None:
    assert CommandExamples().problems(app) == []
    assert isinstance(CommandExamples(), CommandExamplesInterface)


def test_the_six_commands_the_issue_names_each_have_one_or_two_examples() -> None:
    assert set(REQUIRED) == {"new", "answer", "gates", "projects", "doctor", "watch"}
    for command in REQUIRED:
        count = sum(1 for example in EXAMPLES if example.command == command)
        assert 1 <= count <= 2, command


def test_each_commands_help_ends_with_its_examples() -> None:
    for command in REQUIRED:
        text = _help(command).rstrip()
        examples = [e for e in EXAMPLES if e.command == command]
        assert "Examples:" in text, command
        for example in examples:
            assert example.line in text and example.note in text, example.line
        # Nothing follows the last example's note: the examples end the help.
        assert text.endswith(examples[-1].note), command


def test_vibey_new_names_and_describes_its_argument() -> None:
    text = _help("new")
    assert "NAME" in text and "{name}" not in text
    assert "A name for the project" in text
    answer = _help("answer")
    assert "GATE_ID" in answer and "{gate_id}" not in answer
    assert "the id `vibey gates` prints" in answer


def test_rare_options_sit_under_named_panels_after_the_common_ones() -> None:
    new = _help("new")
    common = new.index("--intake")
    for flag, panel in (
        ("--max-cycle-dollars", "Spending and turn limits"),
        ("--skills-context-mode", "Skills"),
        ("--accept-spec-json", "Advanced"),
        ("--ignore-sabbath", "Advanced"),
    ):
        assert new.index(panel) < new.index(flag), flag
        assert common < new.index(panel), panel
    doctor = _help("doctor")
    for flag, panel in (
        ("--record", "Recording"),
        ("--cluster", "In-cluster preflight"),
        ("--sovereign-fit", "Capacity probe"),
    ):
        assert doctor.index("--conformance") < doctor.index(panel) < doctor.index(flag), flag
    assert _help("answer").index("--defaults") < _help("answer").index("Advanced")
    assert _help("gates").index("Reminders") < _help("gates").index("--remind")


def test_no_option_was_removed_by_regrouping() -> None:
    new = _help("new")
    for flag in ("--repo", "--intake", "--max-cycles", "--json", "--design-default-scope"):
        assert flag in new, flag


def test_the_root_help_keeps_its_own_examples() -> None:
    root = _help()
    assert EPILOG.splitlines()[-1] in root
    assert "vibey new my-app   start a project" in root
    assert "Examples:" in root and "Follow the work live." not in root


def _small_app() -> typer.Typer:
    small = typer.Typer(name="demo")

    @small.command("greet")
    def greet(who: str, loud: bool = False) -> None: ...

    @small.command()
    def other_one() -> None: ...

    return small


def test_apply_sets_only_the_named_commands_epilog() -> None:
    small = _small_app()
    root_before = small.info.epilog
    examples = CommandExamples([Example("greet", "vibey greet bob", "Say hi.")], ["greet"])
    examples.apply(small)
    greet, other = small.registered_commands
    assert greet.epilog is not None and "vibey greet bob" in greet.epilog
    assert other.epilog is None and small.info.epilog is root_before


def test_apply_finds_a_command_by_its_callback_name_when_none_was_declared() -> None:
    small = _small_app()
    CommandExamples([Example("other-one", "vibey other-one", "Run it.")], []).apply(small)
    assert small.registered_commands[1].epilog is not None


def test_a_bad_example_is_named_with_the_reason() -> None:
    small = _small_app()
    bad = CommandExamples(
        [
            Example("greet", "vibey greet bob --loud", "Fine."),
            Example("greet", "vibey greet bob --shout", "A flag that does not exist."),
            Example("greet", "vibey greet", "A missing argument."),
            Example("greet", "vibey other-one", "Filed under the wrong command."),
            Example("ghost", "vibey ghost", "A command that is not there."),
            Example("greet", "greet bob", "Does not start with vibey."),
            Example("greet", "vibey", "Names no command."),
        ],
        ["greet", "absent"],
    )
    found = "\n".join(bad.problems(small))
    assert "absent: no example" in found
    assert "greet: more than 2 examples" in found
    assert "--shout" in found and "No such option" in found
    assert "Missing" in found
    assert "filed under 'greet' but runs 'other-one'" in found
    assert "there is no command 'ghost'" in found
    assert found.count("an example starts with 'vibey COMMAND'") == 2
    assert "vibey greet bob --loud" not in found


def test_a_clean_table_reports_nothing() -> None:
    clean = CommandExamples([Example("greet", "vibey greet bob", "Say hi.")], ["greet"])
    assert clean.problems(_small_app()) == []
