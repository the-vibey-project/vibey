# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Bitbucket adapter against a real repository, read-only (#1621, part of #298).

Every other Bitbucket test answers from a fixture, so the suite can be green against a wire
the real service never speaks. These tests close that gap and nothing more: they are marked
`network` (so `conftest` skips them unless `VIBEY_GH_NETWORK_TESTS=1`), and they skip again,
naming the variable, unless a repository and a token are supplied. They call read verbs only
and never mutate the repository.

A run that skipped is not evidence (sub-doctrine 10.f). The recorded passing run is the
operator's to make:

    VIBEY_GH_NETWORK_TESTS=1 VIBEY_GH_BITBUCKET_TOKEN=... \\
    VIBEY_GH_BITBUCKET_REPOSITORY=workspace/repo-slug \\
    python -m pytest test/test_forge_bitbucket_live.py -m network -rs -q

The token's value is never printed or asserted on; failures carry the problem string only.
"""

from __future__ import annotations

import re

import pytest

from vibey_gh.config import GhConfig, PlatformConfig
from vibey_gh.forge_bitbucket import BitbucketForge
from vibey_gh.forge_selector import ForgeSelector

TOKEN_ENV = "VIBEY_GH_BITBUCKET_TOKEN_ENV"
DEFAULT_TOKEN_ENV = "VIBEY_GH_BITBUCKET_TOKEN"
REPOSITORY_ENV = "VIBEY_GH_BITBUCKET_REPOSITORY"
HEAD_SHA = re.compile(r"[0-9a-f]{40}")


class LiveBitbucket:
    """Builds the adapter the way a user's `.vibey-gh.toml` does: through the selector."""

    @staticmethod
    def forge(tmp_path, environ):
        """The adapter for the configured repository, or a skip naming what is missing."""
        token_env = environ.get(TOKEN_ENV) or DEFAULT_TOKEN_ENV
        repository = environ.get(REPOSITORY_ENV, "")
        if not repository:
            pytest.skip(f"set {REPOSITORY_ENV}=workspace/repo-slug to run against Bitbucket")
        if not environ.get(token_env):
            pytest.skip(f"set {token_env} to a Bitbucket access token to run against Bitbucket")
        cfg = GhConfig(
            root=tmp_path,
            platform=PlatformConfig(kind="bitbucket", repository=repository, token_env=token_env),
        )
        forge = ForgeSelector().select(cfg)
        assert isinstance(forge, BitbucketForge)
        return forge


@pytest.fixture
def live_forge(tmp_path):
    import os

    return LiveBitbucket.forge(tmp_path, os.environ)


@pytest.mark.network
def test_the_open_change_request_heads_answer_without_a_problem(live_forge):
    heads, problem = live_forge.open_change_request_heads(limit=5)
    assert problem == ""
    assert isinstance(heads, frozenset)


@pytest.mark.network
def test_the_protected_refs_answer_without_a_problem(live_forge):
    refs, problem = live_forge.get_protected_refs()
    assert problem == ""
    assert isinstance(refs, frozenset)


@pytest.mark.network
def test_a_change_request_read_back_by_number_carries_its_head_commit(live_forge):
    listed, problem = live_forge.list_artifacts("change-request", limit=1)
    assert problem == ""
    if not listed:
        pytest.skip("the repository has no change request to read back")
    number = int(listed[0]["id"])
    change, problem = live_forge.get_change_request(number)
    assert problem == ""
    assert change is not None
    assert HEAD_SHA.fullmatch(change.head_sha)


# --- the guard, offline: counts toward the floor and proves the skip leaks no value ----


def test_the_guard_skips_naming_the_repository_variable_when_none_is_set(tmp_path):
    with pytest.raises(pytest.skip.Exception) as skipped:
        LiveBitbucket.forge(tmp_path, {})
    assert REPOSITORY_ENV in str(skipped.value)


def test_the_guard_skips_naming_the_token_variable_and_never_its_value(tmp_path):
    environ = {REPOSITORY_ENV: "ws/repo", TOKEN_ENV: "MY_BB_TOKEN"}
    with pytest.raises(pytest.skip.Exception) as skipped:
        LiveBitbucket.forge(tmp_path, environ)
    assert "MY_BB_TOKEN" in str(skipped.value)


def test_the_guard_builds_the_adapter_through_the_selector_without_echoing_the_token(tmp_path):
    secret = "s3cret-value"
    environ = {REPOSITORY_ENV: "ws/repo", DEFAULT_TOKEN_ENV: secret}
    forge = LiveBitbucket.forge(tmp_path, environ)
    assert isinstance(forge, BitbucketForge)
    assert secret not in repr(forge)
