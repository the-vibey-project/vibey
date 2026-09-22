## Title
feat(gh): [platform] kind = "paid" resolves to github, 8.b's default paid forge, and vibey-gh doctor says so

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139` and `:188-194` at integration HEAD
`d3b4a388`) makes self-hosted Forgejo the forge default, GitHub and GitLab declared-only, and
fixes **GitHub** as the forge an unnamed paid declaration reaches. Gap C2
(`issue-audit/gaps.md:189-200`): `PlatformConfig.kind` accepts only concrete forges
(`src/vibey_tools/gh/vibey_gh/config.py:288-296`), so "a paid forge, whichever is the default" cannot
be written, and nothing would show the resolution.

**Where the forge default lives.** vibey-gh cannot import vibey (it is a dependency-free tenant;
ADR-0022), and it owns `[platform]` and the forge adapters (#138). So the forge's paid default is
declared here, in `vibey_gh/config.py` beside `ADAPTED_PLATFORM_KINDS` (`:263`), as
`PAID_DEFAULT_PLATFORM_KIND`. vibey's catalogue (`vibey.domain.paid_defaults`, lane
`gap-paid-defaults`) keeps its own `"github"`, and lane `gap-paid-defaults-agree` adds the root meta
test that fails the moment the two copies, or their declaration words, differ. (vibey's domain
could import `vibey_gh` — it is dependency-free — but that would make the pure catalogue wait on
the forge wave and couple it to a 1,850-line config module; a meta test keeps them equal at no
such cost.)

A default among paid options never makes paid a default over sovereign (8.a): `kind` still
defaults to `forgejo`, and only the exact word `"paid"` resolves.

## Required behaviour
1. `vibey_gh/config.py` declares, directly after `ADAPTED_PLATFORM_KINDS = ("github", "gitlab", "forgejo")`
   (line 263), with the comment shown:
   ```python
   # 8.b's paid defaults: `[platform] kind = "paid"` declares a paid forge without naming
   # which, and that is always GitHub. vibey keeps its own copy in
   # `vibey.domain.paid_defaults` (vibey-gh cannot import vibey); vibey's
   # tests/meta/test_paid_defaults_agree.py holds the two equal. The default kind stays
   # forgejo (8.a): a paid default is never a default over sovereign.
   PAID_PLATFORM_KIND = "paid"
   PAID_DEFAULT_PLATFORM_KIND = ForgeKind.GITHUB.value
   ```
2. `PlatformConfig(kind="paid")` resolves in place: the first statement of `__post_init__`
   (line 293) becomes
   ```python
           if self.kind == PAID_PLATFORM_KIND:
               # The dataclass is frozen; the declaration resolves once, here.
               object.__setattr__(self, "kind", PAID_DEFAULT_PLATFORM_KIND)
   ```
   so `PlatformConfig(kind="paid") == PlatformConfig(kind="github")`, and
   `load_config(root)` of a `.vibey-gh.toml` holding `[platform]\nkind = "paid"\n` gives
   `cfg.platform.kind == "github"`. Every other check in `__post_init__` then runs on `"github"`.
3. The unknown-kind message (line 296) keeps its prefix and names the declaration:
   `f"platform.kind must be one of {', '.join(kinds)}, or {PAID_PLATFORM_KIND!r} for 8.b's default paid forge: {self.kind!r}"`.
   (`test_a_forge_the_standard_does_not_name_is_refused` matches the unchanged prefix.)
4. `PlatformConfig` gains the static method
   `declaration_note_for(root: Path) -> str`: it reads `root / CONFIG_NAME` with `tomllib` when the
   file exists and returns
   `f"platform.kind = {PAID_PLATFORM_KIND!r} resolves to {PAID_DEFAULT_PLATFORM_KIND!r}: GitHub is 8.b's default paid forge"`
   when its `[platform]` table's `kind` is exactly `PAID_PLATFORM_KIND`; otherwise (no file, no
   table, a non-table `platform`, any other kind) it returns `""`.
5. `vibey-gh doctor` prints that note as an `info` finding: in `vibey_gh/doctor.py`'s `diagnose`
   (line 260), directly after `findings += _check_unknown_keys(cfg.root)`, add
   ```python
       note = PlatformConfig.declaration_note_for(cfg.root)
       if note:
           findings.append(Finding("info", note))
   ```
   An `info` finding is printed and never counted (`vibey_gh/cli.py:945-951`), so the exit code is
   unchanged. No new module-level function is added.
6. The module docstring's `[platform]` example line (`config.py:33`) reads
   `kind = "forgejo"        # the sovereign, self-hosted default forge; github/gitlab declared-only; "paid" is github`.

