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
HEREDOC = re.compile(r"<<-?\s*'?(PY|EOF|EOT|SH)'?")
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
    return problems


def main() -> int:
    targets: list[tuple[Path, bool]] = []
    for fragment in sorted(SPECS.glob("*-queue.txt")):
        for line in fragment.read_text().splitlines():
            parts = line.split()
            if (
                parts
                and not parts[0].startswith("#")
                and (len(parts) < 2 or not parts[1].isdigit())
            ):
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
