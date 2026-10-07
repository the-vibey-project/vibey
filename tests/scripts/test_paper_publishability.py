# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/paper_publishability.py`: every required check, the recommended ones, the
reviewer's rubric, the JSON form and the command's exit codes.

Each check is proved both ways on fixtures written to `tmp_path`: a minimal paper and
citation record that pass every required check, and one variant per check that breaks it
by name, so a check that could never fail -- the one outcome that proves nothing -- is
caught here rather than on the day it mattered.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts import paper_publishability as pp

REPO = Path(__file__).resolve().parents[2]
SETTINGS = pp.PublishabilitySettings.load(REPO / pp.DEFAULT_CONFIG)
TITLE = "A Demo Paper: Its Long Title"

PAPER = f"""\
# {TITLE}

**Abstract.** We present a demo. It has one claim and one number. The claim is bounded by
what the number can carry, and the number is recomputed from a tracked record.

*Artifacts.* This paper is typeset from `docs/paper.md`. Unless a passage names its own,
this revision's cutoff is `develop` at `abc1234`.

## Introduction

Its contributions are: a demo, and a measurement of it. The reviewer caught 18 of 25
planted defects (Wilson 95% interval 0.524 to 0.857) and blocked none of 14 clean changes.

A preregistered study of its failures is in progress; its registration, log and data are
in `research/large-diff-review/experiments/`.

```latex
## Not a heading: figure source inside a fence
```

## Conclusion

The demo is a demo. Its one number stands until the record it is computed from changes.

## Declarations

### Data and code availability

Every number in this paper is recomputed from tracked files in the repository by the
evidence script, and the figures are redrawn by the figure script, so a reader holding
the checkout reproduces each of them without asking the author for anything.

### Use of generative AI

Drafts of this paper were written with Claude and revised with the local engine; every
claim and citation was checked by the author, who remains responsible for the whole text,
including the parts a model produced first.

### Authorship, funding and competing interests

The single author meets all four ICMJE criteria: conception, drafting, approval and
accountability. The work was unfunded. The author maintains the software the paper
describes and declares that interest; there is no other competing interest.

### Reporting guidelines and registrations

Computer-science systems papers run through conference review, so no EQUATOR reporting
guideline applies to this paper and none is claimed. The large-diff study was
preregistered before its data were read, in `research/large-diff-review/experiments/`.

## References

- A. Author, "A Paper," *Journal of Demos* 1(1):1–2, 2026. doi:10.1000/demo.
- B. Author, *A Book*, Demo Press, 2020.
- C. Author, "A Preprint," 2024. arXiv:2401.00001.
- D. Author, *A Page*, `https://example.org/page`, 2023.
"""

CITATION = f"""\
# A citation record, as GitHub renders it.
cff-version: 1.2.0
title: demo
type: software
authors:
  - family-names: Example
    given-names: Ada
    orcid: https://orcid.org/0000-0000-0000-0000
version: "1.0.0"
preferred-citation:
  # Not yet in a journal.
  type: generic
  title: >-
    {TITLE.split(":")[0]}:
    {TITLE.split(": ")[1]}
  authors:
    - family-names: Example
      given-names: Ada
  year: 2026
  doi: 10.1000/demo
"""


def _write(tmp_path: Path, paper: str = PAPER, citation: str = CITATION) -> tuple[Path, Path]:
    paper_path = tmp_path / "paper.md"
    citation_path = tmp_path / "CITATION.cff"
    paper_path.write_text(paper, encoding="utf-8")
    citation_path.write_text(citation, encoding="utf-8")
    return paper_path, citation_path


def _evaluate(tmp_path: Path, paper: str = PAPER, citation: str = CITATION) -> pp.Evaluation:
    return pp.PublishabilityEvaluator(SETTINGS).evaluate(*_write(tmp_path, paper, citation))


def _rows(evaluation: pp.Evaluation, check: str) -> list[pp.Row]:
    return [row for row in evaluation.rows if row.check == check]


def _failing(evaluation: pp.Evaluation) -> set[str]:
    return {row.check for row in evaluation.failures}


# ------------------------------------------------------------------------ the passing fixture


