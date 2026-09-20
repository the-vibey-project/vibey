#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Verify documentation links without touching the network.

Three surfaces render this project's Markdown, each against a different base URL:

    GitHub repo view   https://github.com/<slug>/blob/<ref>/...  relative links work
    PyPI project page  https://pypi.org/project/<name>/          relative links BREAK
    Pages site         https://<org>.github.io/<name>/           relative links work in docs/

1.0.0 shipped `](.claude-plugin/marketplace.json)` in README.md, which PyPI resolved to
`https://pypi.org/project/<name>/.claude-plugin/marketplace.json` — a 404
that looked fine on GitHub. That class of bug is invisible to a human reviewer and to
`mkdocs build`, so it gets its own check.

Rules enforced:

  1. Root Markdown (README, CONTRIBUTING, CLAUDE, SECURITY, CODE_OF_CONDUCT) must contain
     NO relative links — PyPI and the Pages site cannot resolve them.
  2. Every absolute URL into this repository (`/blob/<ref>/<p>` or `/tree/<ref>/<p>`) must
     name a long-lived branch, and a path that actually exists IN THE REPOSITORY, with
     blob-vs-tree matching file-vs-directory. This tree is a tenant of the vibey monorepo
     (ADR-0021), so `<p>` is relative to the monorepo root, not to this folder, and the
     long-lived branches are the ones the root `.vibey-gh.toml` names in `[branches]`.
  3. Relative links inside docs/ must resolve on disk (mkdocs --strict also covers this,
     but this runs without installing mkdocs).
  4. No link may reference the former publishing org (the project was developed as
     TheViziusGroup/vibe-engineering-skills and republished under the maintainer's own
     account as vibey-skills). The only file allowed to name the old coordinates is
     NOTICE.md, which exists precisely to record the attribution; everywhere else a
     stale org URL is a bug — every such link must point at the canonical slug below.

