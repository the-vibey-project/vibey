# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The start-up sweep of the session registry (SP-LOOPS Phase 6, Task 7; R4).

A worker that crashed or was killed never revoked its sessions, so their entries stay in the
hub's registry until their expiry, refused from then on, and are the next worker's to remove.
The sweep removes only expired entries, never a live one, never an unreadable one (it is named,
and kept), and is idempotent under replay.

Over a fake registry; the real one has its own tests. Module-level test functions rather than a
class with an interface beside it (ADR-0016)."""

from __future__ import annotations

from uuid import UUID

import pytest

from vibey.application.dto import (
    SessionRegistryEntry,
    SessionRegistryListing,
    SessionSweepReport,
)
from vibey.application.interfaces import SessionRegistrySweepInterface
from vibey.application.session_registry_sweep import SessionRegistrySweep
from vibey.domain.session_principal import SessionPrincipal

NOW = 1_800_000_000.0


def _principal(n: int, expires_at: float) -> SessionPrincipal:
    run = UUID(int=n)
    return SessionPrincipal(name=f"session:{run}", run_id=run, expires_at=expires_at)


def _entry(n: int, expires_at: float) -> SessionRegistryEntry:
    return SessionRegistryEntry(digest=f"{n:064x}", principal=_principal(n, expires_at))


class Registry:
    def __init__(
        self,
        *entries: SessionRegistryEntry,
        unreadable: tuple[str, ...] = (),
        fails: Exception | None = None,
    ) -> None:
        self.held = {entry.digest: entry for entry in entries}
        self.unreadable = unreadable
        self.fails = fails
        self.forgotten: list[str] = []

    def entries(self) -> SessionRegistryListing:
        if self.fails is not None:
            raise self.fails
        return SessionRegistryListing(
            entries=tuple(self.held[d] for d in sorted(self.held)), unreadable=self.unreadable
        )

    def forget(self, digest: str) -> bool:
        self.forgotten.append(digest)
        return self.held.pop(digest, None) is not None


def test_the_sweep_meets_its_seam() -> None:
    sweep = SessionRegistrySweep(Registry(), clock=lambda: NOW)
    assert isinstance(sweep, SessionRegistrySweepInterface)


def test_expired_entries_go_and_live_ones_stay() -> None:
    gone, at_expiry, live = _entry(1, NOW - 60), _entry(2, NOW), _entry(3, NOW + 0.001)
    registry = Registry(gone, at_expiry, live)

    report = SessionRegistrySweep(registry, clock=lambda: NOW).sweep()

    # Expiry is exclusive: at the expiry instant the hub refuses already, so it goes too.
    assert report == SessionSweepReport(
        removed=(gone.principal.name, at_expiry.principal.name), kept=1, refused=()
    )
    assert list(registry.held) == [live.digest]
    assert sorted(registry.forgotten) == sorted([gone.digest, at_expiry.digest])


def test_an_unreadable_entry_is_named_and_never_removed() -> None:
    reason = "/hub/sessions/" + "1" * 64 + ".json is open to other accounts; refusing to use it"
    registry = Registry(_entry(2, NOW - 1), unreadable=(reason,))

    report = SessionRegistrySweep(registry, clock=lambda: NOW).sweep()

    assert report.refused == (reason,)
    assert registry.forgotten == [f"{2:064x}"]  # only the entry it could read and judge


def test_the_sweep_is_idempotent_under_replay() -> None:
    registry = Registry(_entry(1, NOW - 1), _entry(2, NOW + 3600))
    sweep = SessionRegistrySweep(registry, clock=lambda: NOW)

    first = sweep.sweep()
    second = sweep.sweep()

    assert len(first.removed) == 1
    assert second == SessionSweepReport(removed=(), kept=1, refused=())


def test_an_entry_another_sweep_removed_first_is_not_counted_twice() -> None:
    """Two workers starting at once: whoever forgets second removed nothing."""
    entry = _entry(1, NOW - 1)
    registry = Registry(entry)
    original = registry.forget

    def raced(digest: str) -> bool:
        original(digest)
        return False

    registry.forget = raced  # type: ignore[method-assign]

    report = SessionRegistrySweep(registry, clock=lambda: NOW).sweep()

    assert report == SessionSweepReport(removed=(), kept=0, refused=())


def test_a_registry_that_cannot_be_listed_is_not_swept_and_says_so() -> None:
    registry = Registry(fails=PermissionError("/hub/sessions is open to other accounts"))

    with pytest.raises(PermissionError, match="open to other accounts"):
        SessionRegistrySweep(registry, clock=lambda: NOW).sweep()
    assert registry.forgotten == []


@pytest.mark.parametrize("now", [float("inf"), float("nan")])
def test_a_clock_that_is_not_finite_sweeps_nothing(now: float) -> None:
    """An infinite now would read every live session as expired."""
    registry = Registry(_entry(1, NOW - 1), _entry(2, NOW + 3600))

    with pytest.raises(ValueError, match="finite"):
        SessionRegistrySweep(registry, clock=lambda: now).sweep()
    assert registry.forgotten == []
