# SP-LOOPS Phase 6: per-session web principal and hub-served search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every loop (`claudeloop`, `claudeloop-local`, `gptossloop`, `qwenloop`) reaches `vibey_search` and `vibey_fetch` through the hub, under a web-only principal the worker mints for each engine session, and no engine session environment holds a SearXNG address or a Brave key.

**Architecture:** Today a local-runner session searches in-process: the worker overlays `WEBSEARCH_PROVIDER`, `WEBSEARCH_COMMAND` and the SearXNG address into every session, and `infrastructure/web/search.py` reads them there. Phase 6 moves the search to the hub, which already serves `vibey_search` and `vibey_fetch` to the agent principal with per-principal `[web]` budgets (ADR-0102). The worker mints a principal holding only `HubScope.WEB` for each engine session, writes its token to a 0600 file in the run's own folder, and revokes it when the session ends. Sessions call the hub with that token; the hub charges the session's own cap and the existing hourly bucket.

**Tech Stack:** Python 3.12+, typer CLI, the existing hub (Starlette routes in `infrastructure/hub/app.py`), pytest + Hypothesis, import-linter, 100% branch coverage per layer.

**Spec:** `docs/superpowers/specs/2026-11-22-uniform-loop-capabilities-design.md` (approved by the operator 2026-11-22), Goal 5 and Decision 5. Its "Decisions I made while designing" are binding; the rulings in this plan decide only what the spec leaves open.

**Scope of this document.** Eight tasks, each one PR-sized commit series within this phase's single PR, written in full now because Phase 5 has landed. Phases 7 and 8 stay as listed in the parent plan until they start.

## Global Constraints

- A session never receives the host token, the agent token, a SearXNG address (`VIBEY_SEARXNG_URL`, `WEBSEARCH_SEARXNG_URL`) or any Brave key (`VIBEY_BRAVE_API_KEY`, `WEBSEARCH_BRAVE_API_KEY`, `BRAVE_SEARCH_API_KEY`). `VIBEY_CREDENTIAL_ALIASES` and `MODEL_SESSION_FORBIDDEN` keep their current meaning.
- A session principal holds exactly `{HubScope.WEB}`. It is refused every other hub route, including `view`-only reads that the agent principal holds.
- A session token never enters the ledger, a log line, a prompt, a plan file or a `vibey loops` output. The ledger may record the principal's name and the budget outcome only.
- Only the worker mints session principals, and only under a run's own 0700 folder (the discipline Phase 4's snapshot folder already uses).
- The person's own `vibey.toml` decides `[web]` budgets; a project's file may only narrow them (ADR-0101 trust model).
- `domain/` stays pure (AST-enforced). Code lives in classes with an interface beside each (`services/interfaces/`). TypeScript, never JavaScript.
- 100% branch coverage per layer, verified with xdist and an empty Missing column. No test depends on thread timing, sleeps, the platform, the network, or a real container runtime. Clock is injected.
- Conventional Commits, each ending with a `Co-Authored-By:` trailer; `git commit` and `git push` in the foreground; never `--no-verify`. Pushes and test runs in a worktree use `VIBEY_TEST_TEMPLATE_DB=<a worktree-only name>`.

## Review Focus

Failure modes the spec implies that no task's happy path exercises, most likely first:

1. A session token presented to any hub route other than `web/search` and `web/fetch` is refused with 403, and a view-only route is not reachable through it. (Task 3)
2. A session token used after its session ended (revoked) or after its expiry is refused with 401, and a late call does not spend budget. (Tasks 2, 3)
3. Two concurrent sessions draw from their own session caps; one exhausting its cap does not refuse the other. (Task 3)
4. A worker with no hub mints no token, writes no token file, starts sessions, and tells the agent search is unavailable with a named reason. (Task 5)
5. A token file left behind by a crashed worker is removed by the worker's start-up sweep and is never readable by another run's folder. (Task 7)

## Rulings made for this phase

The spec leaves these open. Each is recorded in the ledger as `Ruling:` with its cost if wrong.

