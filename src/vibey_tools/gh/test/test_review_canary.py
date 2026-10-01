# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The review canary: the corpus, the matching rule, the scores, the ledger, the page, the
floor, and the command -- and that it asks the review the pull request gets, flag for flag.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh import cli, review_outcome
from vibey_gh.config import (
    GhConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
    ReviewCanaryConfig,
    load_config,
)
from vibey_gh.interfaces.review_canary_interface import (
    CAUGHT,
    CLEAN,
    FALSE_POSITIVE,
    MISSED,
    NO_VERDICT,
    BuiltCase,
    CanaryCase,
    CanaryEdit,
    CanaryFloor,
    CanaryLedgerInterface,
    CanaryReportInterface,
    CanaryScorerInterface,
    CaseResult,
    CorpusLoaderInterface,
    FindingMatcherInterface,
    ReviewCanaryInterface,
    WilsonIntervalInterface,
)
from vibey_gh.local_review import SOURCE_CONTEXT
from vibey_gh.review_canary import (
    BEGIN,
    END,
    VERDICT_SETTINGS,
    CanaryLedger,
    CanaryReport,
    CanaryScorer,
    CorpusLoader,
    FindingMatcher,
    ReviewCanary,
    WilsonInterval,
)

REPO = Path(__file__).resolve().parents[4]
PIN = "a" * 40
HEAD = "b" * 40

SOURCE = """\
def total(items):
    count = 0
    for item in items:
        count += item
    return count


def guard(user):
    if not user.allowed:
        raise PermissionError(user)
    return True
"""

CLASSES = """
[classes.off_by_one]
summary = "a bound one away"
keywords = ["off-by-one", "boundary"]

[classes.removed_guard]
summary = "a check removed"
keywords = ["check", "permission"]
"""

DEFECT_ONE = """
[[cases]]
id = "obo-total"
kind = "defect"
class = "off_by_one"
path = "pkg/mod.py"
how = "starts the count at one"
anchors = ["count = 1"]

[[cases.edits]]
find = "    count = 0\\n"
replace = "    count = 1\\n"
planted = "count = 1"
"""

DEFECT_TWO = """
[[cases]]
id = "guard-gone"
kind = "defect"
class = "removed_guard"
path = "pkg/mod.py"
how = "drops the permission check"
anchors = ["allowed"]

[[cases.edits]]
find = "    if not user.allowed:\\n        raise PermissionError(user)\\n    return True\\n"
replace = "    return True\\n"
planted = "return True"
"""

CONTROL = """
[[cases]]
id = "ctl-rename"
kind = "control"
path = "pkg/mod.py"
how = "renames count"

[[cases.edits]]
find = "    count = 0\\n    for item in items:\\n        count += item\\n    return count\\n"
replace = "    tally = 0\\n    for item in items:\\n        tally += item\\n    return tally\\n"
"""


def corpus_text(*cases: str, pin: str = PIN, extra: str = "") -> str:
    return f'schema = "vibey-gh/review-canary-corpus/1"\npin = "{pin}"\n{extra}{CLASSES}' + "".join(
        cases
    )


class FakeGit:
    """`git show <pin>:<path>` and `git rev-parse HEAD` over files held in memory."""

    def __init__(self, files: dict[str, str] | None = None, head: str = HEAD) -> None:
        self.files = {"pkg/mod.py": SOURCE} if files is None else files
        self.head = head
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        if argv[3] == "show":
            _, path = argv[4].split(":", 1)
            if path in self.files:
                return subprocess.CompletedProcess(argv, 0, self.files[path], "")
            return subprocess.CompletedProcess(argv, 128, "", f"fatal: no {path}\n")
        if self.head:
            return subprocess.CompletedProcess(argv, 0, f"{self.head}\n", "")
        return subprocess.CompletedProcess(argv, 128, "", "fatal: not a repository")


def load(tmp_path: Path, text: str, git: FakeGit | None = None):
    path = tmp_path / "corpus.toml"
    path.write_text(text, encoding="utf-8")
    loader = CorpusLoader(tmp_path, run=git or FakeGit())
    return loader, loader.load(path)


# ------------------------------------------------------------------------- the real corpus


def test_the_committed_corpus_builds_and_is_large_enough_to_say_something():
    canary = load_config(REPO).pr_automation.review_canary
    loader = CorpusLoader(REPO)
    corpus = loader.load(REPO / canary.corpus)
    problems = loader.problems(
        corpus,
        min_defects=canary.min_defects,
        min_classes=canary.min_classes,
        min_controls=canary.min_controls,
    )
    assert problems == []
    assert len(corpus.defects) >= 24 and len(corpus.controls) >= 8
    classes = {case.defect_class for case in corpus.defects}
    assert len(classes) >= 8 and classes == set(corpus.classes)
    # Every class carries at least two defects, so no class rests on a single case.
    assert all(sum(case.defect_class == name for case in corpus.defects) >= 2 for name in classes)


