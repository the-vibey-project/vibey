## Title
docs(agents): SD-01 is carried verbatim in every agent router and rule tree, and a meta-test keeps it there

## Why
SD-01 §8 (`src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md:75-77`): "Carry
this text verbatim in the system prompt or CLAUDE.md of every agent it governs … Do not
paraphrase it". 7.b (`src/vibey_tools/gh/docs/doctrines.md:80`) puts governance on every agent
guide. At integration HEAD `4317cff6` the text is carried by root `CLAUDE.md:247-312` and ten
tenant files, and is **missing from 14 tracked router files**: `AGENTS.md`, `GEMINI.md`,
`src/vibey_runners/{agy,claude,codex}/{AGENTS,GEMINI}.md`,
`src/vibey_runners/cursor/{AGENTS,CURSOR,GEMINI}.md`, `src/vibey_tools/gh/GEMINI.md`,
`src/vibey_tools/skills/{AGENTS,GEMINI}.md`. `.cursor/rules/` and `.agent/rules/` carry nothing,
and no test checks carriage (gap N1, `issue-audit/gaps.md:705-712`).

**The canonical source** is one file: `src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md`,
from the line `# Subdoctrine SD-01 — Counterparties, Trust, and Verification` (`:14`) to the end
(`:77`). Every carried copy at HEAD equals it byte for byte, so the test compares against that
file and holds no copy of its own.

**Which files carry it, decided from §8's words.** §8 binds "the system prompt or CLAUDE.md of
every agent it governs": the always-loaded instruction file of each agent, not every document an
agent may open. ADR-0011 (`docs/architecture/decisions/0011-agent-surface-provisioning.md:11-17`)
names that file per engine: `CLAUDE.md`, `AGENTS.md`, `CURSOR.md`, `GEMINI.md`, `QWEN.md`, the
`RouterFile` vocabulary (`src/vibey/domain/provision.py:20-27`). So:
- **every tracked router file** carries it, and the root tracks all five. Root `CURSOR.md` and
  `QWEN.md` do not exist yet. Without them, a BUILD worktree of this repository gets those two
  from `render_block` alone (`src/vibey/infrastructure/provision/agent_surface.py:69-77`), with
  no SD-01;
- **every rule-files tree** (`.cursor/rules`, `.agent/rules`, and any tree added later) gets one
  always-applied carrier rule `<root>/sd-01-counterparties-trust-verification<suffix>`. Cursor
  reads its rules, not `CURSOR.md`;
- **skill trees and skill files do not.** Skills load on demand, so a copy in each of 24 skill
  files would not make the text always present, and it would add 24 places where §8's
  "paraphrase drifts" can happen. Claude Code and Codex, which read `.claude/skills` and
  `.agents/skills`, always load `CLAUDE.md` and `AGENTS.md`.
- **Tenants with no router file** (`src/vibey_runners/opencode`, `src/vibey_runners/common`) get
  none. An agent working there loads the repository-root routers, which all carry SD-01 after
  this lane.

**A regenerate never drops it.** The generator is `render_block`/`merge_router`
(`src/vibey/domain/provision.py:36-71`). `merge_router` replaces only the text between
`<!-- vibey:begin -->` and `<!-- vibey:end -->`. The carried section sits after the end marker,
as root `CLAUDE.md` already does (`:245-247`). The test proves both facts.

## Required behaviour
1. Run this once from the repository root with the `shell` tool, as
   `["uv", "run", "python", "-c", <the script>]` (or save it to `$TMPDIR/sd01.py` and run that):
