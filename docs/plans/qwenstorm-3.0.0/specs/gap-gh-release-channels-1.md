## Title
feat(gh): vibey-gh reads a declared release-channel registry and renders each channel's packaging templates

## Why
Sub-doctrine 2.b (`src/vibey_tools/gh/docs/doctrines.md:30`) says: "Every packaging
definition lives in the repository as code. Every channel is a support surface: nothing is
added that is not published by the same automation as everything else, because a stale
package installs an old version silently." ADR-0019 (`docs/architecture/decisions/0019-installable-wherever-its-users-are.md:97-100`)
puts the conductor in vibey-gh: "Releasing to N channels is release automation ... The
capability belongs there — beside `report-superseded`". vibey-gh has no channel logic
(`issue-audit/gaps.md` G4, lines 416-423; `ls src/vibey_tools/gh/vibey_gh/` has no channel module).

This lane is the conductor's data layer: one generic registry format (the file itself is
declared by `gap-pkg-channels`) and one renderer that turns a template such as a PKGBUILD
into the published file for one version. It is generic (12.c, `doctrines.md:455`): nothing
here names vibey, AUR or Homebrew. Publishing (`-2` to `-4`), the CLI (`-5`) and the
workflow (`-6`) come after.

## Required behaviour
1. New module `src/vibey_tools/gh/vibey_gh/channels.py` (provenance line 1, copied from
   `vibey_gh/yank.py:1`), with these module constants:
   - `SCHEMA: Final = 1`
   - `PUBLISHERS: Final = ("workflow", "in-tree", "release-asset", "git-push", "pull-request", "command")`
   - `_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")`, `_CREDENTIAL = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")`,
     `_REPOSITORY = re.compile(r"^[\w.-]+/[\w.-]+$")`, `_TOKEN = re.compile(r"@([A-Z][A-Z0-9_]*)(?::([^@\s]+))?@")`.
2. `class ChannelError(RuntimeError)`.
3. `@dataclass(frozen=True) class Probe`: `url: str`, `json: str = ""`, `pattern: str = ""`, `accept: str = "*/*"`.
4. `@dataclass(frozen=True) class Channel` with, in this order: `name: str`, `ecosystem: str`,
   `publisher: str`, `branches: tuple[str, ...]`, `definition: tuple[str, ...]`, `excludes: str`,
   `enabled: bool`, `credential: str = ""`, `grace_hours: int = 24`, `runner: str = "ubuntu-latest"`,
   `probe: Probe | None = None`, `probe_reason: str = ""`,
   `files: tuple[tuple[str, str], ...] = ()` (destination, template; sorted by destination),
   `workflow: str = ""`, `job: str = ""`, `remote: str = ""`, `push_branch: str = "main"`,
   `commit_message: str = "vibey {version}"`, `upstream: str = ""`, `base: str = ""`,
   `branch_name: str = "{channel}-{version}"`, `pr_title: str = ""`, `pr_body: str = ""`,
   `assets: tuple[str, ...] = ()`, `commands: tuple[tuple[str, ...], ...] = ()`,
   `options: tuple[tuple[str, str], ...] = ()` (sorted by key).
   Method `option(self, key: str, default: str = "") -> str` returns the value for `key` in `options`.
5. `@dataclass(frozen=True) class ChannelRegistry`: `source: Path`, `repository: str`,
   `governance_url: str`, `governance_path: str`, `release_tag: str`, `release_url: str`,
   `committer_name: str`, `committer_email: str`, `channels: tuple[Channel, ...]`. Methods:
   - `enabled_for(self, branch: str) -> tuple[Channel, ...]`: the channels with `enabled` true and
     `branch in branches`, in declaration order;
   - `named(self, name: str) -> Channel`, raising `ChannelError(f"no channel named {name!r} in {self.source}")`.
