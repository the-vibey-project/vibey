"""Lint every spec about to be filed: what a lane on GitHub cannot use is a defect.

    python3 lint-specs.py            # every slug in specs/*-queue.txt, plus the rewritten issues

Checks: the template's sections are present; the check block is a fenced block; no shell
heredoc (the lane's `shell` tool takes an argv list); no pointer the lane cannot follow ("as
above", "see the parent", "same block as", a bare specs/ path is rewritten at filing and is
fine); no failure text that ends in an ellipsis.
"""

import csv
import re
import sys
from pathlib import Path

STORM = Path(__file__).resolve().parent.parent
SPECS = STORM / "specs"
AUDIT = STORM / "issue-audit"

SECTIONS = (
    "## Title",
    "## Why",
    "## Required behaviour",
    "## Acceptance criteria",
    "## Checks the lane must run",
)
# Lanes a human runs, never the storm: their "Checks" are a checklist, not a command block.
# The storm runner skips these (file-suite.py's OPERATOR_PREFIXES files them with `operator`).
OPERATOR_PREFIXES = ("gap-ops-", "gap-canon-")
# Any delimiter, not a fixed list: a `psql ... <<'SQL'` block sat in a queued spec unseen
# because SQL was not in the list. What breaks the lane is the heredoc, not its name.
HEREDOC = re.compile(r"<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?")
# A coverage run narrowed to particular test paths, beside a gate over a whole layer. The two
# together are the contradiction: the run measures a slice, the gate judges the whole.
NARROWED_COVERAGE = re.compile(r"^\s*uv run pytest .*--cov-report=((?:\s+tests/\S*)+)\s*$", re.M)
COVERAGE_GATE = re.compile(r"coverage report --include=.*--fail-under=100")
POINTERS = re.compile(
    r"\b(as (specified |shown )?above|see the parent|same block as|the Part \d block|"
    r"see #\d+'s spec)\b",
    re.I,
)
ELLIPSIS_FAILURE = re.compile(r'f?"[^"\n]*…"')
# Reviewed 2026-09-22: an ellipsis inside a quotation of EXISTING text, or an example pattern,
# is not a failure text the lane must produce.
ALLOWED = {
    ("fakes-test-harness.md", '"memory://…"'),  # an example path pattern
    (
        "orm-job-enqueue.md",
        '"NOTIFY\'s payload cannot be a bind parameter…"',
    ),  # quotes today's comment
    (
        "orm-raw-sql-guard.md",
        '"The live repositories still use asyncpg …"',
    ),  # quotes today's docstring
    ("340.md", '"gitlab does not support …"'),  # names a message prefix
    ("loops-retire-opencode-refusals.md", '"provider must be one of …"'),  # quotes today's message
    ("surfaces-failure-policy.md", '"Kannel rejected the message: …"'),  # names a message prefix
    # Reviewed 2026-09-22 (second pass, when the gap and roadmap fragments first reached the
    # linter): each of these quotes text that already exists, or names a prefix whose exact
    # format the same spec states elsewhere.
    (
        "gap-measure-domain.md",
        '"An exception type, so it has no interface beside it …"',
    ),  # quotes today's comment at publication_policy.py:167-172
    ("gap-measure-gh-1.md", '"has format …"'),  # one of an enumerated list of message prefixes
    (
        "roadmap-134-cost-integral-p3.md",
        '"1 of 3 local turn(s) …"',
    ),  # a fixture value: the test feeds this exact literal in and asserts it comes back out
    ("roadmap-85-jira-tracker-adapter.md", '"Jira API error 500 …"'),  # prefix; format at :44
    ("roadmap-85-jira-tracker-adapter.md", '"Jira unreachable …"'),  # prefix; format at :44
    # Reviewed 2026-09-22 (third pass, when queue.txt's own filed lanes first reached the
    # linter): each names a message prefix, not a message the lane must reproduce whole.
    ("forge-4.md", '"gh not found; skipping …"'),
    ("forge-6.md", '"`gh api graphql` failed: …"'),
    ("rmq-r05-async-outbox.md", 'f"… {self._table} …"'),  # an interpolation sketch, not a message
    ("forge-3.md", '"GitHub merged …"'),  # quotes the wording this lane replaces
}
# "as above" pointing at text earlier in the SAME spec is fine (reviewed 2026-09-22).
ALLOWED_POINTERS = {
    ("surfaces-records-fakes.md", "as above"),
    ("loops-config-loop-services.md", "as above"),
}


