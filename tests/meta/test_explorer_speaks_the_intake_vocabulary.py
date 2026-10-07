"""Root meta test: the explorer declares the same provenance vocabulary as the intake.

One vocabulary, checked, not two that drift.  The explorer is stdlib-only and therefore
cannot import ``vibey``; this test holds the two vocabularies equal from the single
source of truth in the intake lane.
"""

from __future__ import annotations

import pytest

from vibey.domain.intake_source import IntakeSourceKind
import vibey_explorer.candidate as vibey_explorer_candidate


def test_explorer_source_kinds_equal_the_intake_kinds() -> None:
    """Prove explorer SOURCE_KINDS and intake IntakeSourceKind carry identical values, in order.

    Lanes: gpt-oss:20b (explorer) × intake (canonical source).
    """
    explorer_kinds = vibey_explorer_candidate.SOURCE_KINDS
    intake_kinds = tuple(k.value for k in IntakeSourceKind)
    assert explorer_kinds == intake_kinds, (
        f"drift detected — explorer={explorer_kinds!r} intake={intake_kinds!r}"
    )
