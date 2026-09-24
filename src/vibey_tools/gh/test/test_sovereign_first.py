# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sovereign first (doctrine 8.a, #133): one review verdict from two lanes.

Two layers. The composer is tested directly, including against a GOLDEN capture of the
`jq` it replaced. Then the acceptance matrix the issue names is run against the RENDERED
workflow itself: its own `if:` conditions and `${{ }}` expressions are evaluated, its own
bash steps are executed with the model calls stubbed, and the gate it would publish is
compared with what the workflow published before the lanes split.

- fresh heartbeat and credits: the sovereign lane carries the diff half and the paid
  reviewer is handed the wider half alone;
- no heartbeat: exactly today's behaviour, down to the gate's words;
- no credits: exactly the local-fallback behaviour (#277).

The golden file was captured by running the pre-change workflow's gate script and `jq`
program (4e9adf18 + #241). It is frozen on purpose: regenerated from a later template it
would stop meaning "what the workflow did before".
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh.config import GhConfig
from vibey_gh.install import WORKFLOWS, render_workflow
from vibey_gh.interfaces import ReviewComposerPort
from vibey_gh.review_composition import (
    FULL,
    NO_PAID,
    PAID_HALVES,
    PAID_LANE,
    REVIEW_COMPOSER,
    SOVEREIGN_LANE,
    ReviewComposer,
)
from vibey_gh.review_contract import (
    DIFF_GROUNDABLE,
    REQUIRES_WIDER_CONTEXT,
    REVIEW_CONTRACT,
    ReviewContract,
)

GOLDEN = json.loads(
    (Path(__file__).parent / "golden/pr-automation-before-sovereign-first.json").read_text(
        encoding="utf-8"
    )
)
JUDGMENTS = REVIEW_CONTRACT.requires_wider_context
FINDING = {
    "severity": "major",
    "path": "README.md",
    "line": 3,
    "explanation": "the quick start names a flag that does not exist",
    "recommended_fix": "name the flag the CLI actually takes",
}


def _paid_full(**changes: Any) -> dict:
    """A paid answer to the FULL schema, every judgment true unless changed."""
    answer = {"pass": True, **{name: True for name in JUDGMENTS}}
    answer |= {"summary": "Documentation is complete.", "findings": []}
    return answer | changes


def _paid_wider(**changes: Any) -> dict:
    """A paid answer to the WIDER-half schema: judgments, then its own prose and findings."""
    answer = {name: True for name in JUDGMENTS}
    answer |= {"wider_summary": "Documentation is complete.", "wider_findings": []}
    return answer | changes


def _local(**changes: Any) -> dict:
    """What the local model itself returns: the diff-groundable half, nothing more."""
    return {"pass": True, "summary": "Adds a flag.", "findings": []} | changes


def _sovereign(**changes: Any) -> dict:
    """The sovereign lane's verdict as `local-review` publishes it: placeholders included."""
    return (
        _local(**changes)
        | REVIEW_CONTRACT.placeholders()
        | {REVIEW_CONTRACT.scope_field: [DIFF_GROUNDABLE]}
    )


def _whole(**changes: Any) -> dict:
    """What the local model returns when it answers the WHOLE review (no paid lane, 8.b)."""
    return _paid_full(summary="Adds a flag; the documentation keeps up.") | changes


def _sovereign_whole(**changes: Any) -> dict:
    """A whole-review verdict as `local-review --scope full` publishes it."""
    return _whole(**changes) | {
        REVIEW_CONTRACT.scope_field: [DIFF_GROUNDABLE, REQUIRES_WIDER_CONTEXT]
    }


# --------------------------------------------------------------------------------------
# The composer
# --------------------------------------------------------------------------------------


def test_the_composer_satisfies_its_declared_seam():
    assert isinstance(REVIEW_COMPOSER, ReviewComposerPort)
    assert REVIEW_COMPOSER == ReviewComposer()
    assert PAID_HALVES == (FULL, REQUIRES_WIDER_CONTEXT, NO_PAID)


@pytest.mark.parametrize("case", GOLDEN["paid_verdicts"], ids=lambda case: case["name"])
def test_a_full_review_persists_exactly_what_the_old_jq_did(case):
    """No heartbeat means today's behaviour. The persisted verdict was the output of a jq
    program listing the sixteen judgments by name; it is now computed from the contract,
    and must agree with that program on every captured answer -- values AND key order,
    including the cases where the model's own `pass` disagreed with its booleans."""
    envelope = REVIEW_COMPOSER.compose(case["structured"], half=FULL, head_sha=case["head_sha"])

    assert envelope["verdict"] == case["payload"]
    assert list(envelope["verdict"]) == list(case["payload"])


def test_a_full_review_hands_repair_the_raw_answer_and_says_the_paid_lane_carried_it():
    answer = _paid_full(**{"pass": False}, findings=[FINDING])

    envelope = REVIEW_COMPOSER.compose(answer, half=FULL, head_sha="abc")

    assert envelope["half"] == FULL
    assert envelope["structured"] == answer
    assert "head_sha" not in envelope["structured"]
    assert envelope["carried"] == {name: PAID_LANE for name in REVIEW_CONTRACT.fields}
    assert envelope["halves"] == {FULL: {"lane": PAID_LANE, "passed": False, "findings": 1}}
    assert envelope["findings"] == 1
    assert envelope["repairable"] is True
    # Golden: the full verdict carries nothing the old one did not.
    assert set(envelope["verdict"]) == set(answer) | {"head_sha"}


def test_a_passing_full_review_is_not_repairable():
    envelope = REVIEW_COMPOSER.compose(_paid_full(), half=FULL, head_sha="abc")

    assert envelope["verdict"]["pass"] is True
    assert envelope["repairable"] is False
    assert envelope["findings"] == 0


def test_a_split_review_names_the_lane_behind_every_field():
    envelope = REVIEW_COMPOSER.compose(
        _paid_wider(), half=REQUIRES_WIDER_CONTEXT, sovereign=_sovereign(), head_sha="abc"
    )
    verdict = envelope["verdict"]

    assert verdict["pass"] is True
    assert envelope["repairable"] is False and verdict["repairable"] is False
    assert envelope["structured"] == verdict
    for name in REVIEW_CONTRACT.diff_groundable:
        assert envelope["carried"][name] == SOVEREIGN_LANE
    for name in (*JUDGMENTS, *REVIEW_CONTRACT.wider_report_fields):
        assert envelope["carried"][name] == PAID_LANE
    assert verdict["carried"] == envelope["carried"]
    # The schema's own key order: verdict, judgments, prose, then the paid lane's report.
    expected = [
        "pass",
        *JUDGMENTS,
        "summary",
        "findings",
        "wider_summary",
        "wider_findings",
        "head_sha",
        "carried",
        "repairable",
    ]
    assert list(verdict) == expected
    assert verdict["summary"] == "Adds a flag."
    assert verdict["wider_summary"] == "Documentation is complete."
    assert envelope["halves"] == {
        DIFF_GROUNDABLE: {"lane": SOVEREIGN_LANE, "passed": True, "findings": 0},
        REQUIRES_WIDER_CONTEXT: {"lane": PAID_LANE, "passed": True, "findings": 0},
    }


def test_the_sovereign_placeholders_never_stand_in_for_the_paid_judgments():
    """The local verdict writes `true` for every judgment it did NOT evaluate. In a split
    review those names are the paid lane's, and its answer is the only one that counts."""
    envelope = REVIEW_COMPOSER.compose(
        _paid_wider(links_valid=False),
        half=REQUIRES_WIDER_CONTEXT,
        sovereign=_sovereign(),
        head_sha="abc",
    )

    assert envelope["verdict"]["links_valid"] is False
    assert envelope["verdict"]["pass"] is False
    assert envelope["repairable"] is True


@pytest.mark.parametrize(
    ("sovereign", "paid", "passed", "repairable", "halves"),
    [
        pytest.param(
            _sovereign(**{"pass": False}, findings=[FINDING]),
            _paid_wider(),
            False,
            False,
            (False, 1, True, 0),
            id="only the sovereign lane found something",
        ),
        pytest.param(
            _sovereign(**{"pass": False}),
            _paid_wider(),
            False,
            False,
            (False, 0, True, 0),
            id="the sovereign lane declined with nothing to point at",
        ),
        pytest.param(
            _sovereign(),
            _paid_wider(wider_findings=[FINDING]),
            False,
            True,
            (True, 0, False, 1),
            id="only the paid lane found something",
        ),
        pytest.param(
            _sovereign(**{"pass": False}, findings=[FINDING]),
            _paid_wider(audience_order=False),
            False,
            True,
            (False, 1, False, 0),
            id="both lanes failed",
        ),
        pytest.param(
            _sovereign(**{"pass": "true"}),
            _paid_wider(),
            False,
            False,
            (False, 0, True, 0),
            id="a verdict spelt as a string is not a pass",
        ),
    ],
)
def test_each_half_passes_or_fails_on_its_own_lane(sovereign, paid, passed, repairable, halves):
    """The combined verdict is both halves passing, and automated repair acts on the paid
    lane's half only: a local model's finding is a lead for a human, never a repair."""
    envelope = REVIEW_COMPOSER.compose(
        paid, half=REQUIRES_WIDER_CONTEXT, sovereign=sovereign, head_sha="abc"
    )
    diff = envelope["halves"][DIFF_GROUNDABLE]
    wider = envelope["halves"][REQUIRES_WIDER_CONTEXT]

    assert envelope["verdict"]["pass"] is passed
    assert envelope["repairable"] is repairable
    assert (diff["passed"], diff["findings"], wider["passed"], wider["findings"]) == halves
    assert envelope["findings"] == diff["findings"] + wider["findings"]


def test_a_field_a_lane_left_out_stays_out_of_the_verdict():
    """Nothing is invented as `null`: an absent judgment fails the half, visibly absent."""
    paid = _paid_wider()
    del paid["examples_sufficient"]

    envelope = REVIEW_COMPOSER.compose(
        paid, half=REQUIRES_WIDER_CONTEXT, sovereign=_sovereign(), head_sha="abc"
    )

    assert "examples_sufficient" not in envelope["verdict"]
    assert envelope["carried"]["examples_sufficient"] == PAID_LANE
    assert envelope["verdict"]["pass"] is False


def test_a_malformed_findings_field_fails_the_half_and_counts_nothing():
    envelope = REVIEW_COMPOSER.compose(
        _paid_wider(wider_findings={"path": "README.md"}),
        half=REQUIRES_WIDER_CONTEXT,
        sovereign=_sovereign(),
        head_sha="abc",
    )

    assert envelope["halves"][REQUIRES_WIDER_CONTEXT] == {
        "lane": PAID_LANE,
        "passed": False,
        "findings": 0,
    }


def test_the_wider_half_alone_needs_the_sovereign_verdict():
    """A review whose diff half nobody carried must never compose into a pass."""
    with pytest.raises(ValueError, match="sovereign lane's verdict is needed"):
        REVIEW_COMPOSER.compose(_paid_wider(), half=REQUIRES_WIDER_CONTEXT, head_sha="abc")


@pytest.mark.parametrize("half", [DIFF_GROUNDABLE, "both", ""])
def test_a_paid_half_that_is_not_one_is_refused(half):
    with pytest.raises(
        ValueError, match="paid half must be one of full, requires-wider-context, none"
    ):
        REVIEW_COMPOSER.compose(_paid_full(), half=half, head_sha="abc")


@pytest.mark.parametrize("half", [FULL, REQUIRES_WIDER_CONTEXT])
def test_a_paid_half_with_no_paid_answer_says_so(half):
    """The workflow hands `combine` an empty answer when the paid call failed. That is
    "the paid lane returned nothing", and it is said in those words rather than as a
    complaint about the type of nothing."""
    with pytest.raises(ValueError, match="the paid lane returned no answer to compose"):
        REVIEW_COMPOSER.compose(None, half=half, sovereign=_sovereign(), head_sha="abc")


def test_answers_that_are_not_objects_are_refused():
    with pytest.raises(TypeError, match="paid answer must be a JSON object, not list"):
        REVIEW_COMPOSER.compose([], half=FULL, head_sha="abc")  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="sovereign verdict must be a JSON object, not str"):
        REVIEW_COMPOSER.compose(
            _paid_wider(),
            half=REQUIRES_WIDER_CONTEXT,
            sovereign="pass",  # type: ignore[arg-type]
            head_sha="abc",
        )


@pytest.mark.parametrize("role", ["verdict_field", "summary_field", "findings_field"])
def test_a_role_must_name_a_diff_groundable_field(role):
    """Each role is read from whichever lane carried the diff half; a field outside that
    half would be read from the wrong lane."""
    with pytest.raises(ValueError, match="must be in the diff-groundable half"):
        ReviewComposer(**{role: "links_valid"})


def test_a_repository_composes_its_own_contract():
    contract = ReviewContract(
        diff_groundable=("ok", "notes", "issues"),
        requires_wider_context=("house_style",),
        field_schemas={
            "ok": {"type": "boolean"},
            "house_style": {"type": "boolean"},
            "notes": {"type": "string"},
            "issues": {"type": "array"},
            "house_notes": {"type": "string"},
            "house_issues": {"type": "array"},
        },
        wider_summary_field="house_notes",
        wider_findings_field="house_issues",
    )
    composer = ReviewComposer(
        contract=contract, verdict_field="ok", summary_field="notes", findings_field="issues"
    )

    envelope = composer.compose(
        {"house_style": True, "house_notes": "fine", "house_issues": []},
        half=REQUIRES_WIDER_CONTEXT,
        sovereign={"ok": True, "notes": "fine", "issues": []},
        head_sha="abc",
    )
    full = composer.compose({"ok": False, "house_style": True, "issues": []}, half=FULL)

    assert envelope["verdict"]["ok"] is True
    assert list(envelope["carried"]) == [
        "ok",
        "house_style",
        "notes",
        "issues",
        "house_notes",
        "house_issues",
    ]
    assert full["verdict"]["ok"] is True
    assert full["verdict"]["head_sha"] == ""


# --------------------------------------------------------------------------------------
# The rendered workflow, evaluated
# --------------------------------------------------------------------------------------

_TOKENS = re.compile(
    r"\s*(?:(?P<string>'(?:[^']|'')*')|(?P<number>\d+(?:\.\d+)?)"
    r"|(?P<op>==|!=|&&|\|\||!|\(|\)|,)|(?P<name>[A-Za-z_][\w.-]*))"
)
_STATUS_FUNCTIONS = ("always(", "success(", "failure(", "cancelled(")


class _Expression:
    """Just enough of GitHub's expression language to evaluate this workflow's own.

    Literals, context lookups (`needs.review-sovereign.outputs.passed`), `!`, `==`, `!=`,
    `&&`, `||`, parentheses, and the status functions. Semantics follow GitHub's: `&&`
    and `||` return an operand rather than a boolean, string comparison ignores case,
    operands of different types compare as numbers, and an absent property is null.
    """

    def __init__(self, source: str, context: dict[str, Any]) -> None:
        self.tokens = [match for match in _TOKENS.finditer(source) if match.lastgroup]
        consumed = "".join(match.group(0) for match in self.tokens)
        assert consumed.strip() == source.strip(), f"cannot tokenize: {source!r}"
        self.context = context
        self.at = 0

    def value(self) -> Any:
        result = self._or()
        assert self.at == len(self.tokens), "trailing tokens"
        return result

    def _peek(self) -> str | None:
        return self.tokens[self.at].group(0).strip() if self.at < len(self.tokens) else None

    def _take(self) -> re.Match[str]:
        token = self.tokens[self.at]
        self.at += 1
        return token

    def _or(self) -> Any:
        left = self._and()
        while self._peek() == "||":
            self._take()
            right = self._and()
            left = left if _truthy(left) else right
        return left

    def _and(self) -> Any:
        left = self._compare()
        while self._peek() == "&&":
            self._take()
            right = self._compare()
            left = right if _truthy(left) else left
        return left

    def _compare(self) -> Any:
        left = self._unary()
        if self._peek() in ("==", "!="):
            operator = self._take().group(0).strip()
            right = self._unary()
            equal = _equal(left, right)
            return equal if operator == "==" else not equal
        return left

    def _unary(self) -> Any:
        if self._peek() == "!":
            self._take()
            return not _truthy(self._unary())
        return self._primary()

    def _primary(self) -> Any:
        token = self._take()
        if token.group("op") == "(":
            inner = self._or()
            assert self._take().group(0).strip() == ")"
            return inner
        if token.group("string") is not None:
            return token.group("string")[1:-1].replace("''", "'")
        if token.group("number") is not None:
            return float(token.group("number"))
        name = token.group("name")
        if self._peek() == "(":
            self._take()
            assert self._take().group(0).strip() == ")", f"{name}() takes no arguments here"
            return {"always": True, "cancelled": False}[name]
        if name in ("true", "false"):
            return name == "true"
        if name == "null":
            return None
        value: Any = self.context
        for part in name.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value


def _truthy(value: Any) -> bool:
    if isinstance(value, float):
        return value != 0 and not math.isnan(value)
    return value not in (None, False, "")


def _number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, float):
        return value
    try:
        return float(value) if value.strip() else 0.0
    except ValueError:
        return math.nan