def lint(path: Path, *, need_sections: bool = True) -> list[str]:
    text = re.sub(r"^<!-- audit:.*-->\n", "", path.read_text(), count=1)  # filing strips it
    problems = []
    if need_sections:
        wanted = (
            SECTIONS if path.parent == SPECS else SECTIONS[1:]
        )  # an existing issue keeps its title
        # A spike's deliverable is an ADR, not code: it states the questions the ADR must
        # decide and the child lanes it must name, in place of behaviour to implement.
        spike = "## Deliverable" in text and "## Questions the ADR must decide" in text
        if spike:
            wanted = tuple(s for s in wanted if s != "## Required behaviour")
        problems += [f"missing section {s!r}" for s in wanted if s not in text]
        checks = text.split("## Checks the lane must run", 1)
        if (
            len(checks) == 2
            and not spike  # a spike writes a document and commits nothing: "None in code"
            and not path.name.startswith(OPERATOR_PREFIXES)
            and "```" not in checks[1].split("\n## ", 1)[0]
            and not re.search(r"^ {4}\S", checks[1].split("\n## ", 1)[0], re.M)
        ):
            problems.append("check block is not a fenced or indented code block")
    problems += [f"heredoc {m.group(0)!r}" for m in HEREDOC.finditer(text)]
    problems += [
        f"pointer {m.group(0)!r}"
        for m in POINTERS.finditer(text)
        if (path.name, m.group(0).lower()) not in ALLOWED_POINTERS
    ]
    problems += [
        f"failure text ends in … : {m.group(0)[:60]!r}"
        for m in ELLIPSIS_FAILURE.finditer(text)
        if (path.name, m.group(0)) not in ALLOWED
    ]
    # A coverage gate that cannot pass however good the lane's work is. Layer coverage is
    # produced by the whole suite -- domain code is exercised from application, infrastructure
    # and system tests -- so a run narrowed to `tests/domain` and then measured against
    # `--include='src/vibey/domain/*' --fail-under=100` reports 78% and always will. Thirty-
    # three specs carried this, and every lane under them was unpublishable by construction
    # rather than by anything the model did. CLAUDE.md's real gate names no path; neither may
    # a spec that then demands a whole layer.
    if COVERAGE_GATE.search(text):
        problems += [
            f"coverage run narrowed to {m.group(1).strip()!r} but the gate demands a whole "
            "layer -- it can never reach 100%; drop the path so the full suite runs"
            for m in NARROWED_COVERAGE.finditer(text)
        ]
    return problems


def main() -> int:
    targets: list[tuple[Path, bool]] = []
    # queue.txt too, not only the fragments: a filed lane still has a spec file, the lane still
    # reads it, and `file-suite.py rewrite` pushes it back over the issue body. Thirteen filed
    # forge-* specs carried a heredoc apiece while this reported a clean corpus.
    seen: set[str] = set()
    fragments = [*sorted(SPECS.glob("*-queue.txt")), STORM / "queue.txt"]
    for fragment in fragments:
        if not fragment.is_file():
            continue
        for line in fragment.read_text().splitlines():
            parts = line.split()
            if parts and not parts[0].startswith("#") and parts[0] not in seen:
                seen.add(parts[0])
                targets.append((SPECS / f"{parts[0]}.md", True))
    disposition = AUDIT / "storm-disposition.tsv"
    if disposition.is_file():
        for row in csv.reader(disposition.open(), delimiter="\t"):
            if row and len(row) > 2 and row[2] == "edit-body":
                targets.append((AUDIT / "updates" / f"{row[0]}.md", True))
    bad = 0
    for path, sections in targets:
        if not path.is_file():
            print(f"MISSING  {path.relative_to(STORM)}")
            bad += 1
            continue
        problems = lint(path, need_sections=sections)
        if problems:
            bad += 1
            print(f"{path.relative_to(STORM)}")
            for problem in problems[:6]:
                print(f"    {problem}")
    print(f"\n{len(targets)} specs checked, {bad} with problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
