## Title
feat(gh): `vibey-gh doctor` warns by name when origin is a hosted forge but no `[platform]` is declared

## Why
Issue #138 (rewrite: `issue-audit/updates/138.md`, "Proposed child issues" 2 and Scope 6: "GitHub
adopters get a clear migration: declare `[platform] kind = "github"`. `vibey-gh check` warns
loudly when a repository's origin is on a hosted forge but no `[platform]` is declared").
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:138-139`) made Forgejo the default forge
and GitHub/GitLab declared-only, so vibey-gh ADR 0002 flipped the default kind to `forgejo`
(`src/vibey_tools/gh/vibey_gh/config.py:288`, `kind: str = ForgeKind.FORGEJO.value`). An adopter
on GitHub with no `[platform]` table is now silently driven as a self-hosted Forgejo at
`forgejo.local`; `specs/forge-adapter.md` appendix item 1 names this rollout break. Nothing
detects it today: `doctor.diagnose` (`vibey_gh/doctor.py:260-270`) runs five checks, none about
the platform.

The finding belongs in `doctor` ("will this repository's automation actually work?",
`doctor.py:1-21`), which promises "No network, no credentials, no execution" (`doctor.py:21`).
The only existing origin reader, `forge_selector._repository` (`forge_selector.py:92-104`), runs
`git config --get remote.origin.url` — execution. So this lane reads git's config **file** through
the family's existing `TextFileReaderInterface` (`vibey_gh/interfaces/text_file_reader_interface.py`,
implemented by `fit.TextFileReader`, `fit.py:247-260`) — 10.e: the family's reader, not a second
one; the selector's subprocess path is left alone. The gaps.md §L6 lane adds a sibling finding
(`GITHUB_ACTIONS=true` with the forgejo default) in the same `diagnose`; both must coexist.

## Required behaviour
1. `PlatformConfig` (`config.py:270-326`) gains
   `hosted_origin_hosts: tuple[str, ...] = ("github.com", "gitlab.com", "bitbucket.org")`
   (12.c: which hosts count as hosted is configuration). `__post_init__` adds:
   `_unique_nonempty("platform.hosted_origin_hosts", self.hosted_origin_hosts)`, and every entry
   must `_HOST_RE.fullmatch` (else `ValueError(f"platform.hosted_origin_hosts entries must be bare host names: {value!r}")`).
   The loader (`config.py:1839-1844`) adds
   `hosted_origin_hosts=tuple(platform.get("hosted_origin_hosts", PlatformConfig.hosted_origin_hosts))`.
2. New `vibey_gh/git_origin.py` with class `GitOriginReader(GitOriginReaderInterface)`:
   - `__init__(self, reader: TextFileReaderInterface | None = None)`; default `fit.TextFileReader()`.
   - `origin_url(self, root: Path) -> str`: find the nearest of `(root, *root.parents)` that has
     a `.git` entry. If `.git` is a directory, the config is `.git/config`. If `.git` is a file,
     read it through the reader; its first line is `gitdir: <path>` (resolve relative to the
     directory holding `.git`); if `<gitdir>/commondir` is readable, the config is
     `(<gitdir> / <its stripped text>).resolve() / "config"`, else `<gitdir>/config`. Parse the
     config text with `configparser.ConfigParser(strict=False, interpolation=None)`; return the
     `url` of section `remote "origin"`, stripped, or `""` when anything is missing or
     unparsable (`configparser.Error` is caught). No subprocess.
   - `host_of(self, url: str) -> str`: `scheme://…` URLs → `urlparse(url).hostname or ""`;
     scp-like `user@host:path` → the text between the last `@` before the first `:` and that
     `:`; anything else → `""`. Lower-cased.
3. New `vibey_gh/interfaces/git_origin_reader_interface.py`: `GitOriginReaderInterface`
   (`runtime_checkable` Protocol) declaring `origin_url(root: Path) -> str` and
   `host_of(url: str) -> str`, docstring saying it reads files only.