def test_the_committed_corpus_pin_is_reachable_from_develop_history():
    corpus = CorpusLoader(REPO).load(REPO / ReviewCanaryConfig().corpus)
    done = subprocess.run(
        ["git", "-C", str(REPO), "cat-file", "-t", corpus.pin],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.stdout.strip() == "commit"


def test_every_committed_defect_is_located_by_a_finding_quoting_its_first_anchor():
    """The matching rule, held to the corpus: a finding on the right file quoting the first
    anchor is located, and one at the planted line is too."""
    loader = CorpusLoader(REPO)
    corpus = loader.load(REPO / ReviewCanaryConfig().corpus)
    matcher = FindingMatcher()
    for case in corpus.defects:
        built = loader.build(corpus, case)
        assert built.lines is not None
        quoting = {"path": case.path, "explanation": f"`{case.anchors[0]}` here"}
        at_line = {"path": case.path, "line": built.lines[0], "explanation": "x"}
        elsewhere = {"path": "elsewhere.py", "line": built.lines[0], "explanation": "x"}
        assert matcher.located(quoting, built), case.id
        assert matcher.located(at_line, built), case.id
        assert not matcher.located(elsewhere, built), case.id


def test_the_runbook_shows_the_latest_committed_measurement():
    canary = ReviewCanary(config=lambda: load_config(REPO), out=lambda _: None)
    assert canary.render(check=True) == 0


def test_the_committed_ledger_chain_holds():
    canary = load_config(REPO).pr_automation.review_canary
    for entry in CanaryLedger().read(REPO / canary.ledger):
        assert entry["corpus"]["cases"] == len(entry["cases"]) or entry["subset"]


# --------------------------------------------------------------------------- the corpus


def test_a_corpus_loads_with_its_classes_cases_and_digest(tmp_path):
    _, corpus = load(tmp_path, corpus_text(DEFECT_ONE, DEFECT_TWO, CONTROL))
    assert corpus.pin == PIN
    assert list(corpus.classes) == ["off_by_one", "removed_guard"]
    assert corpus.classes["off_by_one"].keywords == ("off-by-one", "boundary")
    assert [case.id for case in corpus.defects] == ["obo-total", "guard-gone"]
    assert [case.id for case in corpus.controls] == ["ctl-rename"]
    assert corpus.cases[0].edits[0] == CanaryEdit("    count = 0\n", "    count = 1\n", "count = 1")
    assert len(corpus.digest) == 64


@pytest.mark.parametrize(
    ("text", "said"),
    [
        (corpus_text(DEFECT_ONE).replace("corpus/1", "corpus/9"), "schema is"),
        (corpus_text(DEFECT_ONE, pin="abc"), "pin must be a full 40-character commit"),
        (corpus_text(), "there are no cases"),
        (corpus_text(DEFECT_ONE, DEFECT_ONE), "the id is used twice"),
        (corpus_text(DEFECT_ONE.replace('"obo-total"', '"Obo Total"')), "an id is lower-case"),
        (corpus_text(DEFECT_ONE.replace('"defect"', '"bug"')), "kind must be"),
        (corpus_text(DEFECT_ONE.replace('"pkg/mod.py"', '"../mod.py"')), "repository-relative"),
        (corpus_text(DEFECT_ONE.replace('"pkg/mod.py"', '"/mod.py"')), "repository-relative"),
        (corpus_text(DEFECT_ONE.replace('"starts the count at one"', '" "')), "must be said"),
        (corpus_text(DEFECT_ONE.replace('replace = "    count = 1\\n"', "replace = 3")), "a find"),
        (
            corpus_text(
                DEFECT_ONE.replace('replace = "    count = 1\\n"', 'replace = "    count = 0\\n"')
            ),
            "changes nothing",
        ),
        (corpus_text(DEFECT_ONE.replace('"off_by_one"', '"typo"')), "is not declared"),
        (corpus_text(DEFECT_ONE.replace('planted = "count = 1"', "")), "exactly one edit"),
        (corpus_text(DEFECT_ONE.replace('planted = "count = 1"', 'planted = "zz"')), "not in its"),
        (
            corpus_text(DEFECT_ONE.replace('anchors = ["count = 1"]', "anchors = []")),
            "at least one anchor",
        ),
        (
            corpus_text(DEFECT_ONE.replace('anchors = ["count = 1"]', 'anchors = [""]')),
            "at least one anchor",
        ),
        (
            corpus_text(CONTROL.replace('kind = "control"', 'kind = "control"\nanchors = ["x"]')),
            "a control",
        ),
        (
            corpus_text(
                CONTROL.replace("[[cases.edits]]", "").replace("find", "x").replace("replace", "y")
            ),
            "no edits",
        ),
        (corpus_text(DEFECT_ONE, extra="[classes.Bad-Name]\nkeywords = ['x']\n"), "a name is"),
        (corpus_text(DEFECT_ONE, extra="[classes.empty]\nkeywords = []\n"), "keywords must be"),
        (
            corpus_text(DEFECT_ONE, extra="[classes.odd]\nsummary = 'no words'\n"),
            "keywords must be",
        ),
    ],
)
def test_a_malformed_corpus_is_refused_naming_what_is_wrong(tmp_path, text, said):
    with pytest.raises(ValueError, match=re.escape(said)):
        load(tmp_path, text)


def test_a_case_or_an_edit_that_is_not_a_table_is_refused():
    problems: list[str] = []
    case = CorpusLoader._case(1, "not a table", {}, problems)
    assert case.id == "#1" and any("kind must be" in problem for problem in problems)
    problems = []
    CorpusLoader._case(1, {"id": "x", "edits": ["not a table"]}, {}, problems)
    assert any("every edit has a find" in problem for problem in problems)
    problems = []
    CorpusLoader._defect_class("fine", "not a table", problems)
    assert problems == ["class fine: keywords must be a non-empty list of words"]


def test_a_case_builds_into_a_diff_the_review_reads_and_its_planted_lines(tmp_path):
    git = FakeGit()
    loader, corpus = load(tmp_path, corpus_text(DEFECT_ONE, DEFECT_TWO, CONTROL), git)
    built = loader.build(corpus, corpus.cases[0])
    assert built.before == SOURCE
    assert "    count = 1\n" in built.after
    assert built.lines == (2, 2)
    assert built.diff.startswith("diff --git a/pkg/mod.py b/pkg/mod.py\n--- a/pkg/mod.py\n")
    assert "+++ b/pkg/mod.py\n" in built.diff and "-    count = 0\n+    count = 1\n" in built.diff
    # The review's own reader of a diff finds the change where the corpus says it is.
    start, end = SOURCE_CONTEXT.changed(built.diff)["pkg/mod.py"][0]
    assert start <= built.lines[0] <= built.lines[1] <= end
    gone = loader.build(corpus, corpus.cases[1])
    assert gone.lines == (9, 9) and gone.after.endswith("def guard(user):\n    return True\n")
    control = loader.build(corpus, corpus.cases[2])
    assert control.lines is None
    # The file at the pin is read once, however many cases edit it.
    assert sum(1 for call in git.calls if call[3] == "show") == 1


def test_a_multi_line_planted_text_spans_its_lines(tmp_path):
    defect = DEFECT_ONE.replace('planted = "count = 1"', 'planted = "count = 1\\n"')
    loader, corpus = load(tmp_path, corpus_text(defect))
    assert loader.build(corpus, corpus.cases[0]).lines == (2, 3)


def test_a_case_that_does_not_apply_exactly_once_is_refused(tmp_path):
    twice = DEFECT_ONE.replace('find = "    count = 0\\n"', 'find = "count"')
    loader, corpus = load(tmp_path, corpus_text(twice))
    with pytest.raises(ValueError, match="occurs 3 times"):
        loader.build(corpus, corpus.cases[0])
    ambiguous = DEFECT_TWO.replace(
        'replace = "    return True\\n"', 'replace = "    return count\\n"'
    ).replace('planted = "return True"', 'planted = "return count"')
    loader, corpus = load(tmp_path, corpus_text(ambiguous))
    with pytest.raises(ValueError, match="not unique"):
        loader.build(corpus, corpus.cases[0])


def test_a_file_missing_at_the_pin_is_refused(tmp_path):
    loader, corpus = load(tmp_path, corpus_text(DEFECT_ONE), FakeGit(files={}))
    with pytest.raises(ValueError, match="git show .*: fatal: no pkg/mod.py"):
        loader.build(corpus, corpus.cases[0])


def test_a_corpus_too_small_or_that_does_not_build_is_not_a_measurement(tmp_path):
    broken = CONTROL.replace("count = 0\\n    for", "count = 9\\n    for")
    loader, corpus = load(tmp_path, corpus_text(DEFECT_ONE, broken))
    assert loader.problems(corpus, min_defects=2, min_classes=2, min_controls=2) == [
        "1 defects, fewer than min_defects (2)",
        "1 defect classes, fewer than min_classes (2)",
        "1 controls, fewer than min_controls (2)",
        "case ctl-rename: an edit's find occurs 0 times in pkg/mod.py, not once",
    ]
    loader, corpus = load(tmp_path, corpus_text(DEFECT_ONE, DEFECT_TWO, CONTROL))
    assert loader.problems(corpus, min_defects=2, min_classes=2, min_controls=1) == []


# ------------------------------------------------------------------------ the matching rule


@pytest.mark.parametrize(
    ("said", "expected"),
    [
        ("pkg/mod.py", True),
        ("a/pkg/mod.py", True),
        ("b/pkg/mod.py", True),
        ("./pkg/mod.py", True),
        ("  pkg/mod.py ", True),
        ("mod.py", True),
        ("/home/runner/work/vibey/pkg/mod.py", True),
        ("other/mod.py", False),
        ("pkg/mod.pyc", False),
        ("", False),
        ("a/", False),
    ],
)
def test_a_finding_names_the_planted_file_by_its_path(said, expected):
    assert FindingMatcher().same_path(said, "pkg/mod.py") is expected


def built_defect(lines: tuple[int, int] | None = (10, 11)) -> BuiltCase:
    case = CanaryCase(
        id="d",
        kind="defect",
        path="pkg/mod.py",
        how="x",
        edits=(),
        defect_class="off_by_one",
        anchors=("count = 1",),
    )
    return BuiltCase(case, "", "", "", lines)


@pytest.mark.parametrize(
    ("finding", "expected"),
    [
        ({"path": "pkg/mod.py", "line": 7}, True),
        ({"path": "pkg/mod.py", "line": 14}, True),
        ({"path": "pkg/mod.py", "line": 6}, False),
        ({"path": "pkg/mod.py", "line": 15}, False),
        ({"path": "pkg/mod.py", "line": True}, False),
        ({"path": "pkg/mod.py", "line": "10"}, False),
        ({"path": "pkg/mod.py", "line": 40, "explanation": "`count = 1` is wrong"}, True),
        ({"path": "pkg/mod.py", "recommended_fix": "use count = 1 nowhere"}, True),
        ({"path": "pkg/other.py", "line": 10, "explanation": "count = 1"}, False),
        ({"line": 10}, False),
    ],
)
def test_a_finding_is_located_by_its_line_within_tolerance_or_by_an_anchor(finding, expected):
    assert FindingMatcher(line_tolerance=3).located(finding, built_defect()) is expected


def test_without_planted_lines_only_an_anchor_locates_a_finding():
    built = built_defect(lines=None)
    assert not FindingMatcher().located({"path": "pkg/mod.py", "line": 10}, built)
    assert FindingMatcher().located({"path": "pkg/mod.py", "explanation": "count = 1"}, built)


def test_a_finding_is_classed_by_a_keyword_in_its_words_ignoring_case():
    matcher = FindingMatcher()
    assert matcher.classed({"explanation": "An OFF-BY-ONE error"}, ["off-by-one"])
    assert matcher.classed({"recommended_fix": "fix the Boundary"}, ["off-by-one", "boundary"])
    assert not matcher.classed({"explanation": "style nit"}, ["off-by-one"])
    assert not matcher.classed({}, ["off-by-one"])


# ------------------------------------------------------------------------------- Wilson


def test_the_wilson_interval_matches_known_values():
    wilson = WilsonInterval()
    assert wilson.bounds(0, 0, 1.96) is None
    low, high = wilson.bounds(0, 14, 1.96)
    assert low == 0.0 and high == pytest.approx(0.2153, abs=1e-4)
    low, high = wilson.bounds(19, 27, 1.96)
    assert low == pytest.approx(0.5152, abs=1e-3) and high == pytest.approx(0.8415, abs=1e-3)
    low, high = wilson.bounds(18, 27, 1.96)
    assert low < 0.5
    low, high = wilson.bounds(5, 5, 1.96)
    assert high == 1.0 and low == pytest.approx(0.5655, abs=1e-3)
    assert wilson.confidence(1.96) == pytest.approx(0.95, abs=1e-3)


# ------------------------------------------------------------------------------ scoring


def score(verdict: dict | None, *, kind: str = "defect", **kwargs: Any) -> CaseResult:
    built = built_defect()
    if kind == "control":
        built = dataclasses.replace(
            built,
            case=dataclasses.replace(built.case, kind="control", defect_class="", anchors=()),
            lines=None,
        )
    return CanaryScorer().score(
        built, ["off-by-one"], verdict, code=kwargs.pop("code", "reviewed"), **kwargs
    )


ON_TARGET = {
    "severity": "blocking",
    "path": "pkg/mod.py",
    "line": 10,
    "explanation": "an off-by-one: the count starts at one",
    "recommended_fix": "start at zero",
}


def test_a_defect_is_caught_only_when_blocked_on_the_planted_lines_naming_its_class():
    result = score({"pass": False, "findings": [ON_TARGET]}, seconds=12.5, attempts=1, parts=1)
    assert result.outcome == CAUGHT
    assert (result.blocked, result.located, result.classed) == (True, True, True)
    assert result.findings == 1 and result.blocking_findings == 1
    assert result.matched.startswith("an off-by-one")
    assert result.evidence[0] == {
        "severity": "blocking",
        "path": "pkg/mod.py",
        "line": 10,
        "said": "an off-by-one: the count starts at one start at zero",
    }
    assert (result.seconds, result.attempts, result.parts) == (12.5, 1, 1)


@pytest.mark.parametrize(
    ("verdict", "located", "classed", "blocked"),
    [
        # Flagged, but the gate would have passed it.
        ({"pass": True, "findings": [ON_TARGET]}, True, True, False),
        # Blocked, on the lines, for another reason.
        ({"pass": False, "findings": [{**ON_TARGET, "explanation": "naming"}]}, True, False, True),
        # Blocked for something elsewhere.
        ({"pass": False, "findings": [{**ON_TARGET, "path": "x.py"}]}, False, False, True),
        # Blocked with nothing said at all.
        ({"pass": False, "findings": []}, False, False, True),
        # A verdict that does not say pass is not a pass.
        ({"findings": ["not a finding", ON_TARGET]}, True, True, True),
    ],
)
def test_a_defect_missed_says_why(verdict, located, classed, blocked):
    result = score(verdict)
    expected = CAUGHT if located and classed and blocked else MISSED
    assert result.outcome == expected
    assert (result.located, result.classed, result.blocked) == (located, classed, blocked)


def test_a_control_is_a_false_positive_when_blocked_or_given_a_blocking_finding():
    assert score({"pass": True, "findings": []}, kind="control").outcome == CLEAN
    minor = {**ON_TARGET, "severity": "minor"}
    assert score({"pass": True, "findings": [minor]}, kind="control").outcome == CLEAN
    assert score({"pass": False, "findings": []}, kind="control").outcome == FALSE_POSITIVE
    assert score({"pass": True, "findings": [ON_TARGET]}, kind="control").outcome == FALSE_POSITIVE


def test_no_verdict_is_its_own_outcome_whatever_the_code():
    result = score(None, code="model_timeout", reason="timed out", attempts=2)
    assert result.outcome == NO_VERDICT and result.code == "model_timeout"
    assert result.reason == "timed out" and result.attempts == 2 and not result.blocked


def test_evidence_keeps_a_line_only_when_it_is_a_number():
    result = score({"pass": False, "findings": [{**ON_TARGET, "line": "ten"}]})
    assert result.evidence[0]["line"] is None


def results_for(outcomes: list[tuple[str, str, str]]) -> list[CaseResult]:
    return [
        CaseResult(
            case_id=f"c{index}",
            kind=kind,
            outcome=outcome,
            code="reviewed" if outcome != NO_VERDICT else "model_busy",
            defect_class=klass,
            blocked=outcome in (CAUGHT, FALSE_POSITIVE),
            located=outcome == CAUGHT,
        )
        for index, (kind, klass, outcome) in enumerate(outcomes)
    ]


def test_a_summary_counts_recall_false_positives_and_no_verdict_apart():
    results = results_for(
        [
            ("defect", "a", CAUGHT),
            ("defect", "a", MISSED),
            ("defect", "b", CAUGHT),
            ("defect", "b", NO_VERDICT),
            ("control", "", CLEAN),
            ("control", "", FALSE_POSITIVE),
            ("control", "", NO_VERDICT),
        ]
    )
    results[1] = dataclasses.replace(results[1], blocked=True, located=True)
    summary = CanaryScorer().summarize(results, ["a", "b", "c"], 1.96)
    assert summary["recall"]["k"] == 2 and summary["recall"]["n"] == 3
    assert summary["recall"]["rate"] == pytest.approx(2 / 3)
    assert summary["recall_located"]["k"] == 3
    assert summary["false_positive"]["k"] == 1 and summary["false_positive"]["n"] == 2
    assert summary["no_verdict"] == {"count": 2, "of": 7, "codes": {"model_busy": 2}}
    assert summary["per_class"] == {
        "a": {"caught": 1, "n": 2, "no_verdict": 0},
        "b": {"caught": 1, "n": 1, "no_verdict": 1},
        "c": {"caught": 0, "n": 0, "no_verdict": 0},
    }
    assert summary["confidence"] == pytest.approx(0.95, abs=1e-3)
    empty = CanaryScorer().summarize([], [], 1.96)
    assert empty["recall"] == {"k": 0, "n": 0, "rate": None, "low": None, "high": None}


FLOOR = CanaryFloor(min_recall_lower_bound=0.5, max_false_positive_upper_bound=0.5)


@pytest.mark.parametrize(
    ("recall", "false", "reasons"),
    [
        ((0.6, 0.9), (0.0, 0.3), []),
        ((None, None), (0.0, 0.3), ["no planted defect reached a verdict"]),
        ((0.4, 0.9), (0.0, 0.3), ["recall's lower bound 0.400 is under"]),
        ((0.6, 0.9), (None, None), ["no control reached a verdict"]),
        ((0.6, 0.9), (0.1, 0.6), ["the false-positive rate's upper bound 0.600 is over"]),
    ],
)
def test_the_floor_is_both_bounds_taken_the_hard_way(recall, false, reasons):
    summary = {
        "recall": {"low": recall[0], "high": recall[1]},
        "false_positive": {"low": false[0], "high": false[1]},
    }
    met, said = CanaryScorer().meets(summary, FLOOR)
    assert met is (not reasons)
    assert len(said) == len(reasons)
    for reason, expected in zip(said, reasons, strict=True):
        assert reason.startswith(expected)


# ------------------------------------------------------------------------------- ledger


def test_the_ledger_appends_a_digest_chain_and_reads_it_back(tmp_path):
    ledger, path = CanaryLedger(), tmp_path / "deep" / "ledger.jsonl"
    assert ledger.read(path) == ()
    first = ledger.append(path, {"n": 1})
    second = ledger.append(path, {"n": 2})
    assert first["seq"] == 1 and first["previous_digest"] == "0" * 64
    assert second["seq"] == 2 and second["previous_digest"] == first["digest"]
    assert second["kind"] == "ReviewCanaryMeasured"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert ledger.read(path) == ({"n": 1}, {"n": 2})


def tamper(path: Path, line: int, change) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[line])
    change(record)
    lines[line] = json.dumps(record)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("change", "error", "said"),
    [
        (lambda record: record["payload"].update(n=9), ValueError, "invalid digest"),
        (lambda record: record.update(seq=7), ValueError, "has seq 7, not 2"),
        (lambda record: record.update(previous_digest="f" * 64), ValueError, "breaks the digest"),
        (lambda record: record.update(payload=[1]), TypeError, "not a measurement record"),
    ],
)
def test_an_edited_ledger_is_refused(tmp_path, change, error, said):
    ledger, path = CanaryLedger(), tmp_path / "ledger.jsonl"
    ledger.append(path, {"n": 1})
    ledger.append(path, {"n": 2})
    tamper(path, 1, change)
    with pytest.raises(error, match=said):
        ledger.read(path)