6. `class ChannelRegistryLoader` with `load(self, path: Path) -> ChannelRegistry`. It reads
   with `tomllib`. An `OSError` or `tomllib.TOMLDecodeError` becomes `ChannelError(f"{path}: {exc}")`.
   Every other problem raises `ChannelError(f"{path}: {problem}")`, where `problem` is the exact
   text below. For a channel the text is prefixed with `channel {name!r}: `, or `channel #{i}: `
   (0-based) when its name is missing or invalid.
   - Top level:
     - `schema` must equal 1: `schema must be 1`;
     - `repository` must match `_REPOSITORY`: `repository must be owner/name`;
     - `governance_url` and `release_url` must start with `https://`: `{key} must be an https:// URL`;
     - `release_tag` and `release_url` must contain `{version}`: `{key} must contain {version}`
       (the literal braces in the message);
     - `governance_path`, `committer_name` and `committer_email` must be non-empty strings:
       `{key} must be a non-empty string`;
     - `channel`, when present, must be a list of tables: `channel must be an array of tables`.
   - Per channel:
     - `name` must match `_NAME`, and must not repeat: `name must match [a-z0-9][a-z0-9-]*` and `declared twice`;
     - `ecosystem` must match `_NAME`: `ecosystem must match [a-z0-9][a-z0-9-]*`;
     - `publisher` must be in `PUBLISHERS`: `publisher must be one of workflow, in-tree, release-asset, git-push, pull-request, command`;
     - `branches` and `definition` must be non-empty lists of non-empty strings: `{key} must be a non-empty list of strings`;
     - `excludes` must be a non-empty string: `excludes must say what the install does not include (sub-doctrine 2.b)`;
     - `enabled` must be a bool: `enabled must be true or false`;
     - `credential` must be `""` or match `_CREDENTIAL`: `credential must be a secret NAME such as AUR_SSH_PRIVATE_KEY, never a value`;
     - `grace_hours` must be an int of 0 or more, and not a bool: `grace_hours must be a whole number of hours, 0 or more`;
     - `runner`, when given, must be a non-empty string: `runner must be a non-empty string`;
     - exactly one of the `probe` table and `probe_reason`:
       `declare a probe, or a probe_reason saying why its version cannot be read`, or
       `declare a probe or a probe_reason, not both`;
     - `probe.url` must start with `https://`: `probe.url must be an https:// URL`;
     - a `probe.url` without `{version}` needs `json` or `pattern`:
       `a probe URL without {version} must read a value with json or pattern`;
     - `probe.pattern`, when given, must compile with exactly one group: `probe.pattern must compile with exactly one group`;
     - `files` and `options` must be tables of strings: `{key} must be a table of strings`;
     - `workflow` needs `workflow` and `job`; `git-push` needs `remote` and a non-empty `files`;
       `pull-request` needs `upstream` (matching `_REPOSITORY`), `base`, `pr_title`, `pr_body` and a
       non-empty `files`; `release-asset` needs non-empty `assets`; `command` needs `commands` as a
       non-empty list of non-empty lists of strings. Each missing one gives
       `publisher {publisher} needs {key}`;
     - any other key gives `unknown key {key!r}`. The allowed channel keys are exactly the
       `Channel` field names above plus `probe_reason`, and probe keys are `url`, `json`,
       `pattern` and `accept` (`unknown probe key {key!r}`).
7. `class ChannelRenderer`:
   - `digests(self, artifacts: Path) -> dict[str, str]`: for each regular file directly inside
     `artifacts`, `{file.name: sha256 hex, lowercase}`. A missing directory gives `{}`.
   - `render_text(self, text: str, *, registry: ChannelRegistry, channel: Channel, version: str, digests: Mapping[str, str], source: str = "<text>") -> str`.
     Every `_TOKEN` match is replaced:
     - `@VERSION@` becomes `version`;
     - `@GOVERNANCE_URL@` becomes `registry.governance_url`;
     - `@EXCLUDES@` becomes `channel.excludes`;
     - `@RELEASE_URL@` becomes `registry.release_url` with `{version}` replaced;
     - `@RELEASE_TAG@` becomes `registry.release_tag` with `{version}` replaced;
     - `@SHA256:<name>@` becomes `digests[name]`, where `{version}` in `name` is replaced first.
       A missing name raises `ChannelError(f"{source}: no release artifact named {name}")`.
     - Any other token, a token that takes no argument but has one, or `SHA256` with no
       argument, raises `ChannelError(f"{source}: unknown token @{token}@")`, where `token` is
       the whole text between the two `@`.
   - `render_channel(self, registry: ChannelRegistry, channel: Channel, *, version: str, artifacts: Path, root: Path, out: Path) -> tuple[Path, ...]`.
     For each `(destination, template)` in `channel.files`:
     - read `root / template` as UTF-8. A missing file raises `ChannelError(f"{template}: template not found")`;
     - render it with `source=template` and the digests of `artifacts`;
     - write it to `out / destination` (with `{version}` replaced), creating parents;
     - return the written paths in `files` order.
