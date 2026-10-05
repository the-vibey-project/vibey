# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh approve-check`: the delegated approver's grant, enforced by code (12.f, 12.j).

Before this command existed every condition of `[unattended_approval]` was an instruction to a
model -- read the grant, read the switch, compare the author, look for forbidden paths, look at
the checks -- and nothing in the tree read `authors`, `forbidden_paths` or the live variable at
all. An instruction is a hope with a good track record; these tests hold the replacement to the
standard the grant sets: every condition is checked, every failure is named, and anything the
check could not read is a refusal rather than a pass.

The forge is replaced at two declared seams -- the transport's `survey` and the pull-request
reader -- never by patching an import (9.b).
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import approval_check, cli, merge_train
from vibey_gh.approval_check import ApprovalCheck, ApprovalVerdict
from vibey_gh.config import (
    CODEOWNERS_SENTINEL,
    ApprovalLaneConfig,
    ApprovalTierConfig,
    GhConfig,
    PrAutomationConfig,
    UnattendedApprovalConfig,
    load_config,
)
from vibey_gh.interfaces.approval_check_interface import (
    ApprovalCheckInterface,
    ApprovalVerdictInterface,
)
from vibey_gh.protected_paths import CHANGED_PATHS_KEY, LISTED_FILES_KEY

REPO_ROOT = Path(__file__).resolve().parents[4]
HEAD = "a" * 40
OPERATOR = "adammatthewsteinberger"
APPROVER = "vibey-approver"
VARIABLE = "repos/{owner}/{repo}/actions/variables/VIBEY_UNATTENDED_APPROVAL"


def grant(**kw: Any) -> UnattendedApprovalConfig:
    base: dict[str, Any] = dict(
        enabled=True,
        branches=("develop",),
        authors=(OPERATOR,),
        forbidden_paths=(".vibey-gh.toml", ".github/**", "**/.claude/settings.json"),
    )
    base.update(kw)
    return UnattendedApprovalConfig(**base)


def config(root: Path, **kw: Any) -> GhConfig:
    return GhConfig(
        root=root,
        pr_automation=PrAutomationConfig(enabled=True),
        unattended_approval=grant(**kw),
    )


def green(*names: str) -> list[dict[str, Any]]:
    return [
        {"name": name, "status": "COMPLETED", "conclusion": "SUCCESS"}
        for name in (*merge_train.GATES, "gates", *names)
    ]


def pull_request(**kw: Any) -> dict[str, Any]:
    pr: dict[str, Any] = dict(
        number=7,
        state="OPEN",
        isDraft=False,
        author={"login": OPERATOR},
        baseRefName="develop",
        headRefOid=HEAD,
        statusCheckRollup=green(),
        changedFiles=1,
    )
    pr[CHANGED_PATHS_KEY] = ["src/vibey/domain/rotation.py"]
    pr[LISTED_FILES_KEY] = 1
    pr.update(kw)
    return pr


class Forge:
    """A `survey`-only transport answering from a table, and naming what it was asked.

    An unscripted question is answered the way the real transport answers a failed call --
    an empty value and a problem sentence -- so a test cannot pass by reaching a call it
    never named.
    """

    executable = "gh"

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def survey(self, args, *, cwd=None, stdin=None):
        key = " ".join(args)
        self.asked.append(key)
        answer = self.answers.get(key, "unscripted")
        if isinstance(answer, str):
            return [], f"`gh {key}` failed: {answer}"
        return answer, ""


def forge(**overrides: Any) -> Forge:
    answers: dict[str, Any] = {
        f"api {VARIABLE}": {"name": "VIBEY_UNATTENDED_APPROVAL", "value": "on"},
        "api user": {"login": APPROVER},
        "pr view 7 --json commits": {"commits": [{"authors": [{"login": OPERATOR}]}]},
    }
    answers.update(overrides)
    return Forge(answers)


def check(
    tmp_path: Path,
    *,
    pr: dict[str, Any] | Exception | None = None,
    transport: Forge | None = None,
    **grant_kw: Any,
) -> ApprovalCheck:
    cfg = config(tmp_path, **grant_kw)
    answer = pull_request() if pr is None else pr

    def reader(number: int, given: GhConfig) -> dict[str, Any]:
        assert number == 7
        if isinstance(answer, Exception):
            raise answer
        return answer

    return ApprovalCheck(
        config=lambda: cfg,
        transport=transport or forge(),
        reader=reader,
    )


def refusals(tmp_path: Path, **kw: Any) -> tuple[str, ...]:
    return check(tmp_path, **kw).evaluate(7).refusals


# ------------------------------------------------------------------------------ the seam


def test_the_check_and_its_verdict_implement_their_interfaces(tmp_path: Path) -> None:
    subject = check(tmp_path)
    assert isinstance(subject, ApprovalCheckInterface)
    assert isinstance(subject.evaluate(7), ApprovalVerdictInterface)


def test_every_condition_holding_is_the_only_way_to_a_grant(tmp_path: Path) -> None:
    verdict = check(tmp_path).evaluate(7)
    assert verdict.refusals == ()
    assert verdict.granted
    assert verdict.head == HEAD


# ------------------------------------------------------------------ 1. the grant is in force


