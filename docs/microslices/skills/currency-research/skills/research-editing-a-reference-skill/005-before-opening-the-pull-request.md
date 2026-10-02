---
id: skill-before-opening-the-pull-request-d1efbe0a47
purpose: before opening the pull request
source: src/vibey_tools/skills/plugins/currency-research/skills/research-editing-a-reference-skill/SKILL.md
requires: ["skill-what-else-must-change-when-you-edit-a5ea2fb306"]
links: []
---

## Before opening the pull request

Both must exit 0:

```bash
python3 tools/validate_manifests.py
python3 tools/check_links.py
```

`validate_manifests.py` catches name/version/frontmatter drift and duplicate skill names.
`check_links.py` enforces the absolute-vs-relative link rule (root Markdown uses absolute
GitHub URLs; files under `docs/` use relative links) and is hermetic, so it needs no network.

If the edit changed anything under `docs/` or `mkdocs.yml`, also run:

```bash
mkdocs build --strict
```

⚠️ **A currency edit that fails a checker is not ready.** Fix it or drop that edit from the
pull request — never disable a check to get a change through.
