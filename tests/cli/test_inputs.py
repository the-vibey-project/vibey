# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey inputs add | list` (SP-LOOPS Phase 3, Task 5).

The commands run through the real Typer app with the real run inputs service and the real
hash-addressed store in pytest's temporary folder; only the project lookup and the ledger are
fakes, handed in through the command class's `open_service` seam, so no database is needed.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from typer.testing import CliRunner

import vibey.cli.inputs as inputs_module
from vibey.application.dto import EngineEvent, ProjectRecord
from vibey.application.interfaces.run_inputs_interface import RunInputsInterface
from vibey.application.run_inputs_service import RunInputsService
from vibey.application.run_inputs_settings import RunInputsSettingsLoader
from vibey.cli.inputs import EXIT_CONFIG, EXIT_REFUSED, EXIT_UNKNOWN, InputsCommands
from vibey.cli.interfaces.inputs_interface import InputsCommandsInterface
from vibey.cli.main import app
from vibey.domain.phase import Phase
from vibey.domain.run_input import RunInputsSettings
from vibey.infrastructure.inputs.hash_addressed_input_store import HashAddressedInputStore
from vibey.infrastructure.inputs.no_follow_files import NoFollowFiles
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
AT = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return AT


class _Projects:
    def __init__(self, record: ProjectRecord) -> None:
        self._record = record

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._record if project_id == self._record.project_id else None


class _Ledger:
    def __init__(self) -> None:
        self.events: list[EngineEvent] = []

    async def record(self, *, project_id: UUID, cycle: int, event: EngineEvent) -> None:
        self.events.append(event)


class _World:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.repo = tmp_path / "repo"
        self.repo.mkdir()
        self.store_root = tmp_path / "state" / "inputs"
        self.user_config = tmp_path / "config" / "vibey.toml"
        self.user_config.parent.mkdir()
        self.project_config = tmp_path / "cwd" / "vibey.toml"
        self.project_config.parent.mkdir()
        self.project_id = uuid4()
        self.record = ProjectRecord(
            project_id=self.project_id,
            name="greeter",
            repo_path=self.repo,
            phase=Phase.BUILD,
            cycle=1,
            max_cycles=3,
            config={},
            created_at=AT,
            updated_at=AT,
        )
        self.ledger = _Ledger()
        self.opened_with: list[RunInputsSettings] = []

    @asynccontextmanager
    async def open_service(self, settings: RunInputsSettings) -> AsyncIterator[RunInputsInterface]:
        self.opened_with.append(settings)
        yield RunInputsService(
            store=HashAddressedInputStore(self.store_root, _Clock()),
            projects=_Projects(self.record),
            ledger=self.ledger,
            clock=_Clock(),
            limits=lambda: settings,
            writer=NoFollowFiles(),
        )

    def commands(self) -> InputsCommands:
        return InputsCommands(
            open_service=self.open_service,
            settings=RunInputsSettingsLoader(TomlTrustedTableReader()),
            user_config=lambda: self.user_config,
            project_config=lambda: self.project_config,
        )

    def store_files(self) -> list[Path]:
        root = self.store_root
        return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[_World]:
    made = _World(tmp_path)
    monkeypatch.setattr(inputs_module, "INPUTS", made.commands())
    yield made


def _run(*args: str, input: str | bytes | None = None) -> tuple[int, str]:
    result = runner.invoke(app, ["inputs", *args], input=input)
    return result.exit_code, result.output


def test_the_commands_meet_their_interface() -> None:
    assert isinstance(inputs_module.INPUTS, InputsCommandsInterface)


def test_add_a_paste_then_list_it_as_json(world: _World) -> None:
    code, output = _run("add", str(world.project_id), "--paste", "hi")
    assert code == 0, output
    assert "added paste" in output
    code, output = _run("list", str(world.project_id), "--json")
    assert code == 0, output
    document = json.loads(output)
    assert document["project_id"] == str(world.project_id)
    assert document["skipped"] == 0
    [row] = document["inputs"]
    assert row == {
        "digest": "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
        "kind": "paste",
        "name": "paste",
        "size": 2,
    }
    assert len(world.ledger.events) == 1