Rule 2 once checked almost nothing (#263). It matched only `/main/` and resolved the path
against this folder. The absorption made every self-link monorepo-relative, and the README
points them at `develop`, so 139 links went unchecked while this script printed "ok". A
ref is now matched whatever it is: a long-lived branch is checked, and anything else is
reported rather than skipped.

Deliberately hermetic: no HTTP requests. A link checker that needs the network is a link
checker that gets disabled the first time CI flakes. Reachability of third-party URLs is out
of scope; correctness of our own paths is not.

Exit 0 clean, 1 on any violation.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from interfaces.check_links_interface import LinkCheckerInterface

TENANT = Path(__file__).resolve().parent.parent
# The canonical repository this tree actually lives in. It was
# `adammatthewsteinberger/vibey-skills` while that was a repository of its own; the
# absorption (vibey ADR-0021) retired it and vibey ADR-0037 retired the distribution
# too, so both halves of the old slug now name something that does not exist. This
# value is what a self-referencing absolute link is checked against and what the
# failure messages recommend, so a stale one recommends a 404.
SLUG = "the-vibey-project/vibey"

# The pre-rename coordinates. Attribution lives in NOTICE.md; nothing else may link here.
FORMER_ORG = "TheViziusGroup"
FORMER_ORG_ALLOWED = {"NOTICE.md"}

ROOT_DOCS = [
    "README.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
]

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")

# The keys vibey-gh reads from `[branches]`, with vibey-gh's own defaults, so a
# repository that leaves the table out means the same thing here as it does there.
BRANCH_DEFAULTS = {"integration": "develop", "release": "main"}
TABLE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:#.*)?$")
BRANCH_KEY = re.compile(r'^\s*(\w+)\s*=\s*"([^"]+)"')

# Capture the repo name, then compare it exactly. A negative lookahead was tried first and
# was wrong: `(?!<repo>(?:[/.)]|$))` treats `$` as end-of-STRING, not end-of-line, so a URL
# followed by `"` or a newline slipped past and every occurrence in mkdocs.yml and
# pyproject.toml was reported as a foreign repo. Capture-then-compare cannot have that class
# of bug.
#
# Sibling repositories under the same owner (the README's "Related projects" block) are
# legitimate, so the current org is NOT policed for foreign repos — only the former org is.
FORMER_ORG_REPO = re.compile(rf"https://github\.com/{re.escape(FORMER_ORG)}/([A-Za-z0-9._-]+)")
FORMER_PAGES = re.compile(rf"https://{re.escape(FORMER_ORG.lower())}\.github\.io/")

# Only tracked files matter: .claudeloop/ holds the migration plan and run report, which
# reference internal repos on purpose and are gitignored precisely so they never ship.
SKIP_DIRS = {".git", ".claudeloop", ".remember", "archive", "site", "dist", "build", ".venv"}


class LinkChecker(LinkCheckerInterface):
    """The four rules above, over one tenant folder inside one repository checkout."""

    def __init__(
        self, tenant: Path, repository: Path, refs: tuple[str, ...], slug: str = SLUG
    ) -> None:
        self._tenant = tenant
        self._repository = repository
        self._refs = refs
        self._slug = slug
        self._prefix = tenant.relative_to(repository).as_posix()
        # Any ref, so that none is skipped: the ref is judged after the match, not by it.
        self._self_link = re.compile(
            rf"https://github\.com/{re.escape(slug)}/(blob|tree)/([^/)#\s]+)/([^)#\s]*)"
        )

    @classmethod
    def for_checkout(cls, tenant: Path) -> LinkChecker:
        """The checker for `tenant` as it sits in the checkout that contains it."""
        repository = cls.find_repository_root(tenant)
        return cls(tenant, repository, cls.read_branch_refs(repository))

    @staticmethod
    def find_repository_root(start: Path) -> Path:
        """The nearest ancestor holding `.git`, a directory in a clone and a file in a
        worktree. Outside a checkout there is no repository to resolve a path against, and
        guessing one would be a check that passes on nothing."""
        for candidate in (start, *start.parents):
            if (candidate / ".git").exists():
                return candidate
        raise FileNotFoundError(
            f"no .git at or above {start}: repository links cannot be resolved outside a checkout"
        )

    @staticmethod
    def read_branch_refs(repository: Path) -> tuple[str, ...]:
        """The integration and release branches from `[branches]` in `.vibey-gh.toml`.

        Read line by line rather than with tomllib: this validator deliberately has no
        dependencies, even though the tenant's unified runtime floor includes tomllib.
        `[branches]`
        is a flat table of string keys, which is all this needs to read.
        """
        branches = dict(BRANCH_DEFAULTS)
        config = repository / ".vibey-gh.toml"
        if config.is_file():
            table = ""
            for line in config.read_text(encoding="utf-8").splitlines():
                header = TABLE.match(line)
                if header:
                    table = header.group(1).strip()
                    continue
                entry = BRANCH_KEY.match(line) if table == "branches" else None
                if entry and entry.group(1) in branches:
                    branches[entry.group(1)] = entry.group(2)
        return (branches["integration"], branches["release"])

    @staticmethod
    def is_external(target: str) -> bool:
        return target.startswith(("http://", "https://", "mailto:", "tel:"))

    def scanned_markdown(self) -> list[Path]:
        """Markdown files that will actually be published."""
        return [
            p
            for p in self._tenant.rglob("*.md")
            if not SKIP_DIRS.intersection(p.relative_to(self._tenant).parts)
        ]

    def check_root_docs_are_absolute(self, problems: list[str]) -> None:
        for name in ROOT_DOCS:
            p = self._tenant / name
            if not p.is_file():
                continue
            for target in LINK.findall(p.read_text(encoding="utf-8")):
                if target.startswith("#") or self.is_external(target):
                    continue
                problems.append(
                    f"{name}: relative link `{target}` — breaks on PyPI and the Pages site; "
                    f"use https://github.com/{self._slug}/blob/{self._refs[0]}/"
                    f"{self._prefix}/{target.lstrip('./')}"
                )

    def check_self_paths_exist(self, problems: list[str]) -> None:
        for p in self.scanned_markdown():
            rel = p.relative_to(self._tenant)
            for kind, ref, path in self._self_link.findall(p.read_text(encoding="utf-8")):
                if ref not in self._refs:
                    problems.append(
                        f"{rel}: links to `{path}` on `{ref}`, which is not a long-lived "
                        f"branch ({', '.join(self._refs)}), so its path cannot be checked here"
                    )
                    continue
                target = self._repository / path
                if not target.exists():
                    problems.append(
                        f"{rel}: links to `{path}` via /{kind}/{ref}/, which does not exist "
                        "in the repository"
                    )
                elif kind == "blob" and target.is_dir():
                    problems.append(
                        f"{rel}: `{path}` is a directory but linked with /blob/ (use /tree/)"
                    )
                elif kind == "tree" and target.is_file():
                    problems.append(
                        f"{rel}: `{path}` is a file but linked with /tree/ (use /blob/)"
                    )

    def check_docs_relative_links(self, problems: list[str]) -> None:
        docs = self._tenant / "docs"
        if not docs.is_dir():
            return
        for p in docs.rglob("*.md"):
            rel = p.relative_to(self._tenant)
            for target in LINK.findall(p.read_text(encoding="utf-8")):
                if target.startswith("#") or self.is_external(target):
                    continue
                path = target.partition("#")[0]
                if not path:
                    continue
                # A directory-style target (`reference/`) is resolved by mkdocs to that
                # section's index page; accept it when the generator will produce one.
                if path.endswith("/"):
                    continue
                resolved = (p.parent / path).resolve()
                if resolved.exists():
                    continue
                # Generated pages do not exist on disk until mkdocs runs.
                if "reference/" in target:
                    continue
                problems.append(f"{rel}: relative link `{target}` does not resolve on disk")

    def check_no_former_org_links(self, problems: list[str]) -> None:
        extra = [self._tenant / "mkdocs.yml", self._tenant / "pyproject.toml"]
        for p in self.scanned_markdown() + extra:
            if not p.is_file():
                continue
            rel = p.relative_to(self._tenant)
            if str(rel) in FORMER_ORG_ALLOWED:
                continue
            text = p.read_text(encoding="utf-8")
            for repo in sorted(set(FORMER_ORG_REPO.findall(text))):
                problems.append(
                    f"{rel}: links to the former publishing org (`{FORMER_ORG}/{repo}`) — "
                    f"use https://github.com/{self._slug} (attribution belongs in NOTICE.md only)"
                )
            if FORMER_PAGES.search(text):
                owner, name = self._slug.split("/")
                problems.append(
                    f"{rel}: links to the former Pages site — use https://{owner}.github.io/{name}/"
                )

    def problems(self) -> list[str]:
        found: list[str] = []
        self.check_root_docs_are_absolute(found)
        self.check_self_paths_exist(found)
        self.check_docs_relative_links(found)
        self.check_no_former_org_links(found)
        return found


def main() -> int:
    """The `__main__` entry point, the one bare function ADR-0016 permits here."""
    try:
        checker: LinkCheckerInterface = LinkChecker.for_checkout(TENANT)
    except FileNotFoundError as error:
        print(f"check_links: {error}", file=sys.stderr)
        return 1
    problems = checker.problems()

    if problems:
        print(f"check_links: {len(problems)} problem(s)\n", file=sys.stderr)
        for pb in problems:
            print(f"  - {pb}", file=sys.stderr)
        return 1

    print("check_links: ok — root docs fully absolute, every repository path resolves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