def test_the_minimal_paper_passes_every_required_check(tmp_path: Path) -> None:
    evaluation = _evaluate(tmp_path)
    assert evaluation.passed, [row for row in evaluation.rows if row.status != pp.PASS]
    required = [c.name for c in pp.CHECKS if c.required]
    assert sorted({row.check for row in evaluation.rows if row.required}) == sorted(required)
    # The fixture carries an ORCID and a DOI, so the recommended checks pass too.
    assert all(row.status == pp.PASS for row in evaluation.rows)
    assert evaluation.paper.endswith("paper.md") and evaluation.citation.endswith("CITATION.cff")


def test_each_passing_row_names_the_line_it_read(tmp_path: Path) -> None:
    evaluation = _evaluate(tmp_path)
    by_check = {row.check: row for row in evaluation.rows}
    assert by_check["contribution-statement"].line == 3
    assert by_check["abstract-length"].line == 3
    assert by_check["declarations"].line == PAPER.splitlines().index("## Declarations") + 1
    assert by_check["cutoff-named"].line == 7  # the line of the paragraph that says "cutoff"
    assert by_check["citation-title-matches"].line == 1
    assert by_check["references-well-formed"].line == PAPER.splitlines().index("## References") + 1


# ------------------------------------------------------------------------ one variant per check

Mutation = Callable[[str], str]


def _without_contribution_phrase(paper: str) -> str:
    return paper.replace("We present a demo.", "Here is a demo.")


def _without_contribution_word(paper: str) -> str:
    return paper.replace("Its contributions are:", "It offers:")


def _with_a_long_abstract(paper: str) -> str:
    padding = " ".join(["word"] * (SETTINGS.abstract_max_words + 1))
    return paper.replace("one number.", f"one number. {padding}", 1)


def _without_a_declarations_subsection(paper: str) -> str:
    start = paper.index("### Reporting guidelines and registrations")
    end = paper.index("## References")
    return paper[:start] + paper[end:]


def _with_a_short_declaration(paper: str) -> str:
    start = paper.index("### Data and code availability")
    end = paper.index("### Use of generative AI")
    return paper[:start] + "### Data and code availability\n\nAsk the author.\n\n" + paper[end:]


def _with_declarations_after_references(paper: str) -> str:
    start = paper.index("## Declarations")
    end = paper.index("## References")
    return paper[:start] + paper[end:] + "\n" + paper[start:end]


def _without_a_named_tool(paper: str) -> str:
    return paper.replace("written with Claude", "written with a model")


def _without_responsibility(paper: str) -> str:
    return paper.replace("who remains responsible for the whole text", "who read the whole text")


def _without_cutoff(paper: str) -> str:
    return paper.replace("this revision's cutoff is", "this revision is")


def _with_a_pending_marker(paper: str) -> str:
    return paper.replace(
        "## Conclusion", "<!-- TODO(1.0.0-pending: x) fill in -->\n\n## Conclusion"
    )


def _with_self_promotion(paper: str) -> str:
    return paper.replace(
        "The demo is a demo.", "The demo is the world's first of its kind, a paradigm shift."
    )


def _without_a_registration_path(paper: str) -> str:
    return paper.replace("in `research/large-diff-review/experiments/`", "in the repository")


def _with_one_interval_bound(paper: str) -> str:
    return paper.replace("0.524 to 0.857", "0.524")


def _with_a_bad_reference(paper: str) -> str:
    return paper + "- E. Nobody, *Untitled*.\n- F. Nobody, *Undated*, Demo Press.\n"


@pytest.mark.parametrize(
    ("check", "mutate", "said"),
    [
        ("contribution-statement", _without_contribution_phrase, "the abstract states none of"),
        ("contribution-statement", _without_contribution_word, "## Introduction never says"),
        ("abstract-length", _with_a_long_abstract, "at most 350"),
        ("declarations", _without_a_declarations_subsection, "is missing from ## Declarations"),
        ("declarations", _with_a_short_declaration, "has 3 words; at least 25"),
        ("declarations", _with_declarations_after_references, "comes after ## References"),
        ("ai-disclosure-names-tools", _without_a_named_tool, "names none of the tools"),
        ("ai-disclosure-names-tools", _without_responsibility, "remains responsible"),
        ("cutoff-named", _without_cutoff, 'never says "cutoff"'),
        ("no-pending-markers", _with_a_pending_marker, "TODO(1.0.0-pending: x)"),
        ("no-self-promotion", _with_self_promotion, '"world\'s first" at:'),
        ("registrations-located", _without_a_registration_path, 'mentions "preregist"'),
        ("intervals-complete", _with_one_interval_bound, "1 decimal numbers, at least 2"),
        ("references-well-formed", _with_a_bad_reference, "no year"),
    ],
    ids=lambda value: value if isinstance(value, str) and "-" in value else None,
)
def test_each_required_check_fails_by_name_with_its_line(
    tmp_path: Path, check: str, mutate: Mutation, said: str
) -> None:
    paper = mutate(PAPER)
    assert paper != PAPER, "the mutation changed nothing"
    evaluation = _evaluate(tmp_path, paper)
    assert _failing(evaluation) == {check}, evaluation.failures
    rows = [row for row in _rows(evaluation, check) if row.status == pp.FAIL]
    assert any(said in row.detail for row in rows), rows
    assert all(row.line is not None for row in rows), rows
    assert all(row.required for row in rows)


