# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s `run-inputs` line (SP-LOOPS Phase 3c, Task 6; ADR-0105).

Every collaborator is a seam: the person's `vibey.toml` is a file under pytest's folder, the
environment a dict, and a SeaweedFS store the in-memory S3 behind `httpx.MockTransport`
(`tests/fakes/s3.py`). No network, no real home folder, no thread, no sleep. Module-level test
functions (ADR-0016 is about production code).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from tests.fakes.s3 import ACCESS, BUCKET, ENDPOINT, SECRET, FakeS3
from vibey.application.run_inputs_settings import RunInputsSettingsLoader
from vibey.cli.interfaces.run_inputs_doctor_interface import RunInputsDoctorInterface
from vibey.cli.run_inputs_doctor import RUN_INPUTS_DOCTOR, RunInputsDoctor
from vibey.domain.run_input import InputStoreLocation
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

SEAWEED = f'[inputs]\nstore = "seaweedfs"\nendpoint = "{ENDPOINT}"\nbucket = "{BUCKET}"\n'
ENV = {"VIBEY_INPUTS_ACCESS_KEY": ACCESS, "VIBEY_INPUTS_SECRET_KEY": SECRET}


def _doctor(
    tmp_path: Path,
    *,
    table: str | None = None,
    environ: Mapping[str, str] | None = None,
    fake: FakeS3 | None = None,
) -> RunInputsDoctor:
    config = tmp_path / "config" / "vibey.toml"
    config.parent.mkdir(exist_ok=True)
    if table is not None:
        config.write_text(table)
    s3 = fake or FakeS3()
    return RunInputsDoctor(
        user_config=lambda: config,
        settings=RunInputsSettingsLoader(TomlTrustedTableReader()),
        state_root=lambda: tmp_path / "state" / "inputs",
        environ=lambda: environ if environ is not None else ENV,
        client=lambda location: s3.client(),
    )


def _one(doctor: RunInputsDoctor) -> tuple[str, bool]:
    [line], ok = doctor.doctor_lines()
    return line, ok


def test_the_doctor_meets_its_interface() -> None:
    assert isinstance(RUN_INPUTS_DOCTOR, RunInputsDoctorInterface)


def test_a_local_store_not_made_yet_under_a_writable_parent_passes(tmp_path: Path) -> None:
    line, ok = _one(_doctor(tmp_path))
    root = tmp_path / "state" / "inputs"
    assert ok
    assert line.startswith("PASS run-inputs ")
    assert f"local store at {root} (default; " in line
    assert line.endswith("does not exist); made on the first add")


def test_a_local_store_that_exists_and_is_writable_passes(tmp_path: Path) -> None:
    (tmp_path / "state" / "inputs").mkdir(parents=True)
    line, ok = _one(_doctor(tmp_path, table="[inputs]\nmax_items = 3\n"))
    config = tmp_path / "config" / "vibey.toml"
    assert ok and line == (
        f"PASS {'run-inputs':<20} local store at {tmp_path / 'state' / 'inputs'} (from {config})"
    )


def test_the_line_names_the_config_file_it_read(tmp_path: Path) -> None:
    folder = tmp_path / "named"
    folder.mkdir()
    line, ok = _one(_doctor(tmp_path, table=f'[inputs]\nstore_dir = "{folder}"\n'))
    assert ok
    assert f"local store at {folder} (from {tmp_path / 'config' / 'vibey.toml'})" in line


def test_a_symlink_where_the_local_folder_belongs_fails(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "state" / "inputs").symlink_to(tmp_path / "elsewhere")
    line, ok = _one(_doctor(tmp_path))
    assert not ok and line.startswith("FAIL run-inputs ")
    assert line.endswith("a symlink is where the folder belongs")


