# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import pytest
from fakes import FakeOllamaProbe


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Keep the operator's own qwenloop settings out of every test.

    The CLI layers `$QWENLOOP_CONFIG` (else the user config dir) and `QWENLOOP_*`
    variables into every command, so a developer with Ollama configured would otherwise
    see the suite attach to it. Each test starts from an empty config file and no
    endpoint variables; the ones that want settings write or set their own.
    """
    config = tmp_path / "qwenloop-config.toml"
    config.write_text("", encoding="utf-8")
    monkeypatch.setenv("QWENLOOP_CONFIG", str(config))
    for variable in ("QWENLOOP_BASE_URL", "QWENLOOP_MODEL", "QWENLOOP_API_KEY"):
        monkeypatch.delenv(variable, raising=False)
    return config


@pytest.fixture(autouse=True)
def no_local_ollama(monkeypatch: pytest.MonkeyPatch) -> FakeOllamaProbe:
    """No test reaches a real Ollama: the CLI's probe answers "not running" unless a test
    says otherwise (#388). A developer's own running Ollama would otherwise change which
    backend every CLI test selects."""
    probe = FakeOllamaProbe(available=False)
    monkeypatch.setattr("qwenloop.cli.app._ollama_probe", probe)
    return probe