def test_a_disabled_grant_refuses(tmp_path: Path) -> None:
    cfg = GhConfig(root=tmp_path, unattended_approval=UnattendedApprovalConfig())
    subject = ApprovalCheck(
        config=lambda: cfg, transport=forge(), reader=lambda n, c: pull_request()
    )
    assert any("enabled is false" in r for r in subject.evaluate(7).refusals)


def test_a_grant_that_cannot_be_loaded_refuses(tmp_path: Path) -> None:
    def broken() -> GhConfig:
        raise ValueError("unattended_approval.authors must not be empty when enabled")

    verdict = ApprovalCheck(config=broken, transport=forge(), reader=lambda n, c: {}).evaluate(7)
    assert not verdict.granted
    assert verdict.head == ""
    assert "could not be read" in verdict.refusals[0]
    assert "authors must not be empty" in verdict.refusals[0]


@pytest.mark.parametrize(
    "answer, why",
    [
        ("HTTP 404: Not Found", "could not be read"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": "off"}, "reads 'off'"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": ""}, "reads ''"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": "on "}, "reads 'on '"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": "ON"}, "reads 'ON'"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL"}, "malformed"),
        ([{"value": "on"}], "malformed"),
    ],
    ids=["absent-or-unreadable", "off", "empty", "trailing-space", "case", "no-value", "list"],
)
def test_the_live_switch_must_read_exactly_on(tmp_path: Path, answer: Any, why: str) -> None:
    """Absent, off, empty, malformed and unreadable are all the same answer: no."""
    found = refusals(tmp_path, transport=forge(**{f"api {VARIABLE}": answer}))
    assert len(found) == 1
    assert "VIBEY_UNATTENDED_APPROVAL" in found[0]
    assert why in found[0]


def test_the_switch_is_read_by_its_declared_name_and_value(tmp_path: Path) -> None:
    """12.h: the variable and the value it must hold are declared, never compiled in."""
    custom = "repos/{owner}/{repo}/actions/variables/APPROVER_SWITCH"
    transport = forge(**{f"api {custom}": {"name": "APPROVER_SWITCH", "value": "granted"}})
    found = refusals(
        tmp_path,
        transport=transport,
        switch_variable="APPROVER_SWITCH",
        switch_value="granted",
    )
    assert found == ()
    assert f"api {custom}" in transport.asked
    assert f"api {VARIABLE}" not in transport.asked


# With `live_switch_required = false` the declared grant alone turns approval on, and the
# variable keeps only the power 12.f says must never need a merge: withdrawal.
@pytest.mark.parametrize(
    "answer",
    ["HTTP 404: Not Found", {"name": "VIBEY_UNATTENDED_APPROVAL", "value": "on"}],
    ids=["unset", "on"],
)
def test_a_declared_grant_stands_while_nobody_has_withdrawn_it(tmp_path: Path, answer: Any) -> None:
    transport = forge(**{f"api {VARIABLE}": answer})
    assert refusals(tmp_path, transport=transport, live_switch_required=False) == ()


@pytest.mark.parametrize(
    "answer, why",
    [
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": "off"}, "withdrawn"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": ""}, "withdrawn"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL", "value": "ON"}, "withdrawn"),
        ("HTTP 403: Resource not accessible by integration", "only its absence"),
        ("connection reset by peer", "only its absence"),
        ({"name": "VIBEY_UNATTENDED_APPROVAL"}, "malformed"),
    ],
    ids=["off", "empty", "case", "forbidden", "network", "no-value"],
)
def test_a_declared_grant_is_withdrawn_or_refused_by_anything_else(
    tmp_path: Path, answer: Any, why: str
) -> None:
    """Any value but the documented one withdraws at once, and a variable that cannot be
    read cannot show nobody withdrew -- only a clean 404 says the variable is unset."""
    found = refusals(
        tmp_path, transport=forge(**{f"api {VARIABLE}": answer}), live_switch_required=False
    )
    assert len(found) == 1
    assert "VIBEY_UNATTENDED_APPROVAL" in found[0] and why in found[0]


def test_the_default_still_needs_the_variable_to_say_on(tmp_path: Path) -> None:
    found = refusals(tmp_path, transport=forge(**{f"api {VARIABLE}": "HTTP 404: Not Found"}))
    assert len(found) == 1 and "absence and unreadability are both refusal" in found[0]


# -------------------------------------------------------------------- 2. whose change it is


def test_an_author_outside_the_allowlist_is_refused(tmp_path: Path) -> None:
    found = refusals(tmp_path, pr=pull_request(author={"login": "app/dependabot"}))
    assert found == ("author: @app/dependabot is not in [unattended_approval] authors",)


def test_a_bot_login_matches_whichever_way_it_is_spelled(tmp_path: Path) -> None:
    assert (
        refusals(
            tmp_path, authors=("renovate[bot]",), pr=pull_request(author={"login": "app/renovate"})
        )
        == ()
    )


