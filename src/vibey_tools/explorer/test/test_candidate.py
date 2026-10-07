"""Tests for vibey_explorer.candidate — Candidate with provenance."""

from __future__ import annotations

import datetime as _dt
from typing import TYPE_CHECKING

import pytest

from vibey_explorer.candidate import SOURCE_KINDS, Candidate
from vibey_explorer.interfaces.candidate_interface import CandidateInterface

if TYPE_CHECKING:
    pass


class TestCandidateProvenance:
    """A valid candidate round-trips its fields."""

    def test_a_candidate_keeps_its_provenance(self) -> None:
        now = _dt.datetime.now(_dt.timezone.utc)
        c = Candidate(
            source_url="https://github.com/foo/bar/issues/42",
            source_kind="forge-issue",
            title="Fix crash on startup",
            asks="Patch the null dereference",
            offer="100 USDC",
            repository="foo/bar",
            found_at=now,
        )
        assert c.source_url == "https://github.com/foo/bar/issues/42"
        assert c.source_kind == "forge-issue"
        assert c.title == "Fix crash on startup"
        assert c.asks == "Patch the null dereference"
        assert c.offer == "100 USDC"
        assert c.repository == "foo/bar"
        assert c.found_at is now
        # Immutability check — frozen dataclass.
        with pytest.raises(AttributeError):
            c.source_url = "x"  # type: ignore[misc]

    def test_intake_arguments_are_the_flags_vibey_new_accepts(self) -> None:
        c = Candidate(
            source_url="https://example.org/",
            source_kind="bounty",
            title="t",
            asks="a",
        )
        assert c.intake_arguments() == ("--source-url", "https://example.org/", "--source-kind", "bounty")

    def test_intake_arguments_includes_offer_when_present(self) -> None:
        c = Candidate(
            source_url="https://example.org/",
            source_kind="bounty",
            title="t",
            asks="a",
            offer="50 DAI",
        )
        assert c.intake_arguments() == (
            "--source-url",
            "https://example.org/",
            "--source-kind",
            "bounty",
            "--offer",
            "50 DAI",
        )


class TestCandidateRefused:
    """Every invalid field raises its exact message (one parametrized case each)."""

    @pytest.mark.parametrize(
        ("url", "msg"),
        [
            ("not-a-url", "candidate source_url must be an http(s) URL: 'not-a-url'"),
            ("http://x.com with space", "candidate source_url must be an http(s) URL: 'http://x.com with space'"),
            ("https://" + "x" * 2049, "candidate source_url is longer than 2048 characters"),
        ],
    )
    def test_source_url_invalid(self, url: str, msg: str) -> None:
        with pytest.raises(ValueError, match=msg):
            Candidate(source_url=url, source_kind="other", title="t", asks="a")

    @pytest.mark.parametrize(
        ("kind", "msg"),
        [
            (
                "unexpected",
                "candidate source_kind must be one of forge-issue, help-wanted, bounty, proposal, other: 'unexpected'",
            ),
        ],
    )
    def test_source_kind_invalid(self, kind: str, msg: str) -> None:
        with pytest.raises(ValueError, match=msg):
            Candidate(source_url="https://example.org/", source_kind=kind, title="t", asks="a")

    @pytest.mark.parametrize(
        ("title", "msg"),
        [
            ("   ", "candidate title is empty"),
            ("x" * 301, "candidate title is longer than 300 characters"),
        ],
    )
    def test_title_invalid(self, title: str, msg: str) -> None:
        with pytest.raises(ValueError, match=msg):
            Candidate(source_url="https://example.org/", source_kind="other", title=title, asks="a")

    def test_asks_too_long(self) -> None:
        with pytest.raises(ValueError, match="candidate asks is longer than 2000 characters"):
            Candidate(
                source_url="https://example.org/",
                source_kind="other",
                title="t",
                asks="a" * 2001,
            )

    def test_offer_too_long(self) -> None:
        with pytest.raises(ValueError, match="candidate offer is longer than 500 characters"):
            Candidate(
                source_url="https://example.org/",
                source_kind="other",
                title="t",
                asks="a",
                offer="x" * 501,
            )

    @pytest.mark.parametrize(
        ("repo", "msg"),
        [
            ("/foo/bar", "candidate repository must be a forge namespace such as 'owner/name': '/foo/bar'"),
            ("foo/bar/", "candidate repository must be a forge namespace such as 'owner/name': 'foo/bar/'"),
            ("foo//bar", "candidate repository must be a forge namespace such as 'owner/name': 'foo//bar'"),
            ("foo bar/baz", "candidate repository must be a forge namespace such as 'owner/name': 'foo bar/baz'"),
        ],
    )
    def test_repository_invalid(self, repo: str, msg: str) -> None:
        with pytest.raises(ValueError, match=msg):
            Candidate(
                source_url="https://example.org/",
                source_kind="other",
                title="t",
                asks="a",
                repository=repo,
            )

    def test_found_at_naive(self) -> None:
        naive = _dt.datetime.now()
        with pytest.raises(ValueError, match="candidate found_at must be timezone-aware"):
            Candidate(
                source_url="https://example.org/",
                source_kind="other",
                title="t",
                asks="a",
                found_at=naive,
            )


class TestCandidateInterface:
    """The concrete class satisfies the Protocol."""

    def test_the_candidate_satisfies_its_interface(self) -> None:
        c = Candidate(
            source_url="https://example.org/",
            source_kind="other",
            title="t",
            asks="a",
        )
        assert isinstance(c, CandidateInterface)

    def test_SOURCE_KINDS_order_matches(self) -> None:
        assert SOURCE_KINDS == ("forge-issue", "help-wanted", "bounty", "proposal", "other")