def test_a_file_where_the_local_folder_belongs_fails(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "inputs").write_text("not a folder")
    line, ok = _one(_doctor(tmp_path))
    assert not ok and line.endswith("is not a folder")


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes through any mode")
def test_a_local_folder_that_cannot_be_written_fails(tmp_path: Path) -> None:
    root = tmp_path / "state" / "inputs"
    root.mkdir(parents=True)
    root.chmod(0o500)
    try:
        line, ok = _one(_doctor(tmp_path))
    finally:
        root.chmod(0o700)
    assert not ok and line.endswith("is not writable")


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes through any mode")
def test_a_local_folder_whose_parent_cannot_be_written_fails(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    state.chmod(0o500)
    try:
        line, ok = _one(_doctor(tmp_path))
    finally:
        state.chmod(0o700)
    assert not ok and line.endswith(f"cannot be made; {state} is not writable")


def test_a_reachable_seaweedfs_store_passes_naming_the_variables(tmp_path: Path) -> None:
    fake = FakeS3()
    line, ok = _one(_doctor(tmp_path, table=SEAWEED, fake=fake))
    assert ok
    assert line.startswith("PASS run-inputs ")
    assert f"seaweedfs store {ENDPOINT}/{BUCKET}/vibey/inputs (from " in line
    assert line.endswith(
        ": reachable; credentials from VIBEY_INPUTS_ACCESS_KEY, VIBEY_INPUTS_SECRET_KEY"
    )
    [probe] = fake.requests  # one ListObjectsV2 of at most one key
    assert probe.url.params["max-keys"] == "1"


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({}, "VIBEY_INPUTS_ACCESS_KEY"),
        ({"VIBEY_INPUTS_ACCESS_KEY": ACCESS}, "VIBEY_INPUTS_SECRET_KEY"),
        (
            {"VIBEY_INPUTS_ACCESS_KEY": ACCESS, "VIBEY_INPUTS_SECRET_KEY": ""},
            "VIBEY_INPUTS_SECRET_KEY",
        ),
    ],
)
def test_an_unset_credential_variable_fails_naming_it(
    tmp_path: Path, environ: dict[str, str], variable: str
) -> None:
    fake = FakeS3()
    line, ok = _one(_doctor(tmp_path, table=SEAWEED, environ=environ, fake=fake))
    assert not ok and line.endswith(f": {variable} is not set")
    assert fake.requests == []  # nothing is sent without credentials


@pytest.mark.parametrize(
    ("answer", "ending"),
    [
        (httpx.ConnectError("refused"), ": not reachable (ConnectError)"),
        (
            httpx.Response(403),
            ": refused the credentials in VIBEY_INPUTS_ACCESS_KEY, VIBEY_INPUTS_SECRET_KEY",
        ),
        (
            httpx.Response(404, content=b"<Error><Code>NoSuchBucket</Code></Error>"),
            f": bucket {BUCKET} does not exist",
        ),
    ],
)
def test_a_seaweedfs_store_that_does_not_answer_as_one_fails_saying_why(
    tmp_path: Path, answer: object, ending: str
) -> None:
    fake = FakeS3()

    def respond(request: httpx.Request) -> httpx.Response:
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, httpx.Response)
        return answer

    fake.answer = respond
    line, ok = _one(_doctor(tmp_path, table=SEAWEED, fake=fake))
    assert not ok and line.startswith("FAIL run-inputs ")
    assert ending in line


def test_doctor_never_prints_a_credential_value(tmp_path: Path) -> None:
    sentinels = {
        "VIBEY_INPUTS_ACCESS_KEY": "ACCESS-SENTINEL-1",
        "VIBEY_INPUTS_SECRET_KEY": "SECRET-SENTINEL-2",
    }
    fake = FakeS3(secret="SECRET-SENTINEL-2")
    fake.answer = lambda request: None
    for answer in (None, httpx.Response(403), httpx.Response(503)):
        fake.answer = lambda request, a=answer: a  # type: ignore[misc]
        lines, _ = _doctor(tmp_path, table=SEAWEED, environ=sentinels, fake=fake).doctor_lines()
        assert all("SENTINEL" not in line for line in lines), lines


