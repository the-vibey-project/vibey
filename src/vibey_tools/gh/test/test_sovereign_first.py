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
    return _local(**changes) | REVIEW_CONTRACT.placeholders()


# --------------------------------------------------------------------------------------
# The composer
# --------------------------------------------------------------------------------------


def test_the_composer_satisfies_its_declared_seam():
    assert isinstance(REVIEW_COMPOSER, ReviewComposerPort)
    assert REVIEW_COMPOSER == ReviewComposer()
    assert PAID_HALVES == (FULL, REQUIRES_WIDER_CONTEXT)


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
    with pytest.raises(ValueError, match="paid half must be one of full, requires-wider-context"):
        REVIEW_COMPOSER.compose(_paid_full(), half=half, head_sha="abc")


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

    body = json.dumps({{"message": {{"content": verdict}}}}).encode()
    local_review.urllib.request.urlopen = lambda request, timeout=None: _Response(body)
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
    scan gate and is not part of this workflow's decision surface)."""

    def __init__(self, tmp_path: Path) -> None:
        self.text = render_workflow(WORKFLOWS / "pr-review.yml", GhConfig(root=tmp_path))
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
    ) -> _Run:
        for log in ("vibey-gh.jsonl", "gh.jsonl"):
            (self.tmp / log).unlink(missing_ok=True)
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
            "sovereign": {"outputs": {"ready": _text(heartbeat)}},
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
            result_step = self._step("review-sovereign", id="result")
            completed, outputs = self._bash(
                result_step, context, {"SIM_LOCAL_VERDICT": json.dumps(local) if local else ""}
            )
            job_steps = {"result": {"outputs": outputs}}
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
            if credits:
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

    assert run.lane == {"sovereign_lane": "true", "sovereign_carries": "true"}
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

    assert run.lane == {"sovereign_lane": "false", "sovereign_carries": "false"}
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

    assert run.lane["sovereign_lane"] == "true"
    assert run.lane["sovereign_carries"] == _text(trusted)
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

    assert run.lane == {"sovereign_lane": "true", "sovereign_carries": "false"}
    assert run.jobs["review-sovereign"]["result"] == "success"
    assert run.schema == REVIEW_CONTRACT.json_schema()
    assert "sovereign lane" not in run.prompt
    _assert_gate_is_golden(run.gate, _golden("review", review_passed, "success"))


@needs_bash_and_jq
def test_a_fork_never_reaches_the_self_hosted_runner(workflow):
    run = workflow.run(
        heartbeat=True, credits=True, trusted=True, same_repo=False, paid=_paid_full()
    )

    assert run.lane == {"sovereign_lane": "false", "sovereign_carries": "false"}
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
    assert jobs["evaluate"]["steps"][-1]["env"]["ENABLED"] is False
