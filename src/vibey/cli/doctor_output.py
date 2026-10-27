# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where `vibey doctor` puts what it finds: the lines it has always printed, or one document.

`doctor` printed at least five kinds of line, and none of them was data: an engine's preflight,
`MARK name detail` from the sabbath, supervisor, host-health and database sections, the Ollama
line, the PostgreSQL line, and free `note:` lines. `--json` (#1686) must not read those back out
of text with a pattern that could match the wrong thing and report a pass nobody observed
(sub-doctrine 12.e). So each emission carries the exact text it has always had and, where the
caller held the structure (an engine's fields, a conformance check, a PostgreSQL status, a
cluster check), the structure itself. `TextDoctorOutput` prints the text and nothing else, so the
text form is unchanged. `JsonDoctorOutput` keeps the structure.

Only the sections that already return or print text in the `MARK name detail` grammar are read
back, by one parser over that one grammar; a line it does not recognise is kept verbatim as a
finding with no mark, never dropped. A line that starts with whitespace continues the finding
before it. `--json` changes the output only, never what runs or the exit code.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Awaitable, Callable, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass, replace
from typing import Any

import typer

from vibey.cli.interfaces.doctor_output_interface import DoctorOutputInterface
from vibey.infrastructure.postgres import PostgresStatus

__all__ = [
    "DoctorFinding",
    "DoctorFormat",
    "DoctorLineParser",
    "JsonDoctorOutput",
    "TextDoctorOutput",
]


@dataclass(frozen=True)
class DoctorFinding:
    """One check's result. `line` is set only when the text fit no grammar, and is then the
    verbatim line (with `name` and `mark` None)."""

    name: str | None
    mark: str | None
    detail: str
    line: str | None = None

    def document(self) -> dict[str, object]:
        found: dict[str, object] = {"name": self.name, "mark": self.mark, "detail": self.detail}
        if self.line is not None:
            found["line"] = self.line
        return found


class DoctorLineParser:
    """Reads a section's line in the one grammar those sections share."""

    #: `MARK name detail`, the grammar of the sabbath, supervisor, host-health, database,
    #: hub-exposure and gate-notice sections.
    MARKED = re.compile(r"(PASS|WARN|FAIL|UNKNOWN)\s+(\S+)\s*(.*)")
    #: `name MARK: detail`, the Ollama residency line (`OK` and `SKIP` as well).
    NAMED = re.compile(r"(\S+)\s+(WARN|OK|SKIP):\s*(.*)")

    def parse(self, text: str) -> DoctorFinding:
        marked = self.MARKED.fullmatch(text)
        if marked:
            return DoctorFinding(marked.group(2), marked.group(1), marked.group(3).strip())
        named = self.NAMED.fullmatch(text)
        if named:
            return DoctorFinding(named.group(1), named.group(2), named.group(3).strip())
        return DoctorFinding(None, None, text, line=text)


class DoctorFormat:
    """The text of the lines that are built from fields, in the one place that builds them."""

    @staticmethod
    def engine_line(engine_id: str, installed: bool, version: str | None, auth_ok: bool) -> str:
        status = "installed" if installed else "NOT INSTALLED"
        auth = "auth OK" if auth_ok else "auth FAIL"
        return f"{engine_id:<16} {status:<14} v{version or '?':<10} {auth}"

    @staticmethod
    def conformance_line(name: str, ok: bool, detail: str) -> str:
        mark = "PASS" if ok else "FAIL"
        return f"  {mark} {name}{f' — {detail}' if detail else ''}"

    @staticmethod
    def postgres_state(status: PostgresStatus) -> str:
        if not status.installed:
            return "NOT INSTALLED"
        if not status.supported:
            return "UNSUPPORTED"
        if not status.running:
            return "NOT READY"
        return "READY"

    @classmethod
    def postgres_line(cls, status: PostgresStatus) -> str:
        version = f"v{status.version}" if status.version is not None else "v?"
        return f"postgresql      {cls.postgres_state(status):<14} {version:<8} {status.detail}"

    @staticmethod
    def cluster_line(mark: str, name: str, detail: str) -> str:
        return f"{mark} {name:<20} {detail}"


class TextDoctorOutput(DoctorOutputInterface):
    """Prints exactly what `vibey doctor` has always printed."""

    def note(self, text: str) -> None:
        typer.echo(f"note: {text}")

    def error(self, text: str) -> None:
        typer.echo(text)

    def say(self, text: str) -> None:
        typer.echo(text)

    def lines(self, lines: Sequence[str]) -> None:
        for line in lines:
            typer.echo(line)

    def engine(self, engine_id: str, installed: bool, version: str | None, auth_ok: bool) -> None:
        typer.echo(DoctorFormat.engine_line(engine_id, installed, version, auth_ok))

    def engine_detail(self, detail: str) -> None:
        typer.echo(f"  detail: {detail}")

    def conformance(self, name: str, ok: bool, detail: str) -> None:
        typer.echo(DoctorFormat.conformance_line(name, ok, detail))

    def recorded(self, engine_id: str, kind: str) -> None:
        typer.echo(f"  recorded {kind} for {engine_id}")

    def postgres(self, status: PostgresStatus) -> None:
        typer.echo(DoctorFormat.postgres_line(status))

    def postgres_detail(self, detail: str) -> None:
        typer.echo(f"  detail: {detail}")

    def cluster_check(self, mark: str, name: str, detail: str) -> None:
        typer.echo(DoctorFormat.cluster_line(mark, name, detail))

    async def captured(self, run: Callable[[], Awaitable[bool]]) -> bool:
        return await run()

    def captured_sync(self, run: Callable[[], bool]) -> bool:
        return run()

    def finish(self, ok: bool) -> None:
        return None


class JsonDoctorOutput(DoctorOutputInterface):
    """Keeps what `doctor` finds and prints it as one document at the end.

    stdout carries only that document. Notes and refusals go to stderr, so a program reading
    stdout never has to skip a line.
    """

    def __init__(self, *, cluster: bool = False, parser: DoctorLineParser | None = None) -> None:
        self._cluster = cluster
        self._parser = parser or DoctorLineParser()
        self._findings: list[DoctorFinding] = []
        self._engines: list[dict[str, Any]] = []
        self._postgres: dict[str, object] | None = None
        self._notes: list[str] = []

    def note(self, text: str) -> None:
        self._notes.append(text)
        typer.echo(f"note: {text}", err=True)

    def error(self, text: str) -> None:
        typer.echo(text, err=True)

    def say(self, text: str) -> None:
        self._add(text)

    def lines(self, lines: Sequence[str]) -> None:
        for line in lines:
            self._add(line)

    def _add(self, text: str) -> None:
        previous = self._findings[-1] if self._findings else None
        if text[:1].isspace() and previous is not None and previous.line is None:
            joined = f"{previous.detail}\n{text.strip()}" if previous.detail else text.strip()
            self._findings[-1] = replace(previous, detail=joined)
        else:
            self._findings.append(self._parser.parse(text))

    def engine(self, engine_id: str, installed: bool, version: str | None, auth_ok: bool) -> None:
        self._engines.append(
            {
                "engine_id": engine_id,
                "installed": installed,
                "version": version,
                "auth_ok": auth_ok,
                "detail": None,
                "conformance": [],
                "recorded": None,
            }
        )

    def engine_detail(self, detail: str) -> None:
        self._engines[-1]["detail"] = detail

    def conformance(self, name: str, ok: bool, detail: str) -> None:
        self._engines[-1]["conformance"].append({"name": name, "ok": ok, "detail": detail})

    def recorded(self, engine_id: str, kind: str) -> None:
        self._engines[-1]["recorded"] = kind

    def postgres(self, status: PostgresStatus) -> None:
        self._postgres = {
            "state": DoctorFormat.postgres_state(status),
            "version": str(status.version) if status.version is not None else None,
            "ready": status.ready,
            "detail": status.detail,
        }

    def postgres_detail(self, detail: str) -> None:
        return None  # already the `detail` of the postgresql entry

    def cluster_check(self, mark: str, name: str, detail: str) -> None:
        self._findings.append(DoctorFinding(name, mark, detail))

    async def captured(self, run: Callable[[], Awaitable[bool]]) -> bool:
        printed = io.StringIO()
        with redirect_stdout(printed):
            ok = await run()
        self.lines(printed.getvalue().splitlines())
        return ok

    def captured_sync(self, run: Callable[[], bool]) -> bool:
        printed = io.StringIO()
        with redirect_stdout(printed):
            ok = run()
        self.lines(printed.getvalue().splitlines())
        return ok

    def finish(self, ok: bool) -> None:
        document: dict[str, object] = {
            "ok": ok,
            "mode": "cluster" if self._cluster else "local",
            "checks": [finding.document() for finding in self._findings],
        }
        if not self._cluster:
            document["engines"] = self._engines
            document["postgresql"] = self._postgres
        document["notes"] = self._notes
        typer.echo(json.dumps(document, indent=2))
