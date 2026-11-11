# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The automation-bootstrap gate: which checks it waits on, and which paths it admits (#214).

The rendered step is run end to end in `test_templates.py`; these pin the derivation.
"""

from __future__ import annotations

import dataclasses
import json
import re
import shutil
import subprocess
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
    required = (
        "zeta",
        "gate",
        "PR automation / gate",
        "PR evaluate / gate",
        "PR review / gate",
        "Automation bootstrap / gate",
        "Flaky",
    )
    cfg = _config(required=required + ("alpha",), ignored=("Flaky",))
    assert GATE.required_checks(cfg) == ("zeta", "alpha")


def test_the_excluded_checks_are_the_gates_this_path_routes_around():
    assert GATE.excluded_checks() == EXCLUDED_CHECKS
    assert set(EXCLUDED_CHECKS) == {
        "gate",
        "PR automation / gate",
        "PR evaluate / gate",
        "PR review / gate",
        "Automation bootstrap / gate",
    }


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


# --- the check-run verdict (the jq expression), executed -------------------------------------

_JQ = re.compile(r"jq -e (?P<flags>.*?)'\n(?P<program>.*?)\n\s*' <<<\"\$checks\"", re.DOTALL)
_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "vibey_gh" / "templates" / "workflows"
) / "automation-bootstrap.yml"


def _verdict(runs: list[tuple[str, str, str]], required: list[str]) -> bool:
    """Run the template's own jq program over check runs `(name, status, conclusion)`."""
    assert shutil.which("jq"), "jq is required to test the bootstrap verdict"
    match = _JQ.search(_TEMPLATE.read_text(encoding="utf-8"))
    assert match, "the jq verdict is no longer in the template"
    document = {
        "check_runs": [
            {"name": name, "status": status, "conclusion": conclusion}
            for name, status, conclusion in runs
        ]
    }
    done = subprocess.run(
        [
            "jq",
            "-e",
            "--argjson",
            "required",
            json.dumps(required),
            "--argjson",
            "excluded",
            json.dumps(list(EXCLUDED_CHECKS)),
            "--argjson",
            "strict",
            json.dumps(["gates"]),
            match.group("program"),
        ],
        input=json.dumps(document),
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def test_the_template_declares_gates_as_a_success_only_check():
    text = _TEMPLATE.read_text(encoding="utf-8")
    assert 'SUCCESS_ONLY_CHECKS: "[\\"gates\\"]"' in text
    assert '--argjson strict "$SUCCESS_ONLY_CHECKS"' in text


def test_a_skipped_gates_is_not_green_for_the_admin_bootstrap():
    # `gates` is skipped when `uv-lock` or `lint` failed: the suite never ran.
    runs = [("gates", "completed", "skipped"), ("Lint and static gates", "completed", "success")]
    assert not _verdict(runs, ["gates", "Lint and static gates"])


def test_a_successful_gates_passes_and_other_checks_may_still_be_skipped():
    runs = [
        ("gates", "completed", "success"),
        ("Lint and static gates", "completed", "success"),
        ("VS Code extension (macos-latest)", "completed", "skipped"),
        ("krypton desktop (arch)", "completed", "neutral"),
    ]
    required = ["gates", "Lint and static gates", "VS Code extension (macos-latest)"]
    assert _verdict(runs, required)


def test_a_failed_or_unfinished_gates_is_not_green():
    for status, conclusion in (
        ("completed", "failure"),
        ("in_progress", None),
        ("completed", "cancelled"),
    ):
        runs = [("gates", status, conclusion)]
        assert not _verdict(runs, ["gates"]), (status, conclusion)  # type: ignore[arg-type]


def test_a_missing_required_gate_is_still_refused():
    assert not _verdict([("Lint and static gates", "completed", "success")], ["gates"])


def test_a_repository_without_a_gates_check_is_not_held_to_one():
    # The named check is accepted on `success` alone only where it is reported.
    assert _verdict([("test", "completed", "success")], ["test"])
