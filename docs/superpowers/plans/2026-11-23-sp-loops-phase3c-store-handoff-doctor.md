# SP-LOOPS Phase 3c: the shipped marketplace, a configurable input store, its doctor line, and inputs across a handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Carry out the four operator decisions made after Phase 3 Tasks 1 to 6 merged (PR #1966, develop `b5f66fc22`): the wheel's default marketplace carries all 157 plugins (D3); the run input store has a configurable location with a `local` or `seaweedfs` backend (D2); `vibey doctor` says which store is in force and whether it is reachable (D2); and a BUILD run handed off to another engine sees the run inputs in its prompt, while the no-loss gate still passes (D1).

**Architecture:** The wheel's marketplace becomes a second rendering of the root manifest, made by the existing `vibey-gh marketplace` renderer with every source flattened to `./plugins/<name>`. The input store stays behind `InputStoreInterface`. `[inputs] store` selects between the existing `HashAddressedInputStore` and a new `SeaweedFsInputStore` that speaks the S3 API over `httpx`, signed by the SigV4 signer the family already ships in `GarageBlobAdapter` (extracted, not rewritten). A ledger cross-check makes the ledger, not the store, the authority on which inputs exist. For a handoff, the gate-verified seed prompt stays a byte-exact prefix of the run prompt. The input section follows it, rebuilt from the digests the outgoing run was given, which the wind-down pins in the follow-up job's payload.

**Tech Stack:** Python 3.12+; `httpx` (`httpx.Client`, and `httpx.MockTransport` in tests); stdlib `hashlib`, `hmac`, `xml.etree.ElementTree` behind a DOCTYPE and size guard; Typer; hatchling `force-include`; the `vibey-gh marketplace` renderer; the existing `TrustedTableReaderInterface` for `[inputs]`.

**Spec:** `docs/superpowers/specs/2026-11-22-uniform-loop-capabilities-design.md` (Goals 1 and 4, Decisions 1, 3, 5 and 6). Parent plans: `docs/superpowers/plans/2026-11-22-sp-loops-uniform-loop-capabilities.md`, `docs/superpowers/plans/2026-11-23-sp-loops-phase3-input-set.md`. Phase 3 report: `.superpowers/sdd/2026-11-23-sp-loops-phase3/task-1-6-report.md` (loops-p3 worktree), concern 2 and the N7 limit. Handoff law: `docs/plans/handoff-protocol.md` §4.1, §6 and §9; ADR-0004.

## Global Constraints

- The project's `vibey.toml` is untrusted: marketplaces, plugins and MCP servers come only from the person's own configuration (`user_config_path("vibey")/vibey.toml`); a project may only narrow.
- A run never fetches from the network on its own. Marketplace fetches happen only on an explicit `vibey loops ...` command; runs use the lock.
- A loop never receives the host token, the agent token or any Brave key.
- Plugin, skill and MCP-config text from the locked bundle is instruction; MCP output, fetched pages, search results and project files are untrusted data, bounded and marked.
- A capability claim needs evidence (`EngineAffordances.evidence`); unknown is `None`, never `True`.
- `domain/` stays pure (AST-enforced). Code lives in classes with an interface beside each (`services/interfaces/`). TypeScript, never JavaScript.
- 100% branch coverage per layer, verified with xdist and an empty Missing column. No test depends on thread timing, sleeps, the platform, the network, or a real docker/podman/launchctl/systemctl.
- Never read or print real keys (fake values in tests). Conventional Commits, each ending with a `Co-Authored-By:` trailer naming the model that wrote it; run `git commit` and `git push` in the foreground; never `--no-verify`.
- Pushes and test runs in a worktree use `VIBEY_TEST_TEMPLATE_DB=<a worktree-only name>`.
- Nothing enters Postgres: inputs are files; the ledger records digests, byte counts and kinds only.
- Limits are configuration, never constants in code (ADR-0018): `[inputs]` keys, defaults in the settings value.

Two Phase 3c additions, which the constraints above do not already say: credentials for a remote store come only from environment variables that `[inputs]` names. They never come from `vibey.toml`, and they never appear in a log, an error, a URL or doctor output. With `store = "seaweedfs"`, a BUILD run reads its inputs over the network from an endpoint the person configured, which bends the second constraint. That is part of operator ruling OR-1.

## Operator rulings this plan needs (surfaced, not decided)