8. New `src/vibey_tools/gh/vibey_gh/interfaces/channels_interface.py` (provenance line 1),
   `@runtime_checkable` Protocols with properties and methods matching the classes above:
   - `ProbeInterface`;
   - `ChannelInterface` (every field as a read-only property, plus `option`);
   - `ChannelRegistryInterface` (every field, plus `enabled_for` and `named`);
   - `ChannelRegistryLoaderInterface`, `ChannelRendererInterface` and `ChannelErrorInterface`
     (an `args` property, as `class_contracts.py:255-257` does).
   They import only the standard library.
9. `.importlinter` (repository root), contract `vibey-gh-interfaces-declare-only` (`:137-153`):
   add `    vibey_gh.channels` to `forbidden_modules`, after `    vibey_gh.conversation` (`:153`).
10. Default instances for callers: `CHANNEL_REGISTRY_LOADER: Final = ChannelRegistryLoader()` and
    `CHANNEL_RENDERER: Final = ChannelRenderer()`.

## Where to change
- New `src/vibey_tools/gh/vibey_gh/channels.py`.
- New `src/vibey_tools/gh/vibey_gh/interfaces/channels_interface.py`.
- `.importlinter`: one line (edit_file).
- New `src/vibey_tools/gh/test/test_channels.py`. Write registries into `tmp_path` with a
  helper `_registry(tmp_path, channels: str) -> Path` that writes the valid top level below,
  then the given `[[channel]]` text:
  ```toml
  schema = 1
  repository = "acme/tool"
  governance_url = "https://acme.example/governance/"
  governance_path = "GOVERNANCE.md"
  release_tag = "tool-v{version}"
  release_url = "https://github.com/acme/tool/releases/download/tool-v{version}"
  committer_name = "acme[bot]"
  committer_email = "bot@acme.example"
  ```

## Acceptance criteria
- [ ] A registry with one channel of each of the six publishers loads, and each field
      round-trips (a test asserts every field of one `git-push` channel).
- [ ] Each rule in item 6 has a test that asserts its exact message (parametrize over rule and text).
- [ ] `render_text` renders every token, and raises on an unknown token and on a missing artifact.
- [ ] `render_channel` writes `out/Formula/tool.rb` from a template, and `{version}` in a
      destination such as `manifests/{version}/x.yaml` is expanded.
- [ ] `isinstance` holds for each default instance and record against its interface.
- [ ] `(cd src/vibey_tools/gh && python -m pytest -q)` passes at the 100% floor.

## Tests to write first (TDD)
`src/vibey_tools/gh/test/test_channels.py`:
- `test_a_registry_with_every_publisher_loads`
- `test_a_git_push_channel_round_trips_every_field`
- `test_enabled_for_keeps_declaration_order_and_skips_disabled_and_other_branches`
- `test_named_raises_for_an_unknown_channel`
- `test_the_loader_rejects_each_invalid_declaration` (parametrized: every message in item 6)
- `test_an_unreadable_or_malformed_file_is_a_channel_error`
- `test_digests_are_sha256_of_each_artifact_and_empty_for_a_missing_directory`
- `test_render_text_replaces_every_token`
- `test_render_text_refuses_an_unknown_token_and_a_missing_artifact`
- `test_render_channel_writes_each_destination_with_its_version_expanded`
- `test_render_channel_names_a_missing_template`
- `test_the_defaults_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && python -m pytest -q
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports

## Out of scope
- The repository's own registry file (`gap-pkg-channels`).
- Publishing (`gap-gh-release-channels-2` to `-4`), the CLI (`-5`), the workflow (`-6`) and
  reading a channel's published version (`gap-gh-channel-lag-1`).
- Measurement (8.g): the `gap-measure-gh-*` lanes. Docs: the docs wave.

Commit as `feat(gh): a declared release-channel registry and its template renderer`. Do not push.

## Lane card
- **Depends on:** none.
- **Standing constraints:** vibey-gh stays dependency-free (stdlib only; `tomllib` is stdlib);
  black and ruff format are both enforced on this tenant; line 1 of every new file is the
  provenance line; never rewrite an existing file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