def test_a_missing_section_is_reported_without_a_line(tmp_path: Path) -> None:
    paper = PAPER.replace("## Declarations", "## Statements")
    evaluation = _evaluate(tmp_path, paper)
    rows = _rows(evaluation, "declarations")
    assert [(row.status, row.line) for row in rows] == [(pp.FAIL, None)]
    assert "no ## Declarations section" in rows[0].detail
    # The disclosure check cannot find its subsection either, and says so on its own row.
    assert _failing(evaluation) == {"declarations", "ai-disclosure-names-tools"}


def test_every_missing_or_short_declaration_is_its_own_row(tmp_path: Path) -> None:
    paper = _with_a_short_declaration(_without_a_declarations_subsection(PAPER))
    rows = [r for r in _rows(_evaluate(tmp_path, paper), "declarations") if r.status == pp.FAIL]
    details = sorted(row.detail for row in rows)
    assert len(details) == 2
    assert details[0].startswith("### Data and code availability has 3 words")
    assert details[1].startswith("### Reporting guidelines and registrations is missing")


def test_every_offending_reference_is_named_with_its_line(tmp_path: Path) -> None:
    paper = _with_a_bad_reference(PAPER)
    rows = [r for r in _rows(_evaluate(tmp_path, paper), "references-well-formed")]
    assert len(rows) == 2
    total = len(paper.splitlines())
    untitled, undated = sorted(rows, key=lambda row: row.line or 0)
    assert untitled.line == total - 1 and "E. Nobody" in untitled.detail
    assert "no year" in untitled.detail and "no locator" in untitled.detail
    assert undated.line == total and "no year" in undated.detail
    assert "no locator" not in undated.detail  # "Demo Press" is a venue word


def test_every_self_promoting_line_is_reported(tmp_path: Path) -> None:
    paper = _with_self_promotion(PAPER) + "\nAn unprecedented result.\n"
    rows = _rows(_evaluate(tmp_path, paper), "no-self-promotion")
    phrases = sorted(row.detail.split(" at:")[0] for row in rows)
    assert phrases == ['"paradigm shift"', '"unprecedented"', '"world\'s first"']
    assert len({row.line for row in rows}) == 2


def test_an_ai_tool_named_as_an_author_fails(tmp_path: Path) -> None:
    citation = CITATION.replace(
        "  authors:\n    - family-names: Example\n      given-names: Ada\n",
        "  authors:\n    - family-names: Example\n      given-names: Ada\n    - name: Claude\n",
    )
    assert citation != CITATION
    evaluation = _evaluate(tmp_path, citation=citation)
    assert _failing(evaluation) == {"no-ai-author"}
    (row,) = [r for r in _rows(evaluation, "no-ai-author") if r.status == pp.FAIL]
    assert row.detail == "preferred-citation.authors: 'Claude' names Claude"
    assert row.line is None  # the finding is in the citation record, not the paper


def test_a_citation_title_that_differs_from_the_paper_fails(tmp_path: Path) -> None:
    citation = CITATION.replace("Long Title", "Short Title")
    evaluation = _evaluate(tmp_path, citation=citation)
    assert _failing(evaluation) == {"citation-title-matches"}
    (row,) = _rows(evaluation, "citation-title-matches")
    assert "Short Title" in row.detail and "Long Title" in row.detail and row.line == 1