def test_the_codeowners_sentinel_is_expanded_by_the_shared_function(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODEOWNERS").write_text(f"*  @{OPERATOR}\n", encoding="utf-8")
    assert refusals(tmp_path, authors=(CODEOWNERS_SENTINEL,)) == ()


def test_a_missing_codeowners_expands_the_sentinel_to_nobody(tmp_path: Path) -> None:
    found = refusals(tmp_path, authors=(CODEOWNERS_SENTINEL,))
    assert found == ("author: [unattended_approval] authors expands to nobody",)


# ------------------------------------------------------------------------ 3. where it lands


def test_a_base_branch_outside_the_grant_is_refused(tmp_path: Path) -> None:
    found = refusals(tmp_path, branches=("lane/*",))
    assert found == ("branch: base 'develop' matches no [unattended_approval] branches glob",)


def test_a_branch_glob_admits_what_it_names(tmp_path: Path) -> None:
    assert refusals(tmp_path, branches=("lane/*",), pr=pull_request(baseRefName="lane/s2")) == ()


# ---------------------------------------------------------------------- 4. what it touches


def test_one_forbidden_path_refuses_the_whole_pull_request(tmp_path: Path) -> None:
    pr = pull_request(changedFiles=3)
    pr[CHANGED_PATHS_KEY] = ["src/a.py", ".github/workflows/ci.yml", "src/b.py"]
    pr[LISTED_FILES_KEY] = 3
    found = refusals(tmp_path, pr=pr)
    assert found == ("forbidden path: touches .github/workflows/ci.yml",)


@pytest.mark.parametrize(
    "path",
    [".claude/settings.json", "src/vibey_runners/claude/.claude/settings.json"],
    ids=["zero-directories", "nested"],
)
def test_a_leading_double_star_matches_zero_directories_too(tmp_path: Path, path: str) -> None:
    """`**/x` forbids `x` at the root as well as below it.

    The repository's own matcher reads `**` as `*`, and there `**/x` needs a `/` before `x` --
    so the root copy escapes unless it is listed separately. A forbidden list is a bound; the
    reading that forbids MORE is the one that holds, so both readings are applied.
    """
    pr = pull_request()
    pr[CHANGED_PATHS_KEY] = [path]
    found = refusals(
        tmp_path, forbidden_paths=(".vibey-gh.toml", "**/.claude/settings.json"), pr=pr
    )
    assert found == (f"forbidden path: touches {path}",)


def test_an_interior_double_star_matches_zero_directories_too(tmp_path: Path) -> None:
    pr = pull_request(changedFiles=2)
    pr[CHANGED_PATHS_KEY] = ["docs/tools/lane.py", "docs/plans/x/y/tools/lane.py"]
    pr[LISTED_FILES_KEY] = 2
    found = refusals(tmp_path, forbidden_paths=(".vibey-gh.toml", "docs/**/tools/**"), pr=pr)
    assert found == ("forbidden path: touches docs/plans/x/y/tools/lane.py, docs/tools/lane.py",)


def test_many_forbidden_paths_are_summarised(tmp_path: Path) -> None:
    pr = pull_request(changedFiles=5)
    pr[CHANGED_PATHS_KEY] = [f".github/{n}.yml" for n in "abcde"]
    pr[LISTED_FILES_KEY] = 5
    (found,) = refusals(tmp_path, pr=pr)
    assert found.endswith("and 2 more")


def test_an_unlisted_change_cannot_be_ruled_clean(tmp_path: Path) -> None:
    pr = pull_request()
    del pr[CHANGED_PATHS_KEY]
    found = refusals(tmp_path, pr=pr)
    assert found == ("forbidden path: the changed files could not be listed",)


def test_a_truncated_listing_cannot_be_ruled_clean(tmp_path: Path) -> None:
    found = refusals(tmp_path, pr=pull_request(changedFiles=3000))
    assert found == ("forbidden path: GitHub listed 1 of 3000 changed files",)


def test_the_default_reader_lists_changed_files_for_the_forbidden_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The merge train's own reader does the listing, asked for it through the one key it reads."""
    seen: list[tuple[int, GhConfig | None]] = []

    def reader(number: int, cfg: GhConfig | None = None) -> dict[str, Any]:
        seen.append((number, cfg))
        return pull_request()

    monkeypatch.setattr(merge_train, "pull_request", reader)
    cfg = config(tmp_path)
    assert ApprovalCheck.read_pull_request(7, cfg) == pull_request()
    ((number, given),) = seen
    assert number == 7
    assert given is not None
    assert given.protected_paths == cfg.unattended_approval.forbidden_paths


# ------------------------------------------------------------------------- 5. the gates


def test_a_failing_check_refuses(tmp_path: Path) -> None:
    rollup = [*green(), {"name": "CodeQL", "status": "COMPLETED", "conclusion": "FAILURE"}]
    found = refusals(tmp_path, pr=pull_request(statusCheckRollup=rollup))
    assert found == ("gates: failing — CodeQL",)


def test_a_running_check_refuses(tmp_path: Path) -> None:
    rollup = [*green(), {"name": "CodeQL", "status": "IN_PROGRESS", "conclusion": None}]
    found = refusals(tmp_path, pr=pull_request(statusCheckRollup=rollup))
    assert found == ("gates: still running — CodeQL",)


def test_a_missing_required_gate_refuses(tmp_path: Path) -> None:
    rollup = [c for c in green() if c["name"] != "PR review / gate"]
    found = refusals(tmp_path, pr=pull_request(statusCheckRollup=rollup))
    assert found == ("gates: not green on this head — PR review / gate",)


@pytest.mark.parametrize(
    "state, label",
    [("PENDING", "still running"), ("EXPECTED", "still running"), ("ERROR", "failing")],
)
def test_a_commit_status_counts_as_a_gate_too(tmp_path: Path, state: str, label: str) -> None:
    """A status carries `state`, not `status`/`conclusion`; reading only the latter passes it."""
    rollup = [*green(), {"context": "ci/legacy", "state": state}]
    assert refusals(tmp_path, pr=pull_request(statusCheckRollup=rollup)) == (
        f"gates: {label} — ci/legacy",
    )
    passing = [*green(), {"context": "ci/legacy", "state": "SUCCESS"}]
    assert refusals(tmp_path, pr=pull_request(statusCheckRollup=passing)) == ()


def test_the_automation_own_leftovers_are_not_counted(tmp_path: Path) -> None:
    """The same exclusions the merge train applies, read from the same place."""
    leftover = {"name": "Evaluate current head", "status": "COMPLETED", "conclusion": "CANCELLED"}
    assert refusals(tmp_path, pr=pull_request(statusCheckRollup=[*green(), leftover])) == ()


def test_gates_are_not_read_when_the_grant_does_not_require_them(tmp_path: Path) -> None:
    assert refusals(tmp_path, require_all_gates=False, pr=pull_request(statusCheckRollup=[])) == ()


# ------------------------------------------------------------------- 6. who is approving


def test_the_approver_may_not_approve_its_own_account_s_pull_request(tmp_path: Path) -> None:
    found = refusals(tmp_path, transport=forge(**{"api user": {"login": OPERATOR}}))
    assert found == (f"authorship: the approving account @{OPERATOR} is the pull request's author",)


def test_the_approver_may_not_approve_a_commit_its_account_wrote(tmp_path: Path) -> None:
    commits = {"commits": [{"authors": [{"login": OPERATOR}, {"login": "app/" + APPROVER}]}]}
    found = refusals(tmp_path, transport=forge(**{"pr view 7 --json commits": commits}))
    assert found == (
        f"authorship: the approving account @{APPROVER} authored a commit in this pull request",
    )


@pytest.mark.parametrize(
    "key, answer",
    [
        ("api user", "HTTP 401"),
        ("api user", {"name": "no login"}),
        ("pr view 7 --json commits", "HTTP 502"),
        ("pr view 7 --json commits", {"commits": "none"}),
        ("pr view 7 --json commits", {"commits": [{"authors": "none"}]}),
    ],
    ids=[
        "identity-unreadable",
        "identity-malformed",
        "commits-unreadable",
        "commits-malformed",
        "authors-malformed",
    ],
)
def test_authorship_that_cannot_be_established_refuses(
    tmp_path: Path, key: str, answer: Any
) -> None:
    (found,) = refusals(tmp_path, transport=forge(**{key: answer}))
    assert found.startswith("authorship: ")
    assert "could not be established" in found


def test_a_commit_listing_that_may_be_truncated_refuses(tmp_path: Path) -> None:
    many = {"commits": [{"authors": [{"login": OPERATOR}]}] * 100}
    (found,) = refusals(tmp_path, transport=forge(**{"pr view 7 --json commits": many}))
    assert "may be truncated" in found


# ----------------------------------------------------------------- the pull request itself


def test_a_pull_request_that_cannot_be_read_refuses_and_still_reports_the_rest(
    tmp_path: Path,
) -> None:
    found = refusals(
        tmp_path,
        pr=RuntimeError("gh pr view 7: HTTP 502"),
        transport=forge(**{f"api {VARIABLE}": {"value": "off"}}),
    )
    assert len(found) == 2
    assert "reads 'off'" in found[0]
    assert found[1] == "pull request: #7 could not be read from the forge (gh pr view 7: HTTP 502)"


@pytest.mark.parametrize(
    "field, value, why",
    [("state", "MERGED", "is MERGED, not open"), ("isDraft", True, "is a draft")],
)
def test_only_an_open_ready_pull_request_is_approvable(
    tmp_path: Path, field: str, value: Any, why: str
) -> None:
    assert refusals(tmp_path, pr=pull_request(**{field: value})) == (f"pull request: {why}",)


def test_a_pinned_head_that_has_moved_refuses(tmp_path: Path) -> None:
    """What was examined is what is approved, or nothing is."""
    verdict = check(tmp_path).evaluate(7, head="b" * 40)
    assert verdict.refusals == (f"head: is {HEAD}, not the pinned {'b' * 40}",)
    assert check(tmp_path).evaluate(7, head=HEAD).granted


def test_every_refusal_is_reported_not_just_the_first(tmp_path: Path) -> None:
    """12.d: the refusals are the most useful part of the report."""
    pr = pull_request(author={"login": "stranger"}, baseRefName="main")
    pr[CHANGED_PATHS_KEY] = [".vibey-gh.toml"]
    found = refusals(tmp_path, pr=pr, transport=forge(**{f"api {VARIABLE}": {"value": "off"}}))
    assert [r.split(":")[0] for r in found] == [
        "switch",
        "author",
        "branch",
        "forbidden path",
    ]


# ------------------------------------------------------------------------------ reporting


def test_run_prints_every_refusal_and_exits_non_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    subject = check(tmp_path, branches=("lane/*",), transport=forge(**{"api user": "HTTP 401"}))
    assert subject.run(7) == 1
    out = capsys.readouterr().out
    assert out.startswith(f"vibey-gh approve-check: #7 at {HEAD}: REFUSED")
    assert "  - branch: " in out
    assert "  - authorship: " in out


def test_run_names_the_head_it_granted_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert check(tmp_path).run(7) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"vibey-gh approve-check: #7 at {HEAD}: every condition")
    assert f"--head {HEAD}" in out


