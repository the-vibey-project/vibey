# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey explain`: the cause and the fix for a code, with no database (#1691)."""

from __future__ import annotations

from typer.testing import CliRunner

from vibey.cli.error_catalog import ErrorCatalog
from vibey.cli.explain import PAGE, ErrorExplainer
from vibey.cli.interfaces.explainer_interface import ErrorExplainerInterface
from vibey.cli.main import app

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

CATALOG = ErrorCatalog.from_toml(
    '[[error]]\nclass = "a.Base"\ntitle = "A base"\nabstract = true\ncause = "never raised"\n'
    '[[error]]\ncode = "E0001"\nclass = "a.One"\ntitle = "One"\ncause = "It broke.\\n\\nTwice."\nfix = "Mend it."\n'
    '[[error]]\ncode = "E0002"\nclass = "a.Two"\ntitle = "Two"\ncause = "c"\nfix = "f"\nretired = true\n'
)


def test_it_honours_its_interface() -> None:
    assert isinstance(ErrorExplainer(), ErrorExplainerInterface)
    assert ErrorExplainer().catalog is ErrorCatalog.shipped()


def test_a_code_prints_its_title_cause_fix_and_page() -> None:
    status, text = ErrorExplainer(CATALOG).explain("e0001")
    assert status == 0
    assert text.splitlines()[0] == "E0001  One"
    assert "Raised as a.One" in text and "  It broke.\n\n  Twice." in text
    assert "What to do\n  Mend it." in text
    assert text.endswith(f"{PAGE}#e0001")
    assert "retired" not in text


def test_a_retired_code_still_explains_and_says_so() -> None:
    status, text = ErrorExplainer(CATALOG).explain("E0002")
    assert status == 0 and "(retired: vibey no longer raises it)" in text


def test_an_unknown_code_exits_2_naming_the_nearest() -> None:
    status, text = ErrorExplainer(CATALOG).explain("E0003")
    assert status == 2 and "Did you mean" in text and "E0001" in text
    status, text = ErrorExplainer(CATALOG).explain("zzz")
    assert status == 2 and "Did you mean" not in text


def test_listing_names_every_coded_entry_and_no_abstract_base() -> None:
    assert ErrorExplainer(CATALOG).listing() == "E0001  One\nE0002  Two"


def test_the_command_explains_without_a_database(monkeypatch) -> None:
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    done = runner.invoke(app, ["explain", "E0003"])
    assert done.exit_code == 0 and "VIBEY_PG_URL" in done.output


def test_the_command_lists_and_rejects_bad_input() -> None:
    assert "E0001" in runner.invoke(app, ["explain", "--list"]).output
    nothing = runner.invoke(app, ["explain"])
    assert nothing.exit_code == 2 and "give a code" in nothing.output
    unknown = runner.invoke(app, ["explain", "E9999"])
    assert unknown.exit_code == 2 and "no error has the code" in unknown.output
