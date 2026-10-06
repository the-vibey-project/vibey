# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey state` (ADR-0086): what each subcommand prints, where, and what it exits with.

The service and the key store are fakes; `default_service` and `default_key_store` are
built for real from a declared environment, without a database, a keychain or `gh`."""

import asyncio
import io
import json
import os
import stat
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

import vibey.cli.state as state_module
from vibey.application.state_sync import StateSyncService
from vibey.cli import main as cli_main
from vibey.cli.interfaces.state_interface import StateCommandInterface
from vibey.cli.state import STATE, StateCommand, default_key_store, default_service
from vibey.domain.errors import VibeyError
from vibey.domain.state_sync import Conflict, StateSyncRefused, SyncReport, SyncState
from vibey.infrastructure.state.aes_gcm_cipher import StateKey
from vibey.infrastructure.state.state_key import StateKeyMissing, StateKeyStore

REMOTE = "o/r@vibey-state"
COMMIT = "0123456789abcdef0123"
NOW = datetime(2026, 10, 6, 12, 0, 0, tzinfo=UTC)

IN_SYNC = SyncReport(SyncState.IN_SYNC, REMOTE, commit=COMMIT, rows=7)
SYNCED = SyncReport(SyncState.SYNCED, REMOTE, pulled=2, pushed=True, commit=COMMIT, rows=9)
PENDING = SyncReport(SyncState.PENDING, REMOTE, pulled=3, to_push=True, commit=COMMIT, rows=4)
CONFLICT = SyncReport(
    SyncState.CONFLICT,
    REMOTE,
    commit=COMMIT,
    rows=4,
    conflicts=(Conflict("job", '["j1"]', "both ends changed it"),),
)


class FakeService:
    """A `StateSyncServiceInterface` that answers from a script, one entry per call."""

    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.calls: list[tuple[str, object]] = []

    def _next(self) -> object:
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    async def status(self) -> SyncReport:
        self.calls.append(("status", None))
        answer = self._next()
        assert isinstance(answer, SyncReport)
        return answer

    async def sync(self, *, push: bool = True) -> SyncReport:
        self.calls.append(("sync", push))
        answer = self._next()
        assert isinstance(answer, SyncReport)
        return answer

    async def export(self) -> bytes:
        self.calls.append(("export", None))
        answer = self._next()
        assert isinstance(answer, bytes)
        return answer

    async def restore(self, sealed: bytes) -> SyncReport:
        self.calls.append(("restore", sealed))
        answer = self._next()
        assert isinstance(answer, SyncReport)
        return answer

    async def forget(self) -> None:
        self.calls.append(("forget", None))
        self._next()


class FakeKeyStore:
    """A `StateKeyStoreInterface`: `where` names the key's place, "" for none."""

    def __init__(
        self, where: str = "", *, text: str = "the-key", fail: Exception | None = None
    ) -> None:
        self._where = where
        self._text = text
        self._fail = fail
        self.created = False

    def where(self) -> str:
        if self._fail is not None:
            raise self._fail
        return self._where

    def text(self) -> str:
        if self._fail is not None:
            raise self._fail
        return self._text

    def load(self) -> bytes:  # pragma: no cover - the command never loads the key itself
        raise AssertionError

    def create(self) -> str:
        if self._fail is not None:
            raise self._fail
        self.created = True
        return "/home/op/.config/vibey/state.key"


class Harness:
    def __init__(
        self,
        service: FakeService | None = None,
        keys: FakeKeyStore | None = None,
        *,
        factory_error: Exception | None = None,
    ) -> None:
        self.service = service or FakeService(IN_SYNC)
        self.keys = keys or FakeKeyStore()
        self.out = io.StringIO()
        self.err = io.StringIO()
        self.slept: list[float] = []
        self.environs: list[Mapping[str, str]] = []
        self.factory_error = factory_error

        async def make(environ: Mapping[str, str]) -> FakeService:
            self.environs.append(environ)
            if self.factory_error is not None:
                raise self.factory_error
            return self.service

        def key_store(environ: Mapping[str, str]) -> FakeKeyStore:
            self.environs.append(environ)
            if self.factory_error is not None:
                raise self.factory_error
            return self.keys

        self.command = StateCommand(
            environ={"VIBEY_STATE_REPOSITORY": "o/r"},
            service=make,
            key_store=key_store,
            out=self.out,
            err=self.err,
            sleep=self.slept.append,
            clock=lambda: NOW,
        )