def _equal(left: Any, right: Any) -> bool:
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    if type(left) is type(right):
        return bool(left == right)
    return _number(left) == _number(right)


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return str(value)


def _interpolate(template: str, context: dict[str, Any]) -> str:
    """Resolve every `${{ }}` in `template`, finding each end the way GitHub does: a `}}`
    inside a single-quoted literal does not close the expression."""
    out, at = [], 0
    while (start := template.find("${{", at)) != -1:
        out.append(template[at:start])
        index, quoted = start + 3, False
        while True:
            char = template[index]
            if char == "'":
                quoted = not quoted
            elif not quoted and template.startswith("}}", index):
                break
            index += 1
        out.append(_text(_Expression(template[start + 3 : index], context).value()))
        at = index + 2
    out.append(template[at:])
    return "".join(out)


def _condition(job: dict[str, Any], context: dict[str, Any], needs: dict[str, Any]) -> bool:
    """A job's `if:`, with GitHub's implicit `success()` when no status function is named."""
    source = job.get("if")
    if source is None:
        return all(needs[name]["result"] == "success" for name in _needs(job))
    implicit_success = not any(function in source for function in _STATUS_FUNCTIONS)
    if implicit_success and any(needs[name]["result"] != "success" for name in _needs(job)):
        return False
    return _truthy(_Expression(source, context).value())


def _needs(job: dict[str, Any]) -> list[str]:
    value = job.get("needs") or []
    return [value] if isinstance(value, str) else list(value)


@dataclass
class _Run:
    """What one simulated workflow run did."""

    jobs: dict[str, dict[str, Any]]
    lane: dict[str, str]
    schema: dict | None
    prompt: str | None
    recorded: list[dict]
    local_calls: list[list[str]]
    gate: dict[str, Any] | None
    gh_calls: list[list[str]]
    errors: list[str]

    @property
    def lanes(self) -> dict[str, str]:
        """The two answers the declared path has always decided, and nothing added since."""
        return {name: self.lane[name] for name in ("sovereign_lane", "sovereign_carries")}


REASONS = {
    "ready": "all scans and applicable reviews passed",
    "review": "current head requires automated review",
    "repair": "completed checks are failing",
    "blocked": "automation is blocked pending operator action",
}

