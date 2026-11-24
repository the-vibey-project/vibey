# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `LoopCapabilitiesSnapshotted` payload: the snapshot a run was given, as a digest, the run's
id and counts -- never a server's command, URL or environment (SP-LOOPS Phase 4, Task 7).

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

import inspect
from uuid import UUID

import pytest

from vibey.domain.interfaces.loop_capabilities_interface import (
    LoopCapabilitiesRecordInterface,
)
from vibey.domain.loop_capabilities import LOOP_CAPABILITIES_RECORD, LoopCapabilitiesRecord

RUN_ID = UUID("6b1f9c2e-0d3a-4c55-9a8e-2f7b1c3d4e5f")
DIGEST = "sha256:" + "0f" * 32
COUNTS: dict[str, int] = {
    "plugins": 3,
    "skills": 7,
    "skills_skipped": 1,
    "mcp_local": 2,
    "mcp_remote": 1,
    "notices": 4,
}


def test_the_record_satisfies_its_interface() -> None:
    assert isinstance(LOOP_CAPABILITIES_RECORD, LoopCapabilitiesRecordInterface)
    assert isinstance(LOOP_CAPABILITIES_RECORD, LoopCapabilitiesRecord)


def test_the_payload_holds_only_the_digest_ids_and_counts() -> None:
    payload = LOOP_CAPABILITIES_RECORD.payload(run_id=RUN_ID, digest=DIGEST, **COUNTS)

    assert payload == {
        "run_id": str(RUN_ID),
        "digest": DIGEST,
        "plugins": 3,
        "skills": 7,
        "skills_skipped": 1,
        "mcp_local": 2,
        "mcp_remote": 1,
        "project_notices": 4,
    }
    # A server's command, URL and environment are never passed in, so no value can carry
    # them: the signature names only the run, the digest and the counts.
    parameters = set(inspect.signature(LOOP_CAPABILITIES_RECORD.payload).parameters)
    assert parameters == {"run_id", "digest", *COUNTS}
    assert not parameters & {"command", "url", "env", "env_allow", "args", "headers"}


def test_zero_counts_are_a_record_of_an_empty_snapshot() -> None:
    zeros = dict.fromkeys(COUNTS, 0)
    payload = LOOP_CAPABILITIES_RECORD.payload(run_id=RUN_ID, digest=DIGEST, **zeros)
    assert [payload[key] for key in payload if key not in {"run_id", "digest"}] == [0] * 6


_MALFORMED_DIGESTS = (
    "",
    "0f" * 32,
    "sha256:" + "0f" * 31,
    "sha256:" + "0f" * 33,
    "sha256:" + "0F" * 32,
    "sha512:" + "0f" * 32,
    "sha256:" + "0f" * 32 + "\n",
    " sha256:" + "0f" * 32,
)


@pytest.mark.parametrize(
    ("digest", "counts", "names"),
    [(digest, COUNTS, "digest") for digest in _MALFORMED_DIGESTS]
    + [(DIGEST, {**COUNTS, name: -1}, name) for name in sorted(COUNTS)],
)
def test_a_malformed_digest_or_negative_count_is_refused(
    digest: str, counts: dict[str, int], names: str
) -> None:
    with pytest.raises(ValueError, match=names):
        LOOP_CAPABILITIES_RECORD.payload(run_id=RUN_ID, digest=digest, **counts)


@pytest.mark.parametrize("name", sorted(COUNTS))
@pytest.mark.parametrize("value", [True, False])
def test_a_boolean_is_not_a_count(name: str, value: bool) -> None:
    counts = {**COUNTS, name: value}
    with pytest.raises(ValueError, match=name):
        LOOP_CAPABILITIES_RECORD.payload(run_id=RUN_ID, digest=DIGEST, **counts)