def test_the_command_is_its_interface() -> None:
    assert isinstance(STATE, StateCommandInterface)
    assert isinstance(StateCommand(), StateCommandInterface)


# --- sync -------------------------------------------------------------------------------


def test_one_sync_in_sync_says_so_on_stdout_and_exits_0() -> None:
    h = Harness(FakeService(IN_SYNC))
    assert h.command.sync() == 0
    assert h.out.getvalue() == f"{IN_SYNC.describe()}\n"
    assert h.err.getvalue() == ""
    assert h.service.calls == [("sync", True)]
    assert h.environs == [{"VIBEY_STATE_REPOSITORY": "o/r"}]
    assert h.slept == []


def test_one_sync_that_synced_says_what_it_pulled_and_pushed() -> None:
    h = Harness(FakeService(SYNCED))
    assert h.command.sync() == 0
    assert "synced at 0123456789ab: 2 row change(s) pulled, pushed; 9 row(s)" in h.out.getvalue()


def test_a_conflict_is_said_on_stderr_and_exits_1() -> None:
    h = Harness(FakeService(CONFLICT))
    assert h.command.sync() == 1
    assert h.out.getvalue() == ""
    assert "1 conflict(s); nothing was changed at either end" in h.err.getvalue()
    assert 'job ["j1"]: both ends changed it' in h.err.getvalue()


def test_no_push_asks_the_service_not_to_push() -> None:
    h = Harness(FakeService(SYNCED))
    assert h.command.sync(push=False) == 0
    assert h.service.calls == [("sync", False)]


def test_every_runs_the_rounds_stamped_and_slept_between() -> None:
    h = Harness(FakeService(IN_SYNC, SYNCED, IN_SYNC))
    assert h.command.sync(every=5, rounds=3) == 0
    assert h.service.calls == [("sync", True)] * 3
    assert h.slept == [5, 5]
    lines = h.out.getvalue().splitlines()
    assert len(lines) == 3
    assert all(line.startswith("2026-10-06T12:00:00+00:00 ") for line in lines)
    assert lines[1].endswith(SYNCED.describe())


def test_every_keeps_going_after_a_failed_round_and_exits_with_the_last_one() -> None:
    h = Harness(
        FakeService(VibeyError("GitHub refused"), ValueError("bad setting"), IN_SYNC, CONFLICT)
    )
    assert h.command.sync(every=2.5, rounds=2) == 2
    assert h.err.getvalue() == "vibey state: GitHub refused\nvibey state: bad setting\n"
    assert h.out.getvalue() == ""
    assert h.slept == [2.5]

    assert h.command.sync(every=1, rounds=2) == 1
    assert h.out.getvalue().startswith("2026-10-06T12:00:00+00:00 ")
    assert h.err.getvalue().endswith("both ends changed it\n")


def test_a_failed_single_sync_exits_1_on_a_refusal_and_2_on_a_setting() -> None:
    refused = Harness(FakeService(StateSyncRefused("the ledger diverged")))
    assert refused.command.sync() == 1
    assert refused.err.getvalue() == "vibey state: the ledger diverged\n"

    unusable = Harness(factory_error=ValueError("VIBEY_STATE_ATTEMPTS must be at least 1"))
    assert unusable.command.sync() == 2
    assert unusable.err.getvalue() == "vibey state: VIBEY_STATE_ATTEMPTS must be at least 1\n"
    assert unusable.service.calls == []


