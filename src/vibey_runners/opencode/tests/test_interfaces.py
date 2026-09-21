# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every concrete class ships with its interface beside it (ADR-0016)."""

from opencodeloop.application.interfaces import (
    ProcessInterface,
    RunnerInterface,
    RunStoreInterface,
)
from opencodeloop.domain.interfaces import (
    RunIdInterface,
    RunResultInterface,
    RunStatusInterface,
)
from opencodeloop.infrastructure.interfaces import (
    FileRunStoreInterface,
    OpenCodeProcessInterface,
)

_APPLICATION = (ProcessInterface, RunnerInterface, RunStoreInterface)
_DOMAIN = (RunIdInterface, RunResultInterface, RunStatusInterface)
_INFRASTRUCTURE = (OpenCodeProcessInterface, FileRunStoreInterface)


def test_every_interface_is_a_protocol() -> None:
    for interface in (*_APPLICATION, *_DOMAIN, *_INFRASTRUCTURE):
        assert getattr(interface, "_is_protocol", False) is True


def test_infrastructure_mirrors_extend_their_application_port() -> None:
    assert ProcessInterface in OpenCodeProcessInterface.__mro__
    assert RunStoreInterface in FileRunStoreInterface.__mro__