- **R1, delivery by file, not environment.** The session's token is written to `<run folder>/web-token` (0600 inside a 0700 folder) and the session's environment carries only `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE`. Cost if wrong: the model can read its own token, which is still scoped to `web`, capped and expires with the run.
- **R2, budgets: two checks, one spend.** A session search or fetch is charged against the session's own cap (`[web] session_searches`, `[web] session_fetches`, new keys with generic defaults) and against the agent principal's existing hourly bucket. Phase 6 cannot raise total web spend. Cost if wrong: a session can use the agent's whole hourly budget.
- **R3, claudeloop reaches the hub through an MCP connector in its snapshot, not through Bash.** The worker adds a `vibey mcp --scope web --token-file <path>` stdio connector to the run's MCP servers, typed `stdio` and started through the scrubbed launcher (Phase 4's `McpConfigTranslator`). Claude Code's own `WebSearch` and `WebFetch` stay disallowed. Cost if wrong: a Bash-based search would need a second path to test.
- **R4, lifetime.** A session principal expires at the engine run deadline plus the one-hour margin used by the sweep (`DEADLINE_MARGIN`), and is revoked when its session ends, whichever is first.

## Tasks

### Task 1: The session principal (domain)

**Files:**
- Create: `src/vibey/domain/session_principal.py`
- Create: `src/vibey/domain/interfaces/session_principal_interface.py`
- Test: `tests/domain/test_session_principal.py`

**Interfaces:**
- Consumes: `HubScope`, `REQUIRED_SCOPE` from `domain/hub_scope.py`.
- Produces: `SessionPrincipal(name: str, run_id: UUID, expires_at: float)` frozen; `scopes` is always `frozenset({HubScope.WEB})`; `SessionPrincipalPolicy.permits(principal, action: HubAction, now: float) -> bool`, true only for `WEB_SEARCH` and `WEB_FETCH` and only before `expires_at`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_session_principal_holds_only_web():
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert p.scopes == frozenset({HubScope.WEB})

def test_it_permits_only_the_two_web_actions_before_expiry():
    policy = SessionPrincipalPolicy()
    p = SessionPrincipal(name="session:abc", run_id=RUN, expires_at=100.0)
    assert policy.permits(p, HubAction.WEB_SEARCH, now=99.9)
    assert policy.permits(p, HubAction.WEB_FETCH, now=99.9)
    assert not policy.permits(p, HubAction.READ, now=0.0)
    assert not policy.permits(p, HubAction.WEB_SEARCH, now=100.0)  # expiry is exclusive