def test_a_ledger_line_that_is_not_json_or_not_an_object_is_refused(tmp_path):
    path = tmp_path / "ledger.jsonl"
    path.write_text("{oops\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 1 is not JSON"):
        CanaryLedger().read(path)
    path.write_text("[1]\n", encoding="utf-8")
    with pytest.raises(TypeError, match="not a measurement record"):
        CanaryLedger().read(path)


# --------------------------------------------------------------------------- the report


def entry(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "finished_at": "2026-10-01T12:00:00+00:00",
        "host": "mac",
        "commit": HEAD,
        "subset": False,
        "case_ids": [],
        "corpus": {"digest": "c" * 64, "cases": 3, "defects": 2, "controls": 1, "classes": 2},
        "settings": {
            "model": "gpt-oss:20b",
            "think": "",
            "context_window": 65536,
            "reasoning_reserve_tokens": 16384,
            "scope": "full",
            "source_context": True,
        },
        "floor": {"min_recall_lower_bound": 0.5, "max_false_positive_upper_bound": 0.5},
        "meets_floor_as_measured": True,
        "results": {
            "confidence": 0.95,
            "recall": {"k": 2, "n": 2, "rate": 1.0, "low": 0.342, "high": 1.0},
            "recall_located": {"k": 2, "n": 2, "rate": 1.0, "low": 0.342, "high": 1.0},
            "false_positive": {"k": 0, "n": 0, "rate": None, "low": None, "high": None},
            "no_verdict": {"count": 1, "of": 3, "codes": {"model_busy": 1}},
            "per_class": {"a": {"caught": 1, "n": 1, "no_verdict": 0}},
        },
    }
    value.update(changes)
    return value


