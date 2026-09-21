# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the automation-bootstrap admin merge must see green, and where a repair may reach.

`automation-bootstrap.yml` is the one path that squash-merges past PR automation, so the
two things it verifies before that admin merge are the whole of its safety claim:

- **the independent gates on the exact head.** These are the integration branch's own
  required checks -- `[rulesets.integration] required_checks`, the check-run names GitHub
  already enforces on the branch the bootstrap merges into -- less
  `[pr_automation] ignored_checks` and the gates this path exists to route around. They
  were six literal names once, and five of them never report in a repository whose CI
  names its jobs differently. Three (`Build`, `Lint`, the parity check) came from
  vibey-gh's own hand-written workflows rather than from any template, so the recovery
  path failed closed for every adopter, exactly when it was needed (#214).
- **the scope of the change**: workflow, template, and automation-core paths, anchored at
  `[install] self_source`. `gh pr diff` reports repository-root paths, so a monorepo that
  vendors vibey-gh under a subtree must be matched under that subtree; the standalone
  pattern rejected every one of its files.

Both are rendered into the deployed workflow as `env:` values -- JSON-quoted, so no
configured name can break the YAML or the shell around it -- rather than written into it.
"""

from __future__ import annotations

import json

from vibey_gh.config import GhConfig

__all__ = [
    "EXCLUDED_CHECKS",
    "EXCLUDED_CHECKS_PLACEHOLDER",
    "REQUIRED_CHECKS_PLACEHOLDER",
    "SCOPE_PLACEHOLDER",
    "AutomationBootstrapGate",
]

REQUIRED_CHECKS_PLACEHOLDER = "__VIBEY_GH_BOOTSTRAP_REQUIRED_CHECKS__"
EXCLUDED_CHECKS_PLACEHOLDER = "__VIBEY_GH_BOOTSTRAP_EXCLUDED_CHECKS__"
SCOPE_PLACEHOLDER = "__VIBEY_GH_BOOTSTRAP_SCOPE__"

# PR automation's own merge gates -- the split scan and review gates, plus the pre-split
# spelling -- broken, or this path would not be needed -- and this workflow's own. Never
# waited on and never required, whatever the configuration says: a required name the
# bootstrap also ignores could never be satisfied. Fixed by the managed templates' own job
# names rather than configured, as `pr_automation.OWN_CHECKS` is.
EXCLUDED_CHECKS = (
    "gate",
    "PR automation / gate",
    "PR evaluate / gate",
    "PR review / gate",
    "Automation bootstrap / gate",
)

# The paths a repair may touch, as ERE fragments. The deployed workflows are always at the
# repository root; the rest are relative to wherever vibey-gh itself lives. This module is
# automation core too: the logic it holds used to live in the template, which was in scope,
# so a repair of the bootstrap's own gate must not be refused by that gate.
_WORKFLOWS = r"\.github/workflows/"
_AUTOMATION_CORE = (
    r"vibey_gh/templates/workflows/"
    r"|vibey_gh/(automation_bootstrap|cli|install|merge_train|pr_automation)\.py$"
    r"|test/"
)
# POSIX's own list of ERE special characters. `]` and `}` are ordinary outside a bracket
# or an interval, and escaping them is undefined -- GNU grep warns about a stray `\`.
# Escaping `$` and `{` also means no rendered prefix can open a `${{ }}` expression.
_ERE_SPECIAL = frozenset("\\.[()*+?{|^$")
_EXPRESSION = "${{"


class AutomationBootstrapGate:
    """Implements `AutomationBootstrapGateInterface` from a loaded `GhConfig`."""

    def required_checks(self, cfg: GhConfig) -> tuple[str, ...]:
        skipped = set(cfg.pr_automation.ignored_checks) | set(EXCLUDED_CHECKS)
        return tuple(
            name for name in cfg.rulesets.integration.required_checks if name not in skipped
        )

    def excluded_checks(self) -> tuple[str, ...]:
        return EXCLUDED_CHECKS

    def scope_pattern(self, cfg: GhConfig) -> str:
        if cfg.self_source == ".":
            # The standalone layout: the pattern the template always carried, plus this module.
            return f"^({_WORKFLOWS}|{_AUTOMATION_CORE})"
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in cfg.self_source):
            # grep reads a newline in its pattern as a second pattern, which would widen
            # the scope of an admin merge rather than narrow it. Refused, not escaped.
            raise ValueError(
                f"install.self_source contains a control character: {cfg.self_source!r}"
            )
        prefix = "".join(f"\\{char}" if char in _ERE_SPECIAL else char for char in cfg.self_source)
        # The vendored tree's own deployed workflows count too: they are rendered from the
        # same templates, so a repair that re-renders both copies stays in scope.
        return f"^({_WORKFLOWS}|{prefix}/({_WORKFLOWS}|{_AUTOMATION_CORE}))"

    def render(self, text: str, cfg: GhConfig) -> str:
        placeholders = (REQUIRED_CHECKS_PLACEHOLDER, EXCLUDED_CHECKS_PLACEHOLDER, SCOPE_PLACEHOLDER)
        if not any(placeholder in text for placeholder in placeholders):
            # Every other template renders untouched, so a value only the bootstrap refuses
            # never blocks installing the workflows that do not use it.
            return text
        required = self.required_checks(cfg)
        for name in required:
            if _EXPRESSION in name:
                # An `env:` value is evaluated by Actions, so this name would run as an
                # expression in the job that performs the admin merge.
                raise ValueError(
                    f"rulesets.integration.required_checks entry opens a GitHub expression: "
                    f"{name!r}"
                )
        return (
            text.replace(REQUIRED_CHECKS_PLACEHOLDER, self._yaml_json(required))
            .replace(EXCLUDED_CHECKS_PLACEHOLDER, self._yaml_json(self.excluded_checks()))
            .replace(SCOPE_PLACEHOLDER, json.dumps(self.scope_pattern(cfg)))
        )

    @staticmethod
    def _yaml_json(values: tuple[str, ...]) -> str:
        """A JSON array as a double-quoted YAML scalar, so `jq --argjson` reads it back whole.

        The inner `dumps` is the value the step's shell sees; the outer quotes it for YAML,
        whose double-quoted escapes are a superset of JSON's. A name carrying a quote, a
        comma, or parentheses therefore survives YAML and then JSON parsing unchanged.
        """
        return json.dumps(json.dumps(list(values)))