4. `doctor.py`:
   - New `_check_platform_declared(cfg: GhConfig, origin: GitOriginReaderInterface) -> list[Finding]`:
     returns `[]` when `cfg.root / CONFIG_NAME` parses (tomllib) with a `"platform"` table that
     has a `"kind"` key (the forge is declared), or when `cfg.platform.kind != "forgejo"`. Otherwise it takes
     `host = origin.host_of(origin.origin_url(cfg.root))`; when `host in cfg.platform.hosted_origin_hosts`
     it returns exactly one
     `Finding("warning", f"origin is on {host}, a hosted forge, but .vibey-gh.toml declares no [platform]: vibey-gh will drive this repository as a self-hosted Forgejo (the sovereign default, 8.b). Declare the forge it lives on, e.g. [platform] kind = \"github\".")`.
     An unreadable or unparsable TOML is left to `_check_unknown_keys` (return `[]`).
   - `diagnose(...)` gains the keyword `origin: GitOriginReaderInterface | None = None` after the
     `env` keyword that lane `gap-gh-doctor-actions-forgejo` adds (this lane runs after it), and
     appends `_check_platform_declared(cfg, origin or GitOriginReader())` after that lane's
     `_check_actions_forge(cfg, env)`. `_check_platform_declared` is a private module function like
     its siblings (`doctor.py:104-257`), with that reason in its docstring. When both findings
     apply (GitHub Actions and a hosted origin, nothing declared) the doctor prints both.
   - Keep the module docstring's promise; add one bullet naming this failure
     ("an adopter on a hosted forge with no `[platform]` is driven as Forgejo").

## Where to change
- New: `src/vibey_tools/gh/vibey_gh/git_origin.py`,
  `src/vibey_tools/gh/vibey_gh/interfaces/git_origin_reader_interface.py` (provenance header from
  `interfaces/text_file_reader_interface.py:1`).
- Edit: `vibey_gh/config.py` (`PlatformConfig`, loader), `vibey_gh/doctor.py`
  (`_check_platform_declared`, `diagnose`). Use `edit_file`.
- Tests: append to `src/vibey_tools/gh/test/test_doctor.py` (use its `_repo` helper,
  `test_doctor.py:19-22`); new `src/vibey_tools/gh/test/test_git_origin.py`.

## Acceptance criteria
- [ ] A repository whose origin is `git@github.com:o/r.git` and whose `.vibey-gh.toml` has no
      `[platform]` gets exactly one warning naming `github.com`; `vibey-gh doctor` still exits 0
      (warnings block nothing, `doctor.py:57-62`).
- [ ] With `[platform]\nkind = "github"\n` declared, or with an origin on `forgejo.example`, or with
      no origin at all, there is no such finding. A `[platform]` table without `kind` (for example
      one that only sets `hosted_origin_hosts`) does not count as a declaration.
- [ ] `GitOriginReader` never starts a process (it has no `subprocess` import).
- [ ] vibey-gh's suite passes with its 100% branch floor; black, isort, mypy and ruff are clean.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_git_origin.py` (uses real `git init` / `git remote add` in
`tmp_path` as `test_platform.py:250-277` does, and a dict-backed fake
`TextFileReaderInterface` for the unreadable cases):
- `test_the_origin_url_is_read_from_the_git_config_file`
- `test_a_worktree_git_file_is_followed_to_the_common_config` (build `.git` as a file with
  `gitdir:` pointing at a directory holding `commondir` → `../..`, and a config there)
- `test_a_missing_or_broken_config_reads_as_no_origin` (no `.git`; `.git` file with no gitdir;
  config text `"[remote \"origin\"\nurl"` → `""`)
- `test_the_host_is_taken_from_url_and_scp_forms` — `https://github.com/o/r.git` → `github.com`,
  `ssh://git@GitLab.com:22/o/r` → `gitlab.com`, `git@bitbucket.org:o/r.git` → `bitbucket.org`,
  `/local/path` → `""`.
Append to `src/vibey_tools/gh/test/test_doctor.py`:
- `test_an_undeclared_platform_on_a_hosted_origin_is_named`
- `test_a_declared_platform_is_not_warned_about`
- `test_a_self_hosted_or_absent_origin_is_not_warned_about`
- `test_the_hosted_hosts_are_configuration` (`.vibey-gh.toml` = `[platform]\nhosted_origin_hosts = ["git.corp.example"]\n`
  — a table with no `kind` — and origin on `git.corp.example` → warned; origin on `github.com`
  → not warned, because the list replaced the default; `PlatformConfig(hosted_origin_hosts=("bad host",))` raises)

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_git_origin.py test/test_doctor.py test/test_platform.py
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The `GITHUB_ACTIONS=true` trigger (the gaps.md §L6 lane); `check`'s exit code; the selector's
  own origin reader; any adapter.
- Docs (`docs/configuration.md` `[platform]` row) and CHANGELOG.
- Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
