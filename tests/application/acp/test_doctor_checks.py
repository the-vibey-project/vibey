# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`DoctorChecks`: every probe runs, in order; one that raises is one FAIL (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio

import pytest

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.application.acp.dto import DoctorResult
from vibey.application.acp.interfaces.doctor_checks_interface import DoctorChecksInterface
from vibey.application.acp.interfaces.doctor_probe_interface import DoctorProbeInterface


class _Probe:
    def __init__(self, name: str, *results: DoctorResult, error: Exception | None = None) -> None:
        self.name = name
        self._results = results
        self._error = error
        self.ran = 0

    async def run(self) -> tuple[DoctorResult, ...]:
        self.ran += 1
        if self._error is not None:
            raise self._error
        return self._results


def _pass(name: str) -> DoctorResult:
    return DoctorResult("PASS", name, "fine", (f"PASS {name} fine",))


async def test_a_raising_probe_is_one_fail_and_the_rest_run() -> None:
    first = _Probe("first", _pass("a"))
    broken = _Probe("broken", error=RuntimeError("the socket went away"))
    last = _Probe("last", _pass("b"), DoctorResult("WARN", "c", "hm"))

    results = await DoctorChecks((first, broken, last)).run()

    assert [r.name for r in results] == ["a", "broken", "b", "c"]
    failed = results[1]
    assert failed.mark == "FAIL"
    assert failed.detail == "RuntimeError: the socket went away"
    # The failure is said like every other check's line, so `vibey doctor` prints it too.
    assert failed.lines == (f"FAIL {'broken':<20} RuntimeError: the socket went away",)
    assert (first.ran, broken.ran, last.ran) == (1, 1, 1)


async def test_each_yields_every_probe_with_its_own_results_in_order() -> None:
    probes = (_Probe("one", _pass("a")), _Probe("two"), _Probe("three", _pass("b")))

    seen = [(probe.name, results) async for probe, results in DoctorChecks(probes).each()]

    assert seen == [("one", (_pass("a"),)), ("two", ()), ("three", (_pass("b"),))]


async def test_a_cancel_is_never_turned_into_a_fail() -> None:
    cancelled = _Probe("slow", error=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        await DoctorChecks((cancelled,)).run()


def test_passed_means_no_fail_whatever_else_was_found() -> None:
    passed = DoctorChecks.passed
    assert passed(())
    assert passed((_pass("a"), DoctorResult("WARN", "b", ""), DoctorResult("UNKNOWN", "c", "")))
    assert not passed((_pass("a"), DoctorResult("FAIL", "b", "down")))


def test_the_checks_and_a_probe_satisfy_their_interfaces() -> None:
    assert isinstance(DoctorChecks(()), DoctorChecksInterface)
    assert isinstance(_Probe("p"), DoctorProbeInterface)


async def test_a_raised_message_never_repeats_a_dsns_credentials_and_stays_one_cut_line() -> None:
    leaky = _Probe(
        "db",
        error=ValueError(
            "cannot parse postgresql://app:s3cret@db.internal:5432/vibey\nsecond line " + "x" * 400
        ),
    )
    quiet = _Probe("quiet", error=RuntimeError())

    found = await DoctorChecks((leaky, quiet)).run()

    assert "s3cret" not in found[0].detail and "app:" not in found[0].detail
    assert "postgresql://***@db.internal" in found[0].detail
    assert "second line" not in found[0].detail
    assert found[1].detail == "RuntimeError: "
    long = await DoctorChecks((_Probe("long", error=ValueError("y" * 500)),)).run()
    assert long[0].detail.endswith("...") and len(long[0].detail) < 230