def test_the_block_says_there_is_no_measurement_until_there_is_one():
    block = CanaryReport().block(None)
    assert block.startswith(BEGIN) and block.endswith(END)
    assert "No measurement is recorded yet" in block


def test_the_block_states_the_measurement_its_conditions_and_its_intervals():
    block = CanaryReport().block(entry())
    assert "on `mac`, at commit `bbbbbbbbbbbb`, over all 3 cases" in block
    assert "Model `gpt-oss:20b`, think `default`, window 65536, reserve 16384" in block
    assert "source context on." in block
    assert "| 95% Wilson interval |" in block
    assert "| 2 of 2 (100.0%) | 34.2% – 100.0% |" in block
    assert "| False positives: controls blocked | 0 of 0 | unmeasured |" in block
    assert "| No verdict | 1 of 3 (model_busy 1) | not counted either way |" in block
    assert "| `a` | 1 of 1 | 0 |" in block
    assert "this measurement **meets** it" in block


def test_the_block_names_a_subset_and_a_measurement_under_the_floor():
    settings = {**entry()["settings"], "think": "low", "source_context": False}
    block = CanaryReport().block(
        entry(
            subset=True,
            case_ids=["x"],
            meets_floor_as_measured=False,
            settings=settings,
            results={
                **entry()["results"],
                "no_verdict": {"count": 0, "of": 3, "codes": {}},
            },
        )
    )
    assert "over a subset of 1 of the corpus's 3 cases" in block
    assert "think `low`" in block and "source context off." in block
    assert "| No verdict | 0 of 3 | not counted either way |" in block
    assert "**does not meet**" in block


def test_the_block_replaces_only_what_lies_between_the_markers():
    page = f"before\n{BEGIN}\nold\n{END}\nafter\n"
    assert CanaryReport().apply(page, "NEW") == "before\nNEW\nafter\n"
    with pytest.raises(ValueError, match="no generated review-canary block"):
        CanaryReport().apply("nothing here", "NEW")
    with pytest.raises(ValueError, match="no generated review-canary block"):
        CanaryReport().apply(f"{END}\n{BEGIN}", "NEW")