- **OR-1 (D2a): scope.** Spec Decisions 5 and 6 say v1 is one machine and inputs do not follow a job to another machine. `RunInputsService`'s docstring says the same. A shared SeaweedFS store makes a project's inputs readable by every worker that has the endpoint and the credentials, so in practice they follow the job. It also means a run reads from the network (constraint 2 above). The plan builds the adapter behind the `local` default and changes no doctrine text. The PR that adds the `"seaweedfs"` value does not merge until the operator either amends Decisions 5 and 6 (recorded in ADR-0105) or rules that `seaweedfs` is for a store on the same machine only.
- **OR-2 (D2b): canon.** The repository names SeaweedFS nowhere (searched 2026-11-23). Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md`) already enumerates **Files → self-hosted Nextcloud** and **blob storage → Garage (the S3 protocol)**. Both surfaces exist in code: `[files]` with `NextcloudFilesAdapter`, and `[blob]` with `GarageBlobAdapter`. A SeaweedFS input store is a third storage surface beside them, so it touches 8.b (the enumerated sovereign defaults) and 12.c (generic and configurable). ADR-0105 (proposed) sets out three choices:
  - (i) SeaweedFS is a sibling sovereign option for object storage, as OpenProject is beside Plane, and Garage stays the blob default;
  - (ii) SeaweedFS replaces Garage as the blob default;
  - (iii) the value is generic (`store = "s3"`), with SeaweedFS as the first verified target, since the adapter speaks S3 and so would Garage.
  The operator rules. The 8.b amendment is then drafted for ratification by the operator's merge (Article II.3) and never self-ratified.
- **OR-3 (D2c): authentication.** The plan picks **S3 SigV4** against SeaweedFS's S3 gateway, for three reasons:
  - The family already ships a SigV4 signer (`src/vibey/infrastructure/blob/garage.py`), so dogfooding (10.e) means reuse, not a second implementation.
  - The same adapter then reaches Garage, which keeps the store generic (12.c).
  - SeaweedFS's S3 gateway holds access-key identities natively.
  The other option is the filer HTTP API. Its native append (`op=append`) would suit `index.jsonl`, and its listing is JSON rather than XML. My understanding, which I have not checked against a real SeaweedFS, is that the filer authenticates with a JWT signed by a shared key and has no native basic auth, so "basic credentials" would need a reverse proxy in front of it. The operator confirms S3, or rules filer HTTP. If the ruling is filer, only Task 4 changes.
- **OR-4 (D3): the four vibey-gh plugins in the wheel.** `vibey-gh-development`, `-documentation`, `-pr-automation` and `-release-security` are repository-workflow plugins (`src/vibey_tools/gh/plugins/`, 88 KB, no Python). The `vibey_gh` package that they serve already ships in the wheel. Task 0 ships them because the operator ruled that 157 is correct. Two things still need confirming:
  - that they belong in every install's default bundle;
  - that the shipped manifest's name changes from `vibey-skills` to `vibey`, the root's name and `DEFAULT_MARKETPLACE_NAME`. A person who runs `/plugin marketplace add` with the path `vibey-skills` prints from the wheel then registers it as `vibey`.
- **OR-5 (D1): promoting the input pin into the gate.** The plan leaves `domain/noloss.verify` and its ten rules unchanged and enforces the input pin beside the gate (Task 7). Handoff-protocol §9 says a new gate rule needs a minor version bump and one release in a `WARN` mode, and that mode does not exist yet (`GateMode` has STRICT, FULL_TRANSCRIPT, HUMAN and FORCED). Making the pin rule R11 is a later ruling that comes with building `WARN`.

## Review Focus

These are the five failures most likely here that no happy path exercises, most likely first:

1. **A handed-off run loses or alters its inputs.** The incoming prompt lacks the section, carries different digests, picks up an input added after the handoff, or the seed bytes change. The Task 7 tests cover each case: `test_a_wind_down_seed_is_the_byte_exact_prefix_and_the_pinned_section_follows`, `test_an_input_added_after_the_handoff_is_not_given_to_the_incoming_run` and `test_a_pinned_input_missing_from_the_store_parks_the_job_for_a_person`.
2. **A worker runs without inputs, silently, because its store resolves elsewhere.** The causes are the open N7 item (`XDG_STATE_HOME` differs between the shell and the systemd user session), a different `XDG_CONFIG_HOME` that hides `[inputs] store`, and a wrong bucket. Task 5's `test_a_store_missing_inputs_the_ledger_records_fails_the_run_before_the_engine_starts` covers it.
3. **A credential leaks.** The value is accepted from `vibey.toml`, or echoed in an error, a URL, a log record or doctor output. Tests: Task 2's `test_a_credential_in_the_inputs_table_is_refused_without_echoing_it`, Task 4's `test_the_secret_appears_in_no_request_url_header_or_log_record`, and Task 6's `test_doctor_never_prints_a_credential_value`.
4. **A third party who can write the shared bucket plants an input into a project's runs.** Task 5's `test_rows_the_ledger_never_recorded_are_withheld_and_counted` and Task 4's `test_get_refuses_bytes_that_do_not_match_their_digest` cover it.
5. **A listing stops at the first page or is hostile, so limits and the cross-check run over an unknown subset (10.g).** Task 4's `test_listed_follows_every_continuation_token` and `test_a_listing_with_a_doctype_or_over_one_mib_is_refused` cover it.

## Phase 3c: order of work

Task 0 (marketplace, the smallest, independent) → Tasks 1 to 4 (the store: ADR, settings, signer, adapter) → Task 5 (composition and the ledger cross-check) → Task 6 (the doctor line) → Task 7 (the handoff seed, last because it touches the no-loss gate's contract) → Task 8 (docs). Each task lands as its own commit; Task 0 and Task 7 can each be their own PR.

## On the open item: a store folder that is absent in a worker environment

The N7 limit from Phase 3 was this: a worker whose `XDG_STATE_HOME` differs from the shell's sees an empty store and runs without inputs. With a shared SeaweedFS store that particular cause disappears, because the store's location no longer depends on the worker's state folder. **The class of failure does not disappear.** `[inputs]` is read from the person's own `vibey.toml`, located through `XDG_CONFIG_HOME`. A worker with a different config folder reads no `[inputs]`, falls back to `local`, and sees an empty store. A wrong bucket or prefix does the same. Task 5 closes this for both backends: every input the ledger records as added must be in the store the run reads from, or the run fails before the engine starts and the failure names the resolved store. Task 6's doctor line names the resolved store and the config file it came from. An explicit `[inputs] store_dir` (Task 2) also takes the state-folder variable out of the local case.

---

### Task 0: The shipped default marketplace carries all 157 plugins

What ships today, measured 2026-11-23:
- The root `.claude-plugin/marketplace.json` lists 157 plugins under the name `vibey`. Its sources are `./src/vibey_tools/skills/plugins/<x>` and `./src/vibey_tools/gh/plugins/<y>`.
- The wheel (`pyproject.toml [tool.hatch.build.targets.wheel.force-include]`) maps `src/vibey_tools/skills/plugins` and the tenant manifest `src/vibey_tools/skills/.claude-plugin/marketplace.json` to `vibey_skills/marketplace/`. That manifest lists 153 plugins under the name `vibey-skills`, with sources `./plugins/<x>`. Nothing maps `src/vibey_tools/gh/plugins`.
- From a checkout, `vibey_skills.marketplace_root()` falls back to the tenant root, which also has 153.

What must change: the wheel needs a manifest whose sources match the wheel's flat `plugins/` layout, and the four gh plugin trees. The tenant's own 153-plugin manifest stays as it is, because it describes its own tree and its validators check it.

**Files:**
- Modify: `src/vibey_tools/gh/vibey_gh/marketplace.py` (`MarketplaceRenderer`) and its interface; `src/vibey_tools/gh/vibey_gh/config.py` (`MarketplaceConfig.packaged`); `.vibey-gh.toml [marketplace]` (`packaged = "src/vibey_tools/skills/packaged/marketplace.json"`)
- Create (generated, committed): `src/vibey_tools/skills/packaged/marketplace.json`. It lives under `/src` because the sdist includes only `/src`, and `uv build` builds the wheel from the sdist.
- Modify: `pyproject.toml` force-include. Map the packaged manifest to `vibey_skills/marketplace/.claude-plugin/marketplace.json`, and add `"src/vibey_tools/gh/plugins" = "vibey_skills/marketplace/plugins"` beside the skills mapping. If hatchling refuses two sources into one target folder, use one entry per gh plugin directory, with the test below guarding against a missed plugin.
- Modify: `src/vibey/bootstrap.py` (`loops_shipped_root()`: in a checkout, where `marketplace_root()` is the tenant root, use the repository root. The resolver's shipped lock is already scoped to the manifest and the folders it lists, in `CapabilityResolver._shipped_scope`.)
- Test: `src/vibey_tools/gh/test/test_marketplace.py`, `tests/meta/test_shipped_marketplace_matches_root.py`, `tests/meta/test_wheel_ships_default_marketplace.py` (slow), `tests/unit/test_bootstrap_loops_shipped_root.py`

**Interfaces:**
- `MarketplaceConfig.packaged: str = ""`. Empty means nothing is rendered or checked, so standalone adopters are unaffected.
- `MarketplaceRenderer.build_packaged(cfg: GhConfig) -> dict[str, Any]`. This is `build(cfg)` with every source rewritten to `./plugins/<the source folder's last segment>`. Two plugins whose folders share a last segment raise `MarketplaceError`. `write` writes both outputs, and `check` reports drift in either one.

