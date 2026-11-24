# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Search finds the SearXNG vibey provisioned from the PERSON's own record (ADR-0102): when their
environment names neither `VIBEY_SEARXNG_URL` nor `VIBEY_SEARXNG_INSTANCE`, the URL and the
identity marker come from `<their configuration folder>/searxng/provision.json`, never from a
project; their environment still wins."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibey.domain.searxng import SEARXNG_IMAGE, SearxngProvision
from vibey.infrastructure.searxng.searxng_files import SearxngFiles
from vibey.infrastructure.web.search import DEFAULT_SEARXNG_URL, WebSearchSettings

IMAGE = SEARXNG_IMAGE
_REAL_PERSONAL = SearxngFiles.__dict__["personal"]
"""Read at import, before the suite's hermetic fixture stands in for it."""
MINE = SearxngProvision(IMAGE, 28199, "vibey-" + "1" * 32, "dev.vibey.searxng", "/usr/bin/podman")


def _person(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SearxngFiles:
    files = SearxngFiles(tmp_path / "person" / "searxng")
    monkeypatch.setattr(SearxngFiles, "personal", classmethod(lambda cls, folder=None: files))
    return files


def _provision(files: SearxngFiles, provision: SearxngProvision = MINE) -> None:
    files.folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    files.folder.chmod(0o700)
    (files.folder / "settings.yml").write_text("x", "utf-8")
    (files.folder / "settings.yml").chmod(0o600)
    record = files.folder / "provision.json"
    record.touch(mode=0o600)
    record.write_text(
        json.dumps(
            {
                "image": provision.image,
                "port": provision.port,
                "marker": provision.marker,
                "label": provision.label,
                "runtime": provision.runtime,
            }
        ),
        "utf-8",
    )


def test_with_nothing_provisioned_search_asks_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _person(tmp_path, monkeypatch)
    settings = WebSearchSettings.from_environment({})
    assert (settings.searxng_url, settings.searxng_instance) == (DEFAULT_SEARXNG_URL, None)
    assert not settings.provisioned


def test_the_persons_record_gives_the_url_and_the_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _provision(_person(tmp_path, monkeypatch))
    settings = WebSearchSettings.from_environment({})
    assert settings.searxng_url == "http://127.0.0.1:28199"
    assert settings.searxng_instance == MINE.marker
    assert settings.provisioned
    assert settings.searxng_url_env is None


@pytest.mark.parametrize(
    ("environ", "url", "instance"),
    [
        ({"VIBEY_SEARXNG_URL": "http://127.0.0.1:9999"}, "http://127.0.0.1:9999", None),
        ({"WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:9999"}, "http://127.0.0.1:9999", None),
        ({"VIBEY_SEARXNG_INSTANCE": "their-own"}, DEFAULT_SEARXNG_URL, "their-own"),
        ({"WEBSEARCH_SEARXNG_INSTANCE": "their-own"}, DEFAULT_SEARXNG_URL, "their-own"),
    ],
)
def test_the_persons_environment_wins_over_the_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    environ: dict[str, str],
    url: str,
    instance: str | None,
) -> None:
    _provision(_person(tmp_path, monkeypatch))
    settings = WebSearchSettings.from_environment(environ)
    assert not settings.provisioned
    assert (settings.searxng_url, settings.searxng_instance) == (url, instance)


def test_a_record_vibey_would_not_have_written_is_ignored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _person(tmp_path, monkeypatch)
    files.folder.mkdir(parents=True)
    (files.folder / "provision.json").write_text(
        json.dumps({"image": IMAGE, "port": "80@evil.example", "marker": "x"}), "utf-8"
    )
    settings = WebSearchSettings.from_environment({})
    assert (settings.searxng_url, settings.provisioned) == (DEFAULT_SEARXNG_URL, False)


def test_a_hostile_project_cannot_stand_in_for_the_persons_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = _person(tmp_path, monkeypatch)
    _provision(files)
    project = tmp_path / "project"
    evil = SearxngProvision(IMAGE, 8080, "vibey-" + "e" * 32, "evil", "/usr/bin/podman")
    _provision(SearxngFiles(project / "searxng"), evil)
    (project / "vibey.toml").write_text(
        '[search]\nsearxng_url = "http://evil.example"\n[acp]\nsearxng = "ask"\n', "utf-8"
    )
    monkeypatch.chdir(project)
    settings = WebSearchSettings.from_environment({})
    assert settings.searxng_url == "http://127.0.0.1:28199"
    assert settings.searxng_instance == MINE.marker


def test_the_default_reader_is_the_persons_own_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Put back what the suite's hermetic fixture stands in for, and look where it looks."""
    monkeypatch.setattr(SearxngFiles, "personal", _REAL_PERSONAL)
    monkeypatch.setattr(
        "vibey.infrastructure.user_config_folder.user_config_path", lambda name: tmp_path / name
    )
    _provision(SearxngFiles(tmp_path / "vibey" / "searxng"))
    assert WebSearchSettings.from_environment({}).searxng_instance == MINE.marker


def test_a_fifo_for_a_record_never_hangs_search(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    files = _person(tmp_path, monkeypatch)
    files.folder.mkdir(parents=True, mode=0o700)
    os.mkfifo(files.folder / "provision.json", 0o600)
    settings = WebSearchSettings.from_environment({})
    assert (settings.searxng_url, settings.provisioned) == (DEFAULT_SEARXNG_URL, False)
