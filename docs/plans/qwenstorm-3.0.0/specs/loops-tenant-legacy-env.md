## Title
feat(sovereignloop): SOVEREIGNLOOP_* environment names and a sovereignloop config path, with the qwenloop spellings read when the new ones are unset

ADR-0046 lane L18c (slug `loops-tenant-legacy-env`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`) renames the runner's own names,
keeping each old one "read when the new name is unset", through all of 3.x:
- `QWENLOOP_BASE_URL`, `_MODEL`, `_API_KEY`, `_CONFIG`, `_NETWORK` become `SOVEREIGNLOOP_*`;
- `<config>/qwenloop/config.toml` becomes `<config>/sovereignloop/config.toml`, the old one
  "read when the new file is absent".

12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) makes this a rename, never a removal: every
setting keeps working under both names until `vibey doctor` shows no use (lane L07). Nothing
is moved (ADR-0015 #5: an operator's file stays where they put it).

After lane `loops-tenant-rename` (L18a) the tenant is `src/vibey_runners/sovereign`, package
`sovereignloop`. At integration `d3b4a388` (paths before L18a's move):
- `src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py:15-22` declares
  `ENV_CONFIG = "QWENLOOP_CONFIG"`, `ENV_BASE_URL`, `ENV_MODEL`, `ENV_API_KEY`, and `:44` the
  default path `user_config_path("qwenloop") / "config.toml"`;
- `infrastructure/tools.py:46-47` writes `QWENLOOP_NETWORK=disabled` into a sandboxed shell's
  environment (nothing in the repository reads it; it tells a tool subprocess its network is off);
- `cli/app.py:69` and `:76` name `$QWENLOOP_BASE_URL` and `$QWENLOOP_MODEL` in `--help`;
- `tests/conftest.py:9-22` (the autouse `isolated_settings`) clears only the `QWENLOOP_*`
  names, so a developer's `SOVEREIGNLOOP_*` would leak into the suite once they are read.

## Required behaviour
1. `settings.py` names: `ENV_CONFIG = "SOVEREIGNLOOP_CONFIG"`, `ENV_BASE_URL =
   "SOVEREIGNLOOP_BASE_URL"`, `ENV_MODEL = "SOVEREIGNLOOP_MODEL"`, `ENV_API_KEY =
   "SOVEREIGNLOOP_API_KEY"`, and a new `ENV_NETWORK = "SOVEREIGNLOOP_NETWORK"`.
2. `LEGACY_ENV: Final[Mapping[str, str]]` (a `MappingProxyType`) maps each current name to its
   legacy spelling: `SOVEREIGNLOOP_CONFIG → QWENLOOP_CONFIG`, `_BASE_URL`, `_MODEL`,
   `_API_KEY`, `_NETWORK` likewise.
3. `SettingsLoader` reads each variable through one method,
   `_read(self, variable: str) -> tuple[str, str]`: the current name and its stripped value when
   that value is non-blank; else the legacy name and its stripped value (possibly `""`). So:
   - the current name wins whenever it is set and not blank;
   - a blank or unset current name falls back to the legacy one;
   - `api_key`, `load()`'s environment layer and `path` all go through `_read`.
4. The config file:
   - a configured variable (either spelling, via `_read(ENV_CONFIG)`) wins, `~`-expanded;
   - else `<user config dir>/sovereignloop/config.toml` when it exists;
   - else `<user config dir>/qwenloop/config.toml` when **only** that one exists (read in place,
     never copied or moved);
   - else the new default path (a missing default is an empty layer, as today).
   The constructor gains `legacy_path: Path | None = None` beside `default_path`, defaulting to
   `user_config_path("qwenloop") / "config.toml"`; `default_path` now defaults to
   `user_config_path("sovereignloop") / "config.toml"`.
5. A configured file that does not exist raises
   `ValueError(f"{variable} names {path}, which does not exist")` where `variable` is the name
   actually read (`SOVEREIGNLOOP_CONFIG` or `QWENLOOP_CONFIG`).
6. `tools.py`: when network access is off, a sandboxed shell's environment carries **both**
   `SOVEREIGNLOOP_NETWORK=disabled` and `QWENLOOP_NETWORK=disabled` (a script written for
   qwenloop keeps seeing its signal through 3.x). When network access is on, neither is set by
   the tool.
7. `--help` names the new variables and their legacy spellings (behaviour-neutral text).
8. The suite's autouse fixture isolates both spellings.

## Where to change
All paths are after L18a's move.
- `src/vibey_runners/sovereign/src/sovereignloop/infrastructure/settings.py` (76 lines, under
  100: `write_file` with the whole new content is allowed). Its new content:
  ```python
  <line 1: the provenance line, byte for byte as it is now>
  """Where sovereignloop's settings come from: a TOML file, the environment, and flags.

  sovereignloop was qwenloop until ADR-0046. Every name it reads has a current spelling and a
  legacy one, and the legacy one is read only while the current one is unset or blank, through
  3.x (ADR-0046 Migration table). Nothing is moved: a legacy config file is read where it is.
  """

  import tomllib
  from collections.abc import Mapping
  from pathlib import Path
  from types import MappingProxyType
  from typing import Any, ClassVar, Final

  from platformdirs import user_config_path

  from sovereignloop.domain.config import QwenConfig, QwenConfigParser
  from sovereignloop.domain.interfaces import QwenConfigParserInterface

  #: Points sovereignloop at a config file. Unset: `<user config dir>/sovereignloop/config.toml`,
  #: else the legacy `<user config dir>/qwenloop/config.toml` while only that one exists.
  ENV_CONFIG = "SOVEREIGNLOOP_CONFIG"
  #: The OpenAI-compatible base URL to attach to (`base_url`), `/v1` included.
  ENV_BASE_URL = "SOVEREIGNLOOP_BASE_URL"
  #: The model name the endpoint serves (`model`).
  ENV_MODEL = "SOVEREIGNLOOP_MODEL"
  #: The endpoint's API key. Environment only: a secret belongs neither in a config file
  #: nor on a command line, where `ps` would show it to every user on the machine.
  ENV_API_KEY = "SOVEREIGNLOOP_API_KEY"
  #: Set to `disabled` in a sandboxed shell's environment when network access is off.
  ENV_NETWORK = "SOVEREIGNLOOP_NETWORK"
  #: Each current name's legacy spelling, read only while the current one is unset or blank.
  LEGACY_ENV: Final[Mapping[str, str]] = MappingProxyType(
      {
          ENV_CONFIG: "QWENLOOP_CONFIG",
          ENV_BASE_URL: "QWENLOOP_BASE_URL",
          ENV_MODEL: "QWENLOOP_MODEL",
          ENV_API_KEY: "QWENLOOP_API_KEY",
          ENV_NETWORK: "QWENLOOP_NETWORK",
      }
  )


  class SettingsLoader:
      """Layers settings in precedence order: config file, then environment, then flags.

      A missing default config file is an empty layer, so sovereignloop runs with no file at
      all. A file named by `SOVEREIGNLOOP_CONFIG` (or its legacy spelling) that does not exist,
      or any file that does not parse, is an error: an operator who pointed at a file meant it
      to be read.
      """

      ENVIRONMENT_KEYS: ClassVar[Mapping[str, str]] = {ENV_BASE_URL: "base_url", ENV_MODEL: "model"}

      def __init__(
          self,
          environ: Mapping[str, str],
          *,
          parser: QwenConfigParserInterface | None = None,
          default_path: Path | None = None,
          legacy_path: Path | None = None,
      ) -> None:
          self._environ = environ
          self._parser = parser or QwenConfigParser()
          self._default_path = default_path or user_config_path("sovereignloop") / "config.toml"
          self._legacy_path = legacy_path or user_config_path("qwenloop") / "config.toml"

      @property
      def path(self) -> Path:
          configured = self._read(ENV_CONFIG)[1]
          if configured:
              return Path(configured).expanduser()
          if not self._default_path.exists() and self._legacy_path.exists():
              return self._legacy_path
          return self._default_path

      @property
      def api_key(self) -> str:
          return self._read(ENV_API_KEY)[1]

      def load(self, overrides: Mapping[str, object | None] | None = None) -> QwenConfig:
          layered: dict[str, Any] = self._file_layer()
          for variable, key in self.ENVIRONMENT_KEYS.items():
              value = self._read(variable)[1]
              if value:
                  layered[key] = value
          for key, override in (overrides or {}).items():
              if override is not None:
                  layered[key] = override
          return self._parser.parse(layered)

      def _read(self, variable: str) -> tuple[str, str]:
          """The name actually read and its stripped value: the current name while it is set and
          not blank, else its legacy spelling (whose value may be empty)."""
          value = self._environ.get(variable, "").strip()
          if value:
              return variable, value
          legacy = LEGACY_ENV[variable]
          return legacy, self._environ.get(legacy, "").strip()

      def _file_layer(self) -> dict[str, Any]:
          path = self.path
          if not path.exists():
              variable, configured = self._read(ENV_CONFIG)
              if configured:
                  raise ValueError(f"{variable} names {path}, which does not exist")
              return {}
          try:
              with path.open("rb") as stream:
                  return tomllib.load(stream)
          except tomllib.TOMLDecodeError as exc:
              raise ValueError(f"{path} is not valid TOML: {exc}") from exc
  ```
  The interface (`infrastructure/interfaces/settings_interface.py`) does not change: `path`,
  `api_key` and `load` keep their signatures.
- `.../sovereignloop/infrastructure/tools.py` (124 lines: `edit_file`, two edits):
  - `from pathlib import Path\n\n\nclass SandboxTools:` becomes
    `from pathlib import Path\n\nfrom sovereignloop.infrastructure.settings import ENV_NETWORK, LEGACY_ENV\n\n\nclass SandboxTools:`;
  - the two lines
    ```
                if not self.allow_network:
                    env["QWENLOOP_NETWORK"] = "disabled"
    ```
    become
    ```
                if not self.allow_network:
                    # Both spellings through 3.x: a script written for qwenloop still sees it.
                    env[ENV_NETWORK] = "disabled"
                    env[LEGACY_ENV[ENV_NETWORK]] = "disabled"
    ```
- `.../sovereignloop/cli/app.py` (over 100 lines: `edit_file`, two help strings):
  - `        "http://127.0.0.1:11434/v1). Unset: $QWENLOOP_BASE_URL, else config `base_url`.",` becomes
    ```
            "http://127.0.0.1:11434/v1). Unset: $SOVEREIGNLOOP_BASE_URL (or the legacy "
            "$QWENLOOP_BASE_URL), else config `base_url`.",
    ```
  - `        help="Model name the endpoint serves. Unset: $QWENLOOP_MODEL, else config `model`, "`
    followed by `        f"else {DEFAULT_ENDPOINT_MODEL}.",` becomes
    ```
            help="Model name the endpoint serves. Unset: $SOVEREIGNLOOP_MODEL (or the legacy "
            f"$QWENLOOP_MODEL), else config `model`, else {DEFAULT_ENDPOINT_MODEL}.",
    ```
- `src/vibey_runners/sovereign/tests/conftest.py` (`edit_file`, the `isolated_settings` body
  only; leave every other fixture exactly as it is). The block from its docstring through
  `return config` becomes:
  ```python
      """Keep the operator's own sovereignloop settings out of every test.

      The CLI layers `$SOVEREIGNLOOP_CONFIG` (else the user config dir) and the
      `SOVEREIGNLOOP_*` variables, or their legacy `QWENLOOP_*` spellings, into every command,
      so a developer with Ollama configured would otherwise see the suite attach to it. Each
      test starts from an empty config file and no endpoint variable under either name; the
      ones that want settings write or set their own.
      """
      config = tmp_path / "sovereignloop-config.toml"
      config.write_text("", encoding="utf-8")
      monkeypatch.setenv("SOVEREIGNLOOP_CONFIG", str(config))
      for variable in (
          "SOVEREIGNLOOP_BASE_URL",
          "SOVEREIGNLOOP_MODEL",
          "SOVEREIGNLOOP_API_KEY",
          "QWENLOOP_CONFIG",
          "QWENLOOP_BASE_URL",
          "QWENLOOP_MODEL",
          "QWENLOOP_API_KEY",
      ):
          monkeypatch.delenv(variable, raising=False)
      return config
  ```
- `src/vibey_runners/sovereign/tests/test_settings.py`: the one expectation that changes is
  `test_default_path_is_the_user_config_dir` (`:20-22` at `d3b4a388`). Its two asserts become
  (with `tmp_path: Path` added as the test's parameter, so the result does not depend on a
  legacy file in the developer's own config dir):
  ```python
      loader = SettingsLoader({}, legacy_path=tmp_path / "absent.toml")
      assert loader.path.name == "config.toml"
      assert loader.path.parent.name == "sovereignloop"
  ```
  Every other test in that file passes unedited: it sets the legacy names, which are still read.
- **Stop rule.** Any other failing tenant test: stop and report it.

## Acceptance criteria
- [ ] `SettingsLoader({"SOVEREIGNLOOP_MODEL": "new", "QWENLOOP_MODEL": "old"}, ...).load().model == "new"`.
- [ ] `SettingsLoader({"SOVEREIGNLOOP_MODEL": " ", "QWENLOOP_MODEL": "old"}, ...).load().model == "old"`.
- [ ] A legacy config file is read in place when only it exists, and is still at its path afterwards; the new path is not created.
- [ ] Both `SOVEREIGNLOOP_CONFIG` and `QWENLOOP_CONFIG` pointing at a missing file raise with the name read.
- [ ] A sandboxed shell without network sees `SOVEREIGNLOOP_NETWORK=disabled` and `QWENLOOP_NETWORK=disabled`.
- [ ] The tenant suite passes at its 100% floor with no `monkeypatch.setattr` in the new test file.

## Tests to write first (TDD)
`src/vibey_runners/sovereign/tests/test_settings_legacy.py` (line 1: the provenance line from
`tests/test_settings.py`; every loader is built with an explicit `environ` dict and `tmp_path`
paths, never the real user dirs):
- `test_the_names_are_sovereignloop` (the five constants).
- `test_each_name_has_its_qwenloop_spelling`: `dict(LEGACY_ENV)` equals the five pairs.
- `test_the_current_name_wins_over_the_legacy_one` (base URL and model).
- `test_a_blank_current_name_falls_back_to_the_legacy_one`.
- `test_the_api_key_falls_back_to_the_legacy_name`.
- `test_a_missing_configured_file_names_the_variable_read` (parametrized over both names).
- `test_a_configured_legacy_variable_points_at_a_file` (`QWENLOOP_CONFIG` names an existing file; its values load).
- `test_the_new_default_file_is_read_when_it_exists` (both files exist; the new one wins).
- `test_the_legacy_file_is_read_in_place_when_only_it_exists`: loads its `model`; afterwards the legacy file still exists and the default path does not.
- `test_neither_file_is_an_empty_layer`: `path == default_path`, `load() == QwenConfig()`.
- `test_a_shell_without_network_marks_both_names` (async; `monkeypatch.delenv` both names first): `SandboxTools(tmp_path).execute("shell", {"argv": [sys.executable, "-c", "import os; print(os.environ['SOVEREIGNLOOP_NETWORK'], os.environ['QWENLOOP_NETWORK'])"]})` gives `exit_code == 0` and output `disabled disabled`.
- `test_a_shell_with_network_marks_neither`: `SandboxTools(tmp_path, allow_network=True)` and `os.environ.get(...)` prints `None None`.

## Checks the lane must run (all must pass)
    uv sync --extra dev
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m mypy --strict src/sovereignloop && uv run --extra dev lint-imports && uv run --extra dev bandit -q -r src/sovereignloop)
    uv run ruff check . && uv run ruff format --check .
    git grep -n '"QWENLOOP_' -- src/vibey_runners/sovereign/src

The tenant's `pytest` carries its 100% floor. The last command may print only the five
`LEGACY_ENV` values in `settings.py`.

## Out of scope
- The model cache, run directories and the done marker (lane `loops-tenant-legacy-paths`, L18d).
- vibey's side: the endpoint overlay it writes (`SOVEREIGNLOOP_BASE_URL`/`_MODEL`, lane
  `loops-vibey-local-engine-names`) and `vibey doctor`'s report (lane L07).
- Moving or copying any file; removing any legacy name (a 4.0 decision on doctor evidence).
- The tenant's docs and `docs/examples/qwenloop-local.toml` (the docs wave), CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-tenant-rename`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