- [ ] **Step 1: Write the failing tests.**
  - gh tenant:
    - `test_packaged_rendering_flattens_every_source_to_plugins`: every `source == f"./plugins/{Path(root_source).name}"`, and the names and count equal `build(cfg)`'s.
    - `test_packaged_check_reports_drift_when_a_member_gains_a_plugin`.
    - `test_packaged_is_not_rendered_when_unset`.
    - `test_two_plugin_folders_with_one_name_are_refused_for_packaging`.
  - Root meta:
    - `test_the_packaged_manifest_lists_exactly_the_root_plugins`: the set of names equals the root manifest's, and `len(packaged["plugins"]) == len(root["plugins"])`. The count is 157 today; the test asserts equality with the root count and does not pin the number.
    - `test_every_packaged_plugin_has_a_plugin_json_at_its_root_source`: for each entry, `<root source>/.claude-plugin/plugin.json` is a file.
  - Wheel (slow, offline build):
    - `test_the_wheel_manifest_is_the_packaged_rendering`, which replaces the byte comparison against the tenant manifest.
    - `test_the_wheel_carries_every_root_plugin_with_its_plugin_json`: for every root name, `vibey_skills/marketplace/plugins/<name>/.claude-plugin/plugin.json` is in the wheel.
    - `test_the_marketplace_root_holds_the_marketplace_and_nothing_else`, kept, still `{".claude-plugin", "plugins"}`.
  - Bootstrap: `test_a_checkout_locks_the_root_marketplace_with_every_plugin`: the plugin count of `loops_shipped_root()`'s manifest equals the root's.
- [ ] **Step 2: Run them.** `(cd src/vibey_tools/gh && python -m pytest -q test/test_marketplace.py)`; `uv run pytest -q tests/meta/test_shipped_marketplace_matches_root.py tests/unit/test_bootstrap_loops_shipped_root.py`; `uv run pytest -q -m slow tests/meta/test_wheel_ships_default_marketplace.py`. Expected: FAIL.
- [ ] **Step 3: Implement.** Render with `uv run vibey-gh marketplace`. Do not hand-edit the generated file.
- [ ] **Step 4: Run them, and the drift check.** Expected: PASS. `uv run vibey-gh marketplace --check` reports both outputs current. The tenant's own `validate_manifests.py` and `check_links.py` still pass against its 153-plugin manifest.
- [ ] **Step 5: Commit** `feat(loops): the wheel's default marketplace carries every root plugin`.

### Task 1: ADR-0105 (proposed): where run inputs are stored

