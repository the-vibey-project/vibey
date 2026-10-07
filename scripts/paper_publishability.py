# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether the research paper meets the mechanical half of the journal publishability criteria.

    python scripts/paper_publishability.py report [--paper PATH] [--citation PATH] [--json]
    python scripts/paper_publishability.py check  [--paper PATH] [--citation PATH] [--json]

`report` prints the evaluation and exits 0. `check` prints the same and exits 1 when any
REQUIRED check fails, naming each failure with the line it was found on. `--json` emits
the same structure as one JSON document, with the reviewer's rubric under `reviewer`.

The criteria are the `journal-publishability-criteria` skill (the `writing-craft` plugin of
vibey-skills). They split in two. The MECHANICAL half -- a contribution statement, an
abstract within the venue's length, the declarations every journal asks for, an AI
disclosure that names its tools, no AI listed as an author, a citation record that agrees
with the paper, references a reader can locate, a named evidence cutoff, no pending
markers, no self-promotion, located registrations and complete intervals -- is judged here,
on every pull request (`tests/meta/test_paper_publishability.py`) and again before the
paper is rendered and published (`release-surfaces.yml`), so the toil of remembering each
item is automated and a missed one is said out loud (sub-doctrine 12.e). The JUDGMENT half
-- scope and novelty, methodological soundness, claims the evidence can carry, null
results, reproducibility, text recycling, length against the venue -- cannot be read by a
regular expression; it is printed as the reviewer's rubric, never as pass or fail, for a
person or the review lane to apply to any change to the paper.

