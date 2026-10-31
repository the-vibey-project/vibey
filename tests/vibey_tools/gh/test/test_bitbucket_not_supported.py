import dataclasses

import pytest

from vibey_gh.forge import ForgeKind, NotSupported


def test_not_supported_bitbucket_names_problem():
    record = NotSupported(ForgeKind.BITBUCKET, "example_verb", "example_reason")
    assert record.problem == "bitbucket does not support example_verb: example_reason"
    # no direct struct type to check, just ensure record is a dataclass instance
    # The dataclass is frozen, so setting a field should raise FrozenInstanceError.
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.verb = "other"