def test_a_citation_record_with_no_authors_fails(tmp_path: Path) -> None:
    citation = "cff-version: 1.2.0\ntitle: demo\n"
    evaluation = _evaluate(tmp_path, citation=citation)
    assert {"no-ai-author", "citation-title-matches"} <= _failing(evaluation)
    (row,) = _rows(evaluation, "no-ai-author")
    assert "names no author under authors or preferred-citation.authors" in row.detail


# ------------------------------------------------------------------------ recommended and reviewer


def test_recommended_checks_are_reported_and_never_fail(tmp_path: Path) -> None:
    citation = CITATION.replace("    orcid: https://orcid.org/0000-0000-0000-0000\n", "").replace(
        "  doi: 10.1000/demo\n", ""
    )
    evaluation = _evaluate(tmp_path, citation=citation)
    assert evaluation.passed and evaluation.failures == ()
    by_check = {row.check: row for row in evaluation.rows}
    assert by_check["orcid-present"].status == pp.RECOMMENDED
    assert by_check["preprint-or-doi"].status == pp.RECOMMENDED
    assert not by_check["orcid-present"].required
    assert "orcid:" in by_check["orcid-present"].detail
    assert "doi:, identifiers:" in by_check["preprint-or-doi"].detail


def test_an_identifiers_entry_satisfies_the_preprint_recommendation(tmp_path: Path) -> None:
    citation = CITATION.replace("  doi: 10.1000/demo\n", "") + (
        "identifiers:\n  - type: url\n    value: https://example.org/preprint\n"
    )
    (row,) = _rows(_evaluate(tmp_path, citation=citation), "preprint-or-doi")
    assert row.status == pp.PASS and "identifiers:" in row.detail


def test_the_reviewer_rubric_is_printed_and_never_judged(tmp_path: Path) -> None:
    evaluation = _evaluate(tmp_path)
    text = pp.ReportRenderer().text(evaluation)
    assert "Needs a reviewer (judgment, never pass/fail):" in text
    ids = [item.id for item in evaluation.reviewer]
    assert {"scope-and-novelty", "reproducible-methods", "text-recycling-cited"} <= set(ids)
    for item in evaluation.reviewer:
        assert item.id in text and item.criterion in text
        assert item.id not in {row.check for row in evaluation.rows}
    assert "Result: every required check passes" in text


def test_the_text_report_tabulates_every_row_and_its_reason(tmp_path: Path) -> None:
    text = pp.ReportRenderer().text(_evaluate(tmp_path, _with_self_promotion(PAPER)))
    assert text.startswith("Paper publishability: ")
    header = next(line for line in text.splitlines() if line.startswith("CHECK"))
    assert header.split() == ["CHECK", "STATUS", "LINE", "DETAIL"]
    assert "Why each check is applied" in text
    assert "no-self-promotion" in text and "[required] §1:" in text
    assert "orcid-present" in text and "[recommended] §4 and §7:" in text
    assert "Result: 2 required failure(s) in 1 check(s): no-self-promotion" in text


# ------------------------------------------------------------------------ the JSON form


def test_the_json_form_carries_the_same_rows_and_the_rubric(tmp_path: Path) -> None:
    evaluation = _evaluate(tmp_path, _without_cutoff(PAPER))
    document = json.loads(pp.ReportRenderer().json(evaluation))
    assert set(document) == {"paper", "citation", "passed", "checks", "reviewer"}
    assert document["passed"] is False
    assert len(document["checks"]) == len(evaluation.rows)
    for row in document["checks"]:
        assert set(row) == {"check", "required", "status", "detail", "line", "reason"}
        assert row["status"] in pp.STATUSES
    failing = [row for row in document["checks"] if row["status"] == "FAIL"]
    assert [row["check"] for row in failing] == ["cutoff-named"]
    assert [item["id"] for item in document["reviewer"]] == [i.id for i in evaluation.reviewer]


# ------------------------------------------------------------------------ the command


def test_check_exits_1_only_on_a_required_failure(tmp_path: Path, capsys) -> None:
    paper, citation = _write(tmp_path)
    argv = ["--paper", str(paper), "--citation", str(citation)]
    assert pp.main(["check", *argv]) == 0
    assert "Result: every required check passes" in capsys.readouterr().out

    paper.write_text(_with_a_pending_marker(PAPER), encoding="utf-8")
    assert pp.main(["check", *argv]) == 1
    out = capsys.readouterr().out
    assert "no-pending-markers" in out and "FAIL" in out

    # `report` prints the same evaluation and never fails the caller.
    assert pp.main(["report", *argv]) == 0
    assert "no-pending-markers" in capsys.readouterr().out


