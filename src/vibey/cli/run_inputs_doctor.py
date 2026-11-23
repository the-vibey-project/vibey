# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `run-inputs` line `vibey doctor` and `vibey acp`'s doctor step print (SP-LOOPS Phase 3c,
Task 6; ADR-0105).

One line in doctor's `MARK name detail` grammar, naming the store `[inputs]` puts in force and
the config file that said so, so a worker whose store resolves elsewhere (another state or config
folder, a wrong bucket: the Phase 3 N7 limit) can be told from the person's shell:

    PASS run-inputs           local store at /home/p/.local/state/vibey/inputs (from ...)
    PASS run-inputs           seaweedfs store https://h:8333/b/vibey/inputs (from ...): reachable;
                              credentials from VIBEY_INPUTS_ACCESS_KEY, VIBEY_INPUTS_SECRET_KEY
    FAIL run-inputs           ... : VIBEY_INPUTS_SECRET_KEY is not set

A local store passes when its folder is writable, or does not exist yet under a writable parent
(made on the first add); a symlink where the folder belongs, or a folder that cannot be written,
fails. A SeaweedFS store is probed with one ListObjectsV2 of at most one key under the prefix:
doctor is a person's explicit act, so this one network request is not a run fetching on its own.
A credential is named by its variable, never shown. A file that cannot be read is `UNKNOWN`, and
so is any exception: the section never breaks doctor.

Declared by `interfaces/run_inputs_doctor_interface.py::RunInputsDoctorInterface`.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

import httpx

from vibey.application.interfaces.run_inputs_settings_interface import (
    RunInputsSettingsLoaderInterface,
)
from vibey.bootstrap import (
    acp_user_config,
    run_inputs_http_client,
    run_inputs_root,
    run_inputs_settings_loader,
    seaweedfs_input_store,
)
from vibey.cli.interfaces.run_inputs_doctor_interface import RunInputsDoctorInterface
from vibey.domain.config import ConfigError
from vibey.domain.run_input import InputStoreLocation
from vibey.infrastructure.inputs.interfaces.seaweedfs_input_store_interface import (
    SeaweedFsInputStoreInterface,
)

NAME: Final = "run-inputs"
_WIDTH: Final = 20

type StoreFactory = Callable[[InputStoreLocation, httpx.Client], SeaweedFsInputStoreInterface]


class RunInputsDoctor:
    """Declared by `interfaces/run_inputs_doctor_interface.py::RunInputsDoctorInterface`. Every
    collaborator is a seam; the defaults are the composition root's (`bootstrap.py`)."""

    def __init__(
        self,
        *,
        user_config: Callable[[], Path] = lambda: acp_user_config(),
        settings: RunInputsSettingsLoaderInterface | None = None,
        state_root: Callable[[], Path] = lambda: run_inputs_root(),
        environ: Callable[[], Mapping[str, str]] = lambda: os.environ,
        client: Callable[[InputStoreLocation], httpx.Client] = run_inputs_http_client,
        store: StoreFactory | None = None,
    ) -> None:
        self._user_config = user_config
        self._settings = settings
        self._state_root = state_root
        self._environ = environ
        self._client = client
        self._store = store

    def doctor_lines(self) -> tuple[list[str], bool]:
        try:
            return self._lines()
        except Exception as exc:  # noqa: BLE001 - the section never breaks doctor
            return [self._line("UNKNOWN", f"could not check ({type(exc).__name__})")], True

    def _lines(self) -> tuple[list[str], bool]:
        config = self._user_config()
        loader = self._settings or run_inputs_settings_loader()
        try:
            location = loader.load(config, None).settings.store
        except ConfigError:
            return [self._line("UNKNOWN", f"could not read your own vibey.toml ({config})")], True
        origin = f"from {config}" if config.is_file() else f"default; {config} does not exist"
        if location.kind == "local":
            return self._local(location, origin)
        return self._remote(location, origin)

    def _local(self, location: InputStoreLocation, origin: str) -> tuple[list[str], bool]:
        root = Path(location.store_dir) if location.store_dir is not None else self._state_root()
        said = f"local store at {root} ({origin})"
        try:
            mode = os.lstat(root).st_mode
        except FileNotFoundError:
            parent = next(p for p in root.parents if p.exists())
            if os.access(parent, os.W_OK | os.X_OK):
                return [self._line("PASS", f"{said}; made on the first add")], True
            return [self._line("FAIL", f"{said}: cannot be made; {parent} is not writable")], False
        if stat.S_ISLNK(mode):
            return [self._line("FAIL", f"{said}: a symlink is where the folder belongs")], False
        if not stat.S_ISDIR(mode):
            return [self._line("FAIL", f"{said}: is not a folder")], False
        if not os.access(root, os.W_OK | os.X_OK):
            return [self._line("FAIL", f"{said}: is not writable")], False
        return [self._line("PASS", said)], True

    def _remote(self, location: InputStoreLocation, origin: str) -> tuple[list[str], bool]:
        said = f"{location.describe()} ({origin})"
        environ = self._environ()
        for variable in (location.access_key_env, location.secret_key_env):
            if not environ.get(variable):
                return [self._line("FAIL", f"{said}: {variable} is not set")], False
        with self._client(location) as client:
            store = (self._store or self._default_store)(location, client)
            probe = store.probe()
        if not probe.reachable:
            return [self._line("FAIL", f"{said}: {probe.detail}")], False
        names = f"{location.access_key_env}, {location.secret_key_env}"
        return [self._line("PASS", f"{said}: reachable; credentials from {names}")], True

    def _default_store(
        self, location: InputStoreLocation, client: httpx.Client
    ) -> SeaweedFsInputStoreInterface:
        return seaweedfs_input_store(location, client=client, environ=self._environ())

    @staticmethod
    def _line(mark: str, detail: str) -> str:
        return f"{mark} {NAME:<{_WIDTH}} {detail}"


RUN_INPUTS_DOCTOR: Final[RunInputsDoctorInterface] = RunInputsDoctor()
"""The one section, as `vibey doctor` and `vibey acp` run it."""