def test_list_json_carries_digests_and_never_the_text(world: _World) -> None:
    _run("add", str(world.project_id), "--paste", "a secret plan")
    code, output = _run("list", str(world.project_id), "--json")
    assert code == 0
    assert "secret" not in output


def test_add_a_file_names_it_by_its_base_name(world: _World) -> None:
    spec = world.tmp / "docs" / "spec.md"
    spec.parent.mkdir()
    spec.write_bytes(b"# Spec\n")
    code, output = _run("add", str(world.project_id), "--file", str(spec))
    assert code == 0, output
    code, output = _run("list", str(world.project_id), "--json")
    [row] = json.loads(output)["inputs"]
    assert (row["kind"], row["name"], row["size"]) == ("file", "spec.md", 7)


def test_a_symlink_given_as_a_file_is_refused_and_nothing_is_written(world: _World) -> None:
    target = world.tmp / "real.md"
    target.write_bytes(b"real")
    link = world.tmp / "link.md"
    link.symlink_to(target)
    code, output = _run("add", str(world.project_id), "--file", str(link))
    assert code == EXIT_REFUSED == 2
    assert "symlink" in output
    assert world.store_files() == []
    assert world.ledger.events == []


def test_a_folder_given_as_a_file_is_refused(world: _World) -> None:
    code, output = _run("add", str(world.project_id), "--file", str(world.tmp))
    assert code == 2
    assert "not a regular file" in output
    assert world.store_files() == []


def test_a_device_given_as_a_file_is_refused(world: _World) -> None:
    code, output = _run("add", str(world.project_id), "--file", os.devnull)
    assert code == 2
    assert "not a regular file" in output


def test_a_file_that_is_not_there_is_refused(world: _World) -> None:
    code, output = _run("add", str(world.project_id), "--file", str(world.tmp / "missing.md"))
    assert code == 2
    assert "cannot be read" in output


def test_a_file_over_the_item_limit_is_refused_from_its_size_before_it_is_read(
    world: _World,
) -> None:
    world.user_config.write_text("[inputs]\nmax_item_bytes = 4\nmax_project_bytes = 8\n")
    big = world.tmp / "big.bin"
    big.write_bytes(b"12345")
    code, output = _run("add", str(world.project_id), "--file", str(big))
    assert code == 2
    assert "max_item_bytes" in output
    assert world.opened_with == []  # refused before the service was opened
    assert world.store_files() == []


@pytest.mark.parametrize(
    "flags",
    [
        (),
        ("--paste", "a", "--paste-stdin"),
        ("--paste", "a", "--file", "x"),
        ("--paste-stdin", "--file", "x"),
    ],
)
def test_exactly_one_source_is_required(world: _World, flags: tuple[str, ...]) -> None:
    code, output = _run("add", str(world.project_id), *flags)
    assert code == 2
    assert "exactly one of --paste, --paste-stdin or --file" in output
    assert world.store_files() == []


def test_paste_stdin_reads_standard_input(world: _World) -> None:
    code, output = _run("add", str(world.project_id), "--paste-stdin", input=b"from stdin\x00\xff")
    assert code == 0, output
    [row] = json.loads(_run("list", str(world.project_id), "--json")[1])["inputs"]
    assert row["size"] == len(b"from stdin\x00\xff")


def test_paste_stdin_over_the_item_limit_is_refused_without_reading_it_all(
    world: _World,
) -> None:
    world.user_config.write_text("[inputs]\nmax_item_bytes = 4\nmax_project_bytes = 8\n")
    code, output = _run("add", str(world.project_id), "--paste-stdin", input=b"123456789")
    assert code == 2
    assert "max_item_bytes" in output
    assert world.store_files() == []


def test_a_refusal_from_the_service_is_exit_2(world: _World) -> None:
    long_name = world.tmp / "second.md"
    long_name.write_bytes(b"x")
    world.user_config.write_text("[inputs]\nmax_items = 1\n")
    assert _run("add", str(world.project_id), "--paste", "one")[0] == 0
    code, output = _run("add", str(world.project_id), "--file", str(long_name))
    assert code == 2
    assert "max_items" in output


