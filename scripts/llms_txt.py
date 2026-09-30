# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The documentation's `llms.txt`, generated from its own navigation and checked for drift.

    python scripts/llms_txt.py           # write docs/llms.txt
    python scripts/llms_txt.py --check   # exit 1 when docs/llms.txt is not what the nav makes

`llms.txt` (https://llmstxt.org) is the index an AI reader fetches first: the site's name,
one summary line, then every page as a link with one sentence saying what it holds. This
one is written from the same `nav:` block the site and the book are built from, so a page
added to the site is in the index the moment the index is regenerated, and
`tests/meta/test_llms_txt.py` fails the build until it is (sub-doctrine 12.e: the check
that says out loud when the step was missed; 7.d: the machine-readable layer is declared
in the repository and never left to drift).

Nothing here is a second implementation of something the family already does (10.e): the
navigation is read by vibey-gh's own `NavReader` -- the reader the book exporter uses --
and the production channel, the governance source and which offline forms ship are read
through vibey-gh's own configuration loader. Every other input is declared in
`scripts/llms_txt.toml`.

Each description is the page's own `description:` front matter when it declares one, and
otherwise its first prose sentence, with a leading bold label ("**Bottom line:**") taken
off. A decision record -- a page with a `## Decision` section -- carries its title alone:
its title already states the decision, and its first sentences are a status line and a
context that read wrongly out of place. Links, emphasis and code marks are reduced to their
words, because an index line is read as plain text.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.book import NavReader
from vibey_gh.config import load_config

try:
    from scripts.interfaces.llms_txt_interface import (
        LinkSourceInterface,
        LlmsTxtRendererInterface,
        PageDescriberInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.llms_txt_interface import (  # type: ignore[import-not-found,no-redef]
        LinkSourceInterface,
        LlmsTxtRendererInterface,
        PageDescriberInterface,
    )

SCRIPT = "scripts/llms_txt.py"
#: Where this script finds its own configuration: the one location derived rather than
#: declared, because a tool must find its configuration before it can read anything
#: out of it (sub-doctrine 12.h states this exception and forbids widening it).
DEFAULT_CONFIG = Path(__file__).resolve().with_suffix(".toml")
REPO = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LlmsSettings:
    """Everything `scripts/llms_txt.toml` declares, typed. A missing key is an error."""

    site_config: str
    gh_config: str
    output: str
    unsectioned_heading: str
    description_limit: int
    governance_heading: str
    governance_order: tuple[str, ...]
    governance_glob: str
    downloads_heading: str

    @classmethod
    def load(cls, path: Path) -> LlmsSettings:
        table = tomllib.loads(path.read_text(encoding="utf-8"))["llms_txt"]
        return cls(
            site_config=str(table["site_config"]),
            gh_config=str(table["gh_config"]),
            output=str(table["output"]),
            unsectioned_heading=str(table["unsectioned_heading"]),
            description_limit=int(table["description_limit"]),
            governance_heading=str(table["governance_heading"]),
            governance_order=tuple(str(name) for name in table["governance_order"]),
            governance_glob=str(table["governance_glob"]),
            downloads_heading=str(table["downloads_heading"]),
        )


@dataclass(frozen=True)
class IndexEntry:
    """One line of the index: which section it sits in, and the link it carries."""

    section: str
    title: str
    url: str
    description: str = ""


@dataclass(frozen=True)
class SiteFacts:
    """What the site configuration says about the site as a whole."""

    name: str
    description: str
    url: str

    @classmethod
    def read(cls, text: str) -> SiteFacts:
        """The three top-level keys, read as plain `key: value` lines or a folded block.

        Not a YAML parser, for the reason `NavReader` gives for not being one: the
        configuration is a constrained shape this family writes, and reading the three
        keys it needs keeps this script free of a dependency the site build alone owns.
        """
        return cls(
            name=cls._scalar(text, "site_name"),
            description=cls._scalar(text, "site_description"),
            url=cls._scalar(text, "site_url"),
        )

    @staticmethod
    def _scalar(text: str, key: str) -> str:
        lines = text.splitlines()
        for index, line in enumerate(lines):
            match = re.match(rf"^{key}:\s*(.*)$", line)
            if match is None:
                continue
            value = match.group(1).strip()
            if value in (">", ">-", "|", "|-"):
                folded: list[str] = []
                for follow in lines[index + 1 :]:
                    if follow and not follow.startswith((" ", "\t")):
                        break
                    folded.append(follow.strip())
                return " ".join(part for part in folded if part)
            return value.strip("'\"")
        raise ValueError(f"the site configuration declares no {key}")


class MarkdownPageDescriber(PageDescriberInterface):
    """One sentence that says what a Markdown page holds."""

    _FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
    _LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
    _SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'“])")
    # Lines that open a block which is not prose: headings, tables, code, quotes, lists,
    # HTML, display math, images and badges.
    _NOT_PROSE = re.compile(r"^(#|\||```|>|[-*+] |\d+\. |<|\$\$|!\[|\[!\[)")
    # A short bold label that opens a paragraph: "**Bottom line:**", "**What this is.**".
    _LEAD_LABEL = re.compile(r"^\*\*[^*]{1,40}[.:]\*\*\s+")
    _DECISION = re.compile(r"^## Decision\s*$", re.M)
    _COMMENT = re.compile(r"<!--.*?-->", re.S)

    def __init__(self, limit: int) -> None:
        self._limit = limit

    def describe(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        declared = self._declared(text)
        if declared:
            return self._shorten(declared)
        body = self._COMMENT.sub("", self._FRONT_MATTER.sub("", text, count=1))
        if self._DECISION.search(body):
            return ""
        paragraph = self._LEAD_LABEL.sub("", self._first_paragraph(body), count=1)
        return self._shorten(self._first_sentence(self._plain(paragraph)))

    def _declared(self, text: str) -> str:
        match = self._FRONT_MATTER.match(text)
        if match is None:
            return ""
        for line in match.group(1).splitlines():
            found = re.match(r"^description:\s*(.+)$", line)
            if found:
                return found.group(1).strip().strip("'\"")
        return ""

    def _first_paragraph(self, text: str) -> str:
        fenced = False
        paragraph: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("```"):
                fenced = not fenced
                if paragraph:
                    break
                continue
            if fenced:
                continue
            if not stripped:
                if paragraph:
                    break
                continue
            if not paragraph and self._NOT_PROSE.match(stripped):
                continue
            paragraph.append(stripped)
        return " ".join(paragraph)

    def _plain(self, text: str) -> str:
        text = self._LINK.sub(r"\1", text)
        text = re.sub(r"\*\*Abstract\.\*\*\s*", "", text)
        text = text.replace("**", "").replace("`", "")
        text = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])", r"\1", text)
        return re.sub(r"\s+", " ", text).strip()

    def _first_sentence(self, text: str) -> str:
        return self._SENTENCE_END.split(text, maxsplit=1)[0].strip()

    def _shorten(self, text: str) -> str:
        if len(text) <= self._limit:
            return text
        cut = text[: self._limit].rsplit(" ", 1)[0].rstrip(",;:—- ")
        return f"{cut}…"


class NavLinkSource(LinkSourceInterface):
    """Every page in the site's navigation, in navigation order, as a production-channel link."""

    def __init__(
        self,
        site_config_text: str,
        docs_dir: Path,
        channel_url: str,
        unsectioned: str,
        describer: PageDescriberInterface,
    ) -> None:
        self._text = site_config_text
        self._docs = docs_dir
        self._channel_url = channel_url
        self._unsectioned = unsectioned
        self._describer = describer

    def entries(self) -> Sequence[IndexEntry]:
        found: list[IndexEntry] = []
        for chapter in NavReader().read(self._text):
            source = self._docs / chapter.source
            if not source.is_file():
                raise FileNotFoundError(f"the navigation names {chapter.source}, which is missing")
            page = chapter.site_page.removesuffix("index.html")
            found.append(
                IndexEntry(
                    section=" — ".join(chapter.sections) or self._unsectioned,
                    title=chapter.title,
                    url=f"{self._channel_url}{page}",
                    description=self._describer.describe(source),
                )
            )
        return found


class GovernanceLinkSource(LinkSourceInterface):
    """The governance corpus the site publishes as its own section, in publishing order."""

    def __init__(
        self,
        source_dir: Path | None,
        order: Sequence[str],
        glob: str,
        channel_url: str,
        heading: str,
        describer: PageDescriberInterface,
    ) -> None:
        self._source = source_dir
        self._order = tuple(order)
        self._glob = glob
        self._channel_url = channel_url
        self._heading = heading
        self._describer = describer

    def entries(self) -> Sequence[IndexEntry]:
        if self._source is None:
            return []
        names = [*self._order, *sorted(p.name for p in self._source.glob(self._glob))]
        found: list[IndexEntry] = []
        for name in names:
            origin = self._source / name
            if not origin.is_file():
                raise FileNotFoundError(f"the governance source is missing {origin}")
            heading = next(
                (
                    line[2:].strip()
                    for line in origin.read_text(encoding="utf-8").splitlines()
                    if line.startswith("# ")
                ),
                name.removesuffix(".md"),
            )
            found.append(
                IndexEntry(
                    section=self._heading,
                    title=heading.replace(":", " —"),
                    url=f"{self._channel_url}governance/{name.removesuffix('.md')}/",
                    description=self._describer.describe(origin),
                )
            )
        return found


class DownloadLinkSource(LinkSourceInterface):
    """The paper and the book, where the site publishes them beside its pages."""

    def __init__(self, paper: bool, book: bool, channel_url: str, heading: str) -> None:
        self._paper = paper
        self._book = book
        self._channel_url = channel_url
        self._heading = heading

    def entries(self) -> Sequence[IndexEntry]:
        found: list[IndexEntry] = []
        if self._paper:
            found += [
                IndexEntry(
                    self._heading,
                    "Research paper (PDF)",
                    f"{self._channel_url}paper.pdf",
                    "The design as a journal-formatted paper.",
                ),
            ]
        if self._book:
            found += [
                IndexEntry(
                    self._heading,
                    "The book (PDF)",
                    f"{self._channel_url}book.pdf",
                    "Every page of this site, in navigation order, as one book.",
                ),
                IndexEntry(
                    self._heading,
                    "The book (EPUB)",
                    f"{self._channel_url}book.epub",
                    "The same book for e-readers.",
                ),
            ]
        return found


class LlmsTxtRenderer(LlmsTxtRendererInterface):
    """The llms.txt shape: `# name`, `> summary`, a short note, then `## section` link lists."""

    def __init__(self, site: SiteFacts, repository_url: str) -> None:
        self._site = site
        self._repository = repository_url

    def render(self, entries: Sequence[IndexEntry]) -> str:
        sections: dict[str, list[IndexEntry]] = {}
        for entry in entries:
            sections.setdefault(entry.section, []).append(entry)
        lines = [
            f"# {self._site.name}",
            "",
            f"> {self._site.description}",
            "",
            "This index is generated from the documentation's navigation by "
            f"`{SCRIPT}`; every link is the production copy of a page. The source is "
            f"{self._repository}, and the pages there are the same Markdown.",
        ]
        for heading, members in sections.items():
            lines += ["", f"## {heading}", ""]
            for entry in members:
                tail = f": {entry.description}" if entry.description else ""
                lines.append(f"- [{entry.title}]({entry.url}){tail}")
        return "\n".join(lines) + "\n"


class LlmsTxtBuilder:
    """Composes the sources and the renderer, and writes or checks the committed file."""

    def __init__(
        self,
        output: Path,
        sources: Sequence[LinkSourceInterface],
        renderer: LlmsTxtRendererInterface,
    ) -> None:
        self._output = output
        self._sources = tuple(sources)
        self._renderer = renderer

    @classmethod
    def for_repository(cls, root: Path, settings: LlmsSettings) -> LlmsTxtBuilder:
        site_text = (root / settings.site_config).read_text(encoding="utf-8")
        site = SiteFacts.read(site_text)
        gh = load_config(root, config=root / settings.gh_config)
        channel_url = f"{site.url.rstrip('/')}/{gh.release_branch}/"
        describer = MarkdownPageDescriber(settings.description_limit)
        governance = gh.documentation.governance_source
        repository = re.search(r"^repo_url:\s*(\S+)", site_text, re.M)
        return cls(
            output=root / settings.output,
            sources=(
                NavLinkSource(
                    site_text, root / "docs", channel_url, settings.unsectioned_heading, describer
                ),
                GovernanceLinkSource(
                    root / governance if governance else None,
                    settings.governance_order,
                    settings.governance_glob,
                    channel_url,
                    settings.governance_heading,
                    describer,
                ),
                DownloadLinkSource(
                    gh.documentation.generate_paper,
                    gh.documentation.generate_book,
                    channel_url,
                    settings.downloads_heading,
                ),
            ),
            renderer=LlmsTxtRenderer(site, repository.group(1) if repository else site.url),
        )

    def text(self) -> str:
        entries: list[IndexEntry] = []
        for source in self._sources:
            entries.extend(source.entries())
        return self._renderer.render(entries)

    def write(self) -> Path:
        self._output.write_text(self.text(), encoding="utf-8")
        return self._output

    def check(self) -> tuple[bool, str]:
        wanted = self.text()
        if not self._output.is_file():
            return False, f"{self._output.name} is missing: run `python {SCRIPT}`"
        if self._output.read_text(encoding="utf-8") != wanted:
            return False, (
                f"{self._output.name} is stale against the navigation: run `python {SCRIPT}`"
            )
        return True, f"{self._output.name} matches the navigation"


# A bare function because it is this script's `__main__` entry point (ADR-0016): it parses
# one flag, builds the index and either writes or checks it.
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--check", action="store_true", help="fail when the file is stale")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    builder = LlmsTxtBuilder.for_repository(REPO, LlmsSettings.load(args.config))
    if args.check:
        ok, message = builder.check()
        print(message, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1
    print(f"wrote {builder.write().relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
