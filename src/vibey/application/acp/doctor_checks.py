# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s checks as one sequence `vibey doctor` and `vibey acp` both run (SP-ACP).

The probes run one at a time, in order: several of doctor's sections print, and their probes
capture stdout to read what they printed, which only one at a time may do. A probe that raises
is one `FAIL` named after it -- said in the same `MARK name detail` grammar as every other
line, so `vibey doctor` prints it too -- and the rest still run. Its detail is the exception's
type and a cleaned first line of its message: credentials in a URL are never repeated. Declared by
`interfaces/doctor_checks_interface.py`.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from collections.abc import AsyncGenerator, Sequence
from typing import Final

from vibey.application.acp.dto import DoctorResult
from vibey.application.acp.interfaces.doctor_probe_interface import DoctorProbeInterface

_LOG: Final = logging.getLogger(__name__)
CREDENTIALS: Final = re.compile(r"(?P<scheme>[A-Za-z][\w+.-]*://)[^\s/@]+@")
"""A URL's `user[:password]@` part, as a database DSN carries it."""
DETAIL_CHARS: Final = 200
"""The most of a raised check's message a finding carries."""


class DoctorChecks[P: DoctorProbeInterface]:
    """Declared by `interfaces/doctor_checks_interface.py::DoctorChecksInterface`."""

    def __init__(self, probes: Sequence[P]) -> None:
        self._probes = tuple(probes)

    async def each(self) -> AsyncGenerator[tuple[P, tuple[DoctorResult, ...]]]:
        for probe in self._probes:
            try:
                results = await probe.run()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                _LOG.warning("the doctor check %s raised", probe.name, exc_info=exc)
                detail = f"{type(exc).__name__}: {self.cleaned(str(exc))}"
                results = (
                    DoctorResult("FAIL", probe.name, detail, (f"FAIL {probe.name:<20} {detail}",)),
                )
            yield probe, results

    async def run(self) -> tuple[DoctorResult, ...]:
        found: list[DoctorResult] = []
        async for _, results in self.each():
            found.extend(results)
        return tuple(found)

    @staticmethod
    def cleaned(message: str, *, limit: int = DETAIL_CHARS) -> str:
        """Machine text as a finding says it: its first line, every other control, format or
        separator character a space, any URL's credentials replaced by `***` (a DSN in an
        error must not reach a screen or an editor), cut to `limit` characters."""
        first = message.strip().splitlines()[0] if message.strip() else ""
        first = "".join(
            " " if unicodedata.category(char)[0] in "CZ" and char != " " else char for char in first
        )
        first = CREDENTIALS.sub(r"\g<scheme>***@", first)
        return first if len(first) <= limit else f"{first[: limit - 3]}..."

    @staticmethod
    def passed(results: Sequence[DoctorResult]) -> bool:
        return all(result.mark != "FAIL" for result in results)