@pytest.mark.parametrize("every", [0, -3.0])
def test_an_interval_that_is_not_above_zero_is_refused(every: float) -> None:
    h = Harness()
    assert h.command.sync(every=every) == 2
    assert "--every is a number of seconds above 0" in h.err.getvalue()
    assert h.service.calls == []


# --- status -----------------------------------------------------------------------------


def test_status_says_what_a_sync_would_do() -> None:
    h = Harness(FakeService(PENDING))
    assert h.command.status() == 0
    assert h.out.getvalue() == f"{PENDING.describe()}\n"
    assert h.service.calls == [("status", None)]


def test_status_json_is_one_object_with_every_key() -> None:
    h = Harness(FakeService(PENDING))
    assert h.command.status(as_json=True) == 0
    assert json.loads(h.out.getvalue()) == {
        "state": "pending",
        "remote": REMOTE,
        "commit": COMMIT,
        "rows": 4,
        "to_pull": 3,
        "to_push": True,
        "conflicts": [],
    }


def test_status_json_of_a_conflict_names_it_and_exits_1() -> None:
    h = Harness(FakeService(CONFLICT))
    assert h.command.status(as_json=True) == 1
    found = json.loads(h.out.getvalue())
    assert found["state"] == "conflict"
    assert found["conflicts"] == ['job ["j1"]: both ends changed it']
    assert h.err.getvalue() == ""


def test_status_of_a_conflict_as_text_is_said_on_stderr() -> None:
    h = Harness(FakeService(CONFLICT))
    assert h.command.status() == 1
    assert "conflict(s)" in h.err.getvalue()


def test_status_that_cannot_run_says_why() -> None:
    h = Harness(FakeService(VibeyError("no branch access")))
    assert h.command.status(as_json=True) == 1
    assert h.out.getvalue() == ""
    assert h.err.getvalue() == "vibey state: no branch access\n"


# --- export and import ------------------------------------------------------------------


def test_export_writes_the_sealed_bytes_privately_and_atomically(tmp_path: Path) -> None:
    h = Harness(FakeService(b"VBYSTAT1sealed"))
    target = tmp_path / "nested" / "dir" / "state.export"
    assert h.command.export(target) == 0
    assert target.read_bytes() == b"VBYSTAT1sealed"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert sorted(p.name for p in target.parent.iterdir()) == ["state.export"]
    assert h.out.getvalue() == f"vibey state: exported, sealed, to {target}\n"


def test_export_replaces_an_earlier_export(tmp_path: Path) -> None:
    target = tmp_path / "state.export"
    target.write_bytes(b"old and longer than the new one")
    h = Harness(FakeService(b"new"))
    assert h.command.export(target) == 0
    assert target.read_bytes() == b"new"


def test_a_refused_export_writes_nothing(tmp_path: Path) -> None:
    h = Harness(FakeService(StateSyncRefused("no key opens it")))
    target = tmp_path / "state.export"
    assert h.command.export(target) == 1
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []
    assert h.err.getvalue() == "vibey state: no key opens it\n"


def test_import_of_a_missing_file_is_refused_before_the_service_is_built(tmp_path: Path) -> None:
    h = Harness()
    missing = tmp_path / "nowhere.export"
    assert h.command.import_(missing) == 1
    assert h.err.getvalue() == f"vibey state: no export at {missing}\n"
    assert h.environs == []


def test_import_restores_the_export_and_says_what_it_did(tmp_path: Path) -> None:
    export = tmp_path / "state.export"
    export.write_bytes(b"sealed-bytes")
    h = Harness(FakeService(SYNCED))
    assert h.command.import_(export) == 0
    assert h.service.calls == [("restore", b"sealed-bytes")]
    assert h.out.getvalue() == f"{SYNCED.describe()}\n"


def test_import_into_a_database_with_rows_is_refused(tmp_path: Path) -> None:
    export = tmp_path / "state.export"
    export.write_bytes(b"sealed-bytes")
    h = Harness(FakeService(StateSyncRefused("this database holds rows")))
    assert h.command.import_(export) == 1
    assert h.err.getvalue() == "vibey state: this database holds rows\n"
    assert h.out.getvalue() == ""


