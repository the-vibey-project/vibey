# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh rulesets --check`: do the live rulesets say what `.vibey-gh.toml` says?

`vibey-gh rulesets` reconciles the two rulesets it names and preserves everything else,
which is the right behaviour for a writer and the wrong one for an auditor: a ruleset
somebody made by hand beside the declared one is never looked at. A read-only audit found
exactly that -- a live ruleset called `develop`, with a bypass actor the declaration does
not grant, standing next to `vibey-gh: develop` -- and nothing had said so.

This compares, never writes. Drift is every difference a reader of the declaration could
not predict:

* a declared ruleset that is missing, or whose target, enforcement, conditions, bypass
  actors or declared rule parameters differ;
* a rule inside a declared ruleset that the declaration never mentions;
* any repository-level ruleset that is not declared at all, named with its target and its
  bypass actors, because an undeclared bypass is the drift that matters most.

Organisation rulesets are out of scope (`includes_parents=false`): this repository's
declaration cannot speak for them. A ruleset whose bypass actors the forge withheld --
it does so for a token without repository-admin authority -- is reported as unverified,
never as clean.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from vibey_gh import github_state, rulesets
from vibey_gh.config import GhConfig, load_config
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.ruleset_drift_interface import RulesetDriftInterface
from vibey_gh.tracking_issue import TrackingIssue

__all__ = ["RulesetDrift"]


class RulesetDrift(RulesetDriftInterface):
    """Implements `RulesetDriftInterface`."""

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        transport: GhTransportInterface | None = None,
        repository: Callable[[], str] = github_state.repository,
    ) -> None:
        self._config = config
        self._transport: GhTransportInterface = transport or GhTransport()
        self._repository = repository

    def fetch(self) -> list[dict[str, Any]]:
        repository = self._repository()
        path = f"repos/{repository}/rulesets?includes_parents=false&per_page=100"
        run = self._transport.run(["api", "--paginate", path])
        if run.returncode:
            raise RuntimeError(f"gh api {path}: {run.stderr.strip()}")
        # The listing omits every ruleset's rules and bypass actors, so each is re-read.
        return [
            self._transport.json(["api", f"repos/{repository}/rulesets/{item['id']}"])
            for item in TrackingIssue.decode_pages(run.stdout)
        ]

    def compare(self, cfg: GhConfig, live: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
        if not cfg.rulesets.enabled:
            return ()
        declared = {
            rulesets.ruleset_name(branch): (branch, policy)
            for branch, policy in (
                (cfg.integration_branch, cfg.rulesets.integration),
                (cfg.release_branch, cfg.rulesets.release),
            )
        }
        problems: list[str] = []
        seen: dict[str, Mapping[str, Any]] = {}
        for ruleset in live:
            name = str(ruleset.get("name"))
            if name in declared:
                seen[name] = ruleset
                continue
            include = (ruleset.get("conditions") or {}).get("ref_name", {}).get("include", [])
            problems.append(
                f"undeclared ruleset {name!r} (id {ruleset.get('id')}, "
                f"{ruleset.get('enforcement')}) on {', '.join(include) or 'no ref'}; "
                f"bypass: {self._actors(ruleset)}"
            )
        for name, (branch, policy) in declared.items():
            existing = seen.get(name)
            if existing is None:
                problems.append(f"{name}: declared, but no such ruleset exists")
                continue
            problems.extend(
                f"{name}: {detail}"
                for detail in self._differences(rulesets.build_ruleset(branch, policy), existing)
            )
        return tuple(problems)

    @staticmethod
    def _actors(ruleset: Mapping[str, Any]) -> str:
        if "bypass_actors" not in ruleset:
            return "withheld from this token"
        return ", ".join(RulesetDrift._actor_names(ruleset["bypass_actors"] or [])) or "none"

    @staticmethod
    def _actor_names(actors: Sequence[Mapping[str, Any]]) -> list[str]:
        names = []
        for actor in actors:
            name = str(actor.get("actor_type"))
            if actor.get("actor_id") is not None:
                name += f":{actor['actor_id']}"
            if actor.get("bypass_mode", "always") != "always":
                name += f" ({actor['bypass_mode']})"
            names.append(name)
        return sorted(names)

    def _differences(self, desired: dict[str, Any], existing: Mapping[str, Any]) -> list[str]:
        found = []
        for field in ("target", "enforcement", "conditions"):
            if existing.get(field) != desired[field]:
                found.append(f"{field} is {existing.get(field)!r}, declared {desired[field]!r}")
        if "bypass_actors" not in existing:
            found.append(
                "bypass actors were withheld from this token, so they are unverified; "
                "check with a token that has repository-admin authority"
            )
        else:
            live = self._actor_names(existing["bypass_actors"] or [])
            wanted = self._actor_names(desired["bypass_actors"])
            if live != wanted:
                found.append(
                    f"bypass actors are {', '.join(live) or 'none'}, "
                    f"declared {', '.join(wanted) or 'none'}"
                )
        live_rules = {rule["type"]: rule for rule in existing.get("rules") or []}
        for rule in desired["rules"]:
            if not rulesets.rule_matches(live_rules.get(rule["type"]), rule):
                state = "differs" if rule["type"] in live_rules else "is missing"
                found.append(f"rule {rule['type']} {state}")
        declared_types = {rule["type"] for rule in desired["rules"]}
        found.extend(
            f"rule {kind} is live but not declared"
            for kind in sorted(set(live_rules) - declared_types)
        )
        return found

    # ------------------------------------------------------------------ the command

    def run(self) -> int:
        """Print every drift; 0 when the live rulesets match, 1 when they do not."""
        cfg = self._config()
        if not cfg.rulesets.enabled:
            print("vibey-gh: [rulesets] is disabled here; there is no declaration to compare")
            return 0
        try:
            problems = self.compare(cfg, self.fetch())
        except (RuntimeError, TypeError, ValueError) as exc:
            print(f"vibey-gh: could not read the live rulesets: {exc}")
            return 1
        for problem in problems:
            print(f"  drift: {problem}")
        if problems:
            print(
                f"::error::{len(problems)} ruleset drift(s) from .vibey-gh.toml. Declare what "
                "should stay and reconcile it with `vibey-gh rulesets`; a ruleset nobody "
                "declared must be declared or deleted, and vibey-gh never deletes one itself."
            )
            return 1
        print("vibey-gh: the live rulesets match .vibey-gh.toml")
        return 0

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        return cls().run()
