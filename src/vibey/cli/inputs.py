# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey inputs add | list`: the pasted texts and files every BUILD run of a project is given
(SP-LOOPS Phase 3, Task 5; design Goal 4 and Decision 6).

- `add PROJECT_ID (--paste TEXT | --paste-stdin | --file PATH)` stores one input in the
  project's `.vibey/inputs` and records its digest, kind and size on the ledger, never its
  content. Exactly one source is given. `--file` opens the path without following a symlink and
  refuses anything but a regular file (a folder, a device, a FIFO), and refuses one over
  `[inputs] max_item_bytes` from its size before reading a byte; `--paste-stdin` reads at most
  one byte past that limit. The file's name is its base name; a paste is named `paste`.
- `list PROJECT_ID [--json]` prints the inputs in the order added: digest, kind, size and name.

**Whose limits.** `[inputs]` comes only from the person's own `vibey.toml`
(`bootstrap.acp_user_config`); a `[inputs]` table in the folder the command runs in is ignored,
and the notice saying so is printed.

**What a terminal sees.** A name is a person's text and may carry control characters; the human
output prints it through the resolver's own cleaner (`SafeText`). `--json` prints the values as
they are, typed.

Exit codes: 0 done; 1 an unknown project; 2 a refused input, or not exactly one source; 78 the
person's `vibey.toml` cannot be read, or the store cannot be made, read or written. Declared by
`interfaces/inputs_interface.py::InputsCommandsInterface`.
"""

from __future__ import annotations

import asyncio
import errno
import json
import os
import stat
import sys
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Annotated, Final
from uuid import UUID

import typer
from vibey_runners.common.capabilities.interfaces.safe_text_interface import SafeTextInterface
from vibey_runners.common.capabilities.safe_text import SafeText

from vibey.application.interfaces.run_inputs_interface import RunInputsInterface
from vibey.application.interfaces.run_inputs_settings_interface import (
    RunInputsSettingsLoaderInterface,
)
from vibey.bootstrap import acp_user_config, run_inputs_app, run_inputs_settings_loader
from vibey.cli.interfaces.inputs_interface import InputsCommandsInterface
from vibey.domain.config import ConfigError
from vibey.domain.errors import InputStoreError, RunInputRefused, UnknownProject
from vibey.domain.run_input import InputKind, InputListing, RunInput, RunInputsSettings

EXIT_UNKNOWN: Final = 1
EXIT_REFUSED: Final = 2
EXIT_CONFIG: Final = 78
LINE_CHARS: Final = 300
"""The most of one line of a person's text (a name, a path, a reason) a printed line carries."""
PASTE_NAME: Final = "paste"
_OPEN_FLAGS: Final = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