_STUB_VIBEY_GH = """#!{python}
import json, os, sys
sys.path[:0] = {paths!r}
argv = sys.argv[1:]
log = os.environ["SIM_LOG"]
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(argv) + "\\n")
if argv[:2] == ["pr-automation", "record-review"]:
    print("{{}}")
    raise SystemExit(0)
if argv[:1] == ["local-review"]:
    verdict = os.environ.get("SIM_LOCAL_VERDICT", "")
    if not verdict:
        print("local model unreachable", file=sys.stderr)
        raise SystemExit(1)
    from vibey_gh import local_review

    class _Response:
        def __init__(self, body):
            self.body = body
        def read(self):
            return self.body
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            return None

    import re

    def _open(request, timeout=None):
        # A model that read the whole prompt: it echoes both of the request's check codes.
        sent = json.loads(request.data)
        text = "".join(message["content"] for message in sent["messages"])
        codes = re.findall(r"(?:The first is|the second check code is) ([0-9a-f]+)", text)
        answer = json.loads(verdict)
        if isinstance(answer, dict):
            answer = {{local_review.CANARY_FIELD: " ".join(codes), **answer}}
        body = {{"message": {{"content": json.dumps(answer)}}, "done_reason": "stop",
                "prompt_eval_count": 10}}
        return _Response(json.dumps(body).encode())

    local_review.urllib.request.urlopen = _open
from vibey_gh.cli import main
raise SystemExit(main(argv))
"""

_STUB_GH = """#!{python}
import json, os, sys
with open(os.environ["SIM_GH_LOG"], "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
"""


class _Workflow:
    """The rendered pr-review.yml, driven one scenario at a time ("pr-evaluate.yml" is the
    scan gate and is not part of this workflow's decision surface).

    `paid_review` is the 8.b declaration the workflow is rendered with. Every scenario that
    predates it -- the two-lane review, its golden gate -- runs declared, which is the
    configuration it always described; the undeclared path has scenarios of its own."""

    def __init__(
        self,
        tmp_path: Path,
        *,
        paid_review: bool = True,
        paid_repair: bool | None = None,
        paid_conflict_resolution: bool | None = None,
        enabled: bool = True,
    ) -> None:
        from vibey_gh.config import PrAutomationConfig, PrAutomationFallbackConfig

        # Unless a scenario says otherwise, every paid use is declared together or not at
        # all: declared is the world the golden gate was captured in.
        cfg = GhConfig(
            root=tmp_path,
            pr_automation=PrAutomationConfig(
                paid_review=paid_review,
                paid_repair=paid_review if paid_repair is None else paid_repair,
                paid_conflict_resolution=(
                    paid_review if paid_conflict_resolution is None else paid_conflict_resolution
                ),
                fallback=PrAutomationFallbackConfig(enabled=enabled),
            ),
        )
        self.text = render_workflow(WORKFLOWS / "pr-review.yml", cfg)
        self.jobs = yaml.safe_load(self.text)["jobs"]
        self.tmp = tmp_path
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        source = str(Path(__file__).resolve().parent.parent)
        for name, stub in (("vibey-gh", _STUB_VIBEY_GH), ("gh", _STUB_GH)):
            path = bin_dir / name
            path.write_text(stub.format(python=sys.executable, paths=[source]), encoding="utf-8")
            path.chmod(0o755)
        self.path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        (tmp_path / "pr.diff").write_text("+ added a flag\n", encoding="utf-8")

    def _step(self, job: str, *, id: str | None = None, name: str | None = None) -> dict:
        return next(
            step
            for step in self.jobs[job]["steps"]
            if (id is not None and step.get("id") == id) or (name and step.get("name") == name)
        )

    def _bash(self, step: dict, context: dict[str, Any], extra: dict[str, str]) -> tuple:
        output = self.tmp / "github-output"
        output.write_text("", encoding="utf-8")
        # A YAML `true` in `env:` reaches the process as the string `true`, as GitHub sets it.
        env = {name: _interpolate(_text(value), context) for name, value in step["env"].items()}
        completed = subprocess.run(
            ["bash", "-c", _interpolate(step["run"], context)],
            env={
                "PATH": self.path,
                "HOME": str(self.tmp),
                "GITHUB_OUTPUT": str(output),
                "GITHUB_STEP_SUMMARY": str(self.tmp / "step-summary.md"),
                "RUNNER_TEMP": str(self.tmp),
                "GITHUB_SERVER_URL": "https://github.com",
                "GITHUB_RUN_ID": "99",
                "SIM_LOG": str(self.tmp / "vibey-gh.jsonl"),
                "SIM_GH_LOG": str(self.tmp / "gh.jsonl"),
                **env,
                **extra,
            },
            cwd=self.tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        outputs = dict(
            line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines()
        )
        return completed, outputs

    def run(
        self,
        *,
        heartbeat: bool,
        credits: bool,
        trusted: bool = True,
        same_repo: bool = True,
        state: str = "review",
        local: dict | None = None,
        paid: dict | None = None,
        refused: str | None = None,
        probe: str = "",
    ) -> _Run:
        """`refused` is the text of a paid call the API refused (`is_error` in the execution
        record) and `probe` the readiness probe's own reason."""
        for log in ("vibey-gh.jsonl", "gh.jsonl"):
            (self.tmp / log).unlink(missing_ok=True)
        errors: list[str] = []
        github = {
            "repository": "owner/repo",
            "event_name": "workflow_run",
            "event": {"repository": {"default_branch": "develop"}},
            "run_id": "99",
            "token": "token",
        }
        base = {"github": github, "inputs": {}, "secrets": {}, "runner": {"temp": str(self.tmp)}}

        # evaluate: the resolution, the scan evaluation, the probe and the branch metadata
        # are canned; the lane decision is the workflow's own step.
        steps: dict[str, Any] = {
            "resolve": {"outputs": {"pr": "12", "head_sha": "abc123"}},
            "evaluate": {
                "outputs": {
                    "state": state,
                    "evaluated_head_sha": "abc123",
                    "trusted": _text(trusted),
                    "failed_checks": "[]",
                    "repair_attempt": "0",
                    "reason": REASONS[state],
                }
            },
            "sovereign": {"outputs": {"ready": _text(heartbeat), "reason": probe}},
            "meta": {
                "outputs": {
                    "head_ref": "topic",
                    "base_ref": "develop",
                    "head_repo": "owner/repo" if same_repo else "someone/fork",
                    "fork": _text(not same_repo),
                }
            },
        }
        lane_step = self._step("evaluate", id="lane")
        completed, lane = self._bash(lane_step, {**base, "steps": steps}, {})
        assert completed.returncode == 0, completed.stderr
        steps["lane"] = {"outputs": lane}
        evaluate = {
            "result": "success",
            "outputs": {
                name: _interpolate(value, {**base, "steps": steps})
                for name, value in self.jobs["evaluate"]["outputs"].items()
            },
        }
        needs: dict[str, Any] = {"evaluate": evaluate}

        # review-sovereign: the local model is stubbed; the step that calls it is real.
        needs["review-sovereign"] = {"result": "skipped", "outputs": {}}
        context = {**base, "needs": needs}
        if _condition(self.jobs["review-sovereign"], context, needs):
            job_steps: dict[str, Any] = {
                "install": {"outcome": "success"},
                "diff": {"outcome": "success"},
                "context": {"outcome": "skipped"},
            }
            context_step = self._step("review-sovereign", id="context")
            if _truthy(_Expression(context_step["if"], context).value()):
                completed, _ = self._bash(context_step, context, {})
                assert completed.returncode == 0, completed.stderr
                job_steps["context"] = {"outcome": "success"}
            result_step = self._step("review-sovereign", id="result")
            completed, outputs = self._bash(
                result_step, context, {"SIM_LOCAL_VERDICT": json.dumps(local) if local else ""}
            )
            job_steps["result"] = {"outputs": outputs}
            if completed.returncode != 0:
                why = self._step("review-sovereign", id="why")
                done, said = self._bash(why, {**context, "steps": job_steps}, {})
                assert done.returncode == 0, done.stderr
                job_steps["why"] = {"outputs": said}
                errors += [line for line in done.stdout.splitlines() if line.startswith("::")]
            needs["review-sovereign"] = {
                "result": "success" if completed.returncode == 0 else "failure",
                "outputs": {
                    name: _interpolate(value, {**base, "steps": job_steps})
                    for name, value in self.jobs["review-sovereign"]["outputs"].items()
                },
            }

        # review: the paid model is stubbed; the half, the schema and prompt it is handed,
        # and the composition and persistence of its answer are the workflow's own.
        needs["review"] = {"result": "skipped", "outputs": {}}
        schema = prompt = None
        context = {**base, "needs": needs}
        if _condition(self.jobs["review"], context, needs):
            job_steps: dict[str, Any] = {}
            completed, outputs = self._bash(self._step("review", id="half"), context, {})
            assert completed.returncode == 0, completed.stderr
            job_steps["half"] = {"outputs": outputs}
            claude = self._step("review", id="claude")
            step_context = {**context, "steps": job_steps}
            args = shlex.split(_interpolate(claude["with"]["claude_args"], step_context))
            schema = json.loads(args[args.index("--json-schema") + 1])
            prompt = _interpolate(claude["with"]["prompt"], step_context)
            result = "failure"
            if refused is not None:
                # The action failed and left the execution record it always leaves: one
                # `result` entry, `is_error` set, nothing spent.
                record = self.tmp / "claude-execution-output.json"
                record.write_text(
                    json.dumps(
                        [
                            {"type": "system", "subtype": "init"},
                            {
                                "type": "result",
                                "subtype": "success",
                                "is_error": True,
                                "duration_ms": 369,
                                "num_turns": 1,
                                "total_cost_usd": 0,
                                "modelUsage": {},
                                "result": refused,
                            },
                        ]
                    ),
                    encoding="utf-8",
                )
                job_steps["claude"] = {"outputs": {"execution_file": str(record)}}
                done, said = self._bash(
                    self._step("review", id="why"), {**context, "steps": job_steps}, {}
                )
                assert done.returncode == 1, "a refusal is this step's error"
                job_steps["why"] = {"outputs": said}
                errors += [line for line in done.stdout.splitlines() if line.startswith("::")]
            elif credits:
                assert paid is not None
                missing = set(schema["required"]) - set(paid)
                assert not missing, f"the stubbed answer does not fit its schema: {missing}"
                job_steps["claude"] = {"outputs": {"structured_output": json.dumps(paid)}}
                completed, outputs = self._bash(
                    self._step("review", id="result"), {**context, "steps": job_steps}, {}
                )
                assert completed.returncode == 0, completed.stderr
                job_steps["result"] = {"outputs": outputs}
                result = "success"
            needs["review"] = {
                "result": result,
                "outputs": {
                    name: _interpolate(value, {**base, "steps": job_steps})
                    for name, value in self.jobs["review"]["outputs"].items()
                },
            }

        # record-sovereign: the sovereign whole review recorded, when no paid review is
        # declared; its combine and persistence are the workflow's own.
        needs["record-sovereign"] = {"result": "skipped", "outputs": {}}
        context = {**base, "needs": needs}
        if _condition(self.jobs["record-sovereign"], context, needs):
            completed, outputs = self._bash(
                self._step("record-sovereign", id="result"), context, {}
            )
            needs["record-sovereign"] = {
                "result": "success" if completed.returncode == 0 else "failure",
                "outputs": {
                    name: _interpolate(value, {**base, "steps": {"result": {"outputs": outputs}}})
                    for name, value in self.jobs["record-sovereign"]["outputs"].items()
                },
            }

        context = {**base, "needs": needs}
        for job in ("mirror-fork", "repair"):
            ran = _condition(self.jobs[job], context, needs)
            needs[job] = {"result": "success" if ran else "skipped", "outputs": {}}
        for job in ("resolve-conflict", "escalate"):
            needs[job] = {"result": "skipped", "outputs": {}}

        gate = None
        if _condition(self.jobs["gate"], context, needs):
            completed, _ = self._bash(self.jobs["gate"]["steps"][0], context, {})
            calls = [json.loads(line) for line in (self.tmp / "gh.jsonl").read_text().splitlines()]
            check = next(
                call for call in calls if call[:2] == ["api", "repos/owner/repo/check-runs"]
            )
            fields = dict(
                check[index + 1].split("=", 1) for index, token in enumerate(check) if token == "-f"
            )
            gate = {
                "exit": completed.returncode,
                "conclusion": fields["conclusion"],
                "title": fields["output[title]"],
                "summary": fields["output[summary]"],
                "merge_train": any(call[:2] == ["workflow", "run"] for call in calls),
                "stdout": completed.stdout,
            }

        gh_log = self.tmp / "gh.jsonl"
        gh_calls = (
            [json.loads(line) for line in gh_log.read_text().splitlines()]
            if gh_log.exists()
            else []
        )
        log = self.tmp / "vibey-gh.jsonl"
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        recorded = [
            json.loads(call[call.index("--input") + 1])
            for call in calls
            if call[:2] == ["pr-automation", "record-review"]
        ]
        return _Run(
            jobs={name: needs[name] for name in needs},
            lane=lane,
            schema=schema,
            prompt=prompt,
            recorded=recorded,
            local_calls=[call for call in calls if call[:1] == ["local-review"]],
            gate=gate,
            gh_calls=gh_calls,
            errors=errors,
        )


def _golden(state, review_passed, review_result, local_passed="", local_findings=""):
    return next(
        case
        for case in GOLDEN["gate"]
        if (
            case["state"],
            case["review_passed"],
            case["review_result"],
            case["local_passed"],
            case["local_findings"],
        )
        == (state, review_passed, review_result, local_passed, local_findings)
    )


# The three sanctioned differences from the golden: the job the local verdict comes from was
# renamed when it started going first; the gate's own check was renamed from
# `PR automation / gate` to `PR review / gate` when the workflow split; and the local model the
# golden was captured with became configuration that moved on, to this era's default model
# (sub-doctrine 8.d, #389) -- the model is named, never behaved on. Anything else that differs
# is a behaviour change.
_RENAMED = {
    "'Local review fallback'": "'Sovereign diff review'",
    "PR automation:": "PR review:",
    "(qwen2.5-coder:14b)": "(gpt-oss:20b)",
}


def _assert_gate_is_golden(gate: dict, golden: dict) -> None:
    expected = dict(golden)
    for old, new in _RENAMED.items():
        expected["title"] = expected["title"].replace(old, new)
        expected["summary"] = expected["summary"].replace(old, new)
        expected["stdout"] = expected["stdout"].replace(old, new)
    for key in ("exit", "conclusion", "title", "summary", "merge_train", "stdout"):
        assert gate[key] == expected[key], key


needs_bash_and_jq = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("jq") is None,
    reason="the workflow's own steps need bash and jq",
)


