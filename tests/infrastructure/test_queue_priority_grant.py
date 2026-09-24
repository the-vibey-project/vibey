# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the queue-priority grant comes from, and who is asking (ADR-0054, 12.j)."""

import os
import pwd
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.dto import ProjectRecord
from vibey.domain.config import ConfigError
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import Caller
from vibey.infrastructure.interfaces import (
    ProcessCallerInterface,
    ProjectPriorityGrantReaderInterface,
)
from vibey.infrastructure.queue_priority_grant import (
    CONFIG_NAME,
    ProcessCaller,
    ProjectPriorityGrantReader,
)

NOW = datetime(2026, 9, 24, tzinfo=UTC)


def _project(repo: Path) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name="demo",
        repo_path=repo,
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=5,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )


def _me() -> Caller:
    return Caller(uid=os.getuid(), name="me")


def test_the_reader_and_the_caller_satisfy_their_seams() -> None:
    assert isinstance(ProjectPriorityGrantReader(), ProjectPriorityGrantReaderInterface)
    assert isinstance(ProcessCaller(), ProcessCallerInterface)


def test_the_grant_is_the_projects_own_config_and_its_owner_is_the_operator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / CONFIG_NAME).write_text('[queue.priority]\nsources = ["storm"]\n')
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    (elsewhere / CONFIG_NAME).write_text('[queue.priority]\nsources = ["intruder"]\n')
    monkeypatch.chdir(elsewhere)

    grant = ProjectPriorityGrantReader().read(_project(tmp_path))

    assert grant.declared == frozenset({"storm"}), "never the working directory's file"
    assert grant.anchor == str(tmp_path / CONFIG_NAME)
    assert grant.decide(None, _me()).admitted
    assert grant.decide("storm", _me()).admitted
    assert not grant.decide(None, Caller(uid=os.getuid() + 1, name="other")).admitted


def test_with_no_config_the_repository_root_owner_is_the_operator(tmp_path: Path) -> None:
    grant = ProjectPriorityGrantReader().read(_project(tmp_path))
    assert grant.declared == frozenset()
    assert grant.decide(None, _me()).admitted


def test_a_repository_that_is_not_there_admits_nobody(tmp_path: Path) -> None:
    grant = ProjectPriorityGrantReader().read(_project(tmp_path / "gone"))
    assert not grant.decide(None, _me()).admitted


def test_a_malformed_grant_is_an_error_not_an_empty_one(tmp_path: Path) -> None:
    (tmp_path / CONFIG_NAME).write_text("[queue.priority\n")
    with pytest.raises(ConfigError, match="is not valid TOML"):
        ProjectPriorityGrantReader().read(_project(tmp_path))


def test_the_caller_is_the_process_uid_named_from_the_password_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("USER", "somebody-else")
    caller = ProcessCaller().current()
    assert caller.uid == os.getuid()
    assert caller.name == pwd.getpwuid(os.getuid()).pw_name


def test_a_uid_with_no_account_is_named_by_its_number(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(uid: int) -> pwd.struct_passwd:
        raise KeyError(uid)

    monkeypatch.setattr(pwd, "getpwuid", missing)
    assert ProcessCaller().current().name == f"uid-{os.getuid()}"


_ROOT = os.getuid() == 0


@pytest.mark.skipif(_ROOT, reason="root reads through a 0000 mode")
def test_a_repository_it_cannot_search_is_an_error_not_a_grant(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / CONFIG_NAME).write_text('[queue.priority]\nsources = ["storm"]\n')
    repo.chmod(0)
    try:
        with pytest.raises(ConfigError, match="cannot be read"):
            ProjectPriorityGrantReader().read(_project(repo))
    finally:
        repo.chmod(0o755)


@pytest.mark.skipif(_ROOT, reason="root reads through a 0000 mode")
def test_a_config_it_cannot_read_is_an_error_not_a_grant(tmp_path: Path) -> None:
    config = tmp_path / CONFIG_NAME
    config.write_text('[queue.priority]\nsources = ["storm"]\n')
    config.chmod(0)
    try:
        with pytest.raises(ConfigError, match="cannot be read"):
            ProjectPriorityGrantReader().read(_project(tmp_path))
    finally:
        config.chmod(0o644)


def test_a_config_that_is_not_text_is_an_error_not_a_grant(tmp_path: Path) -> None:
    (tmp_path / CONFIG_NAME).write_bytes(b"\xff\xfe[queue]\n")
    with pytest.raises(ConfigError, match="cannot be read"):
        ProjectPriorityGrantReader().read(_project(tmp_path))


def test_an_owner_it_cannot_stat_is_an_error_not_nobody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = Path.stat

    def refusing(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if path == tmp_path:
            raise PermissionError(13, "Permission denied", str(path))
        return real(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "stat", refusing)
    with pytest.raises(ConfigError, match="cannot be read"):
        ProjectPriorityGrantReader().read(_project(tmp_path))