**Files:**
- Create: `docs/architecture/decisions/0105-run-input-store-backends.md`. Status: proposed. It records OR-1 to OR-3 with the options above and leaves the decisions blank for the operator. It names 8.b and 12.c as the sub-doctrines touched, and lists the evidence: 8.b's Files and blob-storage lines, `[files]`, `[blob]`, and no SeaweedFS anywhere in the repository.
- Depends on: Phase 3 Task 8's ADR-0104 (run inputs, still to do) landing first, or both landing in one PR, because the ADR count is generated.

- [ ] **Step 1:** Write the ADR. Write no doctrine text: the 8.b amendment is drafted only after OR-2 is ruled.
- [ ] **Step 2:** `uv run vibey-gh corpus-index --check`, the generator named in `docs/agents/instructions.toml`, and `uv run pytest tests/meta -q`. Expected: PASS.
- [ ] **Step 3: Commit** `docs(adr): ADR-0105 proposed, where run inputs are stored`.

### Task 2: `[inputs]` store keys

**Files:**
- Modify: `src/vibey/domain/run_input.py`, which is where `RunInputsSettings` lives and owns the known-key set.
- Test: `tests/domain/test_run_input_store_location.py`, plus the existing `tests/application/test_run_inputs_settings.py`.

**Interfaces:**
- `StoreKind = Literal["local", "seaweedfs"]`
- `@dataclass(frozen=True, slots=True) class InputStoreLocation`, with these fields:
  - `kind: StoreKind = "local"`
  - `store_dir: str | None = None`
  - `endpoint: str | None = None`
  - `bucket: str | None = None`
  - `prefix: str = "vibey/inputs"`
  - `region: str = "us-east-1"`
  - `access_key_env: str = "VIBEY_INPUTS_ACCESS_KEY"`
  - `secret_key_env: str = "VIBEY_INPUTS_SECRET_KEY"`
  - `timeout_seconds: float = 10.0`
  - method: `def describe(self) -> str` (for doctor and errors: never a credential, never a URL's user info).
- `RunInputsSettings.store: InputStoreLocation`, parsed by the same `from_table`, so one known-key set covers the whole table.

Rules, decided here (each raises `ValueError`, which becomes `ConfigError`):
- `store` is not `"local"` or `"seaweedfs"`.
- With `local`, an `endpoint` or `bucket` is set, because a key that does nothing would hide a typo. A relative `store_dir` is refused, as `UserStateFolder` refuses a relative `XDG_STATE_HOME`.
- With `seaweedfs`, `endpoint` or `bucket` is missing.
- `endpoint` is not `http(s)://host[:port]`: it has user info, a path other than `/`, a query or a fragment. `http` is accepted only for `localhost`, `127.0.0.1` or `::1`, because credentials over plain HTTP to another host are refused.
- `bucket` does not match `^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$`.
- A `prefix` segment is empty, `.` or `..`, or not `[A-Za-z0-9._-]+`.
- `timeout_seconds` is not positive.
- An `*_env` value is not `^[A-Z_][A-Z0-9_]*$`.
- **Any key named `access_key`, `secret_key`, `password` or `token` is refused** with `[inputs] holds no credential; name the environment variable in access_key_env / secret_key_env`. The message never contains the value.

- [ ] **Step 1: Write the failing tests.**
  - `test_the_default_is_local_in_the_persons_state_folder`: `RunInputsSettings().store == InputStoreLocation()`.
  - `test_a_seaweedfs_table_parses`.
  - One parametrized test per refusal above.
  - `test_a_credential_in_the_inputs_table_is_refused_without_echoing_it`: the table has `secret_key = "s3cr3t-sentinel"`, and the message does not contain `s3cr3t-sentinel`.
  - `test_a_projects_store_keys_are_ignored_with_the_notice`.
  - `test_describe_names_scheme_host_bucket_and_prefix_only`.
- [ ] **Step 2: Run them.** `uv run pytest tests/domain/test_run_input_store_location.py tests/application/test_run_inputs_settings.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Stdlib only (`urllib.parse`, `re`, `ipaddress`). Domain purity holds.
- [ ] **Step 4: Run them, and `uv run pytest tests/domain -q`.** Expected: PASS.
- [ ] **Step 5: Commit** `feat(inputs): [inputs] names where the store is, never its credentials`.

### Task 3: One SigV4 signer for the family

The rule this task follows is "dogfood the family": `GarageBlobAdapter` already signs S3 requests, so its signer is extracted rather than written a second time.

**Files:**
- Create: `src/vibey/infrastructure/blob/s3_request_signer.py`, `src/vibey/infrastructure/blob/interfaces/s3_request_signer_interface.py`
- Modify: `src/vibey/infrastructure/blob/garage.py` (uses the signer; behaviour unchanged)
- Test: `tests/infrastructure/blob/test_s3_request_signer.py`, plus the existing Garage tests.

**Interfaces:**
- `class S3RequestSigner(access_key: str, secret_key: str, region: str, clock: Callable[[], datetime])`
- `S3RequestSigner.headers(*, method: str, host: str, canonical_uri: str, query: Mapping[str, str], body: bytes) -> dict[str, str]` returns `host`, `x-amz-content-sha256`, `x-amz-date` and `Authorization`. The signer has no `__repr__` that shows the secret.

- [ ] **Step 1: Write the characterization test first.** Against the current `garage.py`, with `datetime` patched to `2026-01-02T03:04:05Z` and fake keys: `test_garage_signs_exactly_as_before_extraction` records the `Authorization` header Garage produces for a PUT and a GET, and pins it. Then `test_signer_headers_equal_garages_for_the_same_request`, and `test_the_signer_repr_holds_no_secret`. Expected: the pin passes on the old code; the signer tests fail (module missing).
- [ ] **Step 2: Extract.** Garage keeps its stdlib `urllib` transport; migrating it to `httpx` is out of scope.
- [ ] **Step 3: Run** `uv run pytest tests/infrastructure/blob -q`. Expected: PASS, with the pinned header unchanged.
- [ ] **Step 4: Commit** `refactor(blob): one SigV4 signer, shared by Garage and the input store`.

### Task 4: `SeaweedFsInputStore`, the S3 API over `httpx`

**Files:**
- Create: `src/vibey/infrastructure/inputs/seaweedfs_input_store.py`, `src/vibey/infrastructure/inputs/interfaces/seaweedfs_input_store_interface.py`
- Modify: `src/vibey/domain/errors.py`. Add `InputStoreUnavailable(InputStoreError)`, the next free code (E0096 if nothing lands first). The store answered nothing, timed out, or answered 5xx; this is retryable. Also update `src/vibey/cli/error_codes.toml` and regenerate `docs/reference/errors.md` with `scripts/error_catalog.py`.
- Test: `tests/infrastructure/inputs/test_seaweedfs_input_store.py`. The fake is an in-memory S3 behind `httpx.MockTransport`: there is no SeaweedFS and no network.

**Interfaces:**
- `SeaweedFsInputStore(location: InputStoreLocation, clock: Clock, *, signer: S3RequestSignerInterface, client: httpx.Client)` implements `InputStoreInterface` (`put`, `restore`, `get`, `listed`, unchanged signatures), plus:
  - `describe() -> str`
  - `probe() -> StoreProbe`, where `@dataclass(frozen=True, slots=True) class StoreProbe: reachable: bool; detail: str`. Task 6 uses it.
- Layout, path-style (`<endpoint>/<bucket>/<key>`):
  - objects: `<prefix>/<project_id>/objects/<digest[:2]>/<digest>`
  - index rows: one object per row, `<prefix>/<project_id>/index/<at_ns:020d>-<uuid4 hex>.json`. S3 has no append, so each row is its own object; ListObjectsV2 key order is add order, and ties are broken by the uuid.

Rules, decided here:
- The bucket is never created. A missing bucket is an `InputStoreError` saying vibey does not create it, because least authority means the credentials may be scoped to one bucket.
- `put` first checks whether an object with that digest is already there and intact: HEAD for its size, then GET and compare the digest. If it is, the object is not written again. The order is the object first, then the row.
- `get` refuses a `Content-Length` other than the row's size before reading the body. It reads at most `size + 1` bytes and checks the digest.
- `listed` pages ListObjectsV2 until `IsTruncated` is false. It refuses a listing body over 1 MiB, or one containing `<!DOCTYPE` or `<!ENTITY`, before parsing it, and the `# nosec` comment says so. A row that does not parse is skipped and counted, as a torn line is today.
- Requests go only to the endpoint's host; the transport refuses redirects. A 401 or 403 is an `InputStoreError` naming `access_key_env` and `secret_key_env` (the variable names, never the values). Transport errors, timeouts and 5xx raise `InputStoreUnavailable`.

- [ ] **Step 1: Write the failing tests.**
  - `test_put_twice_writes_one_object_and_two_rows`
  - `test_get_returns_the_exact_bytes_with_nul_and_invalid_utf8`
  - `test_get_refuses_a_content_length_other_than_the_row_size_unread`
  - `test_get_refuses_bytes_that_do_not_match_their_digest`
  - `test_listed_follows_every_continuation_token`: 5 rows over pages of 2 gives 5 items, in key order.
  - `test_a_row_that_is_not_json_is_skipped_and_counted`: `skipped == 1`.
  - `test_a_listing_with_a_doctype_or_over_one_mib_is_refused`
  - `test_restore_writes_the_object_and_no_row`
  - `test_object_and_row_keys_follow_the_layout`: the object key is `vibey/inputs/<project>/objects/ba/ba7816bf...` for `b"abc"`.
  - `test_every_request_is_signed_and_goes_only_to_the_endpoint`: the `Authorization` header starts with `AWS4-HMAC-SHA256 Credential=FAKEACCESS/`, and the host equals the endpoint's.
  - `test_the_secret_appears_in_no_request_url_header_or_log_record`: the fake secret is a sentinel, checked against every request and `caplog`.
  - `test_a_403_is_a_store_error_naming_the_variables_not_the_values`
  - `test_a_transport_error_or_503_is_unavailable`
  - `test_a_missing_bucket_is_never_created`: no `PUT /<bucket>` request.
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Use a synchronous `httpx.Client(timeout=location.timeout_seconds, follow_redirects=False)`. The port stays synchronous; see Task 5 for how it stays off the event loop.
- [ ] **Step 4: Run** `uv run pytest tests/infrastructure/inputs -q`, then `uv run lint-imports` and `uv run bandit -q -r src/vibey`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(inputs): a SeaweedFS input store over the S3 API`.

### Task 5: One composed store, and the ledger as the authority on which inputs exist

**Files:**
- Modify: `src/vibey/bootstrap.py`. Add `run_inputs_location() -> InputStoreLocation` (from the person's own `[inputs]`) and `run_inputs_store(resources) -> InputStoreInterface` (local at `store_dir` or `run_inputs_root()`, or SeaweedFS with `S3RequestSigner` and credentials read from the two named environment variables). `run_inputs_service` takes its store from `run_inputs_store`, so the CLI and the worker still share one chain (N7).
- Modify: `src/vibey/application/run_inputs_service.py`, `src/vibey/application/interfaces/run_input_ledger_interface.py`, `src/vibey/infrastructure/inputs/run_input_ledger.py`.
- Modify: `src/vibey/cli/inputs.py`. `InputStoreUnavailable` is exit 69 (EX_UNAVAILABLE). Exit 78 stays for configuration.
- Test: `tests/application/test_run_inputs_service.py`, `tests/application/test_build_implement_inputs.py`, `tests/unit/test_bootstrap_run_inputs.py`, `tests/cli/test_inputs.py`, `tests/infrastructure/inputs/test_run_input_ledger.py`.

**Interfaces:**
- `RunInputLedgerInterface.added(project_id: UUID) -> frozenset[str]` returns the digests of the project's `vibey_run_input` and `vibey_run_input_repaired` events.
- `RunInputsService` calls every store method through `asyncio.to_thread`, so a remote store never blocks the worker's event loop and its lease heartbeat.

Rules, decided here:
- **A missing store input is a loud failure.** If any digest in `added(project_id)` has no row in `listed`, `materialize` raises `InputStoreError`. The message says the store at `<describe()>` holds `<n>` of the `<m>` inputs the ledger records for this project. The handler already turns that into `Failure(VIBEY)` before `engine.start`. This closes the N7 limit for both backends. The remedy is in the message: point `[inputs]` at the store they were added to, or add them again, which goes through the repair path.
- **Rows the ledger never recorded are withheld.** They are counted in the section's notice, never given.
- Credentials missing from the environment at composition are a `ConfigError` naming the variables, never the values.

- [ ] **Step 1: Write the failing tests.**
  - `test_a_store_missing_inputs_the_ledger_records_fails_the_run_before_the_engine_starts`: an empty store root and one add event give `Failure(VIBEY)`; the engine was not started; the message contains `describe()`.
  - `test_rows_the_ledger_never_recorded_are_withheld_and_counted`
  - `test_with_no_inputs_and_no_add_events_the_prompt_is_unchanged`
  - `test_the_service_calls_the_store_off_the_event_loop`: the fake store records `threading.get_ident()`, which differs from the loop thread's. The check compares thread identities and depends on no timing.
  - `test_store_seaweedfs_composes_the_seaweedfs_store_with_the_shared_signer`
  - `test_store_local_with_store_dir_uses_that_folder`
  - `test_missing_credential_variables_refuse_at_composition_naming_the_variables`
  - `test_an_unreachable_store_is_exit_69_and_names_the_store_not_the_key`
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/application tests/unit tests/cli tests/infrastructure/inputs -q`, and the `tests/system/test_worker_run_inputs_wiring.py` system test against PostgreSQL. Expected: PASS. Every layer floor stays at 100%.
- [ ] **Step 5: Commit** `feat(inputs): the store [inputs] names, and no run without the inputs the ledger records`.

### Task 6: `vibey doctor`: the `run-inputs` line

**Files:**
- Create: `src/vibey/cli/run_inputs_doctor.py`, `src/vibey/cli/interfaces/run_inputs_doctor_interface.py`
- Modify: `src/vibey/cli/doctor_probes.py` (`LocalDoctorProbes.for_doctor(..., run_inputs=...)` and `for_editor`, as `web_search` is wired), and `src/vibey/cli/main.py` (doctor wiring and its comment list)
- Test: `tests/cli/test_run_inputs_doctor.py`

**Interfaces:**
- `RunInputsDoctor.doctor_lines() -> tuple[list[str], bool]`, section name `run-inputs`. Each line is `f"{mark} {'run-inputs':<20} {detail}"`, the form the database lines use. The line never raises: an exception becomes `UNKNOWN`, as `SearxngCommands.doctor_line` does.

Lines, pinned:
- `OK` with `local store at <path> (from <config file>)`, adding `; made on the first add` when the folder does not exist yet but its parent is writable.
- `FAIL` when the local folder is not writable, or a symlink is where the folder should be.
- `OK` with `seaweedfs store <describe()> (from <config file>): reachable; credentials from <ACCESS_VAR>, <SECRET_VAR>`, from a one-key ListObjectsV2 under the prefix.
- `FAIL` with `... : not reachable (<exception class>)`, `... : <VAR> is not set`, `... : refused the credentials in <ACCESS_VAR>, <SECRET_VAR>`, or `... : bucket <b> does not exist`.
- `UNKNOWN` with `could not read your own vibey.toml`.

Doctor is a person's explicit act, so its single network probe is not a run fetching on its own.

- [ ] **Step 1: Write the failing tests.**
  - One test for each pinned line, using fake stores and `httpx.MockTransport`.
  - `test_doctor_never_prints_a_credential_value`: both variables are set to sentinels, and neither appears in any line.
  - `test_the_line_names_the_config_file_it_read`
  - `test_an_exception_in_the_probe_is_unknown_never_a_crash`
  - `test_the_section_is_in_doctor_and_in_the_editor_probes`
- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** `uv run pytest tests/cli -q` and `uv run coverage report --include='src/vibey/cli/*' --fail-under=100`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(doctor): say which run input store is in force and whether it answers`.

### Task 7: A handed-off run sees its inputs, and the no-loss gate still passes

Today, a wind-down follow-up's prompt is the seed alone, byte for byte (`build_implement_handler.py`, the two `seed` checks around the skills context and the input section). The inputs reach that run only as files.

**How the inputs enter the prompt.** The seed is `render_seed_prompt(brief)` of a brief that `domain/noloss.verify` passed. It stays a **byte-exact prefix** of the incoming run's prompt. The input section follows it after `"\n\n"`. It is the same fenced data section a fresh run gets, built from the digests the outgoing run was **given**, not from the store as it stands now.

**Why the section does not go inside the brief.** That alternative was considered and rejected:
- The brief's fields are instructions to the next engine, and pasted text is data (Decision 3).
- R10's denylist (`sudo`, `ignore previous instructions`, and so on) would park valid handoffs whose pasted logs merely contain those words.
- It would change the brief's shape.

**What the gate checks.** `verify` keeps its ten rules unchanged:
- R1 to R5: remaining work, questions, decisions, assumptions and findings carried by id.
- R6: the ledger range's digest.
- R7: artifacts referenced by an open item.
- R8: the budget equals the ledger's sums.
- R9: the spec's hard constraints.
- R10: containment.

The input events in the range (`vibey_run_input` and `vibey_run_inputs_given` are `ArtifactProduced` without `referenced_by_open_item`) trip none of them. A new test pins that.

The inputs are enforced beside the gate, with the gate's own routing, in two places:
- The wind-down pins the outgoing job's latest given event into the follow-up's payload.
- The incoming handler refuses to start an engine unless the digests it gave equal the pin. A pinned input that is missing parks the job for a person (`handoff_inputs_missing`). A store that cannot be reached is a retry (`Failure(VIBEY)`).

Neither case is ever a silent partial. Making the pin gate rule R11 is OR-5.

**Files:**
- Modify: `src/vibey/domain/run_input.py`. `GIVEN_ARTIFACT_TYPE` moves here from the service, which re-exports it. Add `HANDOFF_INPUTS_KEY: Final = "handoff_input_digests"`.
- Create: `src/vibey/domain/handoff_inputs.py`, `src/vibey/domain/interfaces/handoff_inputs_interface.py`
- Modify: `src/vibey/application/wind_down.py`, `src/vibey/application/build_implement_handler.py`, `src/vibey/application/run_inputs_service.py`, `src/vibey/application/interfaces/run_inputs_interface.py`, `src/vibey/application/dto.py`, `src/vibey/domain/errors.py`
- Modify: `src/vibey/cli/gate_answers.py`, adding `"handoff_inputs_missing": FREE_FORM` beside `handoff_gate_failed`.
- Modify: `docs/plans/handoff-protocol.md` §4.1 (what the incoming prompt holds).
- Test: `tests/domain/test_handoff_inputs.py`, `tests/domain/test_noloss.py`, `tests/application/test_wind_down.py`, `tests/application/test_build_implement_inputs.py`, `tests/application/test_wind_down_inputs_roundtrip.py`

**Interfaces:**
- `class HandoffInputs` with `pinned(self, events: Sequence[LedgerEvent], job_id: UUID) -> tuple[str, ...] | None`. It returns the `digests` of the latest event, by `seq`, that is an `ArtifactProduced` with `artifact_type == GIVEN_ARTIFACT_TYPE` and `job_id == job_id`; `None` when there is none. A digest that is not lowercase 64-hex raises `ValueError`. Module instance: `HANDOFF_INPUTS: HandoffInputsInterface`.
- `RunInputsInterface.materialize(project_id, run_id, worktree_path, *, job_id=None, pinned: Sequence[str] | None = None) -> RunInputs`. With `pinned`, it gives exactly those digests, in that order. Each digest resolves to its latest index row for the name. `max_items`, `max_item_bytes` and `max_project_bytes` are not applied again, because withholding now would drop what the outgoing engine had. `max_prompt_bytes` still decides what is inlined; anything not inlined stays in `paste.md`, so nothing is lost.
- `RunInputs.digests: tuple[str, ...]` holds what the run was given, the same list its given event records.
- `HandoffInputsMissing(VibeyError)` takes the next free error code (E0097 if nothing lands first). It is raised when a pinned digest has no row or object.
- Payload: the wind-down's follow-up carries `HANDOFF_INPUTS_KEY: list[str]`, which is `[]` when the outgoing run was given nothing. A payload without the key comes from a job enqueued before this change. It keeps today's behaviour, with the prompt exactly equal to the seed.

- [ ] **Step 1: Write the failing tests.**
  - Domain:
    - `test_the_latest_given_event_of_the_job_is_the_pin`: events at seq 5 and seq 9 for one job give seq 9's digests.
    - `test_another_jobs_given_event_is_never_the_pin`
    - `test_no_given_event_is_no_pin`: returns `None`.
    - `test_a_given_event_with_a_digest_that_is_not_hex_is_refused`
  - `test_noloss.py::test_input_events_in_the_range_never_trip_a_rule`: a range of add and given events with the deterministic brief gives `verify(...).ok is True` under STRICT, and `rules_run == tuple(GateRule)`.
  - Wind-down:
    - `test_the_follow_up_payload_pins_the_inputs_the_outgoing_run_was_given`: `payload["handoff_input_digests"] == [d_paste, d_file]`.
    - `test_a_run_given_no_inputs_pins_an_empty_list`
    - `test_the_seed_prompt_bytes_are_unchanged_by_the_pin`: `payload["seed_prompt"] == render_seed_prompt(brief)`.
  - Handler:
    - `test_a_wind_down_seed_is_the_byte_exact_prefix_and_the_pinned_section_follows`. This replaces `test_a_wind_down_seed_reaches_the_engine_verbatim_and_the_files_are_still_there`. It asserts `prompt.startswith(seed)` and `prompt[len(seed):] == "\n\n" + section`, where `section` is the section a fresh run with the same inputs gets.
    - `test_a_legacy_seed_payload_without_a_pin_reaches_the_engine_byte_for_byte`: `prompt == seed`.
    - `test_an_empty_pin_gives_the_seed_byte_for_byte`
    - `test_an_input_added_after_the_handoff_is_not_given_to_the_incoming_run`: `given.digests == tuple(pin)`.
    - `test_limits_lowered_after_the_handoff_do_not_withhold_a_pinned_input`
    - `test_a_pinned_input_missing_from_the_store_parks_the_job_for_a_person`: `Park`, kind `handoff_inputs_missing`, and `engine.start` never called.
    - `test_an_unreachable_store_on_a_handed_off_run_is_a_retry_not_a_park`: `Failure(VIBEY)`, engine not started.
  - Round trip: `test_a_handed_off_run_sees_the_same_input_section_as_the_run_it_replaces`. An outgoing run is given inputs, winds down and is followed up; the incoming section equals the outgoing one.
- [ ] **Step 2: Run them.** `uv run pytest tests/domain tests/application -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** In `WindDownOrchestrator.execute`, compute `HANDOFF_INPUTS.pinned(events, job.id) or ()` and put it in the payload. A `ValueError` parks the job as `handoff_gate_failed` does. In the handler:
  - When the payload has a seed and a pin, call `materialize(..., pinned=pin)`.
  - Map `HandoffInputsMissing` to `Park(HumanGateRequest(kind="handoff_inputs_missing", ...))` and `InputStoreError` to `Failure(VIBEY)`.
  - Check `given.digests == tuple(pin)` (a mismatch also parks), then set `prompt = seed + ("\n\n" + section if section else "")`.

  Leave `render_seed_prompt` and `verify` untouched.
- [ ] **Step 4: Run** `uv run pytest tests/domain tests/application -q`, the `noloss` property suite at 10,000 examples as CI runs it, and the layer floors. Expected: PASS.
- [ ] **Step 5: Commit** `feat(handoff): a handed-off run is given the inputs its predecessor had`.

### Task 8: Documentation

**Files:**
- Modify: `docs/reference/configuration.md`: `[inputs]` gains `store`, `store_dir`, `endpoint`, `bucket`, `prefix`, `region`, `access_key_env`, `secret_key_env` and `timeout_seconds`. If Phase 3 Task 8 has not landed, fold in its `[inputs]` limits.
- Modify: `docs/reference/cli.md` (exit 69 for `vibey inputs`, and the `run-inputs` doctor line); `.importlinter` if the new modules need a contract line.

- [ ] **Step 1:** Extend the cli-doc meta test: the `run-inputs` doctor section and exit 69 appear in `docs/reference/cli.md`. Expected: FAIL.
- [ ] **Step 2:** Write the docs. Run `uv run pytest tests/meta -q`, `uv run lint-imports`, and the strict docs build. Expected: PASS.
- [ ] **Step 3: Commit** `docs(inputs): the store keys, the doctor line, and inputs across a handoff`.

## Verification (the phase is done when all of these hold)

- `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=` passes, and the four layer floors are 100% with an empty Missing column. The gh tenant's suite passes, and so does `tools-lint` (black, isort, mypy).
- `uv run mypy --strict src/vibey`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`, `uv run bandit -q -r src/vibey` and `uv run vibey-gh marketplace --check` are all clean.
- Operator-run checks, each marked unverified until it has been run:
  1. Install the built wheel in a clean venv. The marketplace its shipped lock records lists 157 plugins.
  2. Against a real SeaweedFS (`weed server -s3` with an identity): `vibey doctor` shows `OK run-inputs seaweedfs ... reachable`. Then `vibey inputs add <project> --file ./spec.md`, start a BUILD job, and confirm `.vibey/inputs/<run>/attachments/spec.md` exists.
  3. Force a wind-down on that job. The follow-up's `.vibey/plans/<run>.md` starts with the seed and ends with the same input section.

## Self-review

1. **Decision coverage:**
   - D3: Task 0.
   - D2: Tasks 1 to 6. The configurable location is Task 2, the S3 backend Task 4, the shared composition Task 5, and doctor Task 6.
   - D1: Task 7.
   - The N7 open item: Task 5's cross-check and Task 6's line, as set out in the section on the open item.
2. **Interfaces match across tasks.** `InputStoreLocation` (Task 2) feeds `S3RequestSigner` (Task 3), which feeds `SeaweedFsInputStore` and `StoreProbe` (Task 4). From there, `run_inputs_store` and `RunInputLedgerInterface.added` (Task 5) feed `RunInputsDoctor` (Task 6). `HANDOFF_INPUTS`, `materialize(pinned=)`, `RunInputs.digests` and `HandoffInputsMissing` (Task 7) build on Task 5's service.
3. **Blocked on rulings.** Merging the `"seaweedfs"` value (Tasks 2 and 4 to 6) waits for OR-1 and OR-2. The 8.b canon draft waits for OR-2. Task 0's manifest name waits for OR-4. R11 is OR-5. Tasks 0, 3, 5 (the cross-check) and 7 are independent of OR-1 to OR-3.
4. **Not verified while writing this plan:**
   - SeaweedFS's S3 gateway behaviour: SigV4 identities, ListObjectsV2 continuation, path-style addressing.
   - The filer's authentication model.
   - Whether hatchling accepts two force-include sources into one target folder.
   - That nothing else lands error codes E0096 and E0097 first.
5. **Out of scope and recorded:** `[files]` (`password`) and `[blob]` (`secret_key`) still accept credentials in `vibey.toml`, which contradicts the rule D2 states. That is a follow-up, not this phase's change.
