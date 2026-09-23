# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The forge‑adapter foundation: `NotSupported`, and the seams of the two HTTP transports."""

from __future__ import annotations

import dataclasses
import urllib.request

import pytest

from vibey_gh.forge import ForgeKind, NotSupported
from vibey_gh.forgejo_transport import ForgejoTransport
from vibey_gh.gitlab_transport import GitLabTransport
from vibey_gh.interfaces import (
    ForgejoTransportInterface,
    GitLabTransportInterface,
    NotSupportedInterface,
)


class _HttpResponse:
    def __init__(self, payload: str) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload.encode()


def test_not_supported_names_the_forge_the_verb_and_the_reason():
    record = NotSupported(ForgeKind.GITLAB, "subject_facts", "numbers collide")
    assert record.problem == "gitlab does not support subject_facts: numbers collide"
    assert isinstance(record, NotSupportedInterface)
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.verb = "other"


@pytest.mark.parametrize(
    "transport_type,body",
    [
        (ForgejoTransport, ""),
        (ForgejoTransport, "  \n"),
        (GitLabTransport, ""),
        (GitLabTransport, "  \n"),
    ],
)
def test_transports_read_an_empty_success_as_an_empty_object(transport_type, body):
    def opener(request, timeout):
        return _HttpResponse(body)

    answer = dataclasses.replace(
        transport_type(opener=opener),
    ).survey(["repos/o/r/branches/x", "DELETE", ""])
    assert answer == ({}, "")


# The two tests the lane's own note recorded as "omitted for brevity to fit scope". Both are
# dictated by the spec down to their values, so nothing here is invented -- writing them is
# transcription, and leaving them out is what left GitLab's empty-body path uncovered.


@pytest.mark.parametrize("transport_type", [ForgejoTransport, GitLabTransport])
def test_transports_pass_their_timeout_to_the_opener(transport_type):
    seen: list[float] = []

    def opener(request, timeout):
        seen.append(timeout)
        return _HttpResponse("[]")

    assert transport_type(opener=opener).survey(["one"]) == ([], "")
    assert transport_type(timeout=5.0, opener=opener).survey(["one"]) == ([], "")
    assert seen == [30.0, 5.0]
    assert transport_type().timeout == 30.0


def test_transports_compare_equal_whatever_their_opener():
    def f(request, timeout):
        return _HttpResponse("[]")

    # `compare=False` on the field: two transports differing only in opener are the same
    # transport, so a selector's equality check is unaffected by how a test substitutes.
    assert ForgejoTransport(opener=f) == ForgejoTransport()
    assert GitLabTransport(opener=f) == GitLabTransport()
    # `repr=False`: the opener never shows up in a repr a person reads.
    assert "opener" not in repr(ForgejoTransport(opener=f))
    assert "opener" not in repr(GitLabTransport(opener=f))
    assert ForgejoTransport().opener is urllib.request.urlopen
    assert GitLabTransport().opener is urllib.request.urlopen
    assert isinstance(ForgejoTransport(), ForgejoTransportInterface)
    assert isinstance(GitLabTransport(), GitLabTransportInterface)


def test_every_name_the_interfaces_package_exports_can_be_imported():
    """`__all__` is a promise, and this branch briefly broke one.

    Adding `NotSupportedInterface` to the import block dropped `ProtectedRefInterface` from
    it while leaving the name in `__all__`, so `from vibey_gh.interfaces import
    ProtectedRefInterface` raised ImportError and `import *` broke with it. The tenant's
    2512 tests all passed: none of them imports that name from the package, which is exactly
    the gap `__all__` exists to cover and nothing was checking.
    """
    import vibey_gh.interfaces as package

    missing = [name for name in package.__all__ if not hasattr(package, name)]
    assert missing == [], f"__all__ promises names the package does not import: {missing}"
