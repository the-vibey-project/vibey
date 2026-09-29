# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh rulesets --check`: the live rulesets against the declaration, read-only."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import cli, rulesets as rs
from vibey_gh.config import GhConfig, RulesetConfig, RulesetsConfig
from vibey_gh.interfaces.ruleset_drift_interface import RulesetDriftInterface
from vibey_gh.ruleset_drift import RulesetDrift

REPO = "o/r"
INTEGRATION = RulesetConfig(required_checks=("gates",), bypass_actors=("OrganizationAdmin",))
RELEASE = RulesetConfig(
    required_checks=("gates",), required_approvals=1, allowed_merge_methods=("rebase",)
)


def cfg(tmp_path: Path, enabled: bool = True) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        rulesets=RulesetsConfig(enabled=enabled, integration=INTEGRATION, release=RELEASE),
    )


def as_live(payload: dict[str, Any], ruleset_id: int) -> dict[str, Any]:
    """A declared payload as the forge echoes it back: with an id, and with parameters it
    added on its own that nobody declared."""
    live = copy.deepcopy(payload)
    live["id"] = ruleset_id
    for rule in live["rules"]:
        if rule["type"] == rs.PULL_REQUEST:
            rule["parameters"]["automatic_copilot_code_review_enabled"] = False
        if rule["type"] == rs.STATUS_CHECKS:
            rule["parameters"]["do_not_enforce_on_create"] = False
            for check in rule["parameters"]["required_status_checks"]:
                check["integration_id"] = 15368
    return live


def matching() -> list[dict[str, Any]]:
    return [
        as_live(rs.build_ruleset("develop", INTEGRATION), 1),
        as_live(rs.build_ruleset("main", RELEASE), 2),
    ]


def test_a_declaration_the_forge_echoes_with_its_own_defaults_is_not_drift(tmp_path):
    assert RulesetDrift().compare(cfg(tmp_path), matching()) == ()


def test_an_undeclared_ruleset_is_drift_and_names_its_bypass_actors(tmp_path):
    extra = {
        "id": 20901387,
        "name": "develop",
        "enforcement": "active",
        "conditions": {"ref_name": {"include": ["refs/heads/develop"], "exclude": []}},
        "bypass_actors": [
            {"actor_id": 2, "actor_type": "RepositoryRole", "bypass_mode": "always"},
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request"},
        ],
        "rules": [],
    }
    problems = RulesetDrift().compare(cfg(tmp_path), [*matching(), extra])
    assert problems == (
        (
            "undeclared ruleset 'develop' (id 20901387, active) on refs/heads/develop; "
            "bypass: RepositoryRole:2, RepositoryRole:5 (pull_request)"
        ),
    )


def test_an_undeclared_ruleset_with_hidden_actors_and_no_conditions_still_reports(tmp_path):
    extra = {"id": 3, "name": "tags", "enforcement": "disabled"}
    (problem,) = RulesetDrift().compare(cfg(tmp_path), [*matching(), extra])
    assert problem == (
        "undeclared ruleset 'tags' (id 3, disabled) on no ref; bypass: withheld from this token"
    )
    none = {"id": 4, "name": "none", "enforcement": "active", "bypass_actors": None}
    (problem,) = RulesetDrift().compare(cfg(tmp_path), [*matching(), none])
    assert problem.endswith("bypass: none")


def test_a_missing_declared_ruleset_is_drift(tmp_path):
    problems = RulesetDrift().compare(cfg(tmp_path), matching()[:1])
    assert problems == ("vibey-gh: main: declared, but no such ruleset exists",)


def test_every_difference_in_a_declared_ruleset_is_named(tmp_path):
    live = matching()
    release = live[1]
    release["enforcement"] = "evaluate"
    release["target"] = "tag"
    release["bypass_actors"] = [
        {"actor_id": 2, "actor_type": "RepositoryRole", "bypass_mode": "always"}
    ]
    rules = {rule["type"]: rule for rule in release["rules"]}
    rules[rs.PULL_REQUEST]["parameters"]["allowed_merge_methods"] = ["merge", "squash", "rebase"]
    release["rules"] = [rule for rule in release["rules"] if rule["type"] != rs.STATUS_CHECKS] + [
        {"type": "creation"}
    ]
    problems = RulesetDrift().compare(cfg(tmp_path), live)
    assert problems == (
        "vibey-gh: main: target is 'tag', declared 'branch'",
        "vibey-gh: main: enforcement is 'evaluate', declared 'active'",
        "vibey-gh: main: bypass actors are RepositoryRole:2, declared RepositoryRole:5",
        "vibey-gh: main: rule pull_request differs",
        "vibey-gh: main: rule required_status_checks is missing",
        "vibey-gh: main: rule creation is live but not declared",
    )