# --- forget -----------------------------------------------------------------------------


def test_forget_says_the_next_sync_is_a_first_one() -> None:
    h = Harness(FakeService(None))
    assert h.command.forget() == 0
    assert h.service.calls == [("forget", None)]
    assert "forgot the commit this database last synced with" in h.out.getvalue()


def test_a_forget_that_fails_says_why_and_claims_nothing() -> None:
    h = Harness(FakeService(VibeyError("the database is unreachable")))
    assert h.command.forget() == 1
    assert h.out.getvalue() == ""
    assert h.err.getvalue() == "vibey state: the database is unreachable\n"


# --- key --------------------------------------------------------------------------------


def test_no_key_is_said_and_exits_1() -> None:
    h = Harness(keys=FakeKeyStore(""))
    assert h.command.key() == 1
    assert "no state key here; `vibey state key --new` makes one" in h.err.getvalue()
    assert h.out.getvalue() == ""


def test_where_the_key_is() -> None:
    h = Harness(keys=FakeKeyStore("VIBEY_STATE_KEY"))
    assert h.command.key() == 0
    assert h.out.getvalue() == "vibey state: the state key is in VIBEY_STATE_KEY\n"


def test_show_prints_the_key_and_only_the_key() -> None:
    h = Harness(keys=FakeKeyStore("somewhere", text="k3y"))
    assert h.command.key(show=True) == 0
    assert h.out.getvalue() == "k3y\n"
    assert h.err.getvalue() == ""


def test_new_makes_a_key_and_says_where_on_stderr_only() -> None:
    keys = FakeKeyStore()
    h = Harness(keys=keys)
    assert h.command.key(new=True) == 0
    assert keys.created
    assert h.out.getvalue() == ""
    err = h.err.getvalue()
    assert "made a state key, kept in /home/op/.config/vibey/state.key" in err
    assert "gh secret set VIBEY_STATE_KEY" in err


@pytest.mark.parametrize(
    ("raised", "code"),
    [
        (ValueError("the state key is 32 bytes as base64url"), 2),
        (StateKeyMissing("a state key already exists (VIBEY_STATE_KEY)"), 1),
    ],
)
@pytest.mark.parametrize("flags", [{}, {"new": True}, {"show": True}])
def test_a_key_that_cannot_be_used_is_said(
    raised: Exception, code: int, flags: dict[str, bool]
) -> None:
    h = Harness(keys=FakeKeyStore(fail=raised))
    assert h.command.key(**flags) == code
    assert h.err.getvalue() == f"vibey state: {raised}\n"
    assert h.out.getvalue() == ""


def test_a_key_store_that_cannot_be_built_is_a_setting() -> None:
    h = Harness(factory_error=ValueError("VIBEY_STATE_BRANCH is not a branch name"))
    assert h.command.key() == 2


# --- defaults ---------------------------------------------------------------------------