@pytest.fixture
def workflow(tmp_path: Path) -> _Workflow:
    return _Workflow(tmp_path)


@needs_bash_and_jq
def test_the_expression_evaluator_follows_githubs_rules():
    """The simulation is only as good as its reading of the workflow's expressions."""
    context = {"needs": {"a-b": {"outputs": {"x": "TRUE"}}}, "inputs": {}}

    def value(source):
        return _Expression(source, context).value()

    assert value("needs.a-b.outputs.x == 'true'") is True  # case-insensitive strings
    assert value("inputs.dry_run != true") is True  # null against a boolean, as numbers
    assert value("'' || 'fallback'") == "fallback"  # `||` returns an operand
    assert value("'x' && 'y'") == "y"
    assert value("!(1 == 2)") is True
    assert value("'it''s'") == "it's"
    assert value("null == 0") is True
    assert value("'abc' == 1") is False  # NaN never compares equal
    assert _truthy(0.0) is False and _truthy(1.0) is True
    assert _text(2.5) == "2.5" and _text(2.0) == "2"
    assert _interpolate("a ${{ '}}' }} b", {}) == "a }} b"


@needs_bash_and_jq
def test_fresh_heartbeat_and_credits_the_sovereign_lane_carries_the_diff_half(workflow):
    """Acceptance 1. The local model reviews the diff and its verdict stands for `pass`,
    `summary` and `findings`; the paid reviewer is handed the wider half alone, told so,
    and the gate names the lane behind each half."""
    run = workflow.run(heartbeat=True, credits=True, local=_local(), paid=_paid_wider())

    assert run.lanes == {"sovereign_lane": "true", "sovereign_carries": "true"}
    assert run.jobs["review-sovereign"]["result"] == "success"
    assert run.local_calls and run.local_calls[0][run.local_calls[0].index("--role") + 1] == (
        "sovereign"
    )
    sovereign_verdict = json.loads(run.jobs["review-sovereign"]["outputs"]["verdict"])
    assert sovereign_verdict["summary"].startswith("[SOVEREIGN LANE — ")

    # The paid call: the wider half, and nothing the sovereign lane already answered.
    full = REVIEW_CONTRACT.json_schema()
    assert run.schema == REVIEW_CONTRACT.json_schema([REQUIRES_WIDER_CONTEXT])
    assert not {"pass", "summary", "findings"} & set(run.schema["properties"])
    assert len(run.schema["required"]) < len(full["required"])
    assert len(json.dumps(run.schema, separators=(",", ":"))) < len(
        json.dumps(full, separators=(",", ":"))
    )
    assert "already been reviewed for this exact head by the sovereign lane" in run.prompt
    assert run.jobs["review"]["outputs"]["half"] == REQUIRES_WIDER_CONTEXT

    # One verdict, persisted, saying which lane carried which field.
    (verdict,) = run.recorded
    assert verdict["pass"] is True
    assert verdict["carried"]["pass"] == SOVEREIGN_LANE
    assert verdict["carried"]["links_valid"] == PAID_LANE
    assert json.loads(run.jobs["review"]["outputs"]["carried"]) == verdict["carried"]

    assert run.jobs["repair"]["result"] == "skipped"
    assert run.gate["conclusion"] == "success"
    assert run.gate["merge_train"] is True
    assert run.gate["title"] == ("PR review: gate (diff: sovereign lane, documentation: paid lane)")
    for fact in (
        "diff-groundable half (pass, summary, findings) was carried by the SOVEREIGN lane",
        "local model (gpt-oss:20b)",
        (
            "requires-wider-context half (the documentation-contract judgments) was carried by "
            "the PAID lane (claude-sonnet-5)"
        ),
    ):
        assert fact in run.gate["summary"]


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("local", "paid", "title", "repair", "said"),
    [
        pytest.param(
            _local(**{"pass": False}, findings=[FINDING]),
            _paid_wider(),
            "PR review: sovereign lane found a blocking defect in the diff",
            "skipped",
            "reported a BLOCKING finding",
            id="a local finding",
        ),
        pytest.param(
            _local(**{"pass": False}),
            _paid_wider(),
            "PR review: sovereign lane could not complete the diff review",
            "skipped",
            "declined WITHOUT reporting any finding",
            id="a local decline",
        ),
        pytest.param(
            _local(),
            _paid_wider(wider_findings=[FINDING]),
            "PR review: review findings (documentation half, paid lane)",
            "success",
            "returned actionable findings; bounded repair addresses them",
            id="a paid documentation finding",
        ),
        pytest.param(
            _local(**{"pass": False}, findings=[FINDING]),
            _paid_wider(links_valid=False),
            "PR review: review findings (both halves)",
            "success",
            "reported a BLOCKING finding",
            id="both halves",
        ),
    ],
)
def test_a_split_failure_names_the_half_and_the_lane(workflow, local, paid, title, repair, said):
    """A failing split verdict says which half failed and which lane carried it, and
    automated repair runs only for the paid lane's half: a local finding never repairs."""
    run = workflow.run(heartbeat=True, credits=True, local=local, paid=paid)

    assert run.gate["conclusion"] == "failure"
    assert run.gate["merge_train"] is False
    assert run.gate["title"] == title
    assert said in run.gate["summary"]
    assert run.jobs["repair"]["result"] == repair
    (verdict,) = run.recorded
    assert verdict["pass"] is False
    assert verdict["repairable"] is (repair == "success")
    # The recovery sweep re-probes only parked gates; a real finding must not look parked.
    assert "blocked" not in run.gate["title"] and "review incomplete" not in run.gate["title"]


