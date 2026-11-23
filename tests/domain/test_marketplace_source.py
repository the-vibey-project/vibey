# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which marketplace sources vibey fetches, and how (SP-LOOPS Task 7).

git is handed only an `https://`, `ssh://` or `git://` URL or a `user@host:path`; a plain absolute
folder is copied without git; everything git could read as a transport helper, a local
repository, an option or a path relative to the folder vibey runs in is refused.
"""

from __future__ import annotations

import pytest

from vibey.domain.interfaces.marketplace_source_interface import MarketplaceSourceRuleInterface
from vibey.domain.marketplace_source import (
    MARKETPLACE_SOURCE_RULE,
    MarketplaceSource,
    MarketplaceSourceError,
    MarketplaceSourceRule,
)


def test_the_rule_satisfies_its_interface() -> None:
    assert isinstance(MARKETPLACE_SOURCE_RULE, MarketplaceSourceRuleInterface)


@pytest.mark.parametrize(
    ("source", "protocol"),
    [
        ("https://example.test/acme/marketplace.git", "https"),
        ("https://git.example.test:8443/acme", "https"),
        ("ssh://git@example.test/acme/marketplace.git", "ssh"),
        ("ssh://example.test:2222/acme.git", "ssh"),
        ("git://example.test/acme.git", "git"),
        ("https://[::1]:8443/acme.git", "https"),
        ("git@example.test:acme/marketplace.git", "ssh"),
        ("deploy-1@git.example.test:team/plugins", "ssh"),
    ],
)
def test_a_remote_source_is_fetched_with_git_over_its_protocol(source: str, protocol: str) -> None:
    assert MarketplaceSourceRule().classify(source) == MarketplaceSource(source, "git", protocol)


@pytest.mark.parametrize("source", ["/Users/me/plugins", "/srv/marketplaces/acme/"])
def test_an_absolute_folder_is_copied_without_git(source: str) -> None:
    assert MarketplaceSourceRule().classify(source) == MarketplaceSource(source, "local", "local")


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("ext::sh -c touch% /tmp/pwned", "transport helper"),
        ("fd::17", "transport helper"),
        ("git::https://example.test/x", "transport helper"),
        ("file:///srv/repo.git", "is not a source vibey fetches"),
        ("http://example.test/acme.git", "is not a source vibey fetches"),
        ("ftp://example.test/acme.git", "is not a source vibey fetches"),
        ("-uhelp", "must not start with '-'"),
        ("--upload-pack=touch /tmp/x", "must not start with '-'"),
        ("acme/marketplace", "is not a source vibey fetches"),
        ("./plugins", "is not a source vibey fetches"),
        ("../plugins", "is not a source vibey fetches"),
        ("~/plugins", "is not a source vibey fetches"),
        ("/srv/../etc", "'..'"),
        ("https://user:token@example.test/acme.git", "credentials"),
        ("https://token@example.test/acme.git", "credentials"),
        ("https:///acme.git", "a host"),
        ("https://exa mple.test/acme.git", "is not a source vibey fetches"),
        ("https://[::1/x", "a host"),
        ("ssh://-oProxyCommand=x/acme", "a host"),
        ("git@-oProxyCommand=x:acme", "is not a source vibey fetches"),
        ("git@example.test:-acme", "is not a source vibey fetches"),
        ("example.test:acme.git", "is not a source vibey fetches"),
        ("", "non-empty"),
        ("https://example.test/\u001b[2Jx", "control characters"),
    ],
)
def test_a_source_git_could_misread_is_refused_with_the_reason(source: str, reason: str) -> None:
    with pytest.raises(MarketplaceSourceError, match=reason):
        MarketplaceSourceRule().classify(source)


@pytest.mark.parametrize(
    "ref", ["main", "v1.2.0", "release/2026-11", "a" * 40, "0123456789abcdef" * 4, "v1_2"]
)
def test_a_plain_ref_is_kept(ref: str) -> None:
    assert MarketplaceSourceRule().check_ref(ref) == ref


@pytest.mark.parametrize(
    "ref",
    [
        "-x",
        "--upload-pack=x",
        "a..b",
        "refs/heads/x:refs/heads/y",
        "+main",
        "main/",
        "/main",
        "a//b",
        "main.lock",
        "a b",
        "a" * 256,
        "",
        "@{-1}",
        "x^",
        "x~1",
    ],
)
def test_a_ref_that_is_not_a_plain_name_is_refused(ref: str) -> None:
    with pytest.raises(MarketplaceSourceError, match="ref"):
        MarketplaceSourceRule().check_ref(ref)


@pytest.mark.parametrize(
    ("ref", "pinned"),
    [("a" * 40, True), ("0" * 64, True), ("A" * 40, False), ("main", False), ("a" * 39, False)],
)
def test_a_full_commit_id_is_recognised(ref: str, pinned: bool) -> None:
    assert MarketplaceSourceRule().is_commit(ref) is pinned