def test_a_verdict_with_no_head_says_so() -> None:
    report = ApprovalVerdict(number=7, head="", refusals=("x",)).report()
    assert report.startswith("vibey-gh approve-check: #7 at an unknown head: REFUSED")


def test_the_command_is_registered_and_passes_its_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Any, ...]] = []

    def run(
        self: ApprovalCheck,
        number: int,
        head: str | None = None,
        approve: bool = False,
        body: str | None = None,
    ) -> int:
        calls.append((number, head, approve, body))
        return 1

    monkeypatch.setattr(ApprovalCheck, "run", run)
    assert cli.main(["approve-check", "12"]) == 1
    assert cli.main(["approve-check", "12", "--head", HEAD]) == 1
    assert cli.main(["approve-check", "12", "--head", HEAD, "--approve", "--body", "V"]) == 1
    assert calls == [
        (12, None, False, None),
        (12, HEAD, False, None),
        (12, HEAD, True, "V"),
    ]


# ----------------------------------------------------------- the declared switch, validated


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"switch_variable": ""}, "switch_variable"),
        ({"switch_variable": "HAS SPACE"}, "switch_variable"),
        ({"switch_value": ""}, "switch_value"),
        ({"switch_value": " on"}, "switch_value"),
    ],
)
def test_a_switch_that_could_never_be_read_is_refused_at_load(
    kw: dict[str, str], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        grant(**kw)


def test_the_switch_keys_load_from_the_table(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        "[unattended_approval]\n"
        "enabled = true\n"
        'branches = ["develop"]\n'
        f'authors = ["{OPERATOR}"]\n'
        'switch_variable = "APPROVER_SWITCH"\n'
        'switch_value = "granted"\n',
        encoding="utf-8",
    )
    loaded = load_config(tmp_path).unattended_approval
    assert (loaded.switch_variable, loaded.switch_value) == ("APPROVER_SWITCH", "granted")
    assert dataclasses.replace(loaded, switch_variable="X").switch_variable == "X"


def test_the_switch_defaults_to_the_documented_variable() -> None:
    default = UnattendedApprovalConfig()
    assert (default.switch_variable, default.switch_value) == ("VIBEY_UNATTENDED_APPROVAL", "on")
    assert default.live_switch_required is True


def test_live_switch_required_loads_from_the_table(tmp_path: Path) -> None:
    (tmp_path / ".vibey-gh.toml").write_text(
        "[unattended_approval]\n"
        "enabled = true\n"
        'branches = ["develop"]\n'
        f'authors = ["{OPERATOR}"]\n'
        "live_switch_required = false\n",
        encoding="utf-8",
    )
    assert load_config(tmp_path).unattended_approval.live_switch_required is False


@pytest.mark.parametrize("value", [0, "", "false", None])
def test_live_switch_required_must_be_exactly_a_bool(value: Any) -> None:
    with pytest.raises(TypeError, match="live_switch_required"):
        UnattendedApprovalConfig(live_switch_required=value)


# ------------------------------------------------------- this repository's own grant, read


@pytest.mark.parametrize(
    "path",
    [
        ".vibey-gh.toml",
        ".claude/agents/unattended-approver.md",
        ".claude/settings.json",
        ".github/workflows/ci.yml",
        "src/vibey_tools/gh/vibey_gh/approval_check.py",
        "src/vibey_tools/gh/vibey_gh/interfaces/approval_check_interface.py",
        "src/vibey_tools/gh/vibey_gh/protected_paths.py",
        "src/vibey_tools/gh/vibey_gh/merge_train.py",
        "src/vibey_tools/gh/vibey_gh/config.py",
    ],
)
def test_this_repository_forbids_the_approver_its_own_machinery(path: str) -> None:
    """An approver may never approve a change to what decides whether it may approve."""
    cfg = load_config(REPO_ROOT)
    pr = pull_request()
    pr[CHANGED_PATHS_KEY] = [path]
    subject = ApprovalCheck(config=lambda: cfg, transport=forge(), reader=lambda n, c: pr)
    assert f"forbidden path: touches {path}" in subject.evaluate(7).refusals


PACKAGE = Path(approval_check.__file__).resolve().parent
# The approver's entry point: what its agent definition is allowed to run.
ENTRY_POINT = "vibey_gh.approval_check"


def _source_of(module: str) -> Path | None:
    """The file `module` executes from, or None for a name that is not a module."""
    here = PACKAGE.joinpath(*module.split(".")[1:])
    if (here / "__init__.py").is_file():
        return here / "__init__.py"
    return here.with_suffix(".py") if here.with_suffix(".py").is_file() else None


def _closure(entry: str) -> list[str]:
    """Every `vibey_gh` module that can execute when `entry` runs, followed recursively.

    Conservative on purpose: every import anywhere in a module counts -- inside a function,
    under `TYPE_CHECKING`, behind a branch -- and importing `a.b.c` counts `a` and `a.b`
    too, because their `__init__` runs first. Over-counting forbids a file that did not need
    it; under-counting lets a change the approver may approve rewrite the approver.
    """
    seen: set[str] = set()
    pending = [entry]
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        parts = module.split(".")
        pending += [".".join(parts[:i]) for i in range(1, len(parts))]
        source = _source_of(module)
        assert source is not None, module
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            named: list[str] = []
            if isinstance(node, ast.ImportFrom):
                # A relative import would escape the scan below; there are none, and a new
                # one fails here rather than silently shrinking the closure.
                assert node.level == 0, f"relative import in {module}"
                if node.module and node.module.split(".")[0] == "vibey_gh":
                    named.append(node.module)
                    named += [f"{node.module}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                named += [a.name for a in node.names if a.name.split(".")[0] == "vibey_gh"]
            pending += [name for name in named if _source_of(name) is not None]
    return sorted(seen)


def test_the_closure_reaches_what_the_check_is_built_from_and_not_the_cli() -> None:
    """The scan is only as good as this: it must see the transitive dependencies, and the
    approver's entry point must not reach `cli.py` -- which is why `cli.py` is not forbidden."""
    modules = _closure(ENTRY_POINT)
    for expected in (
        "vibey_gh",
        "vibey_gh.merge_train",
        "vibey_gh.pr_automation",
        "vibey_gh.gh_transport",
        "vibey_gh.forge",
        "vibey_gh.reconcile",
        "vibey_gh.versioning",
        "vibey_gh.github_state",
        "vibey_gh.interfaces",
    ):
        assert expected in modules
    assert "vibey_gh.cli" not in modules


@pytest.mark.parametrize("module", _closure(ENTRY_POINT))
def test_every_module_the_approver_can_execute_is_forbidden_to_it(module: str) -> None:
    """A change to anything the check runs could loosen it while passing it.

    Derived from the entry point's transitive imports rather than listed, so no module can
    join what the approver executes without joining `forbidden_paths` too.
    """
    source = _source_of(module)
    assert source is not None
    path = source.relative_to(REPO_ROOT).as_posix()
    test_this_repository_forbids_the_approver_its_own_machinery(path)


# ------------------------------------------------------------------------- the entry point


def test_the_module_entry_point_takes_the_same_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Any, ...]] = []

    def run(self: ApprovalCheck, number: int, head=None, approve=False, body=None) -> int:
        calls.append((number, head, approve, body))
        return 0

    monkeypatch.setattr(ApprovalCheck, "run", run)
    assert ApprovalCheck.main(["12"]) == 0
    assert ApprovalCheck.main(["12", "--head", HEAD, "--approve", "--body", "V"]) == 0
    assert calls == [(12, None, False, None), (12, HEAD, True, "V")]


