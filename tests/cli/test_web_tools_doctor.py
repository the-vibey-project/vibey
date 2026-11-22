# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s `web-tools` line (ADR-0102, SP-ACP Task 9b): whether the hub serves
`vibey_search` and `vibey_fetch` to the agent, and under which budgets. Added after the
`web-search` lines; nothing it reads is started, written or sent anywhere but the local hub.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from pathlib import Path
from typing import Any

import httpx
import pytest

from vibey.cli.interfaces.web_tools_doctor_interface import WebToolsDoctorInterface
from vibey.cli.web_search_doctor import WebSearchDoctor
from vibey.cli.web_tools_doctor import WEB_TOOLS_DOCTOR, WebToolsDoctor
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

PATHS = {"/api/v1/web/search": {}, "/api/v1/web/fetch": {}}


def _project(tmp_path: Path, text: str = "") -> Path:
    state = tmp_path / "state"
    path = tmp_path / "vibey.toml"
    path.write_text(f"[hub]\nstate_dir = '{state}'\n{text}", encoding="utf-8")
    return path


def _serving(tmp_path: Path, tls: bool = False) -> None:
    LocalTokenStore(tmp_path / "state").record_serving(
        ServingRecord(host="127.0.0.1", port=8765, pid=4242, tls=tls)
    )


def _doctor(
    tmp_path: Path,
    paths: dict[str, Any] | None = None,
    *,
    user: Path | None = None,
    error: Exception | None = None,
) -> tuple[WebToolsDoctor, list[str]]:
    asked: list[str] = []

    def get(url: str, *, verify: Any, timeout: float) -> httpx.Response:
        asked.append(url)
        if error is not None:
            raise error
        return httpx.Response(200, json={"paths": paths if paths is not None else PATHS})

    doctor = WebToolsDoctor(
        config_path=lambda: tmp_path / "vibey.toml",
        user_config=lambda: user or tmp_path / "nowhere" / "vibey.toml",
        get=get,
    )
    return doctor, asked


def test_the_line_meets_its_seam() -> None:
    assert isinstance(WEB_TOOLS_DOCTOR, WebToolsDoctorInterface)


def test_a_running_hub_offering_the_routes_to_an_agent_holding_web_passes(tmp_path: Path) -> None:
    _project(tmp_path)
    _serving(tmp_path)
    doctor, asked = _doctor(tmp_path)
    line = doctor.line()
    assert line.startswith("PASS web-tools ")
    assert "vibey_search and vibey_fetch" in line
    assert "60 searches and 30 fetches per hour per principal" in line
    assert asked == ["http://127.0.0.1:8765/api/v1/openapi.json"]


def test_the_budgets_shown_are_the_persons_narrowed_by_the_folder(tmp_path: Path) -> None:
    user = tmp_path / "me" / "vibey.toml"
    user.parent.mkdir()
    user.write_text("[web]\nsearches_per_hour = 9\nfetches_per_hour = 4\n")
    _project(tmp_path, "[web]\nfetches_per_hour = 2\nsearches_per_hour = 900\n")
    _serving(tmp_path)
    doctor, _ = _doctor(tmp_path, user=user)
    assert "9 searches and 2 fetches per hour" in doctor.line()


def test_an_agent_without_web_is_told_how_to_grant_it(tmp_path: Path) -> None:
    _project(tmp_path, "agent_scopes = ['view', 'answer', 'run']\n")
    _serving(tmp_path)
    doctor, asked = _doctor(tmp_path)
    line = doctor.line()
    assert line.startswith("WARN web-tools ") and "[hub] agent_scopes" in line
    assert asked == []  # nothing to check on the hub for an agent that cannot use it


def test_no_running_hub_is_a_warning_and_nothing_is_started(tmp_path: Path) -> None:
    _project(tmp_path)
    doctor, asked = _doctor(tmp_path)
    line = doctor.line()
    assert line.startswith("WARN web-tools ") and "vibey hub start" in line
    assert asked == []


@pytest.mark.parametrize(
    ("paths", "error", "needle"),
    [
        ({"/api/v1/projects": {}}, None, "does not offer"),
        (None, httpx.ConnectError("refused"), "did not answer"),
    ],
)
def test_a_hub_that_does_not_offer_the_routes_or_does_not_answer_is_a_warning(
    tmp_path: Path, paths: dict[str, Any] | None, error: Exception | None, needle: str
) -> None:
    _project(tmp_path)
    _serving(tmp_path)
    doctor, _ = _doctor(tmp_path, {} if paths is None else paths, error=error)
    line = doctor.line()
    assert line.startswith("WARN web-tools ") and needle in line


def test_a_tls_hub_is_asked_over_https_with_its_own_certificate(tmp_path: Path) -> None:
    _project(tmp_path)
    _serving(tmp_path, tls=True)
    seen: list[Any] = []

    def get(url: str, *, verify: Any, timeout: float) -> httpx.Response:
        seen.append((url, verify))
        return httpx.Response(200, json={"paths": PATHS})

    doctor = WebToolsDoctor(
        config_path=lambda: tmp_path / "vibey.toml",
        user_config=lambda: tmp_path / "nowhere.toml",
        get=get,
    )
    assert doctor.line().startswith("PASS")
    ((url, verify),) = seen
    assert url.startswith("https://127.0.0.1:8765/") and str(verify).endswith("cert.pem")


@pytest.mark.parametrize(
    "text",
    ["[web]\nallow_hosts = ['*.x.com']\n", "[hub]\nport = 'x'\n"],
)
def test_a_setting_the_hub_would_refuse_to_start_with_fails(tmp_path: Path, text: str) -> None:
    (tmp_path / "vibey.toml").write_text(text, encoding="utf-8")
    doctor, _ = _doctor(tmp_path)
    assert doctor.line().startswith("FAIL web-tools ")


def test_a_malformed_serving_record_is_a_warning_never_a_crash(tmp_path: Path) -> None:
    _project(tmp_path)
    (tmp_path / "state").mkdir(exist_ok=True)
    (tmp_path / "state" / "serving.json").write_text("[]")
    doctor, _ = _doctor(tmp_path)
    assert doctor.line().startswith("WARN web-tools ")


def test_the_line_never_raises(tmp_path: Path) -> None:
    def boom() -> Path:
        raise RuntimeError("no folder")

    doctor = WebToolsDoctor(config_path=boom, user_config=boom)
    line = doctor.line()
    assert line.startswith("UNKNOWN web-tools ") and "could not check" in line


def test_the_web_search_section_adds_the_line_after_the_ones_it_had(tmp_path: Path) -> None:
    section = WebSearchDoctor(
        environ=lambda: {},
        opener=lambda request, timeout: (_ for _ in ()).throw(ConnectionRefusedError("down")),
        searxng=lambda: "WARN searxng x",
        web_tools=lambda: "PASS web-tools y",
    )
    lines, ok = section.doctor_lines()
    assert [line.split()[1] for line in lines] == [
        "web-search",
        "web-search-backup",
        "searxng",
        "web-tools",
    ]
    assert ok