def test_the_defaults_read_the_process_environment_and_print_to_the_process_streams(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("VIBEY_STATE_PROBE", "seen")
    seen: list[Mapping[str, str]] = []

    async def make(environ: Mapping[str, str]) -> FakeService:
        seen.append(environ)
        return FakeService(CONFLICT)

    command = StateCommand(service=make)
    assert command.sync() == 1
    assert command.status() == 1
    assert seen[0]["VIBEY_STATE_PROBE"] == "seen"
    assert seen[0] is os.environ
    captured = capsys.readouterr()
    assert "conflict(s)" in captured.err

    async def fine(environ: Mapping[str, str]) -> FakeService:
        return FakeService(IN_SYNC)

    assert StateCommand(service=fine).status() == 0
    assert "in sync" in capsys.readouterr().out


def test_the_default_clock_is_aware_and_the_default_sleep_is_real() -> None:
    async def make(environ: Mapping[str, str]) -> FakeService:
        return FakeService(IN_SYNC)

    out = io.StringIO()
    command = StateCommand(environ={}, service=make, out=out, err=io.StringIO())
    assert command.sync(every=0.001, rounds=2) == 0
    stamp = out.getvalue().split(" ", 1)[0]
    assert datetime.fromisoformat(stamp).tzinfo is not None


def test_the_default_service_is_built_from_the_environment_without_a_network() -> None:
    environ = {
        "VIBEY_STATE_REPOSITORY": "o/r",
        "VIBEY_STATE_KEY": StateKey.new(),
        "VIBEY_STATE_PG_URL": "postgresql://x",
        "VIBEY_STATE_ATTEMPTS": "3",
    }
    service = asyncio.run(default_service(environ))
    assert isinstance(service, StateSyncService)


def test_the_default_service_refuses_a_setting_it_cannot_use() -> None:
    with pytest.raises(ValueError, match="VIBEY_STATE_ATTEMPTS"):
        asyncio.run(default_service({"VIBEY_STATE_ATTEMPTS": "0"}))


def test_the_default_key_store_is_this_machines(tmp_path: Path) -> None:
    store = default_key_store(
        {"VIBEY_STATE_KEY": "", "VIBEY_STATE_KEY_FILE": str(tmp_path / "state.key")}
    )
    assert isinstance(store, StateKeyStore)


# --- the typer commands -----------------------------------------------------------------


class Recording:
    """Stands in for `STATE`: records each call and answers with `code`."""

    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.calls: list[tuple[str, object]] = []

    def sync(self, *, push: bool = True, every: float | None = None, rounds: int = 0) -> int:
        self.calls.append(("sync", (push, every, rounds)))
        return self.code

    def status(self, *, as_json: bool = False) -> int:
        self.calls.append(("status", as_json))
        return self.code

    def export(self, path: Path) -> int:
        self.calls.append(("export", path))
        return self.code

    def import_(self, path: Path) -> int:
        self.calls.append(("import", path))
        return self.code

    def forget(self) -> int:
        self.calls.append(("forget", None))
        return self.code

    def key(self, *, new: bool = False, show: bool = False) -> int:
        self.calls.append(("key", (new, show)))
        return self.code


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recording:
    recording = Recording(code=3)
    monkeypatch.setattr(state_module, "STATE", recording)
    return recording


@pytest.mark.parametrize(
    ("argv", "call"),
    [
        (["state", "sync"], ("sync", (True, None, 0))),
        (["state", "sync", "--no-push", "--every", "5"], ("sync", (False, 5.0, 0))),
        (["state", "status"], ("status", False)),
        (["state", "status", "--json"], ("status", True)),
        (["state", "export", "--out", "x.export"], ("export", Path("x.export"))),
        (["state", "import", "x.export"], ("import", Path("x.export"))),
        (["state", "forget"], ("forget", None)),
        (["state", "key"], ("key", (False, False))),
        (["state", "key", "--new"], ("key", (True, False))),
        (["state", "key", "--show"], ("key", (False, True))),
    ],
)
def test_each_subcommand_reaches_the_command_and_exits_with_its_code(
    recorder: Recording, argv: list[str], call: tuple[str, object]
) -> None:
    result = CliRunner().invoke(cli_main.app, argv)
    assert result.exit_code == 3, result.output
    assert recorder.calls == [call]


def test_state_alone_shows_its_help(recorder: Recording) -> None:
    result = CliRunner().invoke(cli_main.app, ["state"])
    assert "sync" in result.output and "forget" in result.output
    assert recorder.calls == []


def test_the_hub_never_runs_state_on_the_workflows() -> None:
    """`vibey -w state sync` would sync whatever database the runner declares: reserved."""
    from vibey.domain.hub_scope import HUB_SCOPES, RESERVED_COMMANDS

    assert RESERVED_COMMANDS[("state",)] == "state_sync"
    for argv in (("state", "sync"), ("-v", "state", "key", "--show"), ("state",)):
        assert HUB_SCOPES.reserved_command(argv) == "state_sync"
    assert HUB_SCOPES.reserved("state_sync")