# ------------------------------------------------------------- the review the PR review asks


def local_review_flags(text: str) -> set[str]:
    """Every flag the rendered workflow passes `vibey-gh local-review`, with its value."""
    start = text.index("vibey-gh local-review \\")
    end = text.index('> "${RUNNER_TEMP}/verdict.json"', start)
    return set(re.findall(r"(--[a-z][a-z-]+)", text[start:end]))


def test_the_canary_passes_local_review_every_flag_the_pull_request_review_does():
    """Same code path: the rendered sovereign job's `local-review` flags, flag for flag,
    less the head (a case is no commit). Both values of each switch are covered."""
    workflow = (REPO / ".github/workflows/pr-review.yml").read_text(encoding="utf-8")
    expected = local_review_flags(workflow) - {"--head-sha"}
    settings = ReviewCanary.settings(load_config(REPO))
    argv = ReviewCanary.argv(
        {**settings, "scope": "full", "source_context": True},
        base_url="http://model:11434",
        diff=Path("d"),
        outcome=Path("o"),
        context_dir=Path("c"),
        source_dir=Path("s"),
    )
    flags = {item for item in argv if item.startswith("--")}
    assert flags - {"--split-added-hunks", "--no-split-added-hunks"} == expected - {
        "--split-added-hunks"
    }
    assert "--split-added-hunks" in flags or "--no-split-added-hunks" in flags


def test_the_canary_passes_the_same_values_the_rendered_review_does():
    """Every literal value the rendered sovereign job passes `local-review` -- the model,
    think level, window, reserve, limits, deadline rates and slot wait -- is the value the
    canary passes for this repository's configuration."""
    workflow = (REPO / ".github/workflows/pr-review.yml").read_text(encoding="utf-8")
    start = workflow.index("vibey-gh local-review \\")
    end = workflow.index('> "${RUNNER_TEMP}/verdict.json"', start)
    rendered = {
        flag: value.strip("'")
        for flag, value in re.findall(
            r"(--[a-z][a-z-]+) ('[^']*'|[^\s\\$\"]+)", workflow[start:end]
        )
        if not value.startswith("--")
    }
    assert {"--model", "--think", "--context-window", "--slot-wait-seconds"} <= set(rendered)
    settings = ReviewCanary.settings(load_config(REPO))
    argv = ReviewCanary.argv(
        settings,
        base_url="u",
        diff=Path("d"),
        outcome=Path("o"),
        context_dir=Path("c"),
        source_dir=Path("s"),
    )
    for flag, value in rendered.items():
        assert argv[argv.index(flag) + 1] == value, flag


def test_the_canary_argv_follows_each_setting():
    cfg = GhConfig(
        root=Path("."),
        pr_automation=PrAutomationConfig(
            paid_review=True,
            fallback=PrAutomationFallbackConfig(
                think="low", split_added_hunks=False, source_context=False
            ),
        ),
    )
    settings = ReviewCanary.settings(cfg)
    assert settings["scope"] == "diff-groundable" and settings["role"] == "sovereign"
    argv = ReviewCanary.argv(
        settings,
        base_url="u",
        diff=Path("d"),
        outcome=Path("o"),
        context_dir=Path("c"),
        source_dir=Path("s"),
    )
    assert "--no-split-added-hunks" in argv and "--scope" not in argv
    assert "--source-dir" not in argv
    assert argv[argv.index("--think") + 1] == "low"
    assert argv[argv.index("--base-url") + 1] == "u"
    assert set(VERDICT_SETTINGS) <= set(settings)


def test_the_settings_are_read_from_the_fallback_table():
    cfg = load_config(REPO)
    settings = ReviewCanary.settings(cfg)
    fallback = cfg.pr_automation.fallback
    assert settings["model"] == fallback.model
    assert settings["think"] == fallback.think
    assert settings["slot_wait_seconds"] == fallback.slot_wait_seconds
    assert settings["context_paths"] == list(fallback.context_paths)
    assert settings["scope"] == ("diff-groundable" if cfg.pr_automation.paid_review else "full")


# --------------------------------------------------------------------- running the canary


class FakeClient:
    def __init__(self, base_url: str, resident: list[dict] | None = None) -> None:
        self.base_url = base_url
        self.resident = resident

    def version(self) -> str:
        return "0.35.0"

    def loaded(self) -> list[dict] | None:
        return self.resident

    def digest(self, model: str) -> str:
        return f"digest-of-{model}"

    def chat(self, body, timeout_s):  # pragma: no cover - never asked by the canary
        raise AssertionError


class FakeReviewer:
    """`local-review` as the canary sees it: argv in, a verdict on stdout, an outcome
    record, and an exit status. `verdicts` maps a case's planted text to its answer."""

    def __init__(self, answer) -> None:
        self.answer = answer
        self.calls: list[list[str]] = []
        self.seen: list[dict[str, Any]] = []

    def __call__(self, argv: list[str]) -> int:
        self.calls.append(argv)
        flag = dict(zip(argv[::2], argv[1::2], strict=False))
        diff = Path(argv[argv.index("--diff") + 1]).read_text(encoding="utf-8")
        context = Path(argv[argv.index("--context-dir") + 1]) if "--context-dir" in argv else None
        sources = Path(argv[argv.index("--source-dir") + 1]) if "--source-dir" in argv else None
        self.seen.append(
            {
                "diff": diff,
                "context": sorted(p.name for p in context.rglob("*")) if context else None,
                "sources": (
                    sorted(p.relative_to(sources).as_posix() for p in sources.rglob("*.py"))
                    if sources and sources.exists()
                    else None
                ),
                "model": flag.get("--model"),
            }
        )
        status, verdict, record, complaint = self.answer(diff)
        outcome = Path(argv[argv.index("--outcome") + 1])
        if record is not None:
            outcome.write_text(json.dumps(record), encoding="utf-8")
        if complaint:
            print(complaint, file=sys.stderr)
        if verdict is not None:
            print(json.dumps(verdict))
        return status


def answer_by_diff(diff: str):
    if "+    count = 1" in diff:
        finding = {
            "severity": "blocking",
            "path": "pkg/mod.py",
            "line": 2,
            "explanation": "off-by-one: count starts at 1",
            "recommended_fix": "count = 0",
        }
        return (
            0,
            {"pass": False, "findings": [finding]},
            {"code": "reviewed", "attempts": 1, "parts": 1},
            "",
        )
    if "-    if not user.allowed:" in diff:
        return 1, None, {"code": "model_timeout", "attempts": 1, "reason": "x"}, "\ntimed out\n"
    return 0, {"pass": True, "findings": []}, {"code": "reviewed", "attempts": 1, "parts": 1}, ""


def repository(tmp_path: Path, *, report: str = "docs/page.md", **canary: Any) -> GhConfig:
    (tmp_path / "corpus.toml").write_text(
        corpus_text(DEFECT_ONE, DEFECT_TWO, CONTROL), encoding="utf-8"
    )
    (tmp_path / "README.md").write_text("# readme\n", encoding="utf-8")
    page = tmp_path / "docs" / "page.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(f"# page\n\n{BEGIN}\n{END}\n", encoding="utf-8")
    return GhConfig(
        root=tmp_path,
        pr_automation=PrAutomationConfig(
            fallback=PrAutomationFallbackConfig(
                source_context=True, context_paths=("README.md", "docs/missing.md")
            ),
            review_canary=ReviewCanaryConfig(
                **{
                    "corpus": "corpus.toml",
                    "ledger": "ledger.jsonl",
                    "report": report,
                    "min_defects": 2,
                    "min_classes": 2,
                    "min_controls": 1,
                    **canary,
                }
            ),
        ),
    )


