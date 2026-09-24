## Title
fix(docs): README.md's relative links 404 on PyPI — make them absolute, and cross-link the governance canon from README.md and docs/index.md

## Why
`pyproject.toml:9` declares `readme = "README.md"`, so PyPI renders this exact file as
`vibey`'s project description. README.md contains 39 relative markdown links (verified
by walking every `[text](target)` in the file and keeping non-`http`, non-`#` targets —
e.g. `README.md:61` `[claudeloop](src/vibey_runners/claude)`, `:169`
`[CLI reference](docs/reference/cli.md)`, `:311` `[CLAUDE.md](CLAUDE.md)`, `:419`
`[MIT](LICENSE)`). A relative link resolves fine in GitHub's own blob view but 404s on
PyPI's rendered page, because PyPI serves the description from its own domain with no
knowledge of the source repository's file tree. This is not a theoretical risk: the
sibling tenant `vibey-skills` hit exactly this in its own 1.0.0 release
(`src/vibey_tools/skills/tools/check_links.py:11-14`, "1.0.0 shipped
`](.claude-plugin/marketplace.json)` in README.md, which PyPI resolved to
`https://pypi.org/project/<name>/.claude-plugin/marketplace.json` — a 404") and wrote a
`LinkChecker` specifically to catch it (`check_root_docs_are_absolute`,
`check_links.py:167-177`) — but that checker only ever runs inside
`src/vibey_tools/skills` (`.github/workflows/ci.yml`'s `tools` job,
`cd src/vibey_tools/skills && ... python3 tools/check_links.py`); nothing runs it, or
anything like it, against the repository root's own README.md. Every one of the 39
links is currently silently broken on https://pypi.org/project/vibey/ — a page a search
engine or an LLM package-recommender is exactly as likely to land on as GitHub.

Separately, `README.md` and `docs/index.md` (the published site's Home page) each link
CHANGELOG.md, the paper, and the book within one click, but neither links the governing
canon: `grep -c "doctrines.md\|constitution.md" README.md docs/index.md` is 0/0. Both
files already carry a "Project links" table (`README.md:386-394`,
`docs/index.md:374-382`) with Contributing/Security/Support/Code of
Conduct/Changelog rows — the exact place sub-doctrine 7.b's "one click from anywhere"
standard, already met for the changelog and the paper, is not yet met for the canon.

## Required behaviour
1. Convert every relative link in `README.md` to an absolute
   `https://github.com/the-vibey-project/vibey/{blob,tree}/develop/<path>[#anchor]` URL,
   `develop` because that is the ref README.md's own badges already use
   (`README.md:5-10`, e.g. `.../blob/develop/LICENSE`). Use `tree` for a path that is a
   directory and `blob` for a file, decided by checking the real filesystem, not a
   hand-maintained list. Run this exact script from the repository root:
   ```python
   from pathlib import Path
   import re

   REPO_SLUG = "the-vibey-project/vibey"
   REF = "develop"
   ROOT = Path(".")
   README = ROOT / "README.md"
   text = README.read_text(encoding="utf-8")

   LINK = re.compile(r'(\[[^\]]*\]\()([^)\s]+)((?:\s+"[^"]*")?\))')

   def replace(m: re.Match[str]) -> str:
       prefix, target, suffix = m.group(1), m.group(2), m.group(3)
       if target.startswith(("http://", "https://", "mailto:", "#")):
           return m.group(0)
       path, sep, anchor = target.partition("#")
       bare = path.rstrip("/")
       full = ROOT / bare
       if not full.exists():
           raise SystemExit(f"README.md links to {target!r}, which does not exist in the repository")
       kind = "tree" if full.is_dir() else "blob"
       url = f"https://github.com/{REPO_SLUG}/{kind}/{REF}/{bare}"
       if sep:
           url += f"#{anchor}"
       return f"{prefix}{url}{suffix}"

   new_text, count = LINK.subn(replace, text)
   assert count == 39, f"expected 39 relative links converted, found {count}"
   README.write_text(new_text, encoding="utf-8")
   ```
   If the assertion fires with a different count, README.md has changed since this spec
   was written — read the new set of relative links and update the expected count rather
   than silently accepting a different number.
2. In `README.md`'s "Project links" table (`README.md:386-394`), add two rows, after the
   `Changelog` row:
   ```
   | Governing law | [Doctrines](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/doctrines.md) |
   | Constitution | [constitution.md](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/constitution.md) |
   ```
3. In `docs/index.md`'s "Project links" table (`docs/index.md:374-382`), add the same two
   rows, but on `main` — that file's own table already links Contributing/Security/etc. on
   `.../blob/main/...`, and the new rows must match that file's own established
   convention rather than README.md's:
   ```
   | Governing law | [Doctrines](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/doctrines.md) |
   | Constitution | [constitution.md](https://github.com/the-vibey-project/vibey/blob/main/src/vibey_tools/gh/docs/constitution.md) |
   ```
4. Create `scripts/check_root_docs_links.py`, a standalone regression guard (module-level
   functions, matching `scripts/paper_evidence.py`'s own shape — a small single-purpose
   repository-maintenance script, not a package class): it re-derives the same relative-link
   scan used in behaviour 1 and fails (`sys.exit(1)`, printing every offending line) if
   `README.md` contains any relative link at all. It also asserts `doctrines.md` and
   `constitution.md` are each referenced at least once in both `README.md` and
   `docs/index.md`. Give it a `main() -> int` entry point and an `if __name__ ==
   "__main__": raise SystemExit(main())` footer.

## Where to change
- `README.md`: run the script in behaviour 1, then add the two rows from behaviour 2.
- `docs/index.md`: add the two rows from behaviour 3 only (its own relative links are
  covered by `properdocs build --strict`'s own on-disk validation, not this lane — see
  Out of scope).
- Create `scripts/check_root_docs_links.py`.

## Acceptance criteria
- [ ] `grep -cE '\]\((?!https?://|mailto:|#)[^)]+\)' README.md` is 0.
- [ ] `python3 scripts/check_root_docs_links.py` exits 0.
- [ ] `grep -c "doctrines.md" README.md docs/index.md` and
      `grep -c "constitution.md" README.md docs/index.md` are each 1 in both files.
- [ ] Every converted URL resolves to a real path: for each `https://github.com/the-vibey-project/vibey/(blob|tree)/develop/<path>` in README.md, `<path>` exists in the checkout.
- [ ] `git diff --stat` touches exactly `README.md`, `docs/index.md`, and
      `scripts/check_root_docs_links.py`.
- [ ] `uv run pytest -q -p no:cacheprovider tests/scripts/test_check_root_docs_links.py` passes.

## Tests to write first (TDD)
Create `tests/scripts/test_check_root_docs_links.py` (create the `tests/scripts/`
package with an `__init__.py` if it does not already exist):
- `test_passes_against_the_real_repository`: run `main()` against this checkout after
  behaviours 1-3 land; expect exit code 0.
- `test_fails_on_a_relative_link`: write a temporary README.md fixture containing one
  relative link; assert `main()` reports it and returns non-zero.
- `test_fails_when_the_canon_is_not_linked`: a fixture README.md/docs/index.md pair with
  no mention of `doctrines.md`/`constitution.md`; assert failure.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    python3 scripts/check_root_docs_links.py
    uv run pytest -q -p no:cacheprovider tests/scripts/test_check_root_docs_links.py

## Out of scope
- `docs/index.md`'s own relative links (to `paper.md`, guide pages, etc.) — those are
  correct as written: mkdocs resolves a `.md` target to its site page, and
  `properdocs build --strict` already validates every one resolves on disk.
- `CONTRIBUTING.md`, `SECURITY.md`, and `SUPPORT.md` also carry a handful of relative
  links (5, 2, and 5 respectively) but are not PyPI's rendered description and are
  therefore lower severity; a follow-up lane may apply the identical treatment to them.
- The README ↔ `develop` vs. docs-index ↔ `main` ref inconsistency more broadly (it
  predates this lane, e.g. `pyproject.toml`'s own `Changelog` URL uses `main` while the
  README badges use `develop`) — not this wave's job to unify.
- The table of contents (`seo-readme-toc`), pyproject.toml metadata (`seo-pypi-metadata`),
  and every other file in this SEO/LEO wave.
- CHANGELOG.md, ADRs, CLAUDE.md/AGENTS.md/GEMINI.md's generated sections, and skill trees.

Commit as `fix(docs): README.md's relative links 404 on PyPI; cross-link the governance canon`.
Do not push.

## Lane card
- **Depends on:** nothing.
- **Shares a file with:** `seo-readme-toc` (also edits `README.md`) — that lane depends on
  this one so the two do not race on the same file.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