Every threshold, heading, phrase list and path is declared in
`scripts/paper_publishability.toml` (ADR-0051), so an adopter with a different paper
changes the file and not this script. Recommended checks (an ORCID, a DOI or preprint
identifier) are reported and never fail. Status is evidence-bounded (sub-doctrine 10.f):
each row names what it read and the line it read it on.
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from scripts.interfaces.paper_publishability_interface import (
        CheckInterface,
        CitationReaderInterface,
        PaperReaderInterface,
        ReportRendererInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.paper_publishability_interface import (  # type: ignore[import-not-found,no-redef]
        CheckInterface,
        CitationReaderInterface,
        PaperReaderInterface,
        ReportRendererInterface,
    )

SCRIPT = "scripts/paper_publishability.py"
#: Where this script finds its own configuration: the one location derived rather than
#: declared, because a tool must find its configuration before it can read anything
#: out of it (sub-doctrine 12.h states this exception and forbids widening it).
DEFAULT_CONFIG = Path(__file__).resolve().with_suffix(".toml")
REPO = Path(__file__).resolve().parents[1]
PASS = "PASS"
FAIL = "FAIL"
RECOMMENDED = "RECOMMENDED"
STATUSES = (PASS, FAIL, RECOMMENDED)
#: A decimal number: the shape both bounds of a reported interval take.
_DECIMAL = re.compile(r"\d+\.\d+")
#: A YAML block-scalar indicator, the only non-plain scalar a citation record writes.
_BLOCK_INDICATORS = frozenset({">", ">-", ">+", "|", "|-", "|+"})
#: `key:` at the start of a mapping entry, in the Citation File Format's key alphabet.
_CFF_KEY = re.compile(r"^([A-Za-z0-9_-]+):(?:\s|$)")
#: The name parts of a CFF author, in reading order; an entity author carries `name` alone.
_NAME_PARTS = ("given-names", "name-particle", "family-names", "name-suffix", "name")


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class ReviewerItem:
    """One criterion only a reviewer can judge: never pass or fail, always printed."""

    id: str
    section: str
    criterion: str


@dataclass(frozen=True)
class PublishabilitySettings:
    """Everything `scripts/paper_publishability.toml` declares, typed. A missing key is an
    error, not a silent default: a threshold nobody declared is a threshold nobody chose."""

    paper: str
    citation: str
    abstract_marker: str
    abstract_max_words: int
    contribution_phrases: tuple[str, ...]
    introduction_heading: str
    contribution_word: str
    declarations_heading: str
    references_heading: str
    declaration_sections: tuple[str, ...]
    declaration_min_words: int
    ai_disclosure_section: str
    ai_tools: tuple[str, ...]
    responsibility_stem: str
    citation_author_paths: tuple[str, ...]
    citation_title_path: str
    reference_year_pattern: str
    reference_locators: tuple[str, ...]
    reference_venue_words: tuple[str, ...]
    artifacts_marker: str
    cutoff_word: str
    pending_marker: str
    self_promotion_phrases: tuple[str, ...]
    registration_word: str
    registration_paths: tuple[str, ...]
    interval_markers: tuple[str, ...]
    interval_min_numbers: int
    sentence_boundary: str
    orcid_key: str
    identifier_keys: tuple[str, ...]
    reviewer: tuple[ReviewerItem, ...]

    @classmethod
    def load(cls, path: Path) -> PublishabilitySettings:
        table = tomllib.loads(path.read_text(encoding="utf-8"))["paper_publishability"]

        def words(key: str) -> tuple[str, ...]:
            return tuple(str(item) for item in table[key])

        return cls(
            paper=str(table["paper"]),
            citation=str(table["citation"]),
            abstract_marker=str(table["abstract_marker"]),
            abstract_max_words=int(table["abstract_max_words"]),
            contribution_phrases=words("contribution_phrases"),
            introduction_heading=str(table["introduction_heading"]),
            contribution_word=str(table["contribution_word"]),
            declarations_heading=str(table["declarations_heading"]),
            references_heading=str(table["references_heading"]),
            declaration_sections=words("declaration_sections"),
            declaration_min_words=int(table["declaration_min_words"]),
            ai_disclosure_section=str(table["ai_disclosure_section"]),
            ai_tools=words("ai_tools"),
            responsibility_stem=str(table["responsibility_stem"]),
            citation_author_paths=words("citation_author_paths"),
            citation_title_path=str(table["citation_title_path"]),
            reference_year_pattern=str(table["reference_year_pattern"]),
            reference_locators=words("reference_locators"),
            reference_venue_words=words("reference_venue_words"),
            artifacts_marker=str(table["artifacts_marker"]),
            cutoff_word=str(table["cutoff_word"]),
            pending_marker=str(table["pending_marker"]),
            self_promotion_phrases=words("self_promotion_phrases"),
            registration_word=str(table["registration_word"]),
            registration_paths=words("registration_paths"),
            interval_markers=words("interval_markers"),
            interval_min_numbers=int(table["interval_min_numbers"]),
            sentence_boundary=str(table["sentence_boundary"]),
            orcid_key=str(table["orcid_key"]),
            identifier_keys=words("identifier_keys"),
            reviewer=tuple(
                ReviewerItem(str(item["id"]), str(item["section"]), str(item["criterion"]))
                for item in table["reviewer"]
            ),
        )


# ------------------------------------------------------------------------ the paper


@dataclass(frozen=True)
class Paragraph:
    """A block of consecutive non-blank lines; `line` is the first one's number."""

    line: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    def line_of(self, needle: str) -> int:
        """The number of the first line containing `needle` (ignoring case), else `line`."""
        wanted = needle.lower()
        for offset, text in enumerate(self.lines):
            if wanted in text.lower():
                return self.line + offset
        return self.line


@dataclass(frozen=True)
class Section:
    """A heading and the body lines under it; `line` is the heading's number."""

    heading: str
    line: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(self.lines)

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass(frozen=True)
class Bullet:
    """One `- ` list item, its continuation lines folded in; `line` is the item's number."""

    line: int
    text: str


@dataclass(frozen=True)
class Sentence:
    """One sentence of a paragraph, with the number of the line it starts on."""

    line: int
    text: str


class Paper(PaperReaderInterface):
    """The paper's Markdown, read line by line so every finding can name its line.

    Headings are read outside fenced code only, for the reason the microslice converter
    gives (vibey-skills `slice_markdown.py`): a `## ` line inside a ```latex fence is
    figure source, not a section. Paragraphs are blocks between blank lines, fences
    included, because a caption inside a figure fence is published text too.
    """

    def __init__(self, text: str, sentence_boundary: str) -> None:
        self.lines: tuple[str, ...] = tuple(text.splitlines())
        self._boundary = re.compile(sentence_boundary)

    @classmethod
    def read(cls, path: Path, sentence_boundary: str) -> Paper:
        return cls(path.read_text(encoding="utf-8"), sentence_boundary)

    @staticmethod
    def _headings(lines: Sequence[str], max_level: int) -> list[tuple[int, int, str]]:
        """`(index, level, text)` for every ATX heading of level <= `max_level`, outside
        fenced code. A fence opens and closes on a line of three or more backticks or
        tildes, as CommonMark 0.31 has it."""
        found: list[tuple[int, int, str]] = []
        fence: str | None = None
        for index, raw in enumerate(lines):
            bare = raw.rstrip()
            opener = re.match(r" {0,3}(`{3,}|~{3,})", bare)
            if fence is not None:
                if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                    fence = None
                continue
            if opener:
                fence = opener.group(1)
                continue
            match = re.match(r"(#{1,6})[ \t]+(.+?)\s*$", bare)
            if match and len(match.group(1)) <= max_level:
                found.append((index, len(match.group(1)), match.group(2)))
        return found

    def title(self) -> str | None:
        for _index, level, text in self._headings(self.lines, 1):
            if level == 1:
                return text
        return None

    def paragraphs(self) -> list[Paragraph]:
        found: list[Paragraph] = []
        block: list[str] = []
        start = 0
        for index, raw in enumerate(self.lines):
            if raw.strip():
                if not block:
                    start = index
                block.append(raw)
            elif block:
                found.append(Paragraph(start + 1, tuple(block)))
                block = []
        if block:
            found.append(Paragraph(start + 1, tuple(block)))
        return found

    def opening_with(self, marker: str) -> Paragraph | None:
        """The first paragraph whose text begins with `marker`."""
        for paragraph in self.paragraphs():
            if paragraph.lines[0].lstrip().startswith(marker):
                return paragraph
        return None

    def section(self, heading: str) -> Section | None:
        wanted = heading.strip()
        headings = self._headings(self.lines, 2)
        for position, (index, _level, _text) in enumerate(headings):
            if self.lines[index].rstrip() != wanted:
                continue
            end = headings[position + 1][0] if position + 1 < len(headings) else len(self.lines)
            return Section(wanted, index + 1, tuple(self.lines[index + 1 : end]))
        return None

    def subsections(self, section: Section) -> list[Section]:
        headings = self._headings(section.lines, 3)
        found: list[Section] = []
        for position, (index, level, text) in enumerate(headings):
            if level != 3:
                continue
            end = headings[position + 1][0] if position + 1 < len(headings) else len(section.lines)
            found.append(
                Section(text, section.line + 1 + index, tuple(section.lines[index + 1 : end]))
            )
        return found

    def bullets(self, section: Section) -> list[Bullet]:
        found: list[Bullet] = []
        current: list[str] = []
        start = 0
        for index, raw in enumerate(section.lines):
            if raw.startswith("- "):
                if current:
                    found.append(Bullet(section.line + 1 + start, " ".join(current)))
                current = [raw[2:].strip()]
                start = index
            elif current and raw.strip() and not raw.startswith("#"):
                current.append(raw.strip())
            elif current:
                found.append(Bullet(section.line + 1 + start, " ".join(current)))
                current = []
        if current:
            found.append(Bullet(section.line + 1 + start, " ".join(current)))
        return found

    def sentences(self, paragraph: Paragraph) -> list[Sentence]:
        text = paragraph.text
        starts: list[int] = []
        position = 0
        for line in paragraph.lines:
            starts.append(position)
            position += len(line) + 1
        pieces: list[tuple[int, str]] = []
        last = 0
        for boundary in self._boundary.finditer(text):
            pieces.append((last, text[last : boundary.start()]))
            last = boundary.end()
        pieces.append((last, text[last:]))
        found: list[Sentence] = []
        for offset, piece in pieces:
            if piece.strip():
                line_index = max(bisect.bisect_right(starts, offset) - 1, 0)
                found.append(Sentence(paragraph.line + line_index, piece.strip()))
        return found


# ------------------------------------------------------------------------ the citation record


class CitationFile(CitationReaderInterface):
    """The repository's `CITATION.cff`, read for the names, titles and keys the checks ask.

    Not a YAML parser, for the reason `scripts/llms_txt.py` gives for not being one: a
    citation record is a constrained shape -- mappings, lists of mappings, plain or quoted
    scalars and `>-`/`|` block scalars -- and reading that shape keeps this script free of
    a dependency the site build alone owns. Anything outside the shape is an error that
    names its line, never a guess.
    """

    def __init__(
        self, record: Mapping[str, Any], author_paths: Sequence[str], title_path: str
    ) -> None:
        self.record = record
        self.author_paths = tuple(author_paths)
        self.title_path = title_path

    @classmethod
    def read(cls, path: Path, author_paths: Sequence[str], title_path: str) -> CitationFile:
        return cls(cls.parse(path.read_text(encoding="utf-8")), author_paths, title_path)

    @classmethod
    def parse(cls, text: str) -> dict[str, Any]:
        """The record as nested mappings, lists and strings."""
        reader = _CffReader(text.splitlines())
        return reader.document()

    def resolve(self, path: str) -> Any:
        """The value at a dotted key path, or None when any step is missing."""
        value: Any = self.record
        for key in path.split("."):
            if not isinstance(value, Mapping) or key not in value:
                return None
            value = value[key]
        return value

    def author_names(self) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for path in self.author_paths:
            authors = self.resolve(path)
            if not isinstance(authors, list):
                continue
            for author in authors:
                if not isinstance(author, Mapping):
                    continue
                parts = [str(author[part]) for part in _NAME_PARTS if author.get(part)]
                if parts:
                    found.append((path, " ".join(parts)))
        return found

    def preferred_title(self) -> str | None:
        title = self.resolve(self.title_path)
        return title if isinstance(title, str) else None

    def has_key(self, key: str) -> bool:
        return self._carries(self.record, key)

    @classmethod
    def _carries(cls, node: Any, key: str) -> bool:
        if isinstance(node, Mapping):
            return key in node or any(cls._carries(child, key) for child in node.values())
        if isinstance(node, list):
            return any(cls._carries(child, key) for child in node)
        return False


class _CffReader:
    """Reads the citation record's lines into nested mappings and lists by indentation."""

    def __init__(self, lines: Sequence[str]) -> None:
        self.lines = tuple(lines)

    def document(self) -> dict[str, Any]:
        start = self._skip(0)
        if start >= len(self.lines):
            return {}
        record, end = self._mapping(start, self._indent(start))
        end = self._skip(end)
        if end < len(self.lines):
            raise ValueError(f"CITATION.cff line {end + 1}: could not read {self.lines[end]!r}")
        return record

    def _indent(self, index: int) -> int:
        raw = self.lines[index]
        return len(raw) - len(raw.lstrip(" "))

    def _content(self, index: int) -> str:
        return self.lines[index].strip()

    def _skip(self, index: int) -> int:
        """The next line that is neither blank nor a whole-line comment."""
        while index < len(self.lines):
            stripped = self.lines[index].strip()
            if stripped and not stripped.startswith("#"):
                return index
            index += 1
        return index

    def _mapping(
        self, index: int, indent: int, first: tuple[int, str] | None = None
    ) -> tuple[dict[str, Any], int]:
        """A mapping whose entries sit at `indent`. `first` replaces the first entry's
        (indent, content), which is how a list item's leading `- key: value` is read."""
        result: dict[str, Any] = {}
        while True:
            index = self._skip(index)
            if index >= len(self.lines):
                break
            if first is not None:
                line_indent, content = first
                first = None
            else:
                line_indent, content = self._indent(index), self._content(index)
            if line_indent < indent:
                break
            if line_indent > indent or content.startswith("- "):
                raise ValueError(f"CITATION.cff line {index + 1}: unexpected {content!r}")
            match = _CFF_KEY.match(content)
            if match is None:
                raise ValueError(f"CITATION.cff line {index + 1}: not a key: {content!r}")
            key = match.group(1)
            value = content[match.end() :].strip()
            if value in _BLOCK_INDICATORS:
                result[key], index = self._block_scalar(index + 1, indent, value.startswith(">"))
            elif value == "":
                result[key], index = self._nested(index + 1, indent)
            else:
                result[key] = self._scalar(value)
                index += 1
        return result, index

    def _nested(self, index: int, indent: int) -> tuple[Any, int]:
        """What follows a bare `key:` line: a mapping or a list more indented than `indent`
        (a list may also sit at `indent` itself, as YAML allows), else nothing."""
        index = self._skip(index)
        if index >= len(self.lines):
            return None, index
        child_indent, content = self._indent(index), self._content(index)
        if content.startswith("- ") and child_indent >= indent:
            return self._sequence(index, child_indent)
        if child_indent > indent:
            return self._mapping(index, child_indent)
        return None, index

    def _sequence(self, index: int, indent: int) -> tuple[list[Any], int]:
        items: list[Any] = []
        while True:
            index = self._skip(index)
            if index >= len(self.lines):
                break
            line_indent, content = self._indent(index), self._content(index)
            if line_indent < indent or (line_indent == indent and not content.startswith("- ")):
                break
            if line_indent > indent or not content.startswith("- "):
                raise ValueError(f"CITATION.cff line {index + 1}: unexpected {content!r}")
            rest = content[2:].strip()
            if rest == "":
                item, index = self._nested(index + 1, indent)
            elif _CFF_KEY.match(rest):
                item, index = self._mapping(index, indent + 2, first=(indent + 2, rest))
            else:
                item, index = self._scalar(rest), index + 1
            items.append(item)
        return items, index

    def _block_scalar(self, index: int, indent: int, folded: bool) -> tuple[str, int]:
        parts: list[str] = []
        while index < len(self.lines):
            raw = self.lines[index]
            if not raw.strip():
                parts.append("")
                index += 1
                continue
            if self._indent(index) <= indent:
                break
            parts.append(raw.strip())
            index += 1
        while parts and parts[-1] == "":
            parts.pop()
        joiner = " " if folded else "\n"
        return joiner.join(part for part in parts if part or not folded), index

    @staticmethod
    def _scalar(value: str) -> str:
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            return value[1:-1]
        return value.split(" #", 1)[0].strip()


# ------------------------------------------------------------------------ the checks


@dataclass(frozen=True)
class Row:
    """One line of the evaluation: what a check found, where, and why it is applied."""

    check: str
    required: bool
    status: str
    detail: str
    line: int | None
    reason: str


class _Check(CheckInterface):
    """What every check shares: its name, whether it may fail the paper, the reason it is
    applied (the criteria section it cites), and the rows it writes."""

    name = ""
    required = True
    reason = ""

    def __init__(self, settings: PublishabilitySettings) -> None:
        self.settings = settings

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        raise NotImplementedError

    def _row(self, status: str, detail: str, line: int | None = None) -> Row:
        return Row(self.name, self.required, status, detail, line, self.reason)

    def _pass(self, detail: str, line: int | None = None) -> Row:
        return self._row(PASS, detail, line)

    def _fail(self, detail: str, line: int | None = None) -> Row:
        return self._row(FAIL if self.required else RECOMMENDED, detail, line)

    @staticmethod
    def _excerpt(text: str, limit: int = 72) -> str:
        flat = " ".join(text.split())
        return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"

    @staticmethod
    def _contains(haystack: str, needle: str) -> bool:
        return needle.lower() in haystack.lower()

    @staticmethod
    def _word(haystack: str, word: str) -> bool:
        return (
            re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", haystack, re.IGNORECASE) is not None
        )


class ContributionStatement(_Check):
    name = "contribution-statement"
    reason = (
        "§1: editors judge novelty from the abstract and introduction alone, so the "
        "contribution is stated in both"
    )

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        rows: list[Row] = []
        abstract = paper.opening_with(settings.abstract_marker)
        said = None
        if abstract is None:
            rows.append(self._fail(f"no paragraph opens with {settings.abstract_marker}"))
        else:
            said = next(
                (p for p in settings.contribution_phrases if self._contains(abstract.text, p)),
                None,
            )
            if said is None:
                listed = ", ".join(f'"{p}"' for p in settings.contribution_phrases)
                rows.append(self._fail(f"the abstract states none of {listed}", abstract.line))
        intro = paper.section(settings.introduction_heading)
        if intro is None:
            rows.append(self._fail(f"no {settings.introduction_heading} section"))
        elif not self._contains(intro.text, settings.contribution_word):
            rows.append(
                self._fail(
                    f'{settings.introduction_heading} never says "{settings.contribution_word}"',
                    intro.line,
                )
            )
        if rows:
            return rows
        assert abstract is not None and intro is not None
        return [
            self._pass(
                f'the abstract says "{said}" (line {abstract.line}); '
                f'{settings.introduction_heading} says "{settings.contribution_word}" '
                f"(line {intro.line})",
                abstract.line,
            )
        ]


class AbstractLength(_Check):
    name = "abstract-length"
    reason = "§1: the abstract is read first and in full; a venue's limit is a hard one"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        abstract = paper.opening_with(settings.abstract_marker)
        if abstract is None:
            return [self._fail(f"no paragraph opens with {settings.abstract_marker}")]
        body = abstract.text.replace(settings.abstract_marker, "", 1)
        count = len(body.split())
        if count > settings.abstract_max_words:
            return [
                self._fail(
                    f"the abstract has {count} words; at most {settings.abstract_max_words}",
                    abstract.line,
                )
            ]
        return [
            self._pass(
                f"the abstract has {count} words, within {settings.abstract_max_words}",
                abstract.line,
            )
        ]


class Declarations(_Check):
    name = "declarations"
    reason = (
        "§4 and §5: availability, AI use, authorship, funding, competing interests and "
        "reporting guidelines are each declared, before the references"
    )

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        declarations = paper.section(settings.declarations_heading)
        references = paper.section(settings.references_heading)
        if declarations is None:
            return [
                self._fail(
                    f"no {settings.declarations_heading} section before "
                    f"{settings.references_heading}"
                )
            ]
        rows: list[Row] = []
        if references is not None and declarations.line > references.line:
            rows.append(
                self._fail(
                    f"{settings.declarations_heading} (line {declarations.line}) comes after "
                    f"{settings.references_heading} (line {references.line})",
                    declarations.line,
                )
            )
        present = {sub.heading: sub for sub in paper.subsections(declarations)}
        for wanted in settings.declaration_sections:
            found = present.get(wanted)
            if found is None:
                rows.append(
                    self._fail(
                        f"### {wanted} is missing from {settings.declarations_heading}",
                        declarations.line,
                    )
                )
            elif found.words < settings.declaration_min_words:
                rows.append(
                    self._fail(
                        f"### {wanted} has {found.words} words; at least "
                        f"{settings.declaration_min_words}",
                        found.line,
                    )
                )
        if rows:
            return rows
        return [
            self._pass(
                f"{len(settings.declaration_sections)} subsections present, each at least "
                f"{settings.declaration_min_words} words",
                declarations.line,
            )
        ]


class AiDisclosureNamesTools(_Check):
    name = "ai-disclosure-names-tools"
    reason = (
        "§4: AI use is disclosed with the tool named, and the author remains responsible "
        "for every AI-assisted part"
    )

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        declarations = paper.section(settings.declarations_heading)
        disclosure = None
        if declarations is not None:
            disclosure = next(
                (
                    sub
                    for sub in paper.subsections(declarations)
                    if sub.heading == settings.ai_disclosure_section
                ),
                None,
            )
        if disclosure is None:
            return [
                self._fail(
                    f"no ### {settings.ai_disclosure_section} subsection under "
                    f"{settings.declarations_heading}"
                )
            ]
        named = [tool for tool in settings.ai_tools if self._word(disclosure.text, tool)]
        rows: list[Row] = []
        if not named:
            rows.append(
                self._fail(
                    "names none of the tools: " + ", ".join(settings.ai_tools), disclosure.line
                )
            )
        if not self._contains(disclosure.text, settings.responsibility_stem):
            rows.append(
                self._fail(
                    "does not say the author remains responsible (no word containing "
                    f'"{settings.responsibility_stem}")',
                    disclosure.line,
                )
            )
        if rows:
            return rows
        return [
            self._pass(
                "names " + ", ".join(named) + "; says the author remains responsible",
                disclosure.line,
            )
        ]


class NoAiAuthor(_Check):
    name = "no-ai-author"
    reason = "§4: no AI tool can be listed as an author; it cannot take responsibility"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        names = citation.author_names()
        if not names:
            return [
                self._fail(
                    f"{settings.citation} names no author under "
                    + " or ".join(settings.citation_author_paths)
                )
            ]
        rows = [
            self._fail(f"{where}: {name!r} names {tool}")
            for where, name in names
            for tool in settings.ai_tools
            if self._word(name, tool)
        ]
        if rows:
            return rows
        return [self._pass(f"{len(names)} author entries in {settings.citation}, none an AI tool")]


class CitationTitleMatches(_Check):
    name = "citation-title-matches"
    reason = "§4: the citation record is what a citation manager reads; it names this paper"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        title = paper.title()
        recorded = citation.preferred_title()
        if title is None:
            return [self._fail("the paper has no # title")]
        if recorded is None:
            return [self._fail(f"{settings.citation} has no {settings.citation_title_path}")]
        if " ".join(title.split()) != " ".join(recorded.split()):
            return [
                self._fail(
                    f"{settings.citation_title_path} is {self._excerpt(recorded)!r}; "
                    f"the paper's title is {self._excerpt(title)!r}",
                    1,
                )
            ]
        return [self._pass(f"{settings.citation_title_path} equals the paper's title", 1)]


class ReferencesWellFormed(_Check):
    name = "references-well-formed"
    reason = (
        "§1 and the checklist: every reference carries a year and a locator a reader can follow"
    )

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        references = paper.section(settings.references_heading)
        if references is None:
            return [self._fail(f"no {settings.references_heading} section")]
        entries = paper.bullets(references)
        if not entries:
            return [
                self._fail(f"{settings.references_heading} has no `- ` entries", references.line)
            ]
        year = re.compile(settings.reference_year_pattern)
        rows: list[Row] = []
        for entry in entries:
            missing = []
            if year.search(entry.text) is None:
                missing.append("no year")
            located = any(self._contains(entry.text, loc) for loc in settings.reference_locators)
            venue = any(self._word(entry.text, word) for word in settings.reference_venue_words)
            if not located and not venue:
                missing.append(
                    "no locator (" + ", ".join(settings.reference_locators) + " or a venue word)"
                )
            if missing:
                rows.append(
                    self._fail(
                        f"{self._excerpt(entry.text, 60)}: " + "; ".join(missing), entry.line
                    )
                )
        if rows:
            return rows
        return [
            self._pass(f"{len(entries)} entries, each with a year and a locator", references.line)
        ]


class CutoffNamed(_Check):
    name = "cutoff-named"
    reason = "§5 and sub-doctrine 10.f: the evidence names its cutoff, so a claim is bounded"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        artifacts = paper.opening_with(settings.artifacts_marker)
        if artifacts is None:
            return [self._fail(f"no paragraph opens with {settings.artifacts_marker}")]
        if not self._contains(artifacts.text, settings.cutoff_word):
            return [
                self._fail(
                    f'the {settings.artifacts_marker} paragraph never says "{settings.cutoff_word}"',
                    artifacts.line,
                )
            ]
        return [
            self._pass(
                f'the {settings.artifacts_marker} paragraph names its "{settings.cutoff_word}"',
                artifacts.line_of(settings.cutoff_word),
            )
        ]


class NoPendingMarkers(_Check):
    name = "no-pending-markers"
    reason = "sub-doctrine 12.e: a placeholder left for a pending input never ships"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        marker = self.settings.pending_marker
        rows = [
            self._fail(self._excerpt(text), number)
            for number, text in enumerate(paper.lines, 1)
            if marker in text
        ]
        return rows or [self._pass(f"no {marker} anywhere")]


class NoSelfPromotion(_Check):
    name = "no-self-promotion"
    reason = "§1: novelty is shown by the contribution, never asserted by a superlative"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        rows = [
            self._fail(f'"{phrase}" at: {self._excerpt(text)}', number)
            for number, text in enumerate(paper.lines, 1)
            for phrase in self.settings.self_promotion_phrases
            if self._contains(text, phrase)
        ]
        return rows or [self._pass("none of the configured phrases appears")]


class RegistrationsLocated(_Check):
    name = "registrations-located"
    reason = "§4 and §5: a registration is an output with a location, not a word"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        mentions = [
            p for p in paper.paragraphs() if self._contains(p.text, settings.registration_word)
        ]
        rows = [
            self._fail(
                f'mentions "{settings.registration_word}" but names none of: '
                + ", ".join(settings.registration_paths),
                paragraph.line_of(settings.registration_word),
            )
            for paragraph in mentions
            if not any(path in paragraph.text for path in settings.registration_paths)
        ]
        if rows:
            return rows
        if not mentions:
            return [self._pass(f'no paragraph mentions "{settings.registration_word}"')]
        return [
            self._pass(
                f'{len(mentions)} paragraphs mention "{settings.registration_word}", '
                "each naming its registration path"
            )
        ]


class IntervalsComplete(_Check):
    name = "intervals-complete"
    reason = "§2: an estimate is reported with its interval, both bounds, never a bare level"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        rows: list[Row] = []
        counted = 0
        for paragraph in paper.paragraphs():
            for sentence in paper.sentences(paragraph):
                if not any(marker in sentence.text for marker in settings.interval_markers):
                    continue
                counted += 1
                numbers = len(_DECIMAL.findall(sentence.text))
                if numbers < settings.interval_min_numbers:
                    rows.append(
                        self._fail(
                            f"{self._excerpt(sentence.text)}: {numbers} decimal numbers, at least "
                            f"{settings.interval_min_numbers} needed",
                            sentence.line,
                        )
                    )
        if rows:
            return rows
        if counted == 0:
            return [self._pass("no sentence states an interval")]
        return [self._pass(f"{counted} sentences state an interval, each with both bounds")]


class OrcidPresent(_Check):
    name = "orcid-present"
    required = False
    reason = "§4 and §7: an ORCID iD is the credibility signal most journals ask for"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        if citation.has_key(settings.orcid_key):
            return [self._pass(f"{settings.citation} carries an {settings.orcid_key}:")]
        return [self._fail(f"no author in {settings.citation} carries an {settings.orcid_key}:")]


class PreprintOrDoi(_Check):
    name = "preprint-or-doi"
    required = False
    reason = "§7: a DOI or preprint identifier makes the work citable and locatable"

    def run(self, paper: PaperReaderInterface, citation: CitationReaderInterface) -> list[Row]:
        settings = self.settings
        carried = [key for key in settings.identifier_keys if citation.has_key(key)]
        if carried:
            return [
                self._pass(f"{settings.citation} carries " + ", ".join(f"{k}:" for k in carried))
            ]
        return [
            self._fail(
                f"{settings.citation} carries none of "
                + ", ".join(f"{k}:" for k in settings.identifier_keys)
                + "; assign a DOI or deposit a preprint"
            )
        ]


#: The checks, in the order they are reported: required first, then recommended.
CHECKS: tuple[type[_Check], ...] = (
    ContributionStatement,
    AbstractLength,
    Declarations,
    AiDisclosureNamesTools,
    NoAiAuthor,
    CitationTitleMatches,
    ReferencesWellFormed,
    CutoffNamed,
    NoPendingMarkers,
    NoSelfPromotion,
    RegistrationsLocated,
    IntervalsComplete,
    OrcidPresent,
    PreprintOrDoi,
)


# ------------------------------------------------------------------------ the evaluation


@dataclass(frozen=True)
class Evaluation:
    """Every row every check wrote, the reviewer's rubric, and the files they were read from."""

    paper: str
    citation: str
    rows: tuple[Row, ...]
    reviewer: tuple[ReviewerItem, ...]

    @property
    def failures(self) -> tuple[Row, ...]:
        return tuple(row for row in self.rows if row.required and row.status == FAIL)

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "paper": self.paper,
            "citation": self.citation,
            "passed": self.passed,
            "checks": [asdict(row) for row in self.rows],
            "reviewer": [asdict(item) for item in self.reviewer],
        }