class Clock:
    def __init__(self, start: datetime) -> None:
        self.at = start

    def __call__(self) -> datetime:
        return self.at


def canary_for(
    cfg: GhConfig,
    reviewer=None,
    *,
    git: FakeGit | None = None,
    now: datetime | None = None,
    resident: list[dict] | None = None,
    environ: dict[str, str] | None = None,
) -> tuple[ReviewCanary, list[str]]:
    said: list[str] = []
    git = git or FakeGit()
    ticks = iter(range(0, 10_000, 30))
    canary = ReviewCanary(
        config=lambda: cfg,
        reviewer=reviewer or FakeReviewer(answer_by_diff),
        loader=lambda root: CorpusLoader(root, run=git),
        client=lambda url: FakeClient(url, resident),
        run=git,
        now=Clock(now or datetime(2026, 10, 1, 12, tzinfo=UTC)),
        monotonic=lambda: float(next(ticks)),
        environ={} if environ is None else environ,
        out=said.append,
    )
    return canary, said


def test_a_run_reviews_every_case_scores_it_records_it_and_renders_it(tmp_path):
    cfg = repository(tmp_path)
    reviewer = FakeReviewer(answer_by_diff)
    canary, said = canary_for(
        cfg, reviewer, resident=[{"name": "gpt-oss:20b"}], environ={"RUNNER_NAME": "r1"}
    )
    measured = canary.run()
    assert [case["outcome"] for case in measured["cases"]] == [CAUGHT, NO_VERDICT, CLEAN]
    assert measured["cases"][1]["code"] == "model_timeout"
    assert measured["cases"][1]["reason"] == "timed out"
    assert measured["cases"][0]["seconds"] == 30.0
    assert measured["results"]["recall"]["k"] == 1 and measured["results"]["recall"]["n"] == 1
    assert measured["results"]["no_verdict"]["count"] == 1
    assert measured["commit"] == HEAD and measured["runner"] == "r1"
    assert measured["subset"] is False and measured["case_ids"] == []
    assert measured["conditions"]["ollama_version"] == "0.35.0"
    assert measured["conditions"]["model_digest"] == "digest-of-gpt-oss:20b"
    assert measured["conditions"]["loaded_at_start"] == ["gpt-oss:20b"]
    assert list(measured["conditions"]["documents"]) == ["README.md"]
    assert measured["conditions"]["base_url"] == "http://127.0.0.1:11434"
    assert measured["settings_digest"] == ReviewCanary.settings_digest(measured["settings"])
    # The review was shown what the pull request's would be: the declared documents that
    # exist, and the changed file's full text as reference.
    assert reviewer.seen[0]["context"] == ["README.md"]
    assert reviewer.seen[0]["sources"] == ["pkg/mod.py"]
    assert said[0] == "vibey-gh: review-canary 1/3 obo-total: caught (reviewed, 30s)"
    (recorded,) = CanaryLedger().read(tmp_path / "ledger.jsonl")
    assert recorded["results"] == measured["results"]
    page = (tmp_path / "docs" / "page.md").read_text(encoding="utf-8")
    assert "over all 3 cases" in page
    assert canary.render(check=True) == 0


def test_a_run_uses_the_runners_model_url_and_records_nothing_when_asked(tmp_path):
    cfg = repository(tmp_path)
    reviewer = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(cfg, reviewer, environ={"VIBEY_OLLAMA_URL": "http://gpu:1"})
    measured = canary.run(record=False)
    assert all(call[call.index("--base-url") + 1] == "http://gpu:1" for call in reviewer.calls)
    assert measured["conditions"]["loaded_at_start"] is None
    assert not (tmp_path / "ledger.jsonl").exists()


