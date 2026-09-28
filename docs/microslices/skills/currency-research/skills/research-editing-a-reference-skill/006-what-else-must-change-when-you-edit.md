---
id: skill-what-else-must-change-when-you-edit-94e9563c31
purpose: what else must change when you edit
source: src/vibey_tools/skills/plugins/currency-research/skills/research-editing-a-reference-skill/SKILL.md
requires: ["skill-byte-discipline-18c60094fc"]
links: ["skill-before-opening-the-pull-request-8b22dcc065"]
---

## What else must change when you edit

Work through this list every time; the repository's checkers enforce most of it.

1. **`plugins/<plugin>/.claude-plugin/plugin.json`** — bump `version`. A currency edit is a
   patch or minor revision; follow whatever the plugin is already using (`0.1.0` → `0.2.0`
   is this repository's convention for "revised").
2. **`.claude-plugin/marketplace.json`** — mirror the new `version`. Mirror `description`
   and `category` too if they changed. **A mismatch here breaks installation**, and the
   validator fails the build.
3. **`plugins/<plugin>/README.md`** — update the skill bullet only if the section list changed.
4. **Root `README.md` plugin table** — update the version cell for that plugin, and the
   "Covers" cell only if the topic list genuinely changed.
5. **Counts** — only if you added or removed a whole skill or plugin, which a currency edit
   should not do. If it somehow does, the plugin and skill counts appear in `README.md`,
   `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/index.md`, `docs/usage.md`,
   `docs/hooks.py`, `docs/gen_reference.py`, `pyproject.toml`, `mkdocs.yml` and
   `.github/workflows/ci.yml`.
6. **Package version** — `src/vibey_skills/__init__.py` and `marketplace.json`'s
   `metadata.version` must stay equal. Bump them together, or not at all; the validator
   asserts they match.

Do **not** hand-edit anything under `docs/reference/` — that tree is generated from
`plugins/**` at build time.

---
