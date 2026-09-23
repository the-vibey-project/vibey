# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for how the storm's tools decide what a pull request claims, and what they write.

`lane-publish.py` and `lane-reap.py` settle the storm's ledger from what the forge says. A
wrong answer there is not loud: a lane is held "already published" on a pull request that
has nothing to do with it, or a lane whose work merged under another branch name stays
unsettled forever, and both read like a working storm. Each test below is a regression for
one such answer, measured on 2026-09-23.

Why this lives under tests/ rather than beside the tools is set out in
`test_storm_check_parser.py`: a regression test CI does not collect lets the bug come back
green. The tools are addressed by path because their names are not importable.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def load(name: str, filename: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader, f"the storm tool is missing: {TOOLS / filename}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Imported by name, not loaded by path: the tools import it as `storm_forge`, and a second
# copy of the module would carry a second `Unreadable` their `except` clauses never catch.
import storm_forge  # noqa: E402

lane_publish = load("lane_publish_ledger", "lane-publish.py")
lane_reap = load("lane_reap_ledger", "lane-reap.py")
PR = storm_forge.PullRequest


# --- what a pull request body closes ---------------------------------------------------


@pytest.mark.parametrize(
    "body",
    ["Closes #500.", "closes #500", "Fixes: #500", "fixed #500", "Resolves #500", "RESOLVED #500"],
)
def test_every_closing_keyword_is_read(body: str) -> None:
    assert storm_forge.closes(body) == {500}


def test_a_number_is_taken_whole() -> None:
    """#12 must never be read out of #123 -- the shape of the original false match."""
    assert storm_forge.closes("Closes #123") == {123}
    assert 12 not in storm_forge.closes("Closes #123")


@pytest.mark.parametrize(
    "body",
    [
        "Refs #500",
        "Part of #500; this PR's own work is the last commit.",
        "encloses #500",
        "**#500 is not closed** (`Refs`, not `Closes`).",
        "Closes other/repo#500",
        "",
        None,
    ],
)
def test_a_mention_is_not_a_claim(body: str | None) -> None:
    """#268, #269, #277 and #286 mention issues they do not close; search matched them."""
    assert 500 not in storm_forge.closes(body)


def test_one_keyword_governs_one_reference() -> None:
    """#396 carries eight lanes by repeating the keyword, which is how the forge reads it."""
    assert storm_forge.closes("Closes #322, closes #345, closes #346.") == {322, 345, 346}
    assert storm_forge.closes("Closes #1, #2") == {1}


# --- reading the forge -----------------------------------------------------------------


def fake_gh(monkeypatch, rows=None, code: int = 0, stdout: str | None = None) -> list:
    calls: list = []

    def run(argv, **kwargs):
        calls.append(argv)
        out = stdout if stdout is not None else json.dumps(rows or [])
        return subprocess.CompletedProcess(argv, code, out, "boom" if code else "")

    monkeypatch.setattr(storm_forge.subprocess, "run", run)
    return calls


def test_the_list_is_read_once_with_bodies(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {"number": 1040, "state": "MERGED", "headRefName": "feat/amqp", "body": "Closes #350."},
        {"number": 286, "state": "MERGED", "headRefName": "fix/chaos", "body": "Closes #262"},
    ]
    calls = fake_gh(monkeypatch, rows)
    prs = storm_forge.pull_requests(tmp_path, "o/r", 50)
    assert len(calls) == 1 and "body" in calls[0][calls[0].index("--json") + 1]
    assert [p.number for p in storm_forge.closing(prs, 350)] == [1040]
    assert storm_forge.closing(prs, 500) == []


def test_a_full_page_is_refused_as_possibly_truncated(monkeypatch, tmp_path: Path) -> None:
    """A list cut off at --limit makes "nothing closes this" a claim about a subset (10.g)."""
    rows = [{"number": n, "state": "OPEN", "headRefName": "x", "body": ""} for n in range(3)]
    fake_gh(monkeypatch, rows)
    with pytest.raises(storm_forge.Unreadable):
        storm_forge.pull_requests(tmp_path, None, 3)


@pytest.mark.parametrize("code,stdout", [(1, ""), (0, "not json")])
def test_an_unreadable_forge_is_never_an_empty_one(monkeypatch, tmp_path, code, stdout) -> None:
    fake_gh(monkeypatch, code=code, stdout=stdout)
    with pytest.raises(storm_forge.Unreadable):
        storm_forge.pull_requests(tmp_path, None, 50)


def test_the_limit_is_declared_not_compiled(tmp_path: Path) -> None:
    assert storm_forge.limit(tmp_path) == storm_forge.DEFAULT_LIMIT
    (tmp_path / "storm.toml").write_text("[forge]\npr_limit = 7\n", encoding="utf-8")
    assert storm_forge.limit(tmp_path) == 7


# --- lane-publish: already published? --------------------------------------------------


@pytest.fixture
def storm(tmp_path: Path, monkeypatch) -> Path:
    """A storm root with one finished lane, `gap-ci-arch-gates`, filed as issue #500."""
    root = tmp_path / "storm"
    lane = root / "lanes/gap-ci-arch-gates/.qwenstorm"
    lane.mkdir(parents=True)
    (lane / "result.json").write_text('{"completed": true}', encoding="utf-8")
    (lane / "issue.md").write_text(
        "## Checks the lane must run\n```bash\nruff check .\n```\n", encoding="utf-8"
    )
    (lane / "title.txt").write_text("ci: arch gates\n", encoding="utf-8")
    (root / "queue.txt").write_text("gap-ci-arch-gates 500\n", encoding="utf-8")
    for module in (lane_publish, lane_reap):
        monkeypatch.setattr(module, "STORM", root)
        monkeypatch.setattr(module, "LANES", root / "lanes")
    return root


def no_branch(monkeypatch) -> list:
    """`git ls-remote` finds no pushed branch; every other command succeeds silently."""
    ran: list = []

    def run(argv, cwd, timeout=900, extra=None, drop=()):
        ran.append(list(argv))
        return (2, "") if "ls-remote" in argv else (0, "")

    monkeypatch.setattr(lane_publish, "run", run)
    return ran


def test_an_unrelated_pr_does_not_hold_a_lane(storm: Path, monkeypatch) -> None:
    """The regression: gap-ci-arch-gates was held "already published" on #286."""
    no_branch(monkeypatch)
    prs = [PR(286, "MERGED", "fix/test-harness-chaos", frozenset({262}))]
    assert lane_publish.already_published("gap-ci-arch-gates", prs) is None


def test_a_pr_closing_the_issue_under_any_branch_holds_it(storm: Path, monkeypatch) -> None:
    no_branch(monkeypatch)
    prs = [PR(1040, "MERGED", "feat/whatever", frozenset({500}))]
    held = lane_publish.already_published("gap-ci-arch-gates", prs)
    assert held and "#1040" in held


def test_the_lane_branch_itself_holds_it(storm: Path, monkeypatch) -> None:
    no_branch(monkeypatch)
    prs = [PR(9, "CLOSED", "lane/gap-ci-arch-gates", frozenset())]
    assert "#9" in (lane_publish.already_published("gap-ci-arch-gates", prs) or "")


def test_a_check_that_never_runs_holds_the_lane(storm: Path, monkeypatch) -> None:
    """10.f: a dropped line is a check that did not run, and it can never read as a pass."""
    no_branch(monkeypatch)
    monkeypatch.setattr(lane_publish, "verify", lambda slug, record: (True, []))
    issue = storm / "lanes/gap-ci-arch-gates/.qwenstorm/issue.md"
    issue.write_text(
        "## Checks the lane must run\n```bash\nruff check .\nhelm lint deploy\n```\n",
        encoding="utf-8",
    )
    ok, why = lane_publish.ready("gap-ci-arch-gates", [], record=False)
    assert not ok
    assert any("never runs" in reason and "helm" in reason for reason in why)


def test_an_unreadable_forge_holds_every_lane(storm: Path, monkeypatch, capsys) -> None:
    def unreadable(*args, **kwargs):
        raise storm_forge.Unreadable("gh pr list failed: offline")

    monkeypatch.setattr(lane_publish.storm_forge, "pull_requests", unreadable)
    assert lane_publish.sweep(dry=True, only=None) == 0
    assert "offline" in capsys.readouterr().out


# --- lane-publish: report mode writes nothing ------------------------------------------


def tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_report_mode_writes_nothing(storm: Path, monkeypatch) -> None:
    """The regression: a pass with no flags rewrote every lane's verify.json."""
    ran = no_branch(monkeypatch)
    monkeypatch.setattr(lane_publish.storm_forge, "pull_requests", lambda *a, **k: [])
    fake = types.SimpleNamespace(verify=lambda lane: {"files": ["x.py"], "problems": []})
    monkeypatch.setattr(lane_publish, "verifier", lambda: fake)
    before = tree(storm)
    lane_publish.sweep(dry=True, only=None)
    assert tree(storm) == before
    assert not any("lane-verify.py" in " ".join(argv) for argv in ran)


def test_a_verifier_crash_holds_the_lane_not_the_sweep(storm: Path, monkeypatch) -> None:
    def crash(lane):
        raise RuntimeError("no such module")

    monkeypatch.setattr(lane_publish, "verifier", lambda: types.SimpleNamespace(verify=crash))
    ok, why = lane_publish.verify("gap-ci-arch-gates", record=False)
    assert not ok and "no such module" in why[0]


def test_only_the_acting_mode_records_a_verdict(storm: Path, monkeypatch) -> None:
    """--publish still has lane-verify record its report; nothing else is allowed to."""
    ran = no_branch(monkeypatch)
    lane_publish.verify("gap-ci-arch-gates", record=True)
    assert any("lane-verify.py" in " ".join(argv) for argv in ran)


# --- lane-reap: integration found by the closing pull request --------------------------


@pytest.fixture
def reaper(storm: Path, monkeypatch):
    monkeypatch.setattr(
        lane_reap,
        "STOP",
        types.SimpleNamespace(process_table=lambda: [], lane_in_flight=lambda table: None),
    )
    return lane_reap


def test_a_lane_merged_under_another_branch_is_integrated(reaper) -> None:
    """The regression: rmq-r03 merged as feat/amqp-dependency (#1040) and was never settled."""
    prs = [PR(1040, "MERGED", "feat/amqp-dependency", frozenset({500}))]
    found = reaper.survey(0, prs)
    assert [slug for slug, _ in found["integrate"]] == ["gap-ci-arch-gates"]
    assert "#1040" in found["integrate"][0][1]


def test_an_open_claim_under_another_branch_is_in_flight(reaper, storm: Path) -> None:
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text('{"completed": false}')
    prs = [PR(7, "OPEN", "fix/by-hand", frozenset({500}))]
    found = reaper.survey(0, prs)
    assert [slug for slug, _ in found["in-flight"]] == ["gap-ci-arch-gates"]
    assert found["reap"] == []


def test_a_mention_does_not_integrate_a_lane(reaper, storm: Path) -> None:
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text('{"completed": false}')
    prs = [PR(286, "MERGED", "fix/test-harness-chaos", frozenset({262}))]
    found = reaper.survey(0, prs)
    assert found["integrate"] == []
    assert [slug for slug, _ in found["reap"]] == ["gap-ci-arch-gates"]


def test_the_head_ref_map_keeps_the_newest_pull_request(reaper) -> None:
    prs = [PR(2, "OPEN", "lane/x", frozenset()), PR(1, "CLOSED", "lane/x", frozenset())]
    assert reaper.heads(prs) == {"lane/x": (2, "OPEN")}


def test_both_tools_share_one_closing_rule() -> None:
    """10.e: one copy of the rule, or the two tools drift apart about the same lane."""
    for tool in ("lane-publish.py", "lane-reap.py"):
        source = (TOOLS / tool).read_text(encoding="utf-8")
        assert "storm_forge" in source, f"{tool} does not use the shared rule"
        assert "in:body" not in source, f"{tool} still asks the forge's full-text search"