@needs_bash_and_jq
@pytest.mark.parametrize("state", ["ready", "review"])
@pytest.mark.parametrize(
    ("paid", "review_passed"),
    [
        pytest.param(_paid_full(), "true", id="clean"),
        pytest.param(_paid_full(findings=[FINDING]), "false", id="a finding"),
        pytest.param(_paid_full(audience_order=False), "false", id="a judgment fails"),
        pytest.param(_paid_full(**{"pass": False}), "true", id="the model's own pass is ignored"),
    ],
)
def test_no_heartbeat_is_exactly_todays_behaviour(workflow, state, paid, review_passed):
    """Acceptance 2, as a golden diff: the sovereign lane is never offered, the paid
    reviewer is handed the schema it was always handed, and the gate publishes, word for
    word, what it published before the lanes split."""
    run = workflow.run(heartbeat=False, credits=True, state=state, paid=paid)

    assert run.lanes == {"sovereign_lane": "false", "sovereign_carries": "false"}
    assert run.jobs["review-sovereign"]["result"] == "skipped"
    assert run.local_calls == []
    assert run.schema == REVIEW_CONTRACT.json_schema()
    assert "sovereign lane" not in run.prompt
    assert run.jobs["review"]["outputs"]["half"] == FULL
    # The persisted verdict is what the old jq wrote for the same answer.
    (verdict,) = run.recorded
    old = REVIEW_COMPOSER.compose(paid, half=FULL, head_sha="abc123")["verdict"]
    assert verdict == old
    assert "carried" not in verdict and "repairable" not in verdict
    assert run.jobs["review"]["outputs"]["passed"] == review_passed
    assert run.jobs["repair"]["result"] == ("success" if review_passed == "false" else "skipped")
    _assert_gate_is_golden(run.gate, _golden(state, review_passed, "success"))


@needs_bash_and_jq
@pytest.mark.parametrize("state", ["repair", "blocked"])
def test_no_heartbeat_leaves_every_other_state_as_it_was(workflow, state):
    run = workflow.run(heartbeat=False, credits=True, state=state, paid=_paid_full())

    assert run.jobs["review"]["result"] == "skipped"
    _assert_gate_is_golden(run.gate, _golden(state, "", "skipped"))


@needs_bash_and_jq
def test_no_heartbeat_and_no_credits_is_still_review_incomplete(workflow):
    run = workflow.run(heartbeat=False, credits=False)

    assert run.jobs["review"]["result"] == "failure"
    _assert_gate_is_golden(run.gate, _golden("review", "", "failure"))


@needs_bash_and_jq
@pytest.mark.parametrize("trusted", [True, False], ids=["carrying", "in reserve"])
@pytest.mark.parametrize(
    ("local", "local_passed", "local_findings"),
    [
        pytest.param(_local(), "true", "0", id="local pass"),
        pytest.param(
            _local(**{"pass": False}, findings=[FINDING, FINDING]), "false", "2", id="local finding"
        ),
        pytest.param(_local(**{"pass": False}), "false", "0", id="local decline"),
        pytest.param(None, "", "", id="local model unreachable"),
    ],
)
def test_no_credits_is_exactly_the_local_fallback(
    workflow, trusted, local, local_passed, local_findings
):
    """Acceptance 3, as a golden diff against #277: the paid review returns no verdict, and
    the sovereign lane's verdict -- whether it was carrying the diff half or held in reserve
    -- is read as the fallback, in the fallback's own words. Nothing is persisted and
    nothing is repaired, exactly as before."""
    run = workflow.run(heartbeat=True, credits=False, trusted=trusted, local=local)

    assert run.lanes["sovereign_lane"] == "true"
    assert run.lanes["sovereign_carries"] == _text(trusted)
    role = run.local_calls[0][run.local_calls[0].index("--role") + 1]
    assert role == ("sovereign" if trusted else "fallback")
    assert run.jobs["review"]["result"] == "failure"
    assert run.jobs["review"]["outputs"]["passed"] == ""
    assert run.recorded == []
    assert run.jobs["repair"]["result"] == "skipped"
    _assert_gate_is_golden(run.gate, _golden("review", "", "failure", local_passed, local_findings))


@needs_bash_and_jq
def test_a_local_model_that_fails_hands_the_whole_review_to_the_paid_lane(workflow):
    """Fail closed without failing the gate: no sovereign verdict means the paid reviewer
    answers everything, exactly as with no heartbeat."""
    run = workflow.run(heartbeat=True, credits=True, local=None, paid=_paid_full())

    assert run.jobs["review-sovereign"]["result"] == "failure"
    assert run.schema == REVIEW_CONTRACT.json_schema()
    _assert_gate_is_golden(run.gate, _golden("review", "true", "success"))


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("paid", "review_passed"),
    [(_paid_full(), "true"), (_paid_full(findings=[FINDING]), "false")],
)
def test_an_outside_authors_diff_is_still_reviewed_in_full_by_the_paid_lane(
    workflow, paid, review_passed
):
    """The safer of the two defaults: the sovereign lane carries the diff half for trusted
    authors only. An outside author's change still gets the paid correctness and security
    review; the local verdict is held in reserve and, the paid review having answered,
    changes nothing."""
    run = workflow.run(
        heartbeat=True, credits=True, trusted=False, local=_local(**{"pass": False}), paid=paid
    )

    assert run.lanes == {"sovereign_lane": "true", "sovereign_carries": "false"}
    assert run.jobs["review-sovereign"]["result"] == "success"
    assert run.schema == REVIEW_CONTRACT.json_schema()
    assert "sovereign lane" not in run.prompt
    _assert_gate_is_golden(run.gate, _golden("review", review_passed, "success"))


@needs_bash_and_jq
def test_a_fork_never_reaches_the_self_hosted_runner(workflow):
    run = workflow.run(
        heartbeat=True, credits=True, trusted=True, same_repo=False, paid=_paid_full()
    )

    assert run.lanes == {"sovereign_lane": "false", "sovereign_carries": "false"}
    assert run.jobs["review-sovereign"]["result"] == "skipped"
    assert run.local_calls == []
    assert run.schema == REVIEW_CONTRACT.json_schema()


def test_a_repository_that_opts_out_never_offers_the_lane(tmp_path):
    """`enabled = false` renders a literal `false` into the job's condition, so GitHub
    skips the job without ever looking for a runner nobody registered."""
    from vibey_gh.config import PrAutomationConfig, PrAutomationFallbackConfig

    cfg = GhConfig(
        root=tmp_path,
        pr_automation=PrAutomationConfig(fallback=PrAutomationFallbackConfig(enabled=False)),
    )
    jobs = yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", cfg))["jobs"]

    assert jobs["review-sovereign"]["if"].startswith("false &&")
    lane = next(step for step in jobs["evaluate"]["steps"] if step.get("id") == "lane")
    assert lane["env"]["ENABLED"] is False


# --------------------------------------------------------------------------------------
# No paid review declared (sub-doctrine 8.b): the sovereign lane answers the whole review
# --------------------------------------------------------------------------------------


def test_with_no_paid_lane_the_sovereign_verdict_is_the_whole_review():
    envelope = REVIEW_COMPOSER.compose(
        None, half=NO_PAID, sovereign=_sovereign_whole(), head_sha="abc"
    )
    verdict = envelope["verdict"]

    assert envelope["half"] == NO_PAID
    assert verdict["pass"] is True
    assert verdict["head_sha"] == "abc"
    assert envelope["carried"] == {name: SOVEREIGN_LANE for name in REVIEW_CONTRACT.fields}
    assert verdict["carried"] == envelope["carried"]
    # The schema's own key order, then what the composer adds. The scope was checked, not
    # persisted: it is a fact about how the reviewer was run, not part of its answer.
    assert list(verdict) == [
        "pass",
        *JUDGMENTS,
        "summary",
        "findings",
        "head_sha",
        "carried",
        "repairable",
    ]
    assert envelope["structured"] == verdict
    assert envelope["halves"] == {FULL: {"lane": SOVEREIGN_LANE, "passed": True, "findings": 0}}
    assert envelope["findings"] == 0
    # Repair is a paid agent; with no paid lane declared nothing may reach for it.
    assert envelope["repairable"] is False and verdict["repairable"] is False


@pytest.mark.parametrize(
    ("answer", "findings"),
    [
        pytest.param(_sovereign_whole(**{"pass": False}), 0, id="the reviewer declined"),
        pytest.param(_sovereign_whole(findings=[FINDING]), 1, id="a finding"),
        pytest.param(_sovereign_whole(links_valid=False), 0, id="a judgment fails"),
        pytest.param(_sovereign_whole(links_valid="true"), 0, id="a judgment spelt as a string"),
    ],
)
def test_a_whole_sovereign_review_passes_only_on_every_count(answer, findings):
    """Its own `pass` (a local decline is a decline), every judgment exactly true, and no
    findings: the strictest reading of both halves, because nothing else looks."""
    envelope = REVIEW_COMPOSER.compose(None, half=NO_PAID, sovereign=answer, head_sha="abc")

    assert envelope["verdict"]["pass"] is False
    assert envelope["halves"][FULL]["passed"] is False
    assert envelope["findings"] == findings
    assert envelope["repairable"] is False


