# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The automation-bootstrap gate: which checks it waits on, and which paths it admits (#214).

The rendered step is run end to end in `test_templates.py`; these pin the derivation.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path

import pytest
import yaml

from vibey_gh.automation_bootstrap import (
    EXCLUDED_CHECKS,
    EXCLUDED_CHECKS_PLACEHOLDER,
    REQUIRED_CHECKS_PLACEHOLDER,
    SCOPE_PLACEHOLDER,
    AutomationBootstrapGate,
)
from vibey_gh.config import GhConfig, RulesetConfig, RulesetsConfig
from vibey_gh.interfaces.automation_bootstrap_gate_interface import (
    AutomationBootstrapGateInterface,
)

GATE: AutomationBootstrapGateInterface = AutomationBootstrapGate()
TEMPLATE = (
    f"REQUIRED: {REQUIRED_CHECKS_PLACEHOLDER}\n"
    f"EXCLUDED: {EXCLUDED_CHECKS_PLACEHOLDER}\n"
    f"SCOPE: {SCOPE_PLACEHOLDER}\n"
)


def _config(
    *,
    required: tuple[str, ...] | None = None,
    ignored: tuple[str, ...] | None = None,
    self_source: str = ".",
) -> GhConfig:
    cfg = dataclasses.replace(GhConfig(root=Path(".")), self_source=self_source)
    if required is not None:
        integration = RulesetConfig(required_checks=required)
        cfg = dataclasses.replace(cfg, rulesets=RulesetsConfig(integration=integration))
    if ignored is not None:
        automation = dataclasses.replace(cfg.pr_automation, ignored_checks=ignored)
        cfg = dataclasses.replace(cfg, pr_automation=automation)
    return cfg


def test_the_default_configuration_waits_on_the_three_template_gates():
    """The default integration ruleset less the PR automation gate it also requires."""
    expected = ("Provenance", "Analyze Python", "Documentation contract")
    assert GATE.required_checks(_config()) == expected


def test_a_single_job_ci_waits_on_that_job_alone():
    assert GATE.required_checks(_config(required=("gates",))) == ("gates",)


def test_routed_around_and_ignored_checks_are_never_required_and_order_is_kept():
    required = ("zeta", "gate", "PR automation / gate", "Automation bootstrap / gate", "Flaky")
    cfg = _config(required=required + ("alpha",), ignored=("Flaky",))
    assert GATE.required_checks(cfg) == ("zeta", "alpha")


def test_the_excluded_checks_are_the_gates_this_path_routes_around():
    assert GATE.excluded_checks() == EXCLUDED_CHECKS
    assert set(EXCLUDED_CHECKS) == {"gate", "PR automation / gate", "Automation bootstrap / gate"}


def test_the_standalone_scope_is_the_historical_pattern_plus_this_module():
    assert GATE.scope_pattern(_config()) == (
        r"^(\.github/workflows/|vibey_gh/templates/workflows/"
        r"|vibey_gh/(automation_bootstrap|cli|install|merge_train|pr_automation)\.py$|test/)"
    )


def test_a_vendored_scope_is_anchored_at_self_source():
    pattern = re.compile(GATE.scope_pattern(_config(self_source="src/vibey_tools/gh")))
    for admitted in (
        ".github/workflows/ci.yml",
        "src/vibey_tools/gh/.github/workflows/automation-bootstrap.yml",
        "src/vibey_tools/gh/vibey_gh/templates/workflows/automation-bootstrap.yml",
        "src/vibey_tools/gh/vibey_gh/automation_bootstrap.py",
        "src/vibey_tools/gh/vibey_gh/install.py",
        "src/vibey_tools/gh/test/test_templates.py",
    ):
        assert pattern.match(admitted), admitted
    for refused in (
        "vibey_gh/install.py",
        "test/test_templates.py",
        "src/vibey_tools/gh/vibey_gh/install.pyc",
        "src/vibey_tools/gh/vibey_gh/versioning.py",
        "src/vibey_tools/ghost/test/test_x.py",
        "src/vibey/cli/main.py",
    ):
        assert not pattern.match(refused), refused


def test_every_ere_metacharacter_in_self_source_is_matched_literally():
    source = "tools/a.b+c[1](x)*?|^$"
    pattern = re.compile(GATE.scope_pattern(_config(self_source=source)))
    assert pattern.match(f"{source}/test/test_x.py")
    assert not pattern.match("tools/aXb+c[1](x)*?|^$/test/test_x.py")
    assert not pattern.match("tools/a.bbc1x/test/test_x.py")


def test_self_source_cannot_open_a_github_expression_in_the_rendered_scope():
    rendered = GATE.render(TEMPLATE, _config(self_source="${{ secrets.TOKEN }}"))
    assert "${{" not in rendered


@pytest.mark.parametrize("source", ["tools/a\ntest", "tools/\ttab", "tools/\x7fdel"])
def test_a_control_character_in_self_source_is_refused_rather_than_widening_scope(source):
    with pytest.raises(ValueError, match="control character"):
        GATE.scope_pattern(_config(self_source=source))


def test_a_required_name_that_opens_a_github_expression_is_refused():
    cfg = _config(required=("Test (${{ matrix.python }})",))
    with pytest.raises(ValueError, match="opens a GitHub expression"):
        GATE.render(TEMPLATE, cfg)


def test_a_template_without_the_placeholders_renders_untouched_whatever_the_config():
    """Only the bootstrap refuses these values, so they never block the other workflows."""
    cfg = _config(required=("${{ x }}",), self_source="tools/a\ntest")
    assert GATE.render("name: CI\n", cfg) == "name: CI\n"


def test_rendered_values_survive_yaml_then_json_parsing():
    awkward = ('Test "py", (3.12)', "it's \\ fine", "naïve ✓")
    parsed = yaml.safe_load(GATE.render(TEMPLATE, _config(required=awkward)))
    assert json.loads(parsed["REQUIRED"]) == list(awkward)
    assert json.loads(parsed["EXCLUDED"]) == list(EXCLUDED_CHECKS)
    assert parsed["SCOPE"] == GATE.scope_pattern(_config())


def test_an_empty_ruleset_renders_an_empty_list_for_the_step_to_refuse():
    parsed = yaml.safe_load(GATE.render(TEMPLATE, _config(required=())))
    assert json.loads(parsed["REQUIRED"]) == []