```

- [ ] **Step 2: Run them and see them fail** (`uv run pytest tests/domain/test_session_principal.py -q`; expected: ImportError).
- [ ] **Step 3: Implement** the two classes. The policy delegates the action check to `HubScopePolicy.permits` so the scope rule has one owner.
- [ ] **Step 4: Run them and see them pass**, then `uv run lint-imports` and the domain purity test.
- [ ] **Step 5: Commit** `feat(hub): a session principal that holds only the web scope`.

### Task 2: Minting, the token file and revocation (application and infrastructure)

**Files:**
- Create: `src/vibey/application/session_web_principals.py`, `src/vibey/application/interfaces/session_web_principals_interface.py`
- Create: `src/vibey/infrastructure/hub/session_token_store.py`, `src/vibey/infrastructure/hub/interfaces/session_token_store_interface.py`
- Test: `tests/application/test_session_web_principals.py`, `tests/infrastructure/hub/test_session_token_store.py`

**Interfaces:**
- Consumes: `SessionPrincipal` (Task 1); the run folder created by the engine adapter.
- Produces: `SessionWebPrincipals.mint(run_id, folder, now) -> SessionGrant` where `SessionGrant` holds the token file path, the principal name and `expires_at`; `SessionWebPrincipals.revoke(grant)`; `SessionTokenStoreInterface.write(folder, token) -> Path` (0600, in a 0700 folder, refused if the file already exists) and `read(path) -> str` for the hub's authenticator only.

- [ ] **Step 1: Write the failing tests**: mint writes a file whose mode is 0600 and whose folder is 0700 (`os.stat`, POSIX only, skipped on Windows); a second mint for the same run refuses; `revoke` deletes the file and makes the principal unknown to the registry; `mint` with an expired `now` refuses. Tokens come from an injected `TokenSource` returning fixed strings in tests (no real randomness).
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the store (`os.open` with `O_CREAT|O_EXCL`, mode 0o600), the registry (an in-memory map from token digest to `SessionPrincipal`, with expiry), and the service. The registry keeps digests, never tokens.
- [ ] **Step 4: Run and see them pass**, plus `mypy --strict src/vibey`.
- [ ] **Step 5: Commit** `feat(hub): mint a web-only principal per engine session, on a 0600 token file`.

### Task 3: The hub accepts session tokens for web only (infrastructure/hub and application/hub)

**Files:**
- Create: `src/vibey/infrastructure/hub/session_token_authenticator.py` (declared by `interfaces/session_token_authenticator_interface.py`)
- Modify: `src/vibey/cli/serve.py` (`known` list, next to `AgentTokenAuthenticator`, lines ~515–520)
- Modify: `src/vibey/application/hub/web_tools_service.py` (charge the session cap and the agent bucket; refuse with the budget named)
- Test: `tests/infrastructure/hub/test_session_token_authenticator.py`, extend `tests/application/hub/test_web_tools_service.py`

**Interfaces:**
- Consumes: `SessionWebPrincipals` (Task 2), `SessionPrincipalPolicy` (Task 1), `HubAuthenticatorInterface`.
- Produces: `SessionTokenAuthenticator.authenticate(token) -> Caller | None` for session tokens; `WebToolsService.search(caller, ...)` charges `caller.name` (the session) and the agent principal's bucket, in that order, and refuses if either is spent.

- [ ] **Step 1: Write the failing tests**
  - A session token gets `web_search` and `web_fetch` (200 path in an in-process app).
  - The same token gets 403 on `GET /v1/projects` and on `POST /v1/…/answer` (a view-only route and a write route).
  - An expired token gets 401; a revoked one gets 401; a late call does not change the usage counters (assert the counters).
  - Two session principals: exhausting A's `[web] session_searches` refuses A with the budget named and B still answers.
  - The agent bucket is charged once per session call (one spend, two checks: assert the agent counter increases by exactly one).
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.** `FirstOf([...])` order: local, device, agent, session. A session token is never matched by the agent authenticator, because its digest is in the session registry only.
- [ ] **Step 4: Run and see them pass**; `uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100` and the application floor.
- [ ] **Step 5: Commit** `feat(hub): session tokens reach web search and fetch and nothing else, charged twice`.

### Task 4: The session's own client: `vibey search` and `vibey fetch` through the hub (infrastructure/web)

**Files:**
- Modify: `src/vibey/infrastructure/web/session.py` (`COMMAND_VARIABLE`, the session-side settings), `src/vibey/infrastructure/web/search.py` (the in-session backend at the `WEBSEARCH_PROVIDER` branch, ~line 147), `src/vibey/infrastructure/web/page_fetcher.py` (session fetch)
- Modify: `src/vibey/cli/web.py` (`search_command`, line ~153): reads `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` when present, calls the hub; otherwise says so and exits with code 78 (not configured)
- Test: `tests/cli/test_web_session_client.py`, extend `tests/infrastructure/web/test_search.py` and `tests/infrastructure/web/test_page_fetcher.py`

**Interfaces:**
- Consumes: the hub routes `web/search` and `web/fetch` (Task 3).
- Produces: `SessionHubClient.search(query, limit) -> WebSearchAnswer` and `.fetch(url) -> FetchedPage` reading the token from the file on each call (never caching it in memory across a rotation). The answer keeps its existing shape (`backend`, `notice`, `hits`), so the qwen tool test fixtures need no change.

- [ ] **Step 1: Write the failing tests**: with the two variables set and a stub hub, `vibey search` prints the hub's answer; with the token file missing it exits 78 and names the file; with `WEBSEARCH_PROVIDER` set and no hub variables it does not search in-process at all (the in-session backend is no longer constructed for sessions).
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the client; delete the session branch of `search.py` that reads `VIBEY_SEARXNG_URL` and the Brave keys. The hub keeps its own backend (`local_first.py`, unchanged).
- [ ] **Step 4: Run and see them pass**; the qwen suite (`uv run pytest src/vibey_runners/qwen -q`) stays green because its tools call the same `vibey search` command.
- [ ] **Step 5: Commit** `feat(web): a session searches through the hub with its own token, never a local SearXNG`.

### Task 5: The worker overlay and the worker without a hub (infrastructure/engines, bootstrap)

**Files:**
- Modify: `src/vibey/infrastructure/engines/engine_environment.py` (`with_overlay`, `web_search_command`; the overlay names exactly `VIBEY_HUB_URL`, `VIBEY_WEB_TOKEN_FILE`, or `VIBEY_WEB_STATE=none`)
- Modify: `src/vibey/bootstrap.py` (where the worker builds its overlay; grep `WEBSEARCH_PROVIDER` on the branch to find it)
- Modify: `src/vibey/infrastructure/engines/loop_process_adapter.py` (`_render_plan` takes the web state, not a command)
- Test: `tests/infrastructure/engines/test_engine_environment.py`, `tests/infrastructure/engines/test_loop_process_adapter.py`

**Interfaces:**
- Consumes: `SessionWebPrincipals.mint` (Task 2); `None` when the worker has no hub.
- Produces: `WebState = Literal["hub", "none"]` in `domain/session_web_state.py` (Task 5 adds it), read by `_render_plan`.

- [ ] **Step 1: Write the failing tests**: with a hub, the session overlay contains `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` and no name that starts with `WEBSEARCH_` or contains `SEARXNG` or `BRAVE`; without a hub the overlay is `VIBEY_WEB_STATE=none`, no token file exists under the run folder, and the rendered plan says search is unavailable and why ("no hub is running; start one with `vibey serve`"), in fixed text.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement.** `with_overlay` keeps its contract (vibey's overlay bypasses the allow-list and a session's overlay wins), so the new names are added to the overlay only, never to any allow-list.
- [ ] **Step 4: Run and see them pass.**
- [ ] **Step 5: Commit** `feat(engines): sessions get the hub address and their token file, or say search is off`.

### Task 6: claudeloop reaches the hub through its snapshot (claudeloop, infrastructure/engines/descriptors)

**Files:**
- Modify: `src/vibey/infrastructure/engines/descriptors.py` (the claudeloop affordance at ~line 103, and the `web_search=True` affordance at ~line 370 that says "Stays until SP-LOOPS Phase 6"; both comments are removed, evidence text rewritten to name the connector)
- Modify: the worker's snapshot assembly (`src/vibey/application/loop_capabilities_service.py`, `prepare`, adds the `vibey mcp --scope web` connector to the run's MCP servers when a session token exists)
- Modify: `src/vibey_runners/claude/src/claudeloop/domain/capabilities.py` only if the connector needs a type that Phase 4 did not already allow (expected: none)
- Test: `tests/application/test_loop_capabilities_service.py`, `src/vibey_runners/claude/tests/test_mcp_config_translator.py`, `tests/infrastructure/engines/test_descriptors.py`

**Interfaces:**
- Consumes: `SessionGrant` (Task 2); the snapshot's `mcp_servers` (Phase 4).
- Produces: a `LoopCapabilitiesService.prepare(...)` that adds one connector, `vibey-web`, typed `stdio`, with `args=["mcp","--scope","web","--token-file",<path>]`, only when a session grant exists. `claudeloop`'s `web_search` affordance becomes `True` with evidence naming the connector and the disallowed built-in tools.

- [ ] **Step 1: Write the failing tests**: the snapshot for a run with a hub carries `vibey-web` as a stdio connector through the scrubbed launcher; without a hub it carries none; `CLAUDE_BUILTIN_WEB_TOOLS` (`WebSearch`, `WebFetch`) is still in the disallowed list; the descriptor's `web_search` evidence mentions `vibey-web`; `vibey loops` shows `web_search` as supported for claudeloop with that evidence.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the connector in the snapshot, not in the claudeloop runner, so the runner keeps importing nothing from `vibey` (the layer rule).
- [ ] **Step 4: Run and see them pass**, including the descriptor evidence tests added in Phase 1.
- [ ] **Step 5: Commit** `feat(claudeloop): the agent searches the hub through an MCP connector in its snapshot`.

### Task 7: Stale tokens, the start-up sweep and the environment walk (infrastructure/engines, tests)

**Files:**
- Modify: the worker start-up sweep (`src/vibey/cli/main.py`, the guarded block that sweeps snapshot folders; add the session token folders under the same run root)
- Create: `tests/meta/test_session_environment.py` (the environment walk)
- Test: `tests/infrastructure/engines/test_session_token_sweep.py`

**Interfaces:**
- Consumes: the run folder layout (Phase 4) and `SessionWebPrincipals.revoke` (Task 2).
- Produces: the sweep removes a run folder's `web-token` and the folder once the run is older than the run deadline plus `DEADLINE_MARGIN`; the environment walk builds every engine's session environment with a fake SearXNG address, fake Brave keys, the host token and the agent token present in the worker's environment, and asserts none of them, and no `WEBSEARCH_` name, reaches any session.

- [ ] **Step 1: Write the failing tests**: an old run folder with a `web-token` is removed with it; a folder younger than the deadline keeps its token; the environment walk fails when any one of the forbidden names is present, for each of the four engines (parametrised over the engine descriptors, so a fifth engine is walked automatically).
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement** the sweep reuse and the walk. The walk is the parent plan's acceptance test: "no session environment holds a SearXNG address or any Brave key."
- [ ] **Step 4: Run and see them pass**; run the sweep twice (idempotent under replay, the ledger rule).
- [ ] **Step 5: Commit** `test(loops): no session environment holds a SearXNG address or a Brave key`.

### Task 8: Records, skills and the decision (docs, ADR, skill trees)

**Files:**
- Create: a new ADR in `docs/architecture/decisions/` (number taken at merge, the next free one) recording R1 to R4 and the rule that a session holds only `web`.
- Modify: `docs/reference/cli.md` (`vibey search`, `vibey fetch`: the two session variables and exit 78), `docs/reference/configuration.md` (`[web] session_searches`, `session_fetches`).
- Modify: `src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver/SKILL.md` and its copies in the Claude, Cursor, Codex and Antigravity trees (agent-surface rule in CLAUDE.md), only if the search wording changes.
- Test: the existing doc meta-tests (`uv run vibey-gh corpus-index --check`, docs strict build) and `tests/meta/test_cli_reference.py` if one exists.

- [ ] **Step 1: Write the failing check**: the corpus index check and the CLI reference test fail on the new flags until the docs name them.
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Write** the ADR, the reference lines and the skill text.
- [ ] **Step 4: Run the doc checks and see them pass.**
- [ ] **Step 5: Commit** `docs(loops): record the session web principal and the search flags`.

## Verification

- Per task: the tests named above, then `uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src/vibey`.
- Phase gate, as in `CLAUDE.md`: `uv run lint-imports`, `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch`, the four 100% floors, `uv run bandit -q -r src/vibey`, `uv run pip-audit --skip-editable`, the qwenloop and claudeloop suites, and the `vibey-gh` suite.
- Acceptance (parent plan): `tests/meta/test_session_environment.py` walks each engine's child environment and passes.
- **Operator-run probe (not performed here):** start a hub, run one `qwenloop` session and one `claudeloop` session on a project that asks for a web search, and confirm each returns a hub answer with the backend named, and that the session environment in the run folder holds no SearXNG or Brave name.