## Where to change
- `src/vibey_tools/gh/vibey_gh/config.py` (behaviours 1-4, 6) — `edit_file` only; the file is over
  1,800 lines. `ForgeKind`, `tomllib`, `Path` and `CONFIG_NAME` are already imported or defined
  (`:44-53`).
- `src/vibey_tools/gh/vibey_gh/doctor.py` (behaviour 5) — `PlatformConfig` is already imported (`:43`).
- `src/vibey_tools/gh/test/test_platform.py` — append the tests below (never rewrite it; its
  `_config(root, text)` helper at `:38-40` writes `.vibey-gh.toml` and loads it).

## Acceptance criteria
- [ ] `(cd src/vibey_tools/gh && python -m pytest -q)` passes at the tenant's 100% floor.
- [ ] The existing tests in `test/test_platform.py` and `test/test_doctor.py` pass unedited.
- [ ] `git diff --stat` names only `config.py`, `doctor.py` and `test/test_platform.py`.
- [ ] `grep -n "import vibey\b\|from vibey\." src/vibey_tools/gh/vibey_gh/config.py` prints nothing (the tenant never imports vibey).

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_platform.py` (no patching; `tmp_path` only):
- `test_paid_declares_the_default_paid_forge` — `_config(tmp_path, '[platform]\nkind = "paid"\n').platform.kind == "github"`.
- `test_paid_resolves_in_the_constructor_too` — `PlatformConfig(kind="paid") == PlatformConfig(kind="github")`.
- `test_paid_keeps_the_rest_of_the_table` — `[platform]\nkind = "paid"\nhost = "ghe.example.com"\nrepository = "o/n"\n`
  gives `kind == "github"`, `host == "ghe.example.com"`, `repository == "o/n"`.
- `test_the_default_forge_stays_sovereign` — `load_config(tmp_path).platform.kind == "forgejo"` with no file (8.a).
- `test_paid_is_exact` — `PlatformConfig(kind="Paid")` raises `ValueError` matching
  `or 'paid' for 8.b's default paid forge`.
- `test_the_paid_default_is_an_adapted_forge` — `PAID_DEFAULT_PLATFORM_KIND in ADAPTED_PLATFORM_KINDS`.
- `test_the_declaration_note` — parametrized:
  - `'[platform]\nkind = "paid"\n'` → the exact sentence of behaviour 4;
  - `'[platform]\nkind = "github"\n'` → `""`;
  - `'[platform]\n'` → `""`;
  - `'platform = "paid"\n'` → `""` (not a table);
  - no file written → `""`.
- `test_doctor_reports_the_paid_resolution_as_info` — write `[platform]\nkind = "paid"\n`, call
  `doctor.diagnose(root=tmp_path)`; `("info", <the sentence>)` is among
  `[(f.severity, f.message) for f in findings]` exactly once, and no `"error"` finding's message
  contains `platform`. (Other checks may add their own findings for a bare repository; assert only
  on these.)

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta

(Both black and ruff format are enforced on this tenant; run both.)

## Out of scope
- The root meta test tying this value to vibey's catalogue (`gap-paid-defaults-agree`).
- This repository's own `.vibey-gh.toml`, which declares `kind = "github"` explicitly and stays so.
- The forge adapters and `ForgeSelector` (the forge wave, `forge-0a`…`forge-6`); the selector sees
  only the resolved `"github"`.
- Any relay from a sovereign Forgejo host (gap C3, `gap-spike-relay`).
- CHANGELOG.md, docs/ (including `src/vibey_tools/gh/docs/`), ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
  and the skill trees.

Commit as `feat(gh): [platform] kind = "paid" resolves to github, 8.b's default paid forge`. Do not push.

## Lane card
- **Depends on:** `forge-0g`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every other vibey-gh test; the tenant stays dependency-free
  (`dependencies = []`) and never imports vibey.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