@pytest.mark.parametrize(
    "scope",
    [None, [DIFF_GROUNDABLE], [REQUIRES_WIDER_CONTEXT], "full", [DIFF_GROUNDABLE, "both"]],
    ids=["unstated", "diff only", "wider only", "not a list", "an unknown half"],
)
def test_a_verdict_that_did_not_answer_both_halves_never_stands_for_the_whole_review(scope):
    """A diff-only verdict writes `true` into every judgment it never made. Read as a whole
    review it would pass sixteen of them on no evidence at all -- the exact lie the
    placeholders are documented not to tell."""
    answer = _sovereign(**{"pass": True})
    if scope is None:
        del answer[REVIEW_CONTRACT.scope_field]
    else:
        answer[REVIEW_CONTRACT.scope_field] = scope

    with pytest.raises(ValueError, match="did not answer both halves"):
        REVIEW_COMPOSER.compose(None, half=NO_PAID, sovereign=answer, head_sha="abc")


def test_with_no_paid_lane_there_is_no_paid_answer_to_compose():
    with pytest.raises(ValueError, match="no paid review is declared"):
        REVIEW_COMPOSER.compose(_paid_full(), half=NO_PAID, sovereign=_sovereign_whole())
    with pytest.raises(ValueError, match="the sovereign lane's whole-review verdict is needed"):
        REVIEW_COMPOSER.compose({}, half=NO_PAID, head_sha="abc")
    with pytest.raises(TypeError, match="sovereign verdict must be a JSON object, not list"):
        REVIEW_COMPOSER.compose(None, half=NO_PAID, sovereign=[])  # type: ignore[arg-type]


def test_combine_composes_a_sovereign_only_review_from_the_command_line(capsys):
    """`vibey-gh pr-automation combine --half none` is how the workflow records it: no
    `--paid` at all, because nothing paid was asked."""
    from vibey_gh.cli import main

    code = main(
        [
            "pr-automation",
            "combine",
            "--half",
            NO_PAID,
            "--sovereign",
            json.dumps(_sovereign_whole()),
            "--head-sha",
            "abc",
        ]
    )

    assert code == 0
    envelope = json.loads(capsys.readouterr().out)
    assert envelope["verdict"]["pass"] is True
    assert envelope["carried"]["links_valid"] == SOVEREIGN_LANE

    assert main(["pr-automation", "combine", "--half", FULL, "--head-sha", "abc"]) == 1
    assert "the paid lane returned no answer to compose" in capsys.readouterr().err


# --------------------------------------------------------------------------------------
# The declaration itself
# --------------------------------------------------------------------------------------


PAID_DECLARATIONS = ("paid_review", "paid_repair", "paid_conflict_resolution")


@pytest.mark.parametrize("key", PAID_DECLARATIONS)
def test_every_paid_call_in_pr_automation_is_declared_only(tmp_path, key):
    """8.b, applied to every job that reaches the paid model -- review, repair, conflict
    resolution -- one key per use, each false unless a human writes it true."""
    from vibey_gh.config import PrAutomationConfig, load_config

    assert getattr(PrAutomationConfig(), key) is False
    assert getattr(load_config(tmp_path).pr_automation, key) is False
    (tmp_path / ".vibey-gh.toml").write_text(f"[pr_automation]\n{key} = true\n", "utf-8")
    assert getattr(load_config(tmp_path).pr_automation, key) is True
    (tmp_path / ".vibey-gh.toml").write_text(f'[pr_automation]\n{key} = "true"\n', "utf-8")
    with pytest.raises(ValueError, match=f"pr_automation.{key} must be true or false"):
        load_config(tmp_path)


@pytest.mark.parametrize("root", ["tenant", "workspace"])
def test_this_repository_declares_no_paid_pr_automation(root):
    """The operator's instruction: the sovereign lanes INSTEAD OF ANTHROPIC_API_KEY."""
    from vibey_gh.config import load_config

    tenant = Path(__file__).resolve().parent.parent
    where = (
        tenant
        if root == "tenant"
        else next(
            (parent for parent in tenant.parents if (parent / ".vibey-gh.toml").is_file()), None
        )
    )
    if where is None:  # pragma: no cover - a standalone sdist has no workspace
        pytest.skip("no workspace configuration outside the tenant")
    text = (where / ".vibey-gh.toml").read_text(encoding="utf-8")
    for key in PAID_DECLARATIONS:
        assert f"{key} = false" in text
        assert getattr(load_config(where).pr_automation, key) is False


def test_a_paid_review_is_declared_only():
    """8.b: reaching for a paid counterparty is the move that must be declared aloud, in
    the repository. Undeclared -- an absent key, a fresh configuration -- means sovereign
    only, so the default is `false` in the dataclass and the loader alike."""
    from vibey_gh.config import PrAutomationConfig, load_config

    assert PrAutomationConfig().paid_review is False
    assert (
        load_config(Path(__file__).resolve().parent / "golden").pr_automation.paid_review is False
    )


def test_the_declaration_is_read_from_pr_automation(tmp_path):
    from vibey_gh.config import load_config

    (tmp_path / ".vibey-gh.toml").write_text("[pr_automation]\npaid_review = true\n", "utf-8")

    assert load_config(tmp_path).pr_automation.paid_review is True


@pytest.mark.parametrize("value", ['"true"', "1", '"yes"', "[]"])
def test_a_declaration_that_is_not_a_boolean_is_refused_at_load(tmp_path, value):
    """A declaration is a human writing `true` into the repository. A quoted string or a
    number is not that, and reading one as truthy would reach for a paid counterparty on
    a typo -- so it is refused, loudly, before anything renders."""
    from vibey_gh.config import load_config

    (tmp_path / ".vibey-gh.toml").write_text(f"[pr_automation]\npaid_review = {value}\n", "utf-8")

    with pytest.raises(ValueError, match="pr_automation.paid_review must be true or false"):
        load_config(tmp_path)


def test_this_tenants_own_configuration_declares_no_paid_review():
    """The operator's instruction, dogfooded: the tenant that ships the declaration says in
    writing that its reviews run on the sovereign lane."""
    from vibey_gh.config import load_config

    tenant = Path(__file__).resolve().parent.parent
    text = (tenant / ".vibey-gh.toml").read_text(encoding="utf-8")

    assert "paid_review = false" in text
    assert load_config(tenant).pr_automation.paid_review is False


def test_the_whole_review_reads_the_documents_the_repository_declares(tmp_path):
    """Which documents the sovereign lane judges the documentation contract against is a
    key, not a list compiled into the workflow (12.h)."""
    from vibey_gh.config import PrAutomationFallbackConfig, load_config

    assert PrAutomationFallbackConfig().context_paths == ("README.md", "docs/index.md")
    (tmp_path / ".vibey-gh.toml").write_text(
        '[pr_automation.fallback]\ncontext_paths = ["README.md", "docs/guide.md"]\n', "utf-8"
    )

    assert load_config(tmp_path).pr_automation.fallback.context_paths == (
        "README.md",
        "docs/guide.md",
    )


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../README.md",
        "docs/../../x",
        "a b.md",
        "docs/*.md",
        "",
        "README.md?x",
        "~/x",
    ],
)
def test_a_context_path_is_a_plain_repository_path(path):
    """Each entry is fetched from the exact head through the contents API and word-split in
    a shell loop, so it may be neither absolute, nor climbing, nor spaced, nor a glob."""
    from vibey_gh.config import PrAutomationFallbackConfig

    with pytest.raises(ValueError, match="context_paths"):
        PrAutomationFallbackConfig(context_paths=(path,))


def test_context_paths_are_unique():
    from vibey_gh.config import PrAutomationFallbackConfig

    with pytest.raises(ValueError, match="context_paths entries must be unique"):
        PrAutomationFallbackConfig(context_paths=("README.md", "README.md"))


# --------------------------------------------------------------------------------------
# The rendered workflow with NO paid review declared (8.b), evaluated
# --------------------------------------------------------------------------------------

_DECLARED = "(no paid review is declared, 8.b)"


@pytest.fixture
def undeclared(tmp_path: Path) -> _Workflow:
    return _Workflow(tmp_path, paid_review=False)


def _never_paid(run: _Run) -> None:
    """Nothing on the undeclared path asks the paid model or repairs on a local verdict."""
    assert run.jobs["review"]["result"] == "skipped"
    assert run.schema is None and run.prompt is None
    assert run.jobs["repair"]["result"] == "skipped"
    assert run.jobs["mirror-fork"]["result"] == "skipped"


