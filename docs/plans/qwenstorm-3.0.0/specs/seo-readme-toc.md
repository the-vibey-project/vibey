## Title
docs(readme): add a table of contents to README.md

## Why
`README.md` is 435 lines (`wc -l README.md`) and carries 17 top-level `##` sections
("What problem this solves", "Install", "Quickstart", "Command reference",
"Configuration", "Notifications", "Telemetry", "The shape of it", "Why it isn't just
another agent framework", "Documentation", "Status", "Troubleshooting", "Upgrading",
"Formal notes", "Project links", "Related projects", "License") with no in-page
navigation at all (`grep -c '^\[.*\](#' README.md` is 0). GitHub renders an auto-outline
button for long files, but that is a GitHub-only affordance: it does not exist on
PyPI's rendered page, and a search snippet or an LLM answer engine quoting or chunking
this file has no equivalent to fall back on. A short table of contents right after the
opening pitch — before the reader hits 17 unlabelled sections — is the single cheapest
scannability improvement this file can get, and it is also exactly the kind of
structure a RAG chunker uses to decide where one topical chunk ends and the next
begins.

## Required behaviour
1. Insert a table of contents immediately after the two-sentence "Never written code?"
   paragraph and its closing line (`README.md:27-33`), and before the "For the precise
   version:" paragraph (`README.md:35`) — i.e. between the plain-English pitch and the
   first technical sentence, so a reader who already knows what they want can jump
   straight there without reading the pitch again.
2. The table of contents is a flat markdown list, one entry per `##` heading in the file
   (not `###` sub-headings), in document order, each linking to that heading's GitHub-style
   anchor (lower-case, spaces to hyphens, punctuation other than hyphens and word
   characters stripped) — e.g. `- [What problem this solves](#what-problem-this-solves)`.
   Generate the anchor list mechanically rather than by hand, with this script run from
   the repository root:
   ```python
   import re
   from pathlib import Path

   README = Path("README.md")
   text = README.read_text(encoding="utf-8")
   lines = text.splitlines()

   def anchor(title: str) -> str:
       slug = re.sub(r"[^\w\- ]", "", title).strip().lower()
       return re.sub(r"\s+", "-", slug)

   headings = [line[3:].strip() for line in lines if line.startswith("## ")]
   toc = "\n".join(f"- [{h}](#{anchor(h)})" for h in headings)
   print(toc)
   ```
   Paste its output as the table of contents body, under a `## Contents` heading of its
   own — which means the finished file has 18 `##` headings, and `## Contents` itself is
   NOT in its own list.
3. Every generated link must resolve: `properdocs build --strict` (or a plain
   `markdown`+regex check, since installing the pinned `properdocs` package is not
   required for this) must find each `#anchor` heading actually present in the rendered
   output.

## Where to change
- `README.md` only: insert the new `## Contents` section as described in behaviour 1.

## Acceptance criteria
- [ ] `grep -c '^## Contents$' README.md` is 1, positioned after line 33 and before the
      (renumbered) "For the precise version" paragraph.
- [ ] The `## Contents` list has exactly 17 entries, one per pre-existing `##` heading,
      in the same top-to-bottom order they appear in the file.
- [ ] Every `(#anchor)` in the new list matches a real heading's GitHub-style anchor
      later in the same file (verified by the script in behaviour 2, or by installing
      `properdocs`/`markdown` and rendering the file).
- [ ] `git diff --stat` touches only `README.md`, and the diff is a pure insertion — no
      existing line of README.md is removed or reworded.

## Tests to write first (TDD)
No project test suite covers README.md's prose today, and this is a pure documentation
insertion with no runtime behaviour — there is nothing to unit test. The acceptance
commands above are the checks. If a `tests/meta/test_readme_*.py` already exists by the
time this lane runs (check first), extend it with one assertion that every `## Contents`
entry's anchor resolves to a real heading; otherwise do not create a new test file for
this alone — that would be a heavier gate than a table of contents insertion warrants.

## Checks the lane must run (all must pass)
    grep -c '^## Contents$' README.md
    python3 -c 'import re; from pathlib import Path; text = Path("README.md").read_text(encoding="utf-8"); headings = [l[3:].strip() for l in text.splitlines() if l.startswith("## ") and l.strip() != "## Contents"]; anchor = lambda t: re.sub(r"\s+", "-", re.sub(r"[^\w\- ]", "", t).strip().lower()); toc_block = text.split("## Contents", 1)[1].split("\n## ", 1)[0]; assert all(f"(#{anchor(h)})" in toc_block for h in headings), "missing or wrong anchor in TOC"; print("ok:", len(headings), "headings linked")'

## Out of scope
- Reformatting or shortening any existing section — this lane only inserts one new
  section.
- `docs/index.md`, which mkdocs/properdocs already gives an automatic sidebar/TOC via
  `markdown_extensions: - toc: {permalink: true}` (`properdocs.yml:26-28`) — this gap is
  specific to README.md, which has no such tooling.
- The relative-link conversion and governance-canon cross-links (`seo-readme-link-hygiene`).
- CHANGELOG.md, ADRs, CLAUDE.md/AGENTS.md/GEMINI.md, and skill trees.

Commit as `docs(readme): add a table of contents`. Do not push.

## Lane card
- **Depends on:** `seo-readme-link-hygiene` (both edit `README.md`; that lane runs
  first so this one inserts its TOC into the post-link-conversion file rather than
  racing it).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