```python
from pathlib import Path
from vibey.domain.provision import ProvisionSpec, render_block
SRC = Path("src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md").read_text(encoding="utf-8")
CANON = SRC[SRC.index("# Subdoctrine SD-01 — Counterparties, Trust, and Verification"):].rstrip("\n")
SECTION = "\n## Standing subdoctrine SD-01 (carried verbatim per its §8)\n\n" + CANON + "\n"
ROUTER_INTRO = {
    "CURSOR.md": "# CURSOR.md\n\nThe router file `cursorloop` reads in this repository (ADR-0011). The facts and the\nnon-negotiables are in [AGENTS.md](AGENTS.md); procedures are in `.cursor/rules/`; the governing\nlaw is in [the Twelve Doctrines](src/vibey_tools/gh/docs/doctrines.md).\n\n",
    "QWEN.md": "# QWEN.md\n\nThe router file `qwenloop` reads in this repository (ADR-0011). The facts and the\nnon-negotiables are in [AGENTS.md](AGENTS.md); procedures are in `.agents/skills/`; the governing\nlaw is in [the Twelve Doctrines](src/vibey_tools/gh/docs/doctrines.md).\n\n",
}
BLOCK = render_block(ProvisionSpec(non_negotiables=(), plugins=()))
for name, intro in ROUTER_INTRO.items():
    assert not Path(name).exists(), name
    Path(name).write_text(intro + BLOCK + SECTION, encoding="utf-8")
APPEND = [
    "AGENTS.md", "GEMINI.md",
    "src/vibey_runners/agy/AGENTS.md", "src/vibey_runners/agy/GEMINI.md",
    "src/vibey_runners/claude/AGENTS.md", "src/vibey_runners/claude/GEMINI.md",
    "src/vibey_runners/codex/AGENTS.md", "src/vibey_runners/codex/GEMINI.md",
    "src/vibey_runners/cursor/AGENTS.md", "src/vibey_runners/cursor/CURSOR.md",
    "src/vibey_runners/cursor/GEMINI.md", "src/vibey_tools/gh/GEMINI.md",
    "src/vibey_tools/skills/AGENTS.md", "src/vibey_tools/skills/GEMINI.md",
]
for name in APPEND:
    path = Path(name)
    text = path.read_text(encoding="utf-8")
    assert CANON not in text, name
    path.write_text(text + ("" if text.endswith("\n") else "\n") + SECTION, encoding="utf-8")
Path(".cursor/rules/sd-01-counterparties-trust-verification.mdc").write_text(
    "---\ndescription: Standing subdoctrine SD-01 v1.0 — counterparties, trust, and verification, carried verbatim in every session per its §8.\nalwaysApply: true\n---\n\n"
    "> **Standing rule**, carried verbatim from `src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md`. It changes only by the operator's amendment of that file.\n\n"
    + CANON + "\n", encoding="utf-8")
Path(".agent/rules/sd-01-counterparties-trust-verification.md").write_text(
    "# sd-01-counterparties-trust-verification (standing rule, carried verbatim from `src/vibey_tools/gh/docs/sd-01-counterparties-trust-verification.md`)\n\n"
    + CANON + "\n", encoding="utf-8")
```
   Every appended file ends with the section, after any `<!-- vibey:end -->` it has (root
   `AGENTS.md:261`, `GEMINI.md:186`). No existing line of any file changes.
2. New `tests/meta/test_sd01_carriage.py` (provenance header; its module docstring states the
   decision and reasons above, and why its helpers are module functions). It reads
   `AGENT_SURFACE_TREES`, `TreeLayout` and `SD01_RULE_STEM` from `tests.meta.agent_surfaces`
   (lane `gap-agent-tree-parity`), and `RouterFile`, `BEGIN_MARKER`, `END_MARKER`,
   `ProvisionSpec`, `merge_router` and `render_block` from `vibey.domain.provision`. The
   canonical text is computed exactly as in the script (`CANON`). Router files are the tracked
   files (`git ls-files`) whose name is a `RouterFile` value, minus any path with a directory
   component in `{"tests", "test", "fixtures"}`.

## Where to change
- New: `CURSOR.md`, `QWEN.md`, `.cursor/rules/sd-01-counterparties-trust-verification.mdc`,
  `.agent/rules/sd-01-counterparties-trust-verification.md`, `tests/meta/test_sd01_carriage.py`.