def test_bypass_actors_withheld_from_the_token_are_unverified_never_clean(tmp_path):
    live = matching()
    del live[0]["bypass_actors"]
    live[1]["bypass_actors"] = []
    problems = RulesetDrift().compare(cfg(tmp_path), live)
    assert problems[0].startswith("vibey-gh: develop: bypass actors were withheld")
    assert problems[1] == "vibey-gh: main: bypass actors are none, declared RepositoryRole:5"


def test_a_repository_that_declares_no_rulesets_has_nothing_to_compare(tmp_path):
    assert RulesetDrift().compare(cfg(tmp_path, enabled=False), [{"name": "x"}]) == ()


# --------------------------------------------------------------------------- fetching


class Listing:
    executable = "gh"

    def __init__(self, listing: str, rulesets: dict[int, dict], code: int = 0) -> None:
        self.listing, self.rulesets, self.code = listing, rulesets, code
        self.calls: list[tuple[str, ...]] = []

    def run(self, args, *, cwd=None, stdin=None):
        self.calls.append(tuple(args))
        return subprocess.CompletedProcess(list(args), self.code, self.listing, "HTTP 403")

    def json(self, args, *, cwd=None, stdin=None):
        self.calls.append(tuple(args))
        return self.rulesets[int(args[1].rsplit("/", 1)[1])]


def test_every_repository_ruleset_is_refetched_by_id_and_nothing_is_written():
    full = {1: {"id": 1, "name": "a", "rules": []}, 2: {"id": 2, "name": "b", "rules": []}}
    listing = Listing(json.dumps([{"id": 1}]) + json.dumps([{"id": 2}]), full)
    drift = RulesetDrift(transport=listing, repository=lambda: REPO)
    assert drift.fetch() == [full[1], full[2]]
    assert listing.calls[0] == (
        "api",
        "--paginate",
        f"repos/{REPO}/rulesets?includes_parents=false&per_page=100",
    )
    assert not any("--method" in call for call in listing.calls)


def test_a_listing_the_forge_refused_raises():
    drift = RulesetDrift(transport=Listing("", {}, code=1), repository=lambda: REPO)
    with pytest.raises(RuntimeError, match="HTTP 403"):
        drift.fetch()


def test_the_check_honours_its_interface():
    assert isinstance(RulesetDrift(), RulesetDriftInterface)


# ---------------------------------------------------------------------------- command


def checker(tmp_path, live, *, enabled=True) -> RulesetDrift:
    listing = Listing(
        json.dumps([{"id": index} for index in range(len(live))]), dict(enumerate(live))
    )
    config = cfg(tmp_path, enabled)
    return RulesetDrift(config=lambda: config, transport=listing, repository=lambda: REPO)


def test_a_matching_repository_exits_zero(tmp_path, capsys):
    assert checker(tmp_path, matching()).run() == 0
    assert "match .vibey-gh.toml" in capsys.readouterr().out


def test_drift_exits_one_and_prints_every_problem(tmp_path, capsys):
    assert checker(tmp_path, matching()[:1]).run() == 1
    out = capsys.readouterr().out
    assert "drift: vibey-gh: main: declared, but no such ruleset exists" in out
    assert "::error::1 ruleset drift(s)" in out


def test_an_unreadable_forge_is_a_failure_not_a_pass(tmp_path, capsys):
    config = cfg(tmp_path)
    drift = RulesetDrift(
        config=lambda: config, transport=Listing("", {}, code=1), repository=lambda: REPO
    )
    assert drift.run() == 1
    assert "could not read the live rulesets" in capsys.readouterr().out


def test_a_repository_without_rulesets_says_so_and_passes(tmp_path, capsys):
    assert checker(tmp_path, [], enabled=False).run() == 0
    assert "disabled" in capsys.readouterr().out


def test_the_cli_check_flag_runs_the_read_only_check(monkeypatch):
    seen = []
    monkeypatch.setattr(RulesetDrift, "run", lambda self: seen.append("check") or 1)
    monkeypatch.setattr(
        rs, "reconcile", lambda *a, **k: pytest.fail("--check must never reconcile anything")
    )
    assert cli.main(["rulesets", "--check"]) == 1
    assert seen == ["check"]
