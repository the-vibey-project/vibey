# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json

import pytest
from typer.testing import CliRunner

from vibey.cli.interfaces.models_interface import ModelsCommandInterface, ModelsPresenterInterface
from vibey.cli.main import app
from vibey.cli.models import MODELS, ModelsCommand, ModelsPresenter
from vibey.infrastructure.ollama_models import InstalledModel, OllamaUnavailable

runner = CliRunner()


class _Ollama:
    def __init__(self, models: tuple[InstalledModel, ...] = (), *, down: bool = False) -> None:
        self._models, self._down = models, down

    def installed(self) -> tuple[InstalledModel, ...]:
        if self._down:
            raise OllamaUnavailable("no Ollama answered at http://x: refused")
        return self._models

    def capabilities(self, tag: str) -> frozenset[str] | None:
        return None


MODELS_HERE = (
    InstalledModel(
        "qwen2.5-coder:14b", 9_000_000_000, frozenset({"completion", "tools", "insert"})
    ),
    InstalledModel("deepseek-coder:1.3b", 776_000_000, frozenset({"completion"})),
    InstalledModel("mystery:1b", 1_000_000_000, None),
    InstalledModel("empty:1b", 1_000_000_000, frozenset()),
)


def _command(client: _Ollama, environ: dict[str, str] | None = None) -> ModelsCommand:
    return ModelsCommand(client_for=lambda url: client, environ=environ or {})


def test_the_command_and_presenter_satisfy_their_interfaces() -> None:
    assert isinstance(MODELS, ModelsCommandInterface)
    assert isinstance(ModelsPresenter(), ModelsPresenterInterface)


def test_every_family_is_listed_with_the_command_that_fetches_it() -> None:
    report = _command(_Ollama()).report()
    assert [f.key for f in report.families][0] == "qwen-coder"
    assert len(report.families) == 8
    codestral = next(f for f in report.families if f.key == "codestral")
    assert codestral.pull == "ollama pull codestral:22b"


def test_installed_models_say_their_family_and_what_ollama_reports() -> None:
    report = _command(_Ollama(MODELS_HERE)).report()
    by_tag = {m.tag: m for m in report.installed}
    assert by_tag["qwen2.5-coder:14b"].family == "Qwen Coder"
    assert by_tag["qwen2.5-coder:14b"].capabilities == ("completion", "insert", "tools")
    assert by_tag["deepseek-coder:1.3b"].jobs == (
        "DESIGN and DECOMPOSE (JSON mode needs no tool-calling)",
    )
    assert by_tag["mystery:1b"].family is None and by_tag["mystery:1b"].capabilities is None
    assert by_tag["mystery:1b"].jobs == ()
    assert by_tag["empty:1b"].capabilities == () and by_tag["empty:1b"].jobs == ()


def test_the_ollama_address_is_the_one_operator_setting() -> None:
    assert _command(_Ollama()).report().ollama_url == "http://127.0.0.1:11434"
    custom = _command(_Ollama(), {"VIBEY_OLLAMA_URL": "http://gpu:11434"})
    assert custom.report().ollama_url == "http://gpu:11434"


def test_no_ollama_is_reported_and_the_families_still_print() -> None:
    report = _command(_Ollama(down=True)).report()
    assert report.installed == () and "refused" in str(report.problem)
    lines = ModelsPresenter().lines(report)
    assert any("Codestral" in line for line in lines)
    assert any("refused" in line for line in lines)


def test_the_human_reading_names_unknown_and_empty_apart() -> None:
    text = "\n".join(ModelsPresenter().lines(_command(_Ollama(MODELS_HERE)).report()))
    assert "this Ollama does not say what it can do: unknown" in text
    assert "Ollama reports: nothing" in text
    assert "outside the families above" in text
    assert "can be tried for: fill-in-the-middle completion" in text


def test_an_ollama_with_no_models_says_so() -> None:
    text = "\n".join(ModelsPresenter().lines(_command(_Ollama()).report()))
    assert "no models yet" in text


def test_the_json_carries_the_same_facts() -> None:
    document = json.loads(ModelsPresenter().json(_command(_Ollama(MODELS_HERE)).report()))
    assert document["problem"] is None
    assert document["families"][0]["pull"] == "ollama pull qwen2.5-coder:14b"
    tags = {m["tag"]: m for m in document["installed"]}
    assert tags["mystery:1b"]["capabilities"] is None
    assert tags["deepseek-coder:1.3b"]["capabilities"] == ["completion"]


def test_vibey_models_runs_for_a_person_and_for_a_program(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEY_OLLAMA_URL", "http://127.0.0.1:1")
    plain = runner.invoke(app, ["models"])
    assert plain.exit_code == 0 and "Qwen Coder" in plain.stdout
    machine = runner.invoke(app, ["models", "--json"])
    assert machine.exit_code == 0
    assert json.loads(machine.stdout)["problem"] is not None
