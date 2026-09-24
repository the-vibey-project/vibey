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
import inspect
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

# The declaration, loaded by path exactly as the tool loads it, and separately from the
# tool's own copy: conformance is structural, so it must hold against the file itself.
StormForgeInterface = load(
    "storm_forge_interface_declared", "interfaces/storm_forge_interface.py"
).StormForgeInterface

lane_publish = load("lane_publish_ledger", "lane-publish.py")
lane_reap = load("lane_reap_ledger", "lane-reap.py")
PR = storm_forge.PullRequest
Unreadable = storm_forge.Unreadable


class Runner:
    """A double for `subprocess.run`, handed to the forge rather than patched into it."""

    def __init__(self, rows=None, code: int = 0, stdout: str | None = None) -> None:
        self.calls: list = []
        self.out = stdout if stdout is not None else json.dumps(rows if rows is not None else [])
        self.code = code

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, self.code, self.out, "boom" if self.code else "")


class ForgeDouble:
    """The forge as lane-publish and lane-reap see it: through the interface, nothing more."""

    def __init__(self, prs: list | None = None, error: str | None = None) -> None:
        self.prs, self.error = prs or [], error

    def pull_requests(self) -> list:
        if self.error:
            raise Unreadable(self.error)
        return list(self.prs)

    def closes(self, body: str | None) -> frozenset[int]:
        return frozenset()

    def closing(self, prs: list, issue: int | None) -> list:
        return [pr for pr in prs if issue in pr.closes]

    def heads(self, prs: list) -> dict[str, tuple[int, str]]:
        out: dict[str, tuple[int, str]] = {}
        for pr in prs:
            out.setdefault(pr.head, (pr.number, pr.state))
        return out


FORGE = storm_forge.StormForge(Path("."), None, 50)


# --- the declared seam -----------------------------------------------------------------


@pytest.mark.parametrize("candidate", [FORGE, ForgeDouble()])
def test_the_forge_and_its_double_honour_the_interface(candidate) -> None:
    """ADR-0016: the class and the double are both substitutable at the declared seam."""
    assert isinstance(candidate, StormForgeInterface)


def test_the_class_declares_every_method_the_interface_names() -> None:
    declared = {
        name: inspect.signature(member)
        for name, member in vars(StormForgeInterface).items()
        if callable(member) and not name.startswith("_")
    }
    assert declared, "the interface declares nothing"
    for name, signature in declared.items():
        implemented = inspect.signature(getattr(storm_forge.StormForge, name))
        assert list(implemented.parameters) == list(signature.parameters), name