def test_check_with_json_prints_one_document(tmp_path: Path, capsys) -> None:
    paper, citation = _write(tmp_path, _without_cutoff(PAPER))
    assert pp.main(["check", "--json", "--paper", str(paper), "--citation", str(citation)]) == 1
    document = json.loads(capsys.readouterr().out)
    assert document["passed"] is False
    assert document["paper"] == str(paper) and document["citation"] == str(citation)


def test_a_missing_paper_is_named_on_stderr_and_fails(tmp_path: Path, capsys) -> None:
    _paper, citation = _write(tmp_path)
    missing = tmp_path / "absent.md"
    assert pp.main(["report", "--paper", str(missing), "--citation", str(citation)]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and "absent.md" in captured.err


def test_an_unreadable_citation_record_names_its_line(tmp_path: Path, capsys) -> None:
    paper, citation = _write(tmp_path)
    citation.write_text("cff-version: 1.2.0\nauthors:\n  - family-names: X\n   stray: y\n")
    assert pp.main(["check", "--paper", str(paper), "--citation", str(citation)]) == 1
    assert "CITATION.cff line 4" in capsys.readouterr().err


def test_the_defaults_point_at_the_repository_s_own_paper_and_record() -> None:
    assert (REPO / SETTINGS.paper).is_file() and (REPO / SETTINGS.citation).is_file()
    assert SETTINGS.abstract_max_words == 350 and SETTINGS.declaration_min_words == 25
    assert "research/large-diff-review/experiments/" in SETTINGS.registration_paths


# ------------------------------------------------------------------------ the readers


def test_the_citation_reader_reads_the_repository_s_record() -> None:
    record = pp.CitationFile.read(
        REPO / "CITATION.cff", SETTINGS.citation_author_paths, SETTINGS.citation_title_path
    )
    assert record.resolve("cff-version") == "1.2.0"
    assert record.preferred_title() is not None and "Ledger-Mediated" in record.preferred_title()
    names = record.author_names()
    assert ("authors", "Adam Matthew Steinberger") in names
    assert ("preferred-citation.authors", "Adam Matthew Steinberger") in names
    assert record.resolve("references")[0]["type"] == "book"


def test_the_citation_reader_handles_folded_literal_quoted_and_nested_shapes() -> None:
    record = pp.CitationFile.parse(
        'a: >-\n  one\n  two\nb: |\n  line 1\n  line 2\nc: "quoted: value"\n'
        "d: plain # a comment\ne:\n  - x\n  - y\nf:\n- key: 1\n  other: 2\n"
        "g:\n  - nested:\n      deep: true\nh:\n"
    )
    assert record == {
        "a": "one two",
        "b": "line 1\nline 2",
        "c": "quoted: value",
        "d": "plain",
        "e": ["x", "y"],
        "f": [{"key": "1", "other": "2"}],
        "g": [{"nested": {"deep": "true"}}],
        "h": None,
    }


def test_the_citation_reader_refuses_what_it_cannot_read() -> None:
    with pytest.raises(ValueError, match="line 2"):
        pp.CitationFile.parse("a: 1\n  b: 2\n")
    with pytest.raises(ValueError, match="line 1"):
        pp.CitationFile.parse("just text\n")


def test_the_paper_reader_ignores_headings_inside_fences_and_folds_bullets() -> None:
    paper = pp.Paper(
        "# T\n\nIntro. Second one.\nStill second.\n\n```latex\n## Fenced\n```\n\n"
        "## Real\n\n- first item\n  continued\n- second item\n\n### Sub\n\nBody words here.\n",
        SETTINGS.sentence_boundary,
    )
    assert paper.title() == "T"
    assert paper.section("## Fenced") is None
    real = paper.section("## Real")
    assert real is not None and real.line == 10
    assert [(b.line, b.text) for b in paper.bullets(real)] == [
        (12, "first item continued"),
        (14, "second item"),
    ]
    (sub,) = paper.subsections(real)
    assert (sub.heading, sub.line, sub.words) == ("Sub", 16, 3)
    intro = paper.paragraphs()[1]
    assert [(s.line, s.text) for s in paper.sentences(intro)] == [
        (3, "Intro."),
        (3, "Second one."),
        (4, "Still second."),
    ]
    assert intro.line_of("still") == 4