@needs_bash_and_jq
def test_undeclared_a_trusted_head_gets_the_whole_review_from_the_sovereign_lane(undeclared):
    """The operator's instruction: the sovereign lane instead of ANTHROPIC_API_KEY. It is
    asked the whole review, judged against the declared documents fetched read-only at the
    exact head, and its verdict alone is recorded and gates the merge."""
    run = undeclared.run(heartbeat=True, credits=True, local=_whole())

    assert run.lane["sovereign_whole"] == "true" and run.lane["human_reason"] == ""
    assert run.lanes == {"sovereign_lane": "true", "sovereign_carries": "false"}
    (call,) = run.local_calls
    assert call[call.index("--role") + 1] == "sovereign"
    assert call[call.index("--scope") + 1] == "full"
    assert call[call.index("--context-dir") + 1].endswith("/context")
    fetched = [c for c in run.gh_calls if c[:1] == ["api"] and "contents/" in " ".join(c)]
    assert [c[-1] for c in fetched] == [
        "repos/owner/repo/contents/README.md?ref=abc123",
        "repos/owner/repo/contents/docs/index.md?ref=abc123",
    ]
    _never_paid(run)

    (verdict,) = run.recorded
    assert verdict["pass"] is True
    assert set(verdict["carried"].values()) == {SOVEREIGN_LANE}
    assert verdict["summary"].startswith("[SOVEREIGN LANE — gpt-oss:20b — whole review]")
    assert run.jobs["record-sovereign"]["result"] == "success"
    assert run.gate["conclusion"] == "success"
    assert run.gate["merge_train"] is True
    assert run.gate["title"] == "PR review: gate (sovereign lane, whole review)"
    assert "no paid model was asked" in run.gate["summary"]
    assert "not a repository-wide audit" in run.gate["summary"]


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("local", "title", "said"),
    [
        pytest.param(
            _whole(**{"pass": False}, findings=[FINDING]),
            "PR review: sovereign lane found blocking findings",
            "reported 1 finding(s)",
            id="a finding",
        ),
        pytest.param(
            _whole(links_valid=False),
            "PR review: sovereign lane did not pass the review",
            "returned pass=false with no finding",
            id="a judgment fails with no finding",
        ),
    ],
)
def test_undeclared_a_failing_whole_review_is_reported_and_never_repaired(
    undeclared, local, title, said
):
    run = undeclared.run(heartbeat=True, credits=True, local=local)

    _never_paid(run)
    (verdict,) = run.recorded
    assert verdict["pass"] is False and verdict["repairable"] is False
    assert run.gate["conclusion"] == "failure"
    assert run.gate["merge_train"] is False
    assert run.gate["title"] == title
    assert said in run.gate["summary"]
    assert _DECLARED in run.gate["summary"]


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("scenario", "reason", "title"),
    [
        pytest.param(
            {"trusted": False},
            "the author is not a trusted author of this repository, and the sovereign lane"
            " reviews trusted authors only",
            "PR review: needs a human review",
            id="an outside author",
        ),
        pytest.param(
            {"same_repo": False},
            "the head is in a fork (someone/fork), which never reaches the self-hosted"
            " sovereign runner",
            "PR review: needs a human review",
            id="a fork",
        ),
        pytest.param(
            {
                "heartbeat": False,
                "probe": "the sovereign heartbeat is 90m old, past the 15m window",
            },
            "the sovereign lane is not ready: the sovereign heartbeat is 90m old, past the 15m"
            " window",
            # The one reason that clears itself: the recovery sweep re-probes a gate titled
            # "review incomplete" once the runner beats again.
            "PR review: review incomplete (needs a human review)",
            id="an unready sovereign lane",
        ),
    ],
)
def test_undeclared_nothing_the_sovereign_lane_cannot_review_gets_an_automated_pass(
    undeclared, scenario, reason, title
):
    """An outside author, a fork, or an unready lane: no automated pass, and no paid model
    asked in its place. The gate says a human is needed, and why, in so many words."""
    run = undeclared.run(**({"heartbeat": True, "credits": True} | scenario))

    assert run.lane["sovereign_whole"] == "false"
    assert run.jobs["review-sovereign"]["result"] == "skipped"
    assert run.local_calls == [] and run.recorded == []
    _never_paid(run)
    assert run.gate["conclusion"] == "failure"
    assert run.gate["merge_train"] is False
    assert run.gate["title"] == title
    assert f"needs a human review: {reason} {_DECLARED}." in run.gate["summary"]


@needs_bash_and_jq
def test_undeclared_a_lane_switched_off_says_so(tmp_path):
    run = _Workflow(tmp_path, paid_review=False, enabled=False).run(heartbeat=True, credits=True)

    assert run.jobs["review-sovereign"]["result"] == "skipped"
    _never_paid(run)
    assert run.gate["title"] == "PR review: needs a human review"
    assert (
        "needs a human review: the sovereign lane is switched off"
        " ([pr_automation.fallback] enabled = false) (no paid review is declared, 8.b)."
    ) in run.gate["summary"]


@needs_bash_and_jq
def test_undeclared_a_sovereign_lane_that_gives_no_verdict_names_the_reason(undeclared):
    """ "No verdict" is never all the gate can say: the reviewer's own reason travels from
    the step that failed, through the job, into the published check."""
    run = undeclared.run(heartbeat=True, credits=True, local=None)

    assert run.jobs["review-sovereign"]["result"] == "failure"
    assert run.jobs["review-sovereign"]["outputs"]["reason"] == "local model unreachable"
    assert "::error::the sovereign lane produced no verdict: local model unreachable" in run.errors
    assert run.jobs["record-sovereign"]["result"] == "skipped"
    _never_paid(run)
    assert run.gate["conclusion"] == "failure"
    assert run.gate["title"] == "PR review: review incomplete (needs a human review)"
    assert (
        "needs a human review: the sovereign lane produced no verdict: local model unreachable"
        f" {_DECLARED}."
    ) in run.gate["summary"]


@needs_bash_and_jq
def test_undeclared_a_blocked_head_is_as_it_was(undeclared):
    run = undeclared.run(heartbeat=True, credits=True, state="blocked")

    assert run.jobs["review"]["result"] == "skipped"
    _assert_gate_is_golden(run.gate, _golden("blocked", "", "skipped"))


_NO_PAID_REPAIR = "needs a human: automated repair needs a paid model, and none is declared (8.b)"


@needs_bash_and_jq
def test_undeclared_failing_scans_are_handed_to_a_human_not_a_paid_model(undeclared):
    """Failing scans used to start a paid repair. Undeclared, the repair job is never
    scheduled, and the gate says what that leaves: a person."""
    run = undeclared.run(heartbeat=True, credits=True, state="repair")

    assert run.jobs["repair"]["result"] == "skipped"
    assert run.jobs["mirror-fork"]["result"] == "skipped"
    assert run.gate["conclusion"] == "failure"
    assert run.gate["title"] == "PR review: needs a human (failing scans)"
    assert f"completed checks are failing. {_NO_PAID_REPAIR}." in run.gate["summary"]


@needs_bash_and_jq
def test_a_paid_review_without_paid_repair_never_promises_a_repair(tmp_path):
    """Review declared, repair not: the paid review's findings stand, and the gate no
    longer says a bounded repair will address them -- nothing will."""
    workflow = _Workflow(tmp_path, paid_review=True, paid_repair=False)
    run = workflow.run(heartbeat=False, credits=True, paid=_paid_full(findings=[FINDING]))

    assert run.jobs["review"]["result"] == "success"
    assert run.jobs["repair"]["result"] == "skipped"
    assert run.gate["title"] == "PR review: review findings"
    assert "Bounded repair" not in run.gate["summary"]
    assert _NO_PAID_REPAIR in run.gate["summary"]


@needs_bash_and_jq
@pytest.mark.parametrize("declared", [True, False])
def test_a_conflict_says_a_human_is_needed_when_no_paid_resolution_is_declared(tmp_path, declared):
    """The gate publishes nothing for a conflict (a resolution will move the head), so the
    evaluation says it, where the run's summary shows it."""
    workflow = _Workflow(tmp_path, paid_review=True, paid_conflict_resolution=declared)
    step = workflow._step("evaluate", id="unpaid")
    context = {"steps": {"evaluate": {"outputs": {"state": "conflict"}}}}

    completed, _ = workflow._bash(step, context, {})

    said = (
        "needs a human: automated conflict resolution needs a paid model, and none is"
        " declared (8.b)"
    )
    assert completed.returncode == 0
    assert (said in completed.stdout) is not declared
    summary = tmp_path / "step-summary.md"
    assert (summary.exists() and said in summary.read_text("utf-8")) is not declared


def _paid_jobs(jobs: dict) -> dict:
    """Every job that can hand anything to the paid model or read its secret."""
    return {
        name: job
        for name, job in jobs.items()
        if "claude-code-action" in json.dumps(job) or "ANTHROPIC" in json.dumps(job)
    }


def test_with_nothing_paid_declared_no_job_can_run_with_the_api_key(tmp_path):
    """What the operator's next step rests on -- deleting the ANTHROPIC_API_KEY secret:
    with every paid declaration false, every job that references the paid model or its
    secret carries a literal `false` at the head of its condition, so GitHub can never
    schedule it, whatever the event, the state or the author."""
    from vibey_gh.config import PrAutomationConfig

    cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig())
    jobs = yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", cfg))["jobs"]

    paid = _paid_jobs(jobs)
    assert set(paid) == {"review", "repair", "resolve-conflict"}
    for name, job in paid.items():
        assert job["if"].startswith("false &&"), name
        assert _truthy(_Expression(job["if"], {}).value()) is False, name
    # And the ones that stay schedulable never touch it.
    for name, job in jobs.items():
        if name not in paid:
            assert "secrets.ANTHROPIC" not in json.dumps(job), name


@pytest.mark.parametrize("key", PAID_DECLARATIONS)
def test_each_declaration_opens_exactly_its_own_job(tmp_path, key):
    from vibey_gh.config import PrAutomationConfig

    owner = {
        "paid_review": "review",
        "paid_repair": "repair",
        "paid_conflict_resolution": "resolve-conflict",
    }
    cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(**{key: True}))
    jobs = yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", cfg))["jobs"]

    for name, job in _paid_jobs(jobs).items():
        assert job["if"].startswith("true &&" if name == owner[key] else "false &&"), name


@pytest.mark.parametrize(
    ("repair", "conflict", "state", "runs"),
    [
        (False, False, "repair", False),
        (True, False, "repair", True),
        (False, False, "conflict", False),
        (False, True, "conflict", True),
        (True, False, "conflict", False),
    ],
)
def test_a_fork_is_mirrored_only_for_a_declared_paid_job(tmp_path, repair, conflict, state, runs):
    """Mirroring a fork exists so a paid repair or resolution can work on it. With neither
    declared it would replace a contributor's pull request for nothing."""
    workflow = _Workflow(
        tmp_path, paid_review=False, paid_repair=repair, paid_conflict_resolution=conflict
    )
    needs = {
        "evaluate": {"result": "success", "outputs": {"fork": "true", "state": state}},
        "review": {"result": "skipped", "outputs": {}},
    }
    context = {"inputs": {}, "needs": needs}

    assert _condition(workflow.jobs["mirror-fork"], context, needs) is runs