def test_an_interfaces_package_earlier_on_the_path_cannot_shadow_the_declaration(
    tmp_path: Path,
) -> None:
    """The interface is loaded by file path, so no `interfaces` package can stand in for it.

    Imported as `interfaces.storm_forge_interface`, `tools/interfaces/` is a namespace
    package, and a regular package of that name anywhere on `sys.path` outranks it. This
    plants one first on the path -- whose module would raise if it were ever imported -- and
    imports the tool in a fresh interpreter.
    """
    impostor = tmp_path / "interfaces"
    impostor.mkdir()
    (impostor / "__init__.py").write_text("", encoding="utf-8")
    (impostor / "storm_forge_interface.py").write_text(
        "raise RuntimeError('the impostor interface was imported')\n", encoding="utf-8"
    )
    probe = (
        "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]; "
        "import storm_forge; "
        "print(storm_forge._INTERFACE.__file__)"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe, str(tmp_path), str(TOOLS)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    assert Path(done.stdout.strip()) == (TOOLS / "interfaces/storm_forge_interface.py").absolute()


def test_the_interface_declares_and_never_consumes() -> None:
    """It may import the standard library and other interfaces, and nothing of its tree."""
    source = (TOOLS / "interfaces/storm_forge_interface.py").read_text(encoding="utf-8")
    imported = {
        line.split()[1].split(".")[0]
        for line in source.splitlines()
        if line.startswith(("import ", "from "))
    }
    assert imported <= set(sys.stdlib_module_names) | {"__future__", "interfaces"}, imported


# --- what a pull request body closes ---------------------------------------------------


@pytest.mark.parametrize(
    "body",
    ["Closes #500.", "closes #500", "Fixes: #500", "fixed #500", "Resolves #500", "RESOLVED #500"],
)
def test_every_closing_keyword_is_read(body: str) -> None:
    assert FORGE.closes(body) == {500}


def test_a_number_is_taken_whole() -> None:
    """#12 must never be read out of #123 -- the shape of the original false match."""
    assert FORGE.closes("Closes #123") == {123}
    assert 12 not in FORGE.closes("Closes #123")


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
    assert 500 not in FORGE.closes(body)


def test_one_keyword_governs_one_reference() -> None:
    """#396 carries eight lanes by repeating the keyword, which is how the forge reads it."""
    assert FORGE.closes("Closes #322, closes #345, closes #346.") == {322, 345, 346}
    assert FORGE.closes("Closes #1, #2") == {1}


# --- reading the forge -----------------------------------------------------------------


def test_the_list_is_read_once_with_bodies(tmp_path: Path) -> None:
    rows = [
        {"number": 1040, "state": "MERGED", "headRefName": "feat/amqp", "body": "Closes #350."},
        {"number": 286, "state": "MERGED", "headRefName": "fix/chaos", "body": "Closes #262"},
    ]
    runner = Runner(rows)
    forge = storm_forge.StormForge(tmp_path, "o/r", 50, runner=runner)
    prs = forge.pull_requests()
    assert len(runner.calls) == 1
    assert "body" in runner.calls[0][runner.calls[0].index("--json") + 1]
    assert [p.number for p in forge.closing(prs, 350)] == [1040]
    assert forge.closing(prs, 500) == []
    assert forge.closing(prs, None) == []


def test_the_head_ref_map_keeps_the_newest_pull_request() -> None:
    prs = [PR(2, "OPEN", "lane/x", frozenset()), PR(1, "CLOSED", "lane/x", frozenset())]
    assert FORGE.heads(prs) == {"lane/x": (2, "OPEN")}


def test_a_full_page_is_refused_as_possibly_truncated(tmp_path: Path) -> None:
    """A list cut off at --limit makes "nothing closes this" a claim about a subset (10.g)."""
    rows = [{"number": n, "state": "OPEN", "headRefName": "x", "body": ""} for n in range(3)]
    with pytest.raises(Unreadable):
        storm_forge.StormForge(tmp_path, None, 3, runner=Runner(rows)).pull_requests()


@pytest.mark.parametrize("code,stdout", [(1, ""), (0, "not json")])
def test_an_unreadable_forge_is_never_an_empty_one(tmp_path, code, stdout) -> None:
    forge = storm_forge.StormForge(tmp_path, None, 50, runner=Runner(code=code, stdout=stdout))
    with pytest.raises(Unreadable):
        forge.pull_requests()


def test_a_forge_that_cannot_be_run_is_unreadable(tmp_path: Path) -> None:
    def missing(argv, **kwargs):
        raise FileNotFoundError("gh")

    with pytest.raises(Unreadable):
        storm_forge.StormForge(tmp_path, None, 50, runner=missing).pull_requests()


GOOD = {"number": 1, "state": "OPEN", "headRefName": "x", "body": ""}


@pytest.mark.parametrize(
    "payload",
    [
        {"message": "API rate limit exceeded", "documentation_url": "https://docs"},
        [GOOD, "not an object"],
        [{"number": 1, "state": "OPEN", "headRefName": "x"}],
        [{**GOOD, "number": "1"}],
        [{**GOOD, "state": None}],
        [{**GOOD, "body": 7}],
    ],
    ids=[
        "error-envelope",
        "non-object-row",
        "row-missing-body",
        "number-not-int",
        "state-not-str",
        "body-not-str",
    ],
)
def test_json_of_the_wrong_shape_is_unreadable_not_a_crash(tmp_path, payload) -> None:
    """Copilot on #1084: valid JSON of the wrong shape raised TypeError, and publish and
    reap crashed instead of failing closed. Anything but a list of complete rows is refused.
    """
    forge = storm_forge.StormForge(tmp_path, None, 50, runner=Runner(stdout=json.dumps(payload)))
    with pytest.raises(Unreadable):
        forge.pull_requests()


def test_a_null_body_is_a_body_with_nothing_in_it(tmp_path: Path) -> None:
    """The forge sends `null` for a pull request opened with no description."""
    forge = storm_forge.StormForge(tmp_path, None, 50, runner=Runner([{**GOOD, "body": None}]))
    assert forge.pull_requests()[0].closes == frozenset()


def test_the_limit_is_declared_not_compiled(tmp_path: Path) -> None:
    forge = storm_forge.StormForge.declared(tmp_path, tmp_path, None)
    assert forge.most == storm_forge.StormForge.DEFAULT_LIMIT
    (tmp_path / "storm.toml").write_text("[forge]\npr_limit = 7\n", encoding="utf-8")
    assert storm_forge.StormForge.declared(tmp_path, tmp_path, None).most == 7


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
    assert lane_publish.already_published("gap-ci-arch-gates", prs, ForgeDouble()) is None


def test_a_pr_closing_the_issue_under_any_branch_holds_it(storm: Path, monkeypatch) -> None:
    no_branch(monkeypatch)
    prs = [PR(1040, "MERGED", "feat/whatever", frozenset({500}))]
    held = lane_publish.already_published("gap-ci-arch-gates", prs, ForgeDouble())
    assert held and "#1040" in held


def test_the_lane_branch_itself_holds_it(storm: Path, monkeypatch) -> None:
    no_branch(monkeypatch)
    prs = [PR(9, "CLOSED", "lane/gap-ci-arch-gates", frozenset())]
    assert "#9" in (lane_publish.already_published("gap-ci-arch-gates", prs, ForgeDouble()) or "")


def test_a_check_that_never_runs_holds_the_lane(storm: Path, monkeypatch) -> None:
    """10.f: a dropped line is a check that did not run, and it can never read as a pass."""
    no_branch(monkeypatch)
    monkeypatch.setattr(lane_publish, "verify", lambda slug, record: (True, []))
    issue = storm / "lanes/gap-ci-arch-gates/.qwenstorm/issue.md"
    issue.write_text(
        "## Checks the lane must run\n```bash\nruff check .\nhelm lint deploy\n```\n",
        encoding="utf-8",
    )
    ok, why = lane_publish.ready("gap-ci-arch-gates", [], record=False, forge=ForgeDouble())
    assert not ok
    assert any("never runs" in reason and "helm" in reason for reason in why)


def test_an_unreadable_forge_holds_every_lane(storm: Path, capsys) -> None:
    forge = ForgeDouble(error="gh pr list failed: offline")
    assert lane_publish.sweep(dry=True, only=None, forge=forge) == 0
    assert "offline" in capsys.readouterr().out


# --- lane-publish: report mode writes nothing ------------------------------------------


def tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_report_mode_writes_nothing(storm: Path, monkeypatch) -> None:
    """The regression: a pass with no flags rewrote every lane's verify.json."""
    ran = no_branch(monkeypatch)
    fake = types.SimpleNamespace(verify=lambda lane: {"files": ["x.py"], "problems": []})
    monkeypatch.setattr(lane_publish, "VERIFIER", fake)
    before = tree(storm)
    lane_publish.sweep(dry=True, only=None, forge=ForgeDouble())
    assert tree(storm) == before
    assert not any("lane-verify.py" in " ".join(argv) for argv in ran)


def test_a_verifier_crash_holds_the_lane_not_the_sweep(storm: Path, monkeypatch) -> None:
    def crash(lane):
        raise RuntimeError("no such module")

    monkeypatch.setattr(lane_publish, "VERIFIER", types.SimpleNamespace(verify=crash))
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
    found = reaper.survey(0, prs, ForgeDouble())
    assert [slug for slug, _ in found["integrate"]] == ["gap-ci-arch-gates"]
    assert "#1040" in found["integrate"][0][1]


def test_an_open_claim_under_another_branch_is_in_flight(reaper, storm: Path) -> None:
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text('{"completed": false}')
    prs = [PR(7, "OPEN", "fix/by-hand", frozenset({500}))]
    found = reaper.survey(0, prs, ForgeDouble())
    assert [slug for slug, _ in found["in-flight"]] == ["gap-ci-arch-gates"]
    assert found["reap"] == []


def test_a_mention_does_not_integrate_a_lane(reaper, storm: Path) -> None:
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text('{"completed": false}')
    prs = [PR(286, "MERGED", "fix/test-harness-chaos", frozenset({262}))]
    found = reaper.survey(0, prs, ForgeDouble())
    assert found["integrate"] == []
    assert [slug for slug, _ in found["reap"]] == ["gap-ci-arch-gates"]


REFUSED = '{"completed": false, "refused": "issue #500 was edited by an account not allowed"}'


def test_a_refused_lane_is_its_own_verdict_not_a_give_up(reaper, storm: Path) -> None:
    """12.j: a lane the runner refused to start never gave up, so it is not reaped."""
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text(REFUSED)
    found = reaper.survey(0, [], ForgeDouble())
    assert found["reap"] == []
    assert [slug for slug, _ in found["refused"]] == ["gap-ci-arch-gates"]
    assert "not allowed" in found["refused"][0][1]


def test_a_refused_lane_is_never_recorded_or_commented_on(
    reaper, storm: Path, monkeypatch, capsys
) -> None:
    """--reap --sync-issues writes no abandonment and posts nothing on a refused issue."""
    (storm / "lanes/gap-ci-arch-gates/.qwenstorm/result.json").write_text(REFUSED)
    (storm / "queue.txt").write_text(
        "gap-ci-arch-gates 500\nwaits-on-it 501 gap-ci-arch-gates\n", encoding="utf-8"
    )
    posted: list = []
    monkeypatch.setattr(reaper, "gh", lambda args: posted.append(args) or True)
    monkeypatch.setattr(reaper, "worktrees", lambda prs, apply: (0, 0))
    monkeypatch.setattr(sys, "argv", ["lane-reap.py", "--reap", "--sync-issues", "--grace", "0"])
    assert reaper.main(source=ForgeDouble()) == 0
    assert "gap-ci-arch-gates" not in reaper.lines_of("abandoned.txt")
    assert posted == []
    out = capsys.readouterr().out
    assert "refused" in out and "waits-on-it" in out, "its dependants must be named as held"


def test_both_tools_share_one_closing_rule() -> None:
    """10.e: one copy of the rule, or the two tools drift apart about the same lane."""
    for tool in ("lane-publish.py", "lane-reap.py"):
        source = (TOOLS / tool).read_text(encoding="utf-8")
        assert "StormForgeInterface" in source, f"{tool} does not take the declared seam"
        assert "in:body" not in source, f"{tool} still asks the forge's full-text search"
        assert "close[sd]?" not in source, f"{tool} carries its own copy of the closing rule"