class PublishabilityEvaluator:
    """Runs every check against one paper and one citation record."""

    def __init__(
        self, settings: PublishabilitySettings, checks: Sequence[type[_Check]] = CHECKS
    ) -> None:
        self.settings = settings
        self.checks = tuple(checks)

    def evaluate(self, paper_path: Path, citation_path: Path) -> Evaluation:
        settings = self.settings
        paper = Paper.read(paper_path, settings.sentence_boundary)
        citation = CitationFile.read(
            citation_path, settings.citation_author_paths, settings.citation_title_path
        )
        rows: list[Row] = []
        for check in self.checks:
            rows.extend(check(settings).run(paper, citation))
        return Evaluation(
            self._display(paper_path), self._display(citation_path), tuple(rows), settings.reviewer
        )

    @staticmethod
    def _display(path: Path) -> str:
        """The path as the report names it: repository-relative when it is inside the
        repository, as given otherwise."""
        resolved = path.resolve()
        return str(resolved.relative_to(REPO)) if resolved.is_relative_to(REPO) else str(path)


class ReportRenderer(ReportRendererInterface):
    """Writes an evaluation as a table for a person, or as JSON for a machine."""

    def text(self, evaluation: Evaluation) -> str:
        rows = evaluation.rows
        width_check = max(len("CHECK"), *(len(row.check) for row in rows))
        width_status = max(len("STATUS"), *(len(row.status) for row in rows))
        lines = [
            f"Paper publishability: {evaluation.paper} with {evaluation.citation}",
            "",
            f"{'CHECK':<{width_check}}  {'STATUS':<{width_status}}  {'LINE':>5}  DETAIL",
        ]
        for row in rows:
            line = "-" if row.line is None else str(row.line)
            lines.append(
                f"{row.check:<{width_check}}  {row.status:<{width_status}}  {line:>5}  {row.detail}"
            )
        lines += ["", "Why each check is applied (the criteria section it cites):"]
        seen: dict[str, str] = {}
        for row in rows:
            seen.setdefault(row.check, row.reason)
        for check, reason in seen.items():
            kind = "required" if self._required(rows, check) else "recommended"
            lines.append(f"  {check:<{width_check}}  [{kind}] {reason}")
        lines += ["", "Needs a reviewer (judgment, never pass/fail):"]
        width_item = max((len(item.id) for item in evaluation.reviewer), default=0)
        for item in evaluation.reviewer:
            lines.append(f"  {item.id:<{width_item}}  §{item.section}: {item.criterion}")
        lines.append("")
        failures = evaluation.failures
        if failures:
            named = sorted({row.check for row in failures})
            lines.append(
                f"Result: {len(failures)} required failure(s) in {len(named)} check(s): "
                + ", ".join(named)
            )
        else:
            lines.append("Result: every required check passes")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _required(rows: Sequence[Row], check: str) -> bool:
        return next(row.required for row in rows if row.check == check)

    def json(self, evaluation: Evaluation) -> str:
        return json.dumps(evaluation.as_dict(), indent=2, ensure_ascii=False) + "\n"


# The entry point argparse needs: a module-level function, the one this script keeps
# (ADR-0016's method of last resort), so `python scripts/paper_publishability.py` runs.
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("command", choices=("report", "check"))
    parser.add_argument("--paper", type=Path, help="the paper's Markdown (default: from the TOML)")
    parser.add_argument("--citation", type=Path, help="the CITATION.cff (default: from the TOML)")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json", action="store_true", help="emit the evaluation as JSON")
    args = parser.parse_args(argv)
    settings = PublishabilitySettings.load(args.config)
    paper_path = args.paper if args.paper is not None else REPO / settings.paper
    citation_path = args.citation if args.citation is not None else REPO / settings.citation
    try:
        evaluation = PublishabilityEvaluator(settings).evaluate(paper_path, citation_path)
    except (OSError, ValueError) as error:
        print(f"{SCRIPT}: {error}", file=sys.stderr)
        return 1
    renderer = ReportRenderer()
    sys.stdout.write(renderer.json(evaluation) if args.json else renderer.text(evaluation))
    if args.command == "check" and not evaluation.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