def test_a_run_cut_short_resumes_from_its_work_file_and_rescores(tmp_path):
    cfg = repository(tmp_path)
    work = tmp_path / "work" / "canary.jsonl"
    first = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(cfg, first)
    canary.run(["obo-total"], work=work, record=False)
    assert len(first.calls) == 1
    work.write_text(work.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    second = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(cfg, second)
    measured = canary.run(work=work, record=False)
    assert len(second.calls) == 2  # the two cases not yet heard
    assert measured["cases"][0]["outcome"] == CAUGHT
    # Another setting is another measurement: nothing heard under the old one is reused.
    other = dataclasses.replace(
        cfg,
        pr_automation=dataclasses.replace(
            cfg.pr_automation,
            fallback=dataclasses.replace(cfg.pr_automation.fallback, think="high"),
        ),
    )
    third = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(other, third)
    canary.run(work=work, record=False)
    assert len(third.calls) == 3


def test_a_subset_is_recorded_as_one_and_never_meets_the_floor(tmp_path):
    cfg = repository(tmp_path)
    canary, _ = canary_for(cfg)
    measured = canary.run(["obo-total", "ctl-rename"])
    assert measured["subset"] is True
    assert measured["case_ids"] == ["obo-total", "ctl-rename"]
    assert measured["meets_floor_as_measured"] is False


def test_a_run_refuses_a_corpus_that_is_not_a_measurement_or_an_unknown_case(tmp_path):
    cfg = repository(tmp_path, min_defects=5)
    canary, _ = canary_for(cfg)
    with pytest.raises(ValueError, match="not a measurement: 2 defects"):
        canary.run()
    canary, _ = canary_for(repository(tmp_path))
    with pytest.raises(ValueError, match="no such case: nope"):
        canary.run(["nope"])


def test_a_review_of_a_diff_only_scope_is_shown_no_documents(tmp_path):
    cfg = repository(tmp_path)
    cfg = dataclasses.replace(
        cfg, pr_automation=dataclasses.replace(cfg.pr_automation, paid_review=True)
    )
    reviewer = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(cfg, reviewer)
    measured = canary.run(record=False)
    assert reviewer.seen[0]["context"] is None
    assert measured["conditions"]["documents"] == {}


def test_a_source_larger_than_the_fetch_limit_is_not_shown(tmp_path):
    cfg = repository(tmp_path)
    big = "x = 1\n" * 400
    git = FakeGit(files={"pkg/mod.py": SOURCE + big})
    cfg = dataclasses.replace(
        cfg,
        pr_automation=dataclasses.replace(
            cfg.pr_automation,
            fallback=dataclasses.replace(cfg.pr_automation.fallback, max_source_file_bytes=1000),
        ),
    )
    reviewer = FakeReviewer(answer_by_diff)
    canary, _ = canary_for(cfg, reviewer, git=git)
    canary.run(["ctl-rename"], record=False)
    assert reviewer.seen[0]["sources"] is None


def test_a_failed_review_with_no_record_and_no_words_is_unknown(tmp_path):
    cfg = repository(tmp_path)
    canary, _ = canary_for(
        cfg, FakeReviewer(lambda diff: (1, None, None, "")), git=FakeGit(head="")
    )
    measured = canary.run(["ctl-rename"], record=False)
    (case,) = measured["cases"]
    assert case["outcome"] == NO_VERDICT and case["code"] == review_outcome.UNKNOWN
    assert case["reason"] == "" and measured["commit"] == ""


def test_a_failed_review_falls_back_to_the_records_reason(tmp_path):
    cfg = repository(tmp_path)
    answer = (1, None, {"code": "model_busy", "reason": "busy all along"}, "")
    canary, _ = canary_for(cfg, FakeReviewer(lambda diff: answer))
    (case,) = canary.run(["ctl-rename"], record=False)["cases"]
    assert case["code"] == "model_busy" and case["reason"] == "busy all along"


def test_the_default_reviewer_is_local_review_and_the_default_client_is_ollama(
    tmp_path, monkeypatch
):
    from vibey_gh import local_review, slots

    reviewer = FakeReviewer(answer_by_diff)
    monkeypatch.setattr(local_review, "review", reviewer)
    monkeypatch.setattr(slots, "OllamaClient", lambda url: FakeClient(url))
    git = FakeGit()
    canary = ReviewCanary(
        config=lambda: repository(tmp_path),
        loader=lambda root: CorpusLoader(root, run=git),
        run=git,
        environ={},
        out=lambda _: None,
    )
    measured = canary.run(["ctl-rename"], record=False)
    assert len(reviewer.calls) == 1 and measured["conditions"]["ollama_version"] == "0.35.0"


# --------------------------------------------------------------------------- rendering


def test_render_without_a_report_page_says_so(tmp_path):
    canary, said = canary_for(repository(tmp_path, report=""))
    assert canary.render() == 0 and canary.render(check=True) == 0
    assert said[0] == "vibey-gh: [pr_automation.review_canary] declares no report page"
    canary.run()
    assert len(CanaryLedger().read(tmp_path / "ledger.jsonl")) == 1
    assert "# page" in (tmp_path / "docs" / "page.md").read_text(encoding="utf-8")


def test_render_check_fails_on_a_page_that_has_drifted(tmp_path):
    cfg = repository(tmp_path)
    canary, said = canary_for(cfg)
    assert canary.render(check=True) == 1  # the page's block is empty, not "none yet"
    assert canary.render() == 0 and canary.render(check=True) == 0
    CanaryLedger().append(tmp_path / "ledger.jsonl", canary.run(record=False))
    assert canary.render(check=True) == 1
    assert "does not show the latest measurement" in said[-1]
    assert canary.render() == 0 and canary.render(check=True) == 0


# ------------------------------------------------------------------------------ status


def test_status_without_a_measurement_is_unknown(tmp_path):
    canary, _ = canary_for(repository(tmp_path))
    answer = canary.status()
    assert answer["meets_floor"] is None
    assert answer["reasons"] == ["no measurement is recorded in ledger.jsonl"]
    assert answer["floor"]["min_recall_lower_bound"] == 0.5


def passing_reviewer() -> FakeReviewer:
    def answer(diff: str):
        if "+    count = 1" in diff or "-    if not user.allowed:" in diff:
            finding = {
                "severity": "blocking",
                "path": "pkg/mod.py",
                "explanation": "off-by-one at count = 1; the permission check on allowed is gone",
            }
            return 0, {"pass": False, "findings": [finding]}, {"code": "reviewed"}, ""
        return 0, {"pass": True, "findings": []}, {"code": "reviewed"}, ""

    return FakeReviewer(answer)


def test_status_vouches_for_a_fresh_whole_measurement_under_the_settings_in_force(tmp_path):
    cfg = repository(tmp_path, min_recall_lower_bound=0.1, max_false_positive_upper_bound=0.99)
    start = datetime(2026, 10, 1, 12, tzinfo=UTC)
    canary, _ = canary_for(cfg, passing_reviewer(), now=start)
    measured = canary.run()
    assert measured["meets_floor_as_measured"] is True
    canary, _ = canary_for(cfg, now=start + timedelta(days=3))
    answer = canary.status()
    assert answer["meets_floor"] is True and answer["reasons"] == []
    assert answer["age_days"] == 3.0 and answer["model"] == "gpt-oss:20b"
    assert answer["recall"]["k"] == 2 and answer["no_verdict"]["count"] == 0


def test_status_refuses_an_old_subset_measurement_of_another_corpus_and_settings(tmp_path):
    cfg = repository(tmp_path)
    start = datetime(2026, 10, 1, 12, tzinfo=UTC)
    canary, _ = canary_for(cfg, now=start)
    canary.run(["obo-total"])
    (tmp_path / "corpus.toml").write_text(corpus_text(DEFECT_ONE, CONTROL), encoding="utf-8")
    moved = dataclasses.replace(
        cfg,
        pr_automation=dataclasses.replace(
            cfg.pr_automation,
            fallback=dataclasses.replace(cfg.pr_automation.fallback, think="low"),
        ),
    )
    canary, _ = canary_for(moved, now=start + timedelta(days=15))
    answer = canary.status()
    assert answer["meets_floor"] is False
    reasons = "\n".join(answer["reasons"])
    assert "no control reached a verdict" in reasons
    assert "a subset of the corpus" in reasons
    assert "the corpus has changed" in reasons
    assert "settings have changed since it was measured: think" in reasons
    assert "15.0 days old, over max_age_days" in reasons
    (tmp_path / "corpus.toml").unlink()
    assert "the corpus has changed" in "\n".join(canary.status()["reasons"])


# ----------------------------------------------------------------------------- command


def parse(*argv: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    ReviewCanary.declare(parser)
    return parser.parse_args(list(argv))


def test_the_command_checks_shows_runs_renders_and_reports_status(tmp_path):
    cfg = repository(tmp_path, min_recall_lower_bound=0.1, max_false_positive_upper_bound=0.99)
    canary, said = canary_for(cfg, passing_reviewer())
    assert canary.command(parse("check")) == 0
    assert said[-1].startswith("vibey-gh: the review-canary corpus builds: 2 defects in 2")
    assert canary.command(parse("show", "--case", "guard-gone")) == 0
    assert said[-2].startswith("# guard-gone: defect removed_guard, planted at lines 9-9")
    assert said[-1].startswith("diff --git a/pkg/mod.py")
    assert canary.command(parse("show", "--case", "ctl-rename")) == 0
    assert said[-2] == "# ctl-rename: control -- renames count"
    assert canary.command(parse("status")) == 3
    assert said[-2:] == [
        "vibey-gh: the sovereign review has no measurement for the floor",
        "  - no measurement is recorded in ledger.jsonl",
    ]
    assert canary.command(parse("run", "--no-record")) == 0
    assert said[-1].endswith("\nvibey-gh: meets the floor")
    assert canary.command(parse("run", "--json")) == 0
    assert json.loads(said[-1])["subset"] is False
    assert canary.command(parse("render", "--check")) == 0
    assert canary.command(parse("status", "--json")) == 0
    assert json.loads(said[-1])["meets_floor"] is True
    assert canary.command(parse("status")) == 0
    assert said[-1] == "vibey-gh: the sovereign review meets the floor"


def test_the_command_says_why_the_floor_is_not_met_and_refuses_what_it_cannot_do(tmp_path):
    cfg = repository(tmp_path)
    canary, said = canary_for(cfg)
    assert canary.command(parse("run", "--case", "obo-total")) == 0
    assert said[-1].endswith("\nvibey-gh: a subset -- never measured against the floor")
    assert canary.command(parse("status")) == 1
    header = said.index("vibey-gh: the sovereign review does not meet the floor")
    reasons = said[header + 1 :]
    assert reasons[0].startswith("  - recall's lower bound")
    assert reasons[1].startswith("  - no control reached a verdict")
    assert reasons[2].startswith("  - the latest measurement reviewed a subset")
    assert canary.command(parse("show", "--case", "nope")) == 2
    assert said[-1] == "vibey-gh: review-canary: no such case: nope"
    small = repository(tmp_path, min_controls=4)
    canary, said = canary_for(small)
    assert canary.command(parse("check")) == 1
    assert said[-2:] == [
        "  - 1 controls, fewer than min_controls (4)",
        "vibey-gh: the review-canary corpus is not a measurement",
    ]
    assert canary.command(parse("run")) == 2


def test_the_summary_says_what_was_measured_and_against_what():
    measured = {
        "subset": False,
        "meets_floor_as_measured": False,
        "results": {
            "confidence": 0.95,
            "recall": {"k": 1, "n": 2, "rate": 0.5, "low": 0.0945, "high": 0.9055},
            "recall_located": {"k": 0, "n": 0, "rate": None, "low": None, "high": None},
            "false_positive": {"k": 0, "n": 1, "rate": 0.0, "low": 0.0, "high": 0.7935},
            "no_verdict": {"count": 0, "of": 3, "codes": {}},
        },
    }
    lines = ReviewCanary.summary(measured).splitlines()
    assert lines[0] == "vibey-gh: recall 1 of 2 (50.0%; 95% Wilson 9.4%-90.5%)"
    assert lines[1] == "vibey-gh: recall on location alone 0 of 0 (unmeasured)"
    assert lines[-1] == "vibey-gh: does not meet the floor"


def test_the_cli_runs_the_check_on_this_repository(monkeypatch, capsys):
    monkeypatch.chdir(REPO)
    assert cli.main(["review-canary", "check"]) == 0
    assert "the review-canary corpus builds" in capsys.readouterr().out


# ------------------------------------------------------------------------ configuration


def test_the_configuration_defaults_and_this_repositorys_declaration():
    default = ReviewCanaryConfig()
    assert default.report == "" and default.line_tolerance == 3
    assert default.min_recall_lower_bound == 0.5 and default.max_false_positive_upper_bound == 0.5
    declared = load_config(REPO).pr_automation.review_canary
    assert declared.report == "docs/runbooks/sovereign-review-runner.md"
    assert (REPO / declared.corpus).is_file()


@pytest.mark.parametrize(
    ("changes", "said"),
    [
        ({"corpus": " "}, "corpus must be a path"),
        ({"ledger": "/abs.jsonl"}, "ledger must be a repository-relative path"),
        ({"report": "../x.md"}, "report must be a repository-relative path"),
        ({"report": 3}, "report must be a repository-relative path"),
        ({"line_tolerance": -1}, "line_tolerance"),
        ({"line_tolerance": 2.0}, "line_tolerance"),
        ({"confidence_z": 0}, "confidence_z"),
        ({"confidence_z": True}, "confidence_z"),
        ({"confidence_z": float("nan")}, "confidence_z"),
        ({"min_recall_lower_bound": 1.5}, "min_recall_lower_bound"),
        ({"max_false_positive_upper_bound": "0.5"}, "max_false_positive_upper_bound"),
        ({"max_age_days": 0}, "max_age_days"),
        ({"min_controls": 1.0}, "min_controls"),
    ],
)
def test_a_canary_configuration_that_cannot_hold_is_refused(changes, said):
    with pytest.raises(ValueError, match=said):
        ReviewCanaryConfig(**changes)


def test_a_misspelt_key_is_refused_rather_than_read_as_its_default(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.review_canary]\nmin_recall_lowerbound = 0.9\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="does not know min_recall_lowerbound"):
        load_config(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.review_canary]\nmin_recall_lower_bound = 0.9\nreport = 'r.md'\n",
        encoding="utf-8",
    )
    declared = load_config(tmp_path).pr_automation.review_canary
    assert declared.min_recall_lower_bound == 0.9 and declared.report == "r.md"