def test_undeclared_the_rendered_workflow_never_schedules_the_paid_review(tmp_path):
    """The declaration renders as a literal at the head of the paid job's condition, so an
    undeclared repository's workflow skips it before GitHub schedules anything -- the
    API secret is never read on that path."""
    from vibey_gh.config import PrAutomationConfig

    def jobs(paid: bool) -> dict:
        cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(paid_review=paid))
        return yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", cfg))["jobs"]

    undeclared, declared = jobs(False), jobs(True)
    assert undeclared["review"]["if"].startswith("false &&")
    assert declared["review"]["if"].startswith("true &&")
    assert undeclared["record-sovereign"]["if"].startswith("false == false &&")
    assert declared["record-sovereign"]["if"].startswith("true == false &&")
    # The default configuration is the undeclared one.
    default = yaml.safe_load(render_workflow(WORKFLOWS / "pr-review.yml", GhConfig(root=tmp_path)))[
        "jobs"
    ]
    assert default["review"]["if"].startswith("false &&")


# --------------------------------------------------------------------------------------
# Honest failures: a refused paid call is named as one (12.i)
# --------------------------------------------------------------------------------------


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("text", "said"),
    [
        pytest.param("Credit balance is too low", "Credit balance is too low", id="credit"),
        pytest.param("", "no reason given", id="no reason"),
        pytest.param(
            "Denied\n[click](https://evil.example) <b>@someone</b> `x`",
            "Denied click(https://evil.example) bsomeone/b x",
            id="markup is not published",
        ),
    ],
)
def test_a_refused_paid_review_is_named_as_a_refusal(workflow, text, said):
    """The action ends a refused call with "Result subtype: success", which is false. The
    execution record says `is_error`, so the refusal is this step's error, in plain words,
    and the gate reports it instead of a bare "review job: failure"."""
    run = workflow.run(heartbeat=False, credits=False, refused=text)

    refusal = f"the paid review was refused by the API: {said}"
    assert run.jobs["review"]["outputs"]["refusal"] == refusal
    assert f"::error::{refusal}" in run.errors
    assert run.gate["conclusion"] == "failure"
    assert run.gate["title"] == "PR review: review incomplete"
    assert f"returned no verdict ({refusal}) and no local fallback" in run.gate["summary"]


@needs_bash_and_jq
def test_a_refusal_beside_a_passing_fallback_still_names_the_refusal(workflow):
    run = workflow.run(
        heartbeat=True, credits=False, local=_local(), refused="Credit balance is too low"
    )

    assert run.gate["title"] == "PR review: gate (local fallback)"
    assert (
        "returned no verdict (the paid review was refused by the API: Credit balance is too"
        " low), so a LOCAL FALLBACK model"
    ) in run.gate["summary"]


def _refused_record(tmp_path: Path, text: str) -> Path:
    record = tmp_path / "claude-execution-output.json"
    record.write_text(
        "\n".join(  # JSONL: one of the three shapes the record has been seen to take
            json.dumps(entry)
            for entry in (
                {"type": "system", "subtype": "init"},
                {"type": "result", "subtype": "success", "is_error": True, "result": text},
            )
        ),
        encoding="utf-8",
    )
    return record


@needs_bash_and_jq
@pytest.mark.parametrize(
    ("job", "what"),
    [("review", "review"), ("repair", "repair"), ("resolve-conflict", "conflict resolution")],
)
def test_every_paid_call_names_its_own_refusal(workflow, tmp_path, job, what):
    """Wherever the workflow reads a paid result -- review, repair, conflict resolution --
    an `is_error` record is that step's error, in the same plain words."""
    record = _refused_record(tmp_path, "Credit balance is too low")
    context = {"steps": {"claude": {"outputs": {"execution_file": str(record)}}}}

    completed, outputs = workflow._bash(workflow._step(job, id="why"), context, {})

    refusal = f"the paid {what} was refused by the API: Credit balance is too low"
    assert completed.returncode == 1
    assert outputs == {"refusal": refusal}
    assert f"::error::{refusal}" in completed.stdout.splitlines()


@needs_bash_and_jq
def test_a_call_that_was_not_refused_raises_no_refusal(workflow, tmp_path):
    """A model that ran and answered badly is not the API refusing it: the step keeps
    reporting the facts, and names no refusal."""
    record = tmp_path / "claude-execution-output.json"
    record.write_text(json.dumps({"type": "result", "is_error": False, "result": "ok"}), "utf-8")
    context = {"steps": {"claude": {"outputs": {"execution_file": str(record)}}}}

    completed, outputs = workflow._bash(workflow._step("repair", id="why"), context, {})

    assert completed.returncode == 0
    assert outputs == {}
    assert "is_error=false" in completed.stdout


@needs_bash_and_jq
def test_a_refused_repair_is_named_in_the_gate(workflow, tmp_path):
    gate = workflow.jobs["gate"]
    refusal = "the paid repair was refused by the API: Credit balance is too low"
    needs = {
        "evaluate": {"outputs": {"pr": "12", "head_sha": "abc123", "state": "repair"}},
        "repair": {"result": "failure", "outputs": {"refusal": refusal}},
    }
    context = {
        "github": {"repository": "owner/repo", "event": {"repository": {}}},
        "needs": needs
        | {"evaluate": {"outputs": needs["evaluate"]["outputs"] | {"reason": REASONS["repair"]}}},
    }

    completed, _ = workflow._bash(gate["steps"][0], context, {})

    calls = [json.loads(line) for line in (tmp_path / "gh.jsonl").read_text().splitlines()]
    (check,) = [call for call in calls if call[:2] == ["api", "repos/owner/repo/check-runs"]]
    assert f"output[summary]=completed checks are failing. {refusal}. Run " in " ".join(check)
    assert completed.returncode == 1


# --------------------------------------------------------------------------------------
# The sovereign model's window, declared from the host's own measurement (#1090)
# --------------------------------------------------------------------------------------


def test_the_sovereign_models_window_is_declared_not_compiled_in(tmp_path):
    from vibey_gh import fit
    from vibey_gh.config import PrAutomationFallbackConfig, load_config

    default = PrAutomationFallbackConfig()
    assert default.context_window == fit.DEFAULT_CONTEXT_CEILING_TOKENS == 65536
    assert default.reasoning_reserve_tokens == fit.DEFAULT_CONTEXT_RESERVE_TOKENS == 8192
    assert default.chars_per_token == fit.DEFAULT_CHARS_PER_TOKEN == 3
    # The configuration's bound on it is the sizer's own.
    PrAutomationFallbackConfig(chars_per_token=fit.MAX_CHARS_PER_TOKEN)
    with pytest.raises(ValueError, match="chars_per_token"):
        PrAutomationFallbackConfig(chars_per_token=fit.MAX_CHARS_PER_TOKEN + 1)
    assert default.think == ""  # the model's own default: fidelity is not traded blind
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.fallback]\ncontext_window = 131072\nreasoning_reserve_tokens = 4096\n"
        'chars_per_token = 4\nthink = "low"\n',
        "utf-8",
    )
    loaded = load_config(tmp_path).pr_automation.fallback
    assert (loaded.context_window, loaded.reasoning_reserve_tokens) == (131072, 4096)
    assert (loaded.chars_per_token, loaded.think) == (4, "low")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"context_window": 2048}, "context_window"),
        ({"reasoning_reserve_tokens": 512}, "reasoning_reserve_tokens"),
        ({"reasoning_reserve_tokens": 65536}, "reasoning_reserve_tokens"),
        ({"chars_per_token": 0}, "chars_per_token"),
        ({"chars_per_token": 9}, "chars_per_token"),
        ({"chars_per_token": 2.5}, "chars_per_token"),
        ({"chars_per_token": float("nan")}, "chars_per_token"),
        ({"think": "max"}, "think"),
        ({"max_document_chars": 999}, "max_document_chars"),
        ({"max_document_chars": 5000.0}, "max_document_chars"),
    ],
)
def test_a_window_that_could_not_hold_a_review_is_refused(changes, message):
    from vibey_gh.config import PrAutomationFallbackConfig

    with pytest.raises(ValueError, match=message):
        PrAutomationFallbackConfig(**changes)


@pytest.mark.parametrize("name", ["pr-review.yml", "issue-automation.yml"])
def test_every_local_model_call_is_handed_the_declared_window(tmp_path, name):
    """The runner's working directory holds no .vibey-gh.toml, so a window left to the
    command's defaults would be the package's, not the host's own measurement."""
    from vibey_gh.config import PrAutomationConfig, PrAutomationFallbackConfig

    fallback = PrAutomationFallbackConfig(
        context_window=131072, reasoning_reserve_tokens=6000, chars_per_token=4, think="low"
    )
    cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(fallback=fallback))
    text = render_workflow(WORKFLOWS / name, cfg)

    assert "--context-window 131072" in text
    assert "--reasoning-reserve 6000" in text
    assert "--chars-per-token 4" in text
    assert "--think 'low'" in text


def test_the_documents_have_a_limit_of_their_own_not_the_diffs(tmp_path):
    """`max_document_chars` bounds the whole review's documents; `max_diff_chars` bounds the
    diff. Tied together, this repository's own two pages reached the diff's 60,000 and a
    small README edit turned every gate red. Declared, loaded, and handed to the review."""
    from vibey_gh.config import PrAutomationConfig, PrAutomationFallbackConfig, load_config

    assert PrAutomationFallbackConfig().max_document_chars == 120000
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.fallback]\nmax_document_chars = 250000\n", "utf-8"
    )
    assert load_config(tmp_path).pr_automation.fallback.max_document_chars == 250000

    fallback = PrAutomationFallbackConfig(max_diff_chars=50000, max_document_chars=250000)
    cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(fallback=fallback))
    text = render_workflow(WORKFLOWS / "pr-review.yml", cfg)
    assert "--max-chars 50000 \\\n                --max-document-chars 250000" in text
