# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s local sections as doctor probes, for `vibey doctor` and `vibey acp` (SP-ACP).

The sections were written to print: the database's two sections and the hub-exposure line echo
`MARK name detail` lines, and the sabbath, supervisor and host-health sections return theirs.
`vibey acp`'s bootstrap needs the same checks as data, and must never let one write to stdout --
there, stdout is the protocol stream. So each section is wrapped as a `SectionProbe`:

- A section that **prints** runs with stdout redirected into a buffer (`contextlib.
  redirect_stdout`); a synchronous one runs on a worker thread, so a slow check never holds the
  event loop, and one printing capture at a time is allowed (`redirect_stdout` swaps the
  process's `sys.stdout`). Only `vibey doctor` captures: the editor's set reads every section
  as lines (`LocalDatabaseDoctor`'s line forms, `exposure_lines`), so under `vibey acp` nothing
  swaps `sys.stdout` at all.
- What a section printed or returned is read back line by line, in the grammar
  `doctor_output.DoctorLineParser` already reads for `--json`: `MARK name detail`, the Ollama
  line's `name MARK: detail` (`OK` as `PASS`, `SKIP` as `UNKNOWN`), the sabbath's
  `sabbath  <what>` lines, and an indented line continuing the finding before it. A line in no
  grammar is kept as `UNKNOWN`, never dropped.
- A result always agrees with the section's own verdict: a section that failed without a `FAIL`
  line has its last finding (or an added one) marked `FAIL`, and one that passed has no `FAIL`.
  So `DoctorChecks.passed` is exactly what `vibey doctor` decided before.
- Every result keeps the exact lines it came from, and `show` prints them through doctor's
  output the way the section's own call did (`captured_sync` for a printed section, `lines`
  for one that returned lines), so `vibey doctor` and `vibey doctor --json` stay byte for byte
  what they were.

`LOCAL_DOCTOR_PROBES` is the editor's set: the same sections in the order `vibey doctor` prints
them, each read as lines (no capture, and none across an await).
`vibey doctor` builds its own set from the printing helpers it names, through `for_doctor`, so
whatever stands under those names when it runs is what runs. The two database sections moved
here from `cli/main.py` (`LocalDatabaseDoctor`); `main.py` keeps their old names.

Declared by `interfaces/doctor_probes_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import threading
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import replace
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final, cast

import typer

from vibey.application.acp.dto import DoctorMark, DoctorResult
from vibey.cli.doctor_output import DoctorLineParser
from vibey.cli.gate_notices import GATE_NOTICE_DOCTOR
from vibey.cli.host_health import HOST_HEALTH
from vibey.cli.interfaces.doctor_output_interface import DoctorOutputInterface
from vibey.cli.interfaces.doctor_probes_interface import (
    LocalDatabaseDoctorInterface,
    LocalDoctorProbeInterface,
    LocalDoctorProbesInterface,
)
from vibey.cli.llm_tooling import LLM_TOOLING_SECTION
from vibey.cli.sabbath import SABBATH
from vibey.cli.serve import SERVE
from vibey.cli.supervisor import SUPERVISOR
from vibey.infrastructure.engines.local_engines import LocalEngineSettings
from vibey.infrastructure.engines.ollama_residency import OllamaResidency

if TYPE_CHECKING:
    import asyncpg

    from vibey.infrastructure.cluster_preflight import ClusterCheck
    from vibey.infrastructure.interfaces import DatabaseSecurityChecksInterface

type Gather = Callable[[], Awaitable[tuple[tuple[str, ...], bool]]]
"""Run a section: the lines it printed or returned, and whether it passed."""
type Connect = Callable[[str], Awaitable[tuple[ClusterCheck, asyncpg.Connection | None]]]

MARKS: Final[frozenset[str]] = frozenset({"PASS", "WARN", "FAIL", "UNKNOWN"})
NAMED_MARKS: Final[dict[str, DoctorMark]] = {"OK": "PASS", "WARN": "WARN", "SKIP": "UNKNOWN"}
"""The Ollama line's marks, as a doctor result's."""
SABBATH_PREFIX: Final = "sabbath"
LLM_TOOLING: Final = "llm-tooling"
"""The section that reports each detected client's LLM-facing surfaces (`cli/llm_tooling.py`);
it never fails doctor."""


class Emission(StrEnum):
    """How a section's own call put its lines out, so `show` puts them out the same way."""

    PRINTED = "printed"
    LINES = "lines"


class SectionProbe:
    """Declared by `interfaces/doctor_probes_interface.py::LocalDoctorProbeInterface`."""

    _PRINTING: ClassVar[threading.Lock] = threading.Lock()
    """One printing capture at a time: each swaps the process's `sys.stdout`."""

    def __init__(
        self,
        name: str,
        gather: Gather,
        *,
        emission: Emission,
        prefix: str | None = None,
        parser: DoctorLineParser | None = None,
    ) -> None:
        self.name = name
        self._gather = gather
        self._emission = emission
        self._prefix = prefix
        self._parser = parser or DoctorLineParser()

    @classmethod
    def printed(cls, name: str, section: Callable[[], Awaitable[bool]]) -> SectionProbe:
        """An async section that prints its lines and returns its verdict."""

        async def gather() -> tuple[tuple[str, ...], bool]:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                ok = await section()
            return cls._split(buffer.getvalue()), ok

        return cls(name, gather, emission=Emission.PRINTED)

    @classmethod
    def printed_sync(cls, name: str, section: Callable[[], bool]) -> SectionProbe:
        """A synchronous section that prints its lines; run on a worker thread."""

        def capture() -> tuple[tuple[str, ...], bool]:
            buffer = io.StringIO()
            with cls._PRINTING, contextlib.redirect_stdout(buffer):
                ok = section()
            return cls._split(buffer.getvalue()), ok

        async def gather() -> tuple[tuple[str, ...], bool]:
            return await asyncio.to_thread(capture)

        return cls(name, gather, emission=Emission.PRINTED)

    @classmethod
    def listed(
        cls, name: str, section: Callable[[], tuple[list[str], bool]], *, prefix: str | None = None
    ) -> SectionProbe:
        """A synchronous section that returns its lines; run on a worker thread."""

        async def gather() -> tuple[tuple[str, ...], bool]:
            lines, ok = await asyncio.to_thread(section)
            return tuple(lines), ok

        return cls(name, gather, emission=Emission.LINES, prefix=prefix)

    @classmethod
    def listed_async(
        cls, name: str, section: Callable[[], Awaitable[tuple[list[str], bool]]]
    ) -> SectionProbe:
        """An async section that returns its lines."""

        async def gather() -> tuple[tuple[str, ...], bool]:
            lines, ok = await section()
            return tuple(lines), ok

        return cls(name, gather, emission=Emission.LINES)

    @classmethod
    def single(
        cls,
        name: str,
        line: Callable[[], Awaitable[str]],
        *,
        when: Callable[[], bool] = lambda: True,
    ) -> SectionProbe:
        """An async section that returns one line and never fails doctor (doctor `say`s it);
        `when` false (read on a worker thread) runs nothing and says nothing."""

        async def gather() -> tuple[tuple[str, ...], bool]:
            if not await asyncio.to_thread(when):
                return (), True
            return (await line(),), True

        return cls(name, gather, emission=Emission.LINES)

    async def run(self) -> tuple[DoctorResult, ...]:
        lines, ok = await self._gather()
        return self._agreeing(self._read(lines), ok)

    def show(self, out: DoctorOutputInterface, results: Sequence[DoctorResult]) -> None:
        lines = [line for result in results for line in result.lines]
        if not lines:
            return
        if self._emission is Emission.PRINTED:
            out.captured_sync(lambda: self._print(lines))
        else:
            out.lines(lines)

    @staticmethod
    def _print(lines: Sequence[str]) -> bool:
        typer.echo("\n".join(lines))
        return True

    @staticmethod
    def _split(printed: str) -> tuple[str, ...]:
        # On "\n" only, as `typer.echo` wrote them: reprinted joined by "\n", the bytes are the
        # same, and `--json` splits them again exactly as it split the section's own output.
        lines = printed.split("\n")
        if lines[-1] == "":
            lines.pop()
        return tuple(lines)

    def _read(self, lines: Sequence[str]) -> list[DoctorResult]:
        results: list[DoctorResult] = []
        for line in lines:
            if line[:1].isspace() and results:
                before = results[-1]
                more = line.strip()
                detail = f"{before.detail}\n{more}" if before.detail else more
                results[-1] = replace(before, detail=detail, lines=(*before.lines, line))
                continue
            results.append(self._finding(line))
        return results

    def _finding(self, line: str) -> DoctorResult:
        found = self._parser.parse(line)
        if found.name is not None and found.mark in MARKS:
            return DoctorResult(cast(DoctorMark, found.mark), found.name, found.detail, (line,))
        if found.name is not None and found.mark in NAMED_MARKS:
            return DoctorResult(NAMED_MARKS[found.mark], found.name, found.detail, (line,))
        if self._prefix is not None and line.startswith(f"{self._prefix} "):
            said = line[len(self._prefix) :].strip()
            if said.startswith("FAIL:"):
                return DoctorResult("FAIL", self._prefix, said[len("FAIL:") :].strip(), (line,))
            return DoctorResult("PASS", self._prefix, said, (line,))
        return DoctorResult("UNKNOWN", self.name, line.strip(), (line,))

    def _agreeing(self, results: list[DoctorResult], ok: bool) -> tuple[DoctorResult, ...]:
        """The results, their marks held to the section's own verdict."""
        if ok:
            return tuple(replace(r, mark="WARN") if r.mark == "FAIL" else r for r in results)
        if any(result.mark == "FAIL" for result in results):
            return tuple(results)
        if results:
            return (*results[:-1], replace(results[-1], mark="FAIL"))
        return (DoctorResult("FAIL", self.name, "the check failed without saying why"),)


class LocalDatabaseDoctor:
    """`vibey doctor`'s database sections, moved here from `cli/main.py`: the ledger guard and
    password-less access (ADR-0055), and the app DSN's database opened with no password at all
    (SECURITY.md §5, sub-doctrine 10.j). Each is printed as PASS, FAIL or UNKNOWN; an install
    with no `VIBEY_PG_URL` has nothing to check and is UNKNOWN, never PASS.

    Declared by `interfaces/doctor_probes_interface.py::LocalDatabaseDoctorInterface`. The
    database modules are imported when a check runs, as before, so `vibey`'s start-up does not
    load the database driver."""

    def __init__(
        self,
        *,
        connect: Connect | None = None,
        checks: Callable[[], DatabaseSecurityChecksInterface] | None = None,
    ) -> None:
        self._connect = connect
        self._checks = checks

    async def security_lines(self) -> tuple[list[str], bool]:
        from vibey.infrastructure.cluster_preflight import DatabaseSecurityChecks, check_database

        dsn = os.environ.get("VIBEY_PG_URL", "").strip()
        if not dsn:
            return [f"UNKNOWN {'ledger-guard':<20} VIBEY_PG_URL is not set; nothing to check"], True
        connected, conn = await (self._connect or check_database)(dsn)
        if conn is None:
            return [f"FAIL {'ledger-guard':<20} {connected.detail}"], False
        try:
            found = await (self._checks or DatabaseSecurityChecks)().run(conn, dsn)
        finally:
            await conn.close()
        return [f"{check.mark} {check.name:<20} {check.detail}" for check in found], all(
            check.ok for check in found
        )

    async def security(self) -> bool:
        lines, ok = await self.security_lines()
        for line in lines:
            typer.echo(line)
        return ok

    async def passwordless_lines(self) -> tuple[list[str], bool]:
        from vibey.infrastructure.db.passwordless_reach import (
            PasswordlessReachProbe,
            ReachVerdict,
        )

        name = "db-passwordless"
        dsn = os.environ.get("VIBEY_PG_URL", "").strip()
        if not dsn:
            return [f"UNKNOWN {name:<20} VIBEY_PG_URL is not set; nothing to check"], True
        finding = await PasswordlessReachProbe().probe(dsn)
        return [f"{finding.verdict.mark} {name:<20} {finding.detail}"], (
            finding.verdict is not ReachVerdict.FAIL
        )

    async def passwordless(self) -> bool:
        lines, ok = await self.passwordless_lines()
        for line in lines:
            typer.echo(line)
        return ok


LOCAL_DATABASE_DOCTOR: Final[LocalDatabaseDoctorInterface] = LocalDatabaseDoctor()


class LocalDoctorProbes:
    """Declared by `interfaces/doctor_probes_interface.py::LocalDoctorProbesInterface`."""

    def for_doctor(
        self,
        *,
        database_security: Callable[[], Awaitable[bool]],
        passwordless_reach: Callable[[], Awaitable[bool]],
        hub_exposure: Callable[[], bool],
        sabbath: Callable[[], tuple[list[str], bool]],
        gate_notices: Callable[[], Awaitable[str]],
        supervisor: Callable[[], tuple[list[str], bool]],
        host_health: Callable[[], tuple[list[str], bool]],
        ollama_enabled: Callable[[], bool],
        llm_tooling: Callable[[], tuple[list[str], bool]] | None = None,
    ) -> tuple[LocalDoctorProbeInterface, ...]:
        return (
            SectionProbe.printed("database-security", database_security),
            SectionProbe.printed("db-passwordless", passwordless_reach),
            *self._rest(
                hub_exposure=SectionProbe.printed_sync("hub-exposure", hub_exposure),
                sabbath=sabbath,
                gate_notices=gate_notices,
                supervisor=supervisor,
                host_health=host_health,
                ollama_enabled=ollama_enabled,
            ),
            *(() if llm_tooling is None else (SectionProbe.listed(LLM_TOOLING, llm_tooling),)),
        )

    def for_editor(self) -> tuple[LocalDoctorProbeInterface, ...]:
        return (
            SectionProbe.listed_async("database-security", LOCAL_DATABASE_DOCTOR.security_lines),
            SectionProbe.listed_async("db-passwordless", LOCAL_DATABASE_DOCTOR.passwordless_lines),
            *self._rest(
                hub_exposure=SectionProbe.listed("hub-exposure", SERVE.exposure_lines),
                sabbath=SABBATH.doctor_lines,
                gate_notices=GATE_NOTICE_DOCTOR.line,
                supervisor=SUPERVISOR.doctor_lines,
                host_health=HOST_HEALTH.doctor_lines,
                ollama_enabled=self._local_engine_on,
            ),
            SectionProbe.listed(LLM_TOOLING, LLM_TOOLING_SECTION.doctor_lines),
        )

    @staticmethod
    def _rest(
        *,
        hub_exposure: SectionProbe,
        sabbath: Callable[[], tuple[list[str], bool]],
        gate_notices: Callable[[], Awaitable[str]],
        supervisor: Callable[[], tuple[list[str], bool]],
        host_health: Callable[[], tuple[list[str], bool]],
        ollama_enabled: Callable[[], bool],
    ) -> tuple[SectionProbe, ...]:
        async def residency() -> str:
            # Built when it runs, so whatever stands under the name then is what runs.
            return await OllamaResidency().line(os.environ)

        return (
            hub_exposure,
            SectionProbe.single("ollama", residency, when=ollama_enabled),
            SectionProbe.listed("sabbath", sabbath, prefix=SABBATH_PREFIX),
            SectionProbe.single("gate-notices", gate_notices),
            SectionProbe.listed("supervisor", supervisor),
            SectionProbe.listed("host-health", host_health),
        )

    @staticmethod
    def _local_engine_on() -> bool:
        """Whether any local engine is switched on, read as `vibey doctor` reads it: the
        folder's `vibey.toml` under the environment. Only then is the Ollama line said."""
        return LocalEngineSettings.from_toml(
            Path.cwd() / "vibey.toml", environ=os.environ
        ).any_enabled


LOCAL_DOCTOR: Final[LocalDoctorProbesInterface] = LocalDoctorProbes()
LOCAL_DOCTOR_PROBES: Final[tuple[LocalDoctorProbeInterface, ...]] = LOCAL_DOCTOR.for_editor()
"""Doctor's local sections as `vibey acp`'s bootstrap runs them, in `vibey doctor`'s order;
`bootstrap.build_acp_agent` wraps them in its own `DoctorChecks`."""
