# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[web]` read from the person's own `vibey.toml`, narrowed by a project's and never widened
(ADR-0102, SP-ACP Task 9b).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from pathlib import Path

import pytest

from vibey.domain.config import ConfigError
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.web.interfaces.web_settings_loader_interface import (
    WebToolSettingsLoaderInterface,
)
from vibey.infrastructure.web.web_settings_loader import WEB_SETTINGS, WebToolSettingsLoader


def _file(folder: Path, name: str, text: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def test_the_loader_meets_its_seam() -> None:
    assert isinstance(WEB_SETTINGS, WebToolSettingsLoaderInterface)


def test_no_file_and_no_table_are_the_defaults(tmp_path: Path) -> None:
    assert WEB_SETTINGS.load(tmp_path / "missing.toml") == WebToolSettings()
    plain = _file(tmp_path, "vibey.toml", "[hub]\nport = 8765\n")
    assert WEB_SETTINGS.load(plain) == WebToolSettings()


def test_every_key_is_read(tmp_path: Path) -> None:
    path = _file(
        tmp_path,
        "vibey.toml",
        """
[web]
searches_per_hour = 10
fetches_per_hour = 4
allow_hosts = ["python.org", "docs.rs"]
deny_hosts = ["paste.example"]
max_bytes = 200000
max_chars = 5000
timeout_seconds = 7.5
max_redirects = 1
content_types = ["text/html", "text/plain"]
""",
    )
    assert WEB_SETTINGS.load(path) == WebToolSettings(
        searches_per_hour=10,
        fetches_per_hour=4,
        allow_hosts=("python.org", "docs.rs"),
        deny_hosts=("paste.example",),
        max_bytes=200_000,
        max_chars=5_000,
        timeout_seconds=7.5,
        max_redirects=1,
        content_types=("text/html", "text/plain"),
    )


@pytest.mark.parametrize(
    ("text", "needle"),
    [
        ("[web]\nsearches = 1\n", "searches is not a known key"),
        ("[web]\nsearches = 1\nfetches = 2\n", "fetches, searches are not known keys"),
        ("web = 3\n", "[web] must be a table"),
        ("[web]\nsearches_per_hour = '10'\n", "searches_per_hour"),
        ("[web]\nallow_hosts = 'python.org'\n", "allow_hosts must be a list of host names"),
        ("[web]\ndeny_hosts = [1]\n", "deny_hosts must be a list of host names"),
        ("[web]\ncontent_types = 'text/html'\n", "content_types must be a list"),
        ("[web]\ntimeout_seconds = 'soon'\n", "timeout_seconds"),
        ("[web]\nallow_hosts = ['*.example.com']\n", "not a host name"),
        ("[web\n", "is not valid TOML"),
    ],
)
def test_a_wrong_value_is_refused_naming_the_file_and_the_key(
    tmp_path: Path, text: str, needle: str
) -> None:
    path = _file(tmp_path, "vibey.toml", text)
    with pytest.raises(ConfigError) as raised:
        WEB_SETTINGS.load(path)
    assert needle in str(raised.value)


def test_an_unreadable_file_is_refused(tmp_path: Path) -> None:
    folder = tmp_path / "a-folder.toml"
    folder.mkdir()
    with pytest.raises(ConfigError, match="cannot be read"):
        WEB_SETTINGS.load(folder)


def test_a_project_may_only_narrow_what_the_person_set(tmp_path: Path) -> None:
    user = _file(
        tmp_path / "me",
        "vibey.toml",
        "[web]\nsearches_per_hour = 20\ndeny_hosts = ['tracker.example']\n",
    )
    project = _file(
        tmp_path / "repo",
        "vibey.toml",
        "[web]\nsearches_per_hour = 5000\nfetches_per_hour = 2\n"
        "deny_hosts = []\nallow_hosts = ['example.com']\n",
    )
    merged = WEB_SETTINGS.load_trusted(user, project)
    assert merged.searches_per_hour == 20  # the project cannot raise it
    assert merged.fetches_per_hour == 2  # but it can lower one
    assert merged.deny_hosts == ("tracker.example",)  # nor clear a denied host
    assert merged.allow_hosts == ("example.com",)  # and it can narrow to its own list


def test_with_no_project_file_or_the_same_file_the_person_s_settings_stand(tmp_path: Path) -> None:
    user = _file(tmp_path / "me", "vibey.toml", "[web]\nfetches_per_hour = 9\n")
    assert WEB_SETTINGS.load_trusted(user, tmp_path / "none" / "vibey.toml").fetches_per_hour == 9
    assert WEB_SETTINGS.load_trusted(user, user).fetches_per_hour == 9


def test_a_project_file_that_cannot_be_read_is_refused_rather_than_ignored(tmp_path: Path) -> None:
    user = _file(tmp_path / "me", "vibey.toml", "")
    project = _file(tmp_path / "repo", "vibey.toml", "[web]\nmax_bytes = 'all'\n")
    with pytest.raises(ConfigError, match="max_bytes"):
        WebToolSettingsLoader().load_trusted(user, project)