def test_python_dash_m_runs_the_check_without_the_cli() -> None:
    """The form the approver is granted, run for real: argparse's usage error is exit 2."""
    import subprocess
    import sys

    done = subprocess.run(
        [sys.executable, "-m", ENTRY_POINT],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2
    assert "python -m vibey_gh.approval_check" in done.stderr
    helped = subprocess.run(
        [sys.executable, "-m", ENTRY_POINT, "--help"], capture_output=True, text=True, check=False
    )
    assert helped.returncode == 0
    assert "--approve" in helped.stdout


# ------------------------------------------------------------------ fail-closed shapes (#1083)


@pytest.mark.parametrize(
    "item",
    [
        {"name": "CodeQL", "conclusion": "SUCCESS"},
        {"name": "CodeQL", "status": "COMPLETED"},
        {"name": "CodeQL", "status": "COMPLETED", "conclusion": None},
        {"name": "CodeQL", "status": "WEIRD", "conclusion": "SUCCESS"},
    ],
    ids=["no-status", "no-conclusion", "null-conclusion", "unknown-status"],
)
def test_a_check_of_unproven_shape_is_not_green(tmp_path: Path, item: dict[str, Any]) -> None:
    """Green is an explicit COMPLETED with an explicit passing conclusion, and nothing less."""
    found = refusals(tmp_path, pr=pull_request(statusCheckRollup=[*green(), item]))
    assert len(found) == 1
    assert found[0].startswith("gates: ")
    assert "CodeQL" in found[0]


@pytest.mark.parametrize(
    "commits",
    [
        [],
        [{"authors": []}],
        [{"authors": ["vibey-approver"]}],
        [{"authors": [{"name": "unlinked co-author"}]}],
        [{"authors": [{"login": ""}]}],
        [{"authors": [{"login": None}]}],
    ],
    ids=["no-commits", "no-authors", "non-dict-author", "no-login", "empty-login", "null-login"],
)
def test_a_commit_author_that_cannot_be_named_refuses(tmp_path: Path, commits: list) -> None:
    """An author with no login might be the approver; unprovable is refusal."""
    transport = forge(**{"pr view 7 --json commits": {"commits": commits}})
    (found,) = refusals(tmp_path, transport=transport)
    assert found.startswith("authorship: could not be established")


def test_an_unreadable_codeowners_refuses_instead_of_crashing(tmp_path: Path) -> None:
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODEOWNERS").write_bytes(b"* @\xff\xfe\n")
    found = refusals(tmp_path, authors=(CODEOWNERS_SENTINEL,))
    assert len(found) == 1
    assert found[0].startswith("author: [unattended_approval] authors could not be expanded")


def test_the_check_never_raises(tmp_path: Path) -> None:
    """Whatever goes wrong mid-check, the answer is a refusal and never a traceback."""

    class Broken:
        def touched(self, patterns, paths):
            raise RuntimeError("matcher exploded")

    cfg = config(tmp_path)
    subject = ApprovalCheck(
        config=lambda: cfg, transport=forge(), reader=lambda n, c: pull_request(), guard=Broken()
    )
    verdict = subject.evaluate(7)
    assert verdict.refusals == ("check: failed before every condition was read (matcher exploded)",)
    assert verdict.head == HEAD


@pytest.mark.parametrize(
    "kw, match",
    [({"switch_variable": "1BAD"}, "switch_variable"), ({"switch_value": "on "}, "switch_value")],
)
def test_the_switch_is_validated_even_while_the_grant_is_off(
    kw: dict[str, str], match: str
) -> None:
    """A switch that could never be set is wrong the day the grant is turned on, so say so now."""
    with pytest.raises(ValueError, match=match):
        UnattendedApprovalConfig(enabled=False, **kw)


# ------------------------------------------------------------------------------ --approve

REVIEWS = "api -X POST repos/{owner}/{repo}/pulls/7/reviews"


def _submitted(transport: Forge) -> list[str]:
    return [asked for asked in transport.asked if asked.startswith(REVIEWS)]


def test_approve_submits_exactly_one_approval_pinned_to_the_head(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    key = f"{REVIEWS} -f event=APPROVE -f commit_id={HEAD} -f body=VERDICT: approved"
    transport = forge(**{key: {"state": "APPROVED", "commit_id": HEAD}})
    assert (
        check(tmp_path, transport=transport).run(7, HEAD, approve=True, body="VERDICT: approved")
        == 0
    )
    assert _submitted(transport) == [key]
    assert f"approved #7 at {HEAD}" in capsys.readouterr().out


def test_approve_submits_nothing_after_a_refusal(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    transport = forge(**{f"api {VARIABLE}": {"value": "off"}})
    assert check(tmp_path, transport=transport).run(7, HEAD, approve=True, body="x") == 1
    assert _submitted(transport) == []
    assert "no approval was submitted" in capsys.readouterr().out


def test_approve_requires_a_pinned_head(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transport = forge()
    assert check(tmp_path, transport=transport).run(7, None, approve=True) == 1
    assert _submitted(transport) == []
    assert transport.asked == []
    assert "--approve needs --head" in capsys.readouterr().out


def test_approve_submits_nothing_when_the_head_has_moved(tmp_path: Path) -> None:
    transport = forge()
    assert check(tmp_path, transport=transport).run(7, "b" * 40, approve=True) == 1
    assert _submitted(transport) == []


@pytest.mark.parametrize(
    "answer",
    ["HTTP 422: Can not approve your own pull request", {"state": "COMMENTED"}, ["APPROVED"]],
    ids=["refused", "wrong-state", "wrong-shape"],
)
def test_an_approval_the_forge_did_not_record_is_a_failure(
    tmp_path: Path, answer: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    key = f"{REVIEWS} -f event=APPROVE -f commit_id={HEAD} -f body=" + approval_check.DEFAULT_BODY
    transport = forge(**{key: answer})
    assert check(tmp_path, transport=transport).run(7, HEAD, approve=True) == 1
    assert _submitted(transport) == [key]
    assert "was not recorded" in capsys.readouterr().out


# ------------------------------------------------------------------------ lanes (continuation)


def lane(**kw: Any) -> ApprovalLaneConfig:
    base: dict[str, Any] = dict(
        name="continuation",
        branch="continuation/*",
        accept_draft=True,
        tiers=(
            ApprovalTierConfig("code", ("src/**",), max_files=2, paired_tests=("tests/**",)),
            ApprovalTierConfig("tests", ("tests/**",), max_files=3),
            ApprovalTierConfig("docs", ("docs/**",)),
        ),
    )
    base.update(kw)
    return ApprovalLaneConfig(**base)


def lane_pr(*paths: str, **kw: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "isDraft": True,
        "headRefName": "continuation/resume-2026-10-05",
        "changedFiles": len(paths),
        CHANGED_PATHS_KEY: list(paths),
        LISTED_FILES_KEY: len(paths),
    }
    fields.update(kw)
    return pull_request(**fields)


def laned(tmp_path: Path, pr: dict[str, Any], **lane_kw: Any) -> tuple[str, ...]:
    return check(tmp_path, pr=pr, lanes=(lane(**lane_kw),)).evaluate(7).refusals


def test_a_draft_is_refused_without_a_lane_and_admitted_inside_one(tmp_path: Path) -> None:
    pr = lane_pr("docs/a.md")
    assert refusals(tmp_path, pr=pr) == ("pull request: is a draft",)
    assert laned(tmp_path, pr) == ()


def test_a_lane_that_does_not_accept_drafts_leaves_the_draft_refused(tmp_path: Path) -> None:
    assert laned(tmp_path, lane_pr("docs/a.md"), accept_draft=False) == (
        "pull request: is a draft",
    )


def test_a_draft_on_another_branch_is_not_the_lanes_to_admit(tmp_path: Path) -> None:
    pr = lane_pr("docs/a.md", headRefName="feature/x")
    assert laned(tmp_path, pr) == ("pull request: is a draft",)


def test_a_lane_never_replaces_the_general_grant(tmp_path: Path) -> None:
    pr = lane_pr("docs/a.md", author={"login": "stranger"}, baseRefName="main")
    found = laned(tmp_path, pr)
    assert any(r.startswith("author:") for r in found)
    assert any(r.startswith("branch:") for r in found)


def test_the_forbidden_floor_holds_beneath_every_tier(tmp_path: Path) -> None:
    pr = lane_pr("docs/a.md", ".github/workflows/ci.yml")
    found = laned(tmp_path, pr)
    assert any(r.startswith("forbidden path:") for r in found)
    assert any("in no tier" in r for r in found)


def test_a_file_in_no_tier_refuses_the_whole_pull_request(tmp_path: Path) -> None:
    found = laned(tmp_path, lane_pr("docs/a.md", "pr_list.txt"))
    assert found == ("lane continuation: pr_list.txt in no tier",)


def test_each_tier_applies_its_own_file_limit(tmp_path: Path) -> None:
    found = laned(tmp_path, lane_pr("src/a.py", "src/b.py", "src/c.py", "tests/t.py"))
    assert found == ("lane continuation: tier code changes 3 files, more than its 2",)


def test_code_lands_only_with_a_test_and_the_first_matching_tier_wins(tmp_path: Path) -> None:
    found = laned(tmp_path, lane_pr("src/a.py"))
    assert found == ("lane continuation: tier code changes src/a.py with no test beside it",)
    assert laned(tmp_path, lane_pr("src/a.py", "tests/t.py")) == ()
    # tests/t.py is in the tests tier, not code: a test file does not need a test of its own.
    assert laned(tmp_path, lane_pr("tests/t.py")) == ()


def test_a_tier_with_no_limit_and_no_pairing_asks_for_nothing(tmp_path: Path) -> None:
    many = [f"docs/{n}.md" for n in range(40)]
    assert laned(tmp_path, lane_pr(*many)) == ()


def test_a_long_list_of_strays_is_shortened(tmp_path: Path) -> None:
    found = laned(tmp_path, lane_pr("a", "b", "c", "d", "e"))
    assert found == ("lane continuation: a, b, c and 2 more in no tier",)


def test_a_fork_is_never_a_lane_pull_request(tmp_path: Path) -> None:
    found = laned(tmp_path, lane_pr("docs/a.md", isCrossRepository=True))
    assert found == ("lane continuation: the head is on a fork, which no lane admits",)


def test_a_lane_cannot_rule_on_files_nobody_listed(tmp_path: Path) -> None:
    pr = lane_pr("docs/a.md")
    del pr[CHANGED_PATHS_KEY]
    found = laned(tmp_path, pr)
    assert "lane continuation: the changed files could not be listed" in found


def test_the_first_lane_naming_the_head_is_the_one_that_applies(tmp_path: Path) -> None:
    strict = lane(name="strict", tiers=(ApprovalTierConfig("docs", ("docs/**",), max_files=1),))
    loose = lane(name="loose")
    pr = lane_pr("docs/a.md", "docs/b.md")
    found = check(tmp_path, pr=pr, lanes=(strict, loose)).evaluate(7).refusals
    assert found == ("lane strict: tier docs changes 2 files, more than its 1",)


@pytest.mark.parametrize(
    "build",
    [
        lambda: ApprovalTierConfig("", ("a",)),
        lambda: ApprovalTierConfig("t", ()),
        lambda: ApprovalTierConfig("t", ("a", "a")),
        lambda: ApprovalTierConfig("t", ("a",), max_files=-1),
        lambda: ApprovalTierConfig("t", ("a",), max_files=True),
        lambda: ApprovalTierConfig("t", ("a",), max_files="3"),  # type: ignore[arg-type]
        lambda: ApprovalLaneConfig("", "b/*", (ApprovalTierConfig("t", ("a",)),)),
        lambda: ApprovalLaneConfig("l", "", (ApprovalTierConfig("t", ("a",)),)),
        lambda: ApprovalLaneConfig("l", "b/*", ()),
        lambda: ApprovalLaneConfig(
            "l", "b/*", (ApprovalTierConfig("t", ("a",)),), accept_draft=1  # type: ignore[arg-type]
        ),
    ],
)
def test_a_lane_or_tier_that_bounds_nothing_or_is_malformed_is_rejected(build: Any) -> None:
    with pytest.raises((ValueError, TypeError)):
        build()


def test_the_declared_continuation_lane_loads_and_is_a_bound_not_a_pass() -> None:
    declared = load_config(REPO_ROOT).unattended_approval
    [continuation] = [candidate for candidate in declared.lanes if candidate.name == "continuation"]
    assert continuation.accept_draft and continuation.branch == "continuation/*"
    names = [tier.name for tier in continuation.tiers]
    assert names[-1] == "everything-else" and continuation.tiers[-1].paths == ("**",)
    # The catch-all is the last tier, so no earlier tier is shadowed by it, and it demands a test.
    assert continuation.tiers[-1].paired_tests
    assert ".vibey-gh.toml" in declared.forbidden_paths