class InputsCommands:
    """Declared by `InputsCommandsInterface`. Every collaborator is a seam; the defaults are the
    composition root's (`bootstrap.py`)."""

    def __init__(
        self,
        *,
        open_service: Callable[
            [RunInputsSettings], AbstractAsyncContextManager[RunInputsInterface]
        ] = run_inputs_app,
        settings: RunInputsSettingsLoaderInterface | None = None,
        user_config: Callable[[], Path] = lambda: acp_user_config(),
        project_config: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        stdin: Callable[[int], bytes] = lambda limit: sys.stdin.buffer.read(limit),
        text: SafeTextInterface | None = None,
        echo: Callable[[str], object] = typer.echo,
    ) -> None:
        self._open_service = open_service
        self._settings = settings or run_inputs_settings_loader()
        self._user_config = user_config
        self._project_config = project_config
        self._stdin = stdin
        self._text = text or SafeText()
        self._echo = echo

    def add(
        self, project_id: UUID, *, paste: str | None, paste_stdin: bool, file: Path | None
    ) -> int:
        if [paste is not None, paste_stdin, file is not None].count(True) != 1:
            self._echo(
                "vibey inputs add: give exactly one of --paste, --paste-stdin or --file "
                "(see `vibey inputs add --help`)"
            )
            return EXIT_REFUSED
        try:
            loaded = self._settings.load(self._user_config(), self._project_config())
        except ConfigError as exc:
            self._echo(self._clean(f"vibey inputs: {exc}"))
            return EXIT_CONFIG
        for notice in loaded.notices:
            self._echo(self._clean(notice))
        limits = loaded.settings
        try:
            kind, name, data = self._source(paste, file, limits.max_item_bytes)
            item = asyncio.run(self._add(limits, project_id, kind, name, data))
        except RunInputRefused as exc:
            self._echo(self._clean(f"vibey inputs: {exc.reason}"))
            return EXIT_REFUSED
        except UnknownProject:
            self._echo(f"unknown project {project_id}")
            return EXIT_UNKNOWN
        except InputStoreError as exc:
            self._echo(self._clean(f"vibey inputs: {exc}"))
            return EXIT_CONFIG
        self._echo(
            self._clean(
                f"added {item.kind} {item.name} ({self._bytes(item.size)}) as {item.digest}"
            )
        )
        return 0

    def list(self, project_id: UUID, *, as_json: bool) -> int:
        try:
            listing = asyncio.run(self._listed(project_id))
        except UnknownProject:
            self._echo(f"unknown project {project_id}")
            return EXIT_UNKNOWN
        except InputStoreError as exc:
            self._echo(self._clean(f"vibey inputs: {exc}"))
            return EXIT_CONFIG
        if as_json:
            document = {
                "project_id": str(project_id),
                "inputs": [
                    {"digest": i.digest, "kind": i.kind, "name": i.name, "size": i.size}
                    for i in listing.items
                ],
                "skipped": listing.skipped,
            }
            self._echo(json.dumps(document, indent=2))
            return 0
        if not listing.items:
            self._echo(f"no run inputs for {project_id}; add one with `vibey inputs add`")
        for item in listing.items:
            line = f"{item.digest}  {item.kind}  {self._bytes(item.size)}  {item.name}"
            self._echo(self._clean(line))
        if listing.skipped:
            lines = "line" if listing.skipped == 1 else "lines"
            self._echo(f"skipped {listing.skipped} index {lines} that could not be read")
        return 0

    # -- helpers -------------------------------------------------------------------------------

    def _source(
        self, paste: str | None, file: Path | None, limit: int
    ) -> tuple[InputKind, str, bytes]:
        """The input's kind, name and bytes from the one source given."""
        if file is not None:
            return "file", file.name, self._read_file(file, limit)
        if paste is not None:
            # argv was decoded with surrogateescape: this is the bytes as typed.
            return "paste", PASTE_NAME, paste.encode("utf-8", "surrogateescape")
        data = self._stdin(limit + 1)
        if len(data) > limit:
            raise RunInputRefused(
                f"standard input holds more than {limit} bytes; [inputs] max_item_bytes "
                f"allows {limit}"
            )
        return "paste", PASTE_NAME, data

    @staticmethod
    def _read_file(path: Path, limit: int) -> bytes:
        """`path`'s bytes, opened without following a symlink and without blocking, refused for
        anything but a regular file and, from its size, for one over `limit`."""
        try:
            descriptor = os.open(path, _OPEN_FLAGS)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise RunInputRefused(
                    f"a symlink is never followed; give the file itself: {path}"
                ) from exc
            raise RunInputRefused(f"the file cannot be read ({exc.strerror}): {path}") from exc
        facts = os.fstat(descriptor)  # before fdopen, which itself refuses a folder by raising
        refusal = None
        if not stat.S_ISREG(facts.st_mode):
            refusal = f"not a regular file (a folder or a device): {path}"
        elif facts.st_size > limit:
            refusal = (
                f"the file is {facts.st_size} bytes; [inputs] max_item_bytes allows {limit}: {path}"
            )
        if refusal is not None:
            os.close(descriptor)
            raise RunInputRefused(refusal)
        with os.fdopen(descriptor, "rb") as handle:
            return handle.read(limit + 1)

    async def _add(
        self, limits: RunInputsSettings, project_id: UUID, kind: InputKind, name: str, data: bytes
    ) -> RunInput:
        async with self._open_service(limits) as service:
            return await service.add(project_id, kind, name, data)

    async def _listed(self, project_id: UUID) -> InputListing:
        # Listing reads no limit; the defaults stand in for them.
        async with self._open_service(RunInputsSettings()) as service:
            return await service.listed(project_id)

    @staticmethod
    def _bytes(size: int) -> str:
        return "1 byte" if size == 1 else f"{size} bytes"

    def _clean(self, text: str) -> str:
        return self._text.clean(text, LINE_CHARS)


INPUTS: Final[InputsCommandsInterface] = InputsCommands()
"""What the commands below run. Annotated with the interface so `mypy --strict` checks the class
against its declared seam."""

# -- the Typer commands, registered as `vibey inputs` in cli/main.py ---------------------------
# Module-level functions because Typer registers functions; each only hands its arguments to
# `INPUTS` and exits with what it returns.

inputs_app = typer.Typer(
    help="The pasted texts and files every BUILD run of a project is given: add, list."
)


@inputs_app.command("add")
def add_cmd(
    project_id: Annotated[UUID, typer.Argument(help="The project whose BUILD runs get it.")],
    paste: Annotated[
        str | None, typer.Option("--paste", help="The text itself, as one argument.")
    ] = None,
    paste_stdin: Annotated[
        bool, typer.Option("--paste-stdin", help="Read the text from standard input.")
    ] = False,
    file: Annotated[
        Path | None,
        typer.Option("--file", help="A regular file (not a symlink), named by its base name."),
    ] = None,
) -> None:
    """Give every BUILD run of a project one pasted text or one file (exactly one source)."""
    raise typer.Exit(INPUTS.add(project_id, paste=paste, paste_stdin=paste_stdin, file=file))


@inputs_app.command("list")
def list_cmd(
    project_id: Annotated[UUID, typer.Argument(help="The project whose inputs to list.")],
    as_json: Annotated[
        bool, typer.Option("--json", help="Print JSON for a program instead.")
    ] = False,
) -> None:
    """A project's run inputs in the order added: digest, kind, size and name, never content."""
    raise typer.Exit(INPUTS.list(project_id, as_json=as_json))
