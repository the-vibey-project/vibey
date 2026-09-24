## Title
test(meta): the four agent-surface trees carry the same skills with the same body, declared once

## Why
CLAUDE.md's "Agent-surface maintenance" rule (`CLAUDE.md:227-228` at integration HEAD
`4317cff6`) says "when a skill/procedure changes, update Claude, Cursor, Codex, and Antigravity
trees in the same PR". ADR-0011 (`docs/architecture/decisions/0011-agent-surface-provisioning.md:5`,
`:9-23`) owes the rule that agent guidance has one source of truth, "changed for all of them in
the same change", because "if these disagree, rotating engines silently changes the project's
rules mid-build". Runbook 15 (`docs/runbooks/expansion/15-agent-surface-sync.md:3`) is not
started, and `tests/meta/` has no parity test (gap N2, `issue-audit/gaps.md:714-718`). Nothing
stops the trees drifting.

The trees today (read at `4317cff6`), six skills each:
- `.claude/skills/<name>/SKILL.md` is the source. Front matter `name`, `description`,
  `allowed-tools`, then the body.
- `.agents/skills/<name>/SKILL.md` (Codex) is byte-identical to the source.
- `.cursor/rules/<name>.mdc` has front matter `description` (the source's, verbatim) and
  `alwaysApply: false`, then a blank line, the mirror line
  ``> **Cursor rule mirror** of `.claude/skills/<name>/SKILL.md`. When this guidance changes, update Claude, Cursor, Codex, and Antigravity in the same PR.``,
  a blank line, and the body.
- `.agent/rules/<name>.md` (Antigravity) has no front matter. Line 1 is
  ``# <name> (Antigravity mirror of `.claude/skills/<name>/SKILL.md`)``, a blank line, then the body.
All four agree today (bodies compared at `4317cff6`), so the test is a guard: it passes at once
and fails on the first drift.

The tree list is declared **once**, in a module both this test and `gap-sd01-carriage` import.
Lane `gap-vscode-agent-tree` adds a fifth tree by appending one entry to it, with no new test logic.

## Required behaviour
1. New module `tests/meta/agent_surfaces.py` (provenance header on line 1, copied from
   `tests/meta/test_adr_counts.py:1`; a declaration module, not a test module). It holds:
   - `class TreeLayout(StrEnum)`: `SKILL_DIRECTORIES = "skill-directories"` (files are
     `<root>/<name>/SKILL.md`) and `RULE_FILES = "rule-files"` (files are `<root>/<name><suffix>`).
   - `@dataclass(frozen=True, slots=True) class SkillTree` with fields, in this order:
     `root: str` (repository-relative directory), `layout: TreeLayout`, `suffix: str`
     (`"SKILL.md"` for `SKILL_DIRECTORIES`, the file suffix such as `".mdc"` for `RULE_FILES`),
     `front_matter: bool`, `mirror_line: str | None` (a `str.format` template with one field,
     `{name}`), and `always_apply: str | None = None` (the front-matter line that makes a rule
     file load in every session of that tree's tool; read by `gap-sd01-carriage`).
   - `SOURCE_TREE: Final = SkillTree(root=".claude/skills", layout=TreeLayout.SKILL_DIRECTORIES, suffix="SKILL.md", front_matter=True, mirror_line=None)`.
   - `AGENT_SURFACE_TREES: Final[tuple[SkillTree, ...]]`, in this order:
     1. `SOURCE_TREE`;
     2. `SkillTree(root=".agents/skills", layout=TreeLayout.SKILL_DIRECTORIES, suffix="SKILL.md", front_matter=True, mirror_line=None)`;
     3. `SkillTree(root=".cursor/rules", layout=TreeLayout.RULE_FILES, suffix=".mdc", front_matter=True, mirror_line=CURSOR_MIRROR, always_apply="alwaysApply: true")`,
        where `CURSOR_MIRROR = "> **Cursor rule mirror** of `.claude/skills/{name}/SKILL.md`. When this guidance changes, update Claude, Cursor, Codex, and Antigravity in the same PR."`
        (a module constant, byte-for-byte the line in the six `.mdc` files);
     4. `SkillTree(root=".agent/rules", layout=TreeLayout.RULE_FILES, suffix=".md", front_matter=False, mirror_line="# {name} (Antigravity mirror of `.claude/skills/{name}/SKILL.md`)")`.
   - `SD01_RULE_STEM: Final = "sd-01-counterparties-trust-verification"` and
     `STANDING_RULE_STEMS: Final[frozenset[str]] = frozenset({SD01_RULE_STEM})`. A file in a
     `RULE_FILES` tree whose stem is here is a standing rule carried by its own text (SD-01 §8),
     never a skill; `gap-sd01-carriage` adds and checks it.
   - The module docstring says what the declarations are for, names the two tests that read
     them, and gives the reason the declarations are a dataclass and a module constant rather
     than a class with an interface beside it: they are test data, and ADR-0016 is about
     production code (the same reason `tests/meta/test_protected_paths_agree.py:14-16` gives).
2. New test module `tests/meta/test_agent_tree_parity.py` (provenance header; module docstring
   citing CLAUDE.md's rule, ADR-0011, and this spec's definition of "the same body"). Helpers are
   module functions whose reason is that docstring's (pytest collects functions).
   - **Source skills** are the sorted names `p.name` for each directory `p` under
     `REPO / ".claude/skills"` that contains a `SKILL.md` (read from the file system, so the
     test ids are fixed at collection time).
   - **Front matter**: a file with `front_matter=True` must start with `"---\n"`; the front
     matter is the text up to the first following line that is exactly `---`
     (`text.index("\n---\n", 4)`), and the rest starts after that line. A key's value is the
     text after `"<key>: "` on the line that starts with it.
   - **"The same body"**, precisely: the source body is the source file's text after its front
     matter, with leading `"\n"` characters removed (`str.lstrip("\n")`). A mirror's body is its
     text after its front matter (when the tree has one), leading newlines removed; then, when
     the tree has a `mirror_line`, the first line must equal `mirror_line.format(name=name)`
     exactly and is dropped, and leading newlines are removed again. The two bodies must be
     equal as strings, byte for byte, trailing newline included.
3. Nothing outside `tests/meta/` changes. No tree file is edited: the trees already agree.

## Where to change
- New: `tests/meta/agent_surfaces.py`, `tests/meta/test_agent_tree_parity.py`.
- Style to copy: `tests/meta/test_protected_paths_agree.py:20-50` (`REPO`, `git ls-files`
  through `subprocess.run([...], cwd=REPO, capture_output=True, text=True, check=True)`).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_agent_tree_parity.py` passes at the
      current tree, with one parametrized case per (mirror tree, skill): 18 body cases.
- [ ] By hand (then revert): appending `x` to the last line of
      `.agent/rules/vibey-testing.md` fails `test_every_mirror_carries_the_source_body` naming
      that file; deleting `.cursor/rules/vibey-releasing.mdc` fails
      `test_every_tree_holds_exactly_the_source_skills`; editing the `description:` of
      `.agents/skills/vibey-domain-model/SKILL.md` fails the description test.
- [ ] `AGENT_SURFACE_TREES` is the only place the four roots are written in either new file.
- [ ] `git diff --stat` shows only the two new files.

## Tests to write first (TDD)
In `tests/meta/test_agent_tree_parity.py`:
- `test_the_source_tree_comes_first_and_holds_skills`: `AGENT_SURFACE_TREES[0] is SOURCE_TREE`,
  the source has at least one skill, and the roots are unique.
- `test_every_tree_holds_exactly_the_source_skills` (parametrized over
  `AGENT_SURFACE_TREES[1:]`, id `tree.root`): from `git ls-files <root>`, each tracked file maps
  to a skill name (`<name>/SKILL.md` for `SKILL_DIRECTORIES`; a file directly in the root with
  the tree's suffix for `RULE_FILES`, its stem being the name). Stems in `STANDING_RULE_STEMS`
  are skipped. Any other tracked file is a stray. Assert the names equal the source skills and
  there is no stray; the message lists the missing, the extra and the strays, and ends
  "update every agent-surface tree in the same PR (CLAUDE.md, Agent-surface maintenance)".
- `test_every_mirror_carries_the_source_body` (parametrized over every mirror tree × source
  skill, id `f"{tree.root}:{name}"`): the bodies are equal under behaviour 2. On a mismatch
  the message names the file and shows at most 20 lines of `difflib.unified_diff`. A missing
  mirror line fails with the expected line in the message.
- `test_every_mirror_carries_the_source_description` (parametrized over mirror trees with
  `front_matter=True` × skills): the `description` equals the source's. For
  `SKILL_DIRECTORIES` trees the `name` also equals the skill name.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Carrying SD-01 in the trees and its carrier-rule files (`gap-sd01-carriage`).
- The fifth, VS Code tree (`gap-vscode-agent-tree`).
- The tenants' own trees (`src/vibey_runners/{agy,claude,codex,cursor}/.claude/skills` and
  siblings, and those under `src/vibey_tools/*`): they follow their own conventions (ADR-0022),
  and at `4317cff6` they are not name-aligned (for example `src/vibey_runners/claude/.cursor/rules`
  has `claudeloop-router.mdc`, which its `.claude/skills` lacks). A follow-up can declare them.
- Any tree file, CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md and GEMINI.md.

Commit as `test(meta): the agent-surface trees carry the same skills with the same body`. Do not push.

## Lane card
- **Depends on:** nothing.
- **Kind:** a test lane: one declaration module and one meta-test under `tests/meta/`.
- **Consumers:** `gap-sd01-carriage` imports `AGENT_SURFACE_TREES`, `TreeLayout`, `SD01_RULE_STEM`;
  `gap-vscode-agent-tree` appends one `SkillTree` to `AGENT_SURFACE_TREES`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