- Appended (by the script only): the 14 files in `APPEND`.

## Acceptance criteria
- [ ] `git diff --numstat` shows only added lines (deletions `0`) in the 14 appended files.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes, including
      `test_agent_tree_parity.py`: the carrier files' stem is in `STANDING_RULE_STEMS`.
- [ ] By hand (then revert): changing one word of SD-01 §3 in `src/vibey_runners/codex/GEMINI.md`
      fails `test_every_tracked_router_file_carries_sd01_verbatim` naming that file.
- [ ] The skills tenant's checks pass (its `AGENTS.md` is a catalogue-count surface,
      `src/vibey_tools/skills/tests/test_catalogue_counts.py:76`).

## Tests to write first (TDD)
Write these before running the script. Each fails until it runs, except the first, the
outside-the-block test and the partial-copy test, which pass before and after:
- `test_the_canonical_text_is_sd01_v1_0`: it starts with the heading, contains
  `**Status:** Standing. Version 1.0`, and ends with
  `Do not paraphrase it into other prompts; paraphrase drifts.`
- `test_the_root_tracks_every_router_file`: for each `RouterFile`, its name is tracked at the root.
- `test_every_tracked_router_file_carries_sd01_verbatim`: one assertion listing every router
  file without `CANON`, with the fix in the message ("append the SD-01 section after any
  `<!-- vibey:end -->`").
- `test_sd01_sits_outside_the_generated_block`: in every router file that has both markers
  and contains `CANON`, `CANON` begins after `END_MARKER` or ends before `BEGIN_MARKER`.
- `test_reprovisioning_keeps_sd01` (parametrized over `RouterFile`, id the file name): `merge_router(<root file text>,
  render_block(ProvisionSpec(non_negotiables=("a project rule",), plugins=("a-plugin",))))`
  still contains `CANON`.
- `test_every_rule_tree_carries_the_sd01_rule` (parametrized over the `RULE_FILES` trees of
  `AGENT_SURFACE_TREES`, id `tree.root`): `<root>/<SD01_RULE_STEM><suffix>` exists and contains
  `CANON`. When `tree.front_matter` is true, the file starts with `---`, and its front matter has
  a `description:` line and, when `tree.always_apply` is set, that exact line.
- `test_no_file_carries_a_partial_copy`: every tracked `*.md` or `*.mdc` file other than the
  canonical source that contains the heading line also contains the whole `CANON`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta tests/domain/test_provision.py
    cd src/vibey_tools/skills && python3 tools/check_links.py && PYTHONPATH=src python3 -m unittest discover -s tests
    git diff --numstat

## Out of scope
- Putting SD-01 into `render_block`'s generated block, and into the runners' runtime system
  prompts (`src/vibey_runners/claude/src/claudeloop/infrastructure/agent/options.py:40`,
  qwenloop's prompt). That would carry this operator's standing doctrine into adopters' projects:
  an operator decision, listed in the lane report, not taken here.
- Router files for `src/vibey_runners/opencode` and `src/vibey_runners/common` (see Why).
- The tenants' own rule trees (for example `src/vibey_runners/agy/.cursor/rules`): the tenant
  router files carry SD-01 for agents working there. Adding them to `AGENT_SURFACE_TREES` is a
  follow-up.
- Editing `.claude/skills`, `.agents/skills`, any existing line of any file, CHANGELOG.md, docs/, ADRs.

Commit as `docs(agents): SD-01 is carried verbatim in every agent router and rule tree`. Do not push.

## Lane card
- **Depends on:** `gap-agent-tree-parity` (the declared tree list and `SD01_RULE_STEM`).
- **Kind:** a docs lane: the named router and rule files plus one meta-test.
- **Consumers:** `gap-vscode-agent-tree` carries SD-01 in the fifth tree the way this lane does
  in `.cursor/rules/`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
