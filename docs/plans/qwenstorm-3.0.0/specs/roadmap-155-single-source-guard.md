## Title
test(meta): one book and one paper per channel — the release workflow publishes only from the root `properdocs.yml` and `docs/paper.md`

## Why
Issue #155 (rewrite: `issue-audit/updates/155.md`, Scope 1 and 5, "Proposed child issues" 5–6). The
operator asked for "a single book.pdf and single paper.pdf so there aren't multiple of each
anymore". Publication already follows that: the one workflow GitHub runs,
`.github/workflows/release-surfaces.yml`, selects `config=properdocs.yml` at the repository root
(`release-surfaces.yml:210-221`), builds the book with `vibey-gh book --config-file .properdocs-channel.yml`
(`:405-410`), and renders the paper only `if … [ -f docs/paper.md ]` with `vibey-gh paper`
(`:434-450`), whose `--source` defaults to `docs/paper.md` (`src/vibey_tools/gh/vibey_gh/cli.py:1760`).
But the tree still tracks eight tenant `docs/paper.md` and eight tenant `properdocs.yml`
(`git ls-files '*properdocs.yml' '*docs/paper.md'`), and nothing stops a later edit from publishing
one of them. Their fate (fold, appendix or delete) is #155 open question 1 and is not decided here;
this lane only pins the publishing wiring, which is doctrine 6 (`src/vibey_tools/gh/docs/doctrines.md:60-63`)
and 7 "the never-lost reader" (`doctrines.md:65-70`). Nested workflows under a tenant
(`src/vibey_tools/gh/.github/workflows/release-surfaces.yml`) are never read by GitHub — the CI
comment at `.github/workflows/ci.yml:225-229` records that tenants' nested workflows "never fired in
this repository (#263)" — so the root directory is the only one checked.

## Required behaviour
New `tests/meta/test_one_book_one_paper.py` (module-level test functions, with the reason
`tests/meta/test_protected_paths_agree.py:15-17` gives; `REPO = Path(__file__).resolve().parents[2]`;
`WORKFLOWS = REPO / ".github" / "workflows"`; parse YAML with `yaml.safe_load` — `yaml` is already
imported by `tests/meta/test_tools_matrix_covers_every_package.py`):
1. `test_exactly_one_root_workflow_builds_the_book_and_the_paper`: across `WORKFLOWS.glob("*.yml")`,
   the files whose text contains `vibey-gh book` are exactly `["release-surfaces.yml"]`, and the
   same for `vibey-gh paper`.
2. `test_the_book_is_built_from_the_root_definition`: `release-surfaces.yml` contains
   `config=properdocs.yml`, and `re.search(r"src/[^\s\"']*properdocs\.yml", text)` finds nothing.
3. `test_the_paper_is_rendered_from_docs_paper_md`: every line containing `vibey-gh paper` contains
   no `--source`; the text contains `[ -f docs/paper.md ]`; and
   `re.search(r"src/[^\s\"']*docs/paper\.md", text)` finds nothing.
4. `test_no_publishing_step_runs_inside_a_tenant`: in the parsed workflow, no step of any job has a
   `working-directory` beginning with `src/`.
5. Module docstring: this pins where the one book and one paper come from; the tenant copies still
   tracked are the subject of #155 open question 1 and are deliberately not touched.

## Where to change
- New `tests/meta/test_one_book_one_paper.py` only (provenance header copied from
  `tests/meta/test_paper_renders.py:1`). No workflow or docs change. If an assertion fails on the
  current tree, stop and report it rather than editing the workflow.

## Acceptance criteria
- [ ] The four tests pass on the integration tree.
- [ ] Adding `working-directory: src/vibey_tools/gh` to the paper step (try locally, then revert)
      fails test 4; replacing `config=properdocs.yml` with `config=src/vibey_tools/gh/properdocs.yml`
      fails test 2. Record both probes in the commit body; do not commit them.
- [ ] The module needs no network and no database.

## Tests to write first (TDD)
The four tests above: `test_exactly_one_root_workflow_builds_the_book_and_the_paper`,
`test_the_book_is_built_from_the_root_definition`, `test_the_paper_is_rendered_from_docs_paper_md`,
`test_no_publishing_step_runs_inside_a_tenant`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta/test_one_book_one_paper.py tests/meta/test_paper_renders.py

## Out of scope
- Deleting, folding or moving any tenant paper or `properdocs.yml` (blocked on #155 open question 1),
  the ADR-0032 amendment, and anything in `docs/` (docs wave).
- The paper's comprehensiveness (#301). CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