def test_an_unknown_project_is_exit_1(world: _World) -> None:
    stranger = uuid4()
    code, output = _run("add", str(stranger), "--paste", "hi")
    assert code == EXIT_UNKNOWN == 1
    assert f"unknown project {stranger}" in output
    code, output = _run("list", str(stranger))
    assert code == 1


def test_a_store_that_cannot_be_made_is_exit_78(world: _World) -> None:
    world.store_root.parent.mkdir()
    world.store_root.write_bytes(b"a file where the store folder belongs")
    code, output = _run("add", str(world.project_id), "--paste", "hi")
    assert code == EXIT_CONFIG == 78
    assert output.startswith("vibey inputs: ")
    assert world.ledger.events == []


def test_an_unreadable_index_is_exit_78_for_list(world: _World) -> None:
    (world.store_root / str(world.project_id) / "index.jsonl").mkdir(parents=True)
    code, output = _run("list", str(world.project_id))
    assert code == 78
    assert "cannot be read" in output


def test_a_bad_inputs_table_in_your_own_file_is_exit_78(world: _World) -> None:
    world.user_config.write_text("[inputs]\nmax_items = 0\n")
    code, output = _run("add", str(world.project_id), "--paste", "hi")
    assert code == 78
    assert "max_items" in output


def test_a_project_inputs_table_is_ignored_with_its_notice(world: _World) -> None:
    world.project_config.write_text("[inputs]\nmax_item_bytes = 999999999\n")
    code, output = _run("add", str(world.project_id), "--paste", "hi")
    assert code == 0, output
    assert "[inputs] is ignored" in output
    assert world.opened_with == [RunInputsSettings()]


def test_the_human_list_escapes_a_name_with_an_escape_byte(world: _World) -> None:
    named = world.tmp / "esc\x1b[31mred.md"
    named.write_bytes(b"x")
    assert _run("add", str(world.project_id), "--file", str(named))[0] == 0
    code, output = _run("list", str(world.project_id))
    assert code == 0
    assert "\x1b" not in output
    assert "red.md" in output
    assert "1 byte" in output


def test_the_human_list_of_nothing_says_how_to_add(world: _World) -> None:
    code, output = _run("list", str(world.project_id))
    assert code == 0
    assert "vibey inputs add" in output


def test_the_human_list_counts_skipped_index_lines(world: _World) -> None:
    _run("add", str(world.project_id), "--paste", "hi")
    with (world.store_root / str(world.project_id) / "index.jsonl").open("ab") as handle:
        handle.write(b"torn")
    code, output = _run("list", str(world.project_id))
    assert code == 0
    assert "2 bytes" in output
    assert "skipped 1 index line" in output


def test_the_default_seams_are_the_composition_roots() -> None:
    from vibey import bootstrap

    commands = InputsCommands()
    assert commands._open_service is bootstrap.run_inputs_app  # noqa: SLF001
    assert isinstance(commands._settings, RunInputsSettingsLoader)  # noqa: SLF001
    assert commands._user_config() == bootstrap.acp_user_config()  # noqa: SLF001
    assert commands._project_config() == Path.cwd() / "vibey.toml"  # noqa: SLF001


def test_a_file_name_colliding_by_case_is_exit_2(world: _World) -> None:
    # Review finding 7 (R-G).
    first = world.tmp / "a" / "spec.md"
    second = world.tmp / "b" / "SPEC.md"
    for path in (first, second):
        path.parent.mkdir()
        path.write_bytes(path.parent.name.encode())
    assert _run("add", str(world.project_id), "--file", str(first))[0] == 0
    code, output = _run("add", str(world.project_id), "--file", str(second))
    assert code == 2
    assert "only in case" in output


@pytest.mark.parametrize("text", ["[inputs\nnot toml", "inputs = 3\n"])
def test_a_malformed_project_file_in_the_folder_does_not_change_the_exit_code(
    world: _World, text: str
) -> None:
    # Review finding 8 (R-H).
    world.project_config.write_text(text)
    code, output = _run("add", str(world.project_id), "--paste", "hi")
    assert code == 0, output
    assert "cannot be read" in output
    assert world.opened_with == [RunInputsSettings()]