# ------------------------------------------------------------------------- the workflow


def workflow() -> dict:
    return yaml.safe_load(
        (REPO / ".github/workflows/review-canary.yml").read_text(encoding="utf-8")
    )


def test_the_canary_runs_weekly_and_by_hand_on_the_sovereign_runner():
    loaded = workflow()
    triggers = loaded.get("on", loaded.get(True))
    assert set(triggers) == {"schedule", "workflow_dispatch"}
    (cron,) = [entry["cron"] for entry in triggers["schedule"]]
    minute, hour, day, month, weekday = cron.split()
    assert minute.isdigit() and hour.isdigit() and (day, month) == ("*", "*")
    assert weekday.isdigit() and weekday not in ("5", "6"), "never on the Sabbath window"
    label = load_config(REPO).pr_automation.fallback.runner_label
    assert loaded["jobs"]["measure"]["runs-on"] == ["self-hosted", label]
    assert loaded["jobs"]["measure"]["permissions"] == {"contents": "read"}
    assert loaded["concurrency"]["cancel-in-progress"] is False


def test_the_canary_lands_through_a_pull_request_with_every_gate():
    loaded = workflow()
    canary = load_config(REPO).pr_automation.review_canary
    measure = "\n".join(step.get("run", "") for step in loaded["jobs"]["measure"]["steps"])
    assert 'vibey-gh review-canary "$@"' in measure
    assert "canary run --work" in measure and "canary render --check" in measure
    checkout = loaded["jobs"]["measure"]["steps"][0]["with"]
    assert checkout["fetch-depth"] == 0, "the corpus pin is read with git show"
    upload = [
        step
        for step in loaded["jobs"]["measure"]["steps"]
        if "upload-artifact" in str(step.get("uses"))
    ]
    handed = upload[0]["with"]["path"].split()
    assert handed == [canary.ledger, canary.report]
    publish = loaded["jobs"]["publish"]
    script = "\n".join(step.get("run", "") for step in publish["steps"])
    assert "review-canary render --check" in script
    assert f"git add {canary.ledger}" in " ".join(script.split())
    assert canary.report in script
    assert "gh pr create" in script and "--base develop" in script
    assert "[skip ci]" not in script and "--no-verify" not in script
    assert "git push" in script and "HEAD:develop" not in script


# -------------------------------------------------------------------------- interfaces


def test_every_class_satisfies_the_interface_declared_beside_it(tmp_path):
    assert isinstance(CorpusLoader(tmp_path), CorpusLoaderInterface)
    assert isinstance(FindingMatcher(), FindingMatcherInterface)
    assert isinstance(WilsonInterval(), WilsonIntervalInterface)
    assert isinstance(CanaryScorer(), CanaryScorerInterface)
    assert isinstance(CanaryLedger(), CanaryLedgerInterface)
    assert isinstance(CanaryReport(), CanaryReportInterface)
    assert isinstance(ReviewCanary(), ReviewCanaryInterface)


def test_a_case_result_round_trips_through_its_record():
    result = score({"pass": False, "findings": [ON_TARGET]}, seconds=1.25)
    assert CaseResult.from_dict(result.as_dict()) == dataclasses.replace(result, seconds=1.2)
    minimal = CaseResult.from_dict({"case": "x", "kind": "control", "outcome": CLEAN, "code": "r"})
    assert minimal.evidence == () and minimal.defect_class == ""