def test_your_own_vibey_toml_that_cannot_be_read_is_unknown(tmp_path: Path) -> None:
    line, ok = _one(_doctor(tmp_path, table='[inputs]\nsecret_key = "s3cr3t"\n'))
    assert ok and line.startswith("UNKNOWN run-inputs ")
    assert "could not read your own vibey.toml" in line and "s3cr3t" not in line


def test_an_exception_in_the_probe_is_unknown_never_a_crash(tmp_path: Path) -> None:
    def broken(location: InputStoreLocation) -> httpx.Client:
        raise RuntimeError("the client could not be made s3cr3t")

    config = tmp_path / "vibey.toml"
    config.write_text(SEAWEED)
    doctor = RunInputsDoctor(
        user_config=lambda: config,
        settings=RunInputsSettingsLoader(TomlTrustedTableReader()),
        environ=lambda: ENV,
        client=broken,
    )
    line, ok = _one(doctor)
    assert ok and line == f"UNKNOWN {'run-inputs':<20} could not check (RuntimeError)"


def test_the_default_store_is_the_composition_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vibey.infrastructure.inputs.seaweedfs_input_store import SeaweedFsInputStore

    location = InputStoreLocation(kind="seaweedfs", endpoint=ENDPOINT, bucket=BUCKET)
    doctor = RunInputsDoctor(environ=lambda: ENV)
    with httpx.Client() as client:
        store = doctor._default_store(location, client)  # noqa: SLF001
    assert isinstance(store, SeaweedFsInputStore)


def test_the_default_seams_read_your_own_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from vibey import bootstrap

    doctor = RunInputsDoctor()
    assert doctor._user_config() == bootstrap.acp_user_config()  # noqa: SLF001
    assert doctor._state_root() == bootstrap.run_inputs_root()  # noqa: SLF001
    assert doctor._environ() is os.environ  # noqa: SLF001


SECRET_40 = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


@pytest.mark.parametrize("secret", [SECRET_40, "AKIAIOSFODNN7EXAMPLEAKIAIOSFODNN7EXAMPLE"])
def test_a_secret_in_secret_key_env_never_reaches_any_output(
    tmp_path: Path,
    secret: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review B2, across every surface that reads [inputs]: doctor, `vibey inputs`, and the
    worker's composition. A 40-character secret appears in no line, error or log record."""
    import logging

    from typer.testing import CliRunner

    import vibey.cli.inputs as inputs_module
    from vibey import bootstrap
    from vibey.cli.inputs import InputsCommands
    from vibey.cli.main import app
    from vibey.domain.config import ConfigError

    table = SEAWEED + f'secret_key_env = "{secret}"\n'
    config = tmp_path / "config" / "vibey.toml"
    config.parent.mkdir()
    config.write_text(table)
    with caplog.at_level(logging.DEBUG):
        lines, _ = RunInputsDoctor(
            user_config=lambda: config,
            settings=RunInputsSettingsLoader(TomlTrustedTableReader()),
            environ=lambda: {**ENV, secret: "x"},
        ).doctor_lines()
        assert all(secret not in line for line in lines)

        commands = InputsCommands(
            settings=RunInputsSettingsLoader(TomlTrustedTableReader()),
            user_config=lambda: config,
            project_config=lambda: tmp_path / "none" / "vibey.toml",
        )
        mp = pytest.MonkeyPatch()
        mp.setattr(inputs_module, "INPUTS", commands)
        mp.setattr(bootstrap, "acp_user_config", lambda: config)
        try:
            runner = CliRunner()
            for args in (("add", str(uuid4()), "--paste", "x"), ("list", str(uuid4()))):
                result = runner.invoke(app, ["inputs", *args])
                assert result.exit_code == 78
                assert secret not in result.output
            with pytest.raises(ConfigError) as caught:
                bootstrap.run_inputs_location()
            assert secret not in str(caught.value)
        finally:
            mp.undo()
    assert all(secret not in record.getMessage() for record in caplog.records)
    captured = capsys.readouterr()
    assert secret not in captured.out and secret not in captured.err
