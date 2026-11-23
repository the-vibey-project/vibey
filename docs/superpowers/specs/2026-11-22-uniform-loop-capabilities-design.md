# Uniform loop capabilities: every loop gets MCP, plugins, marketplaces, skills, files, pasted text, text, local search and the research methodologies

**Status:** proposed, awaiting the operator's approval. **Date:** 2026-11-22. **Related:** ADR-0092 and issue #1666 (every lane gets full access), ADR-0034 (one marketplace at the root), ADR-0064 (the local runner's two engines), ADR-0100 and ADR-0101 (MCP and ACP), ADR-0102 (local-first search and the hub's web tools), sub-doctrine SD-01.

## Intent and why

A BUILD job can fall to any loop (`claudeloop`, `claudeloop-local`, `codexloop`, `gptossloop`, `qwenloop`): the rotation prefers local engines and falls back to paid ones, and a handoff moves a job between them. Today the loops differ widely in what they can take and use, so a job that works on one can stall on another. The operator's rule: **every loop supports MCP servers, plugins, marketplaces, skills, files, pasted text and plain text, plus the local SearXNG search and the vibey research-methodology skills.** vibey provides one shared layer, not each tool's native behaviour.

## What is true today (read from the code, 2026-11-22)

| | MCP | Plugins | Marketplaces | Skills | Files | Pasted text | Text |
|---|---|---|---|---|---|---|---|
| `claudeloop`, `claudeloop-local` | yes, run-scoped connectors; transport type not explicit | local directories only (the "marketplace name" branch is dead code) | no | names passed to the SDK; discovery unknown | `--attach` copies files that probably never reach the agent; `--add-folder` does | no (plan file only) | yes |
| `codexloop` | no code (descriptor claims yes: a contradiction to resolve) | no | no | no | `--add-dir` from config only | no | yes |
| `gptossloop`, `qwenloop` | stdio only; one subprocess per call; no per-tool schemas | no (commands echo) | no | plan text only | worktree tools | yes | yes |

vibey itself models these as per-engine flags (`EngineAffordances`) and passes none of them except `--web-search` to claudeloop. The `docs/reference/cli.md` capability table is stale against the descriptors. The only MCP client in the family is the local runner's. `claudeloop` and `codexloop` use their tools' own web search, which vibey cannot point at SearXNG. Engine sessions have no channel to the hub, so they cannot use the hub's web tools or the Brave backup.

## Goals

1. **One declarative bundle**, in the person's own configuration, says what every loop gets: marketplaces (name, source, pinned ref), plugins (`name@marketplace`), MCP servers (stdio or HTTP, with a trust level), skills, the research defaults and the search channel. The root `vibey` marketplace (157 plugins) is the default source.
2. **A resolver in the conductor** turns the bundle into a locked, run-scoped snapshot: marketplaces fetched and pinned only on an explicit person action, plugins checked out from the snapshot, a skills index built, a run-scoped MCP configuration written. The snapshot's digest is recorded per run in the ledger. A run never fetches anything from the network on its own.
3. **Each loop applies the snapshot in the way its engine can**, and reports what it applied (evidence, not a claim):
   - `claudeloop` / `claudeloop-local`: plugins as local directories from the snapshot, MCP connectors with an explicit transport type, skills by name from the snapshot, a fixed `setting_sources`, attachments and the paste file added to the agent's folders.
   - `codexloop`: MCP servers and skills through the mechanisms the real Codex supports. Those are not verified from this repo, so this loop is last and needs an operator-run check against a real Codex before any capability is claimed.
   - `gptossloop` / `qwenloop`: a stronger MCP client (HTTP, schemas retrieved on demand within a token budget, a persistent session), on-demand skill tools over the snapshot, and plugin skills and commands as retrievable text. No plugin hooks or agents (no runtime exists for them).
4. **Pasted text and files are first-class inputs for every loop.** The conductor writes one normalised input set per run (the plan, an attachments folder, a paste file) and each loop reads it the same way.
5. **Search for every loop** goes through the hub's `vibey_search` and `vibey_fetch` (local SearXNG first, Brave only a backup). Engine sessions get a per-session principal that holds only the `web` scope, with its own budget, minted by the worker. Sessions then no longer receive the SearXNG address or marker, and never a Brave key.
6. **The research methodologies are on by default**: the vibey research-methodology skills (the `currency-research` plugin: research-search-and-source-quality, research-currency-audit-method, research-editing-a-reference-skill) are in the default bundle for every loop that does research work.
7. **Descriptors tell the truth**: each capability a descriptor claims is backed by evidence from a conformance probe of that loop. `full_access_gaps()` is empty for every loop except a gap a loop truly cannot close, which is declared (see Decisions 7), and the golden tests and the stale `cli.md` table are corrected.

## Non-goals

- Running Claude Code plugin hooks or agents in non-Claude loops. Skills, commands (as retrievable text) and MCP servers are in; hooks and agents are not.
- MCP OAuth, images and pasted images, new marketplaces beyond what the person adds, changes to the upstream tools (Claude Code, Codex).
- Moving the BUILD queue, handoff or rotation logic.

## Anti-goals (what would make this a failure even if it works)

- A repository choosing what a loop loads. The project's `vibey.toml` is untrusted: marketplaces, plugins and MCP servers come only from the person's own configuration, and a project may only narrow.
- A capability claim without evidence, or a descriptor that disagrees with its runner.
- A loop receiving the host token, the agent token or the Brave key.
- A silent network fetch during a run. Marketplace fetches happen only on an explicit `vibey loops ...` command, and runs use the lock.
- Plugin or skill text, or MCP output, treated as instructions. It is data, bounded and marked untrusted. A 32k-token model's context must stay usable.

## Constraints

- The trust model of ADR-0101 and the Task 8 settings loader (the person's own configuration grants; a project only narrows).
- Shared code lives in `vibey_runners.common` (stdlib only, imported by the runners, and shipped in the one `vibey` wheel). The runners do not import `vibey`. The JSON-RPC peer is copied or moved down into `common` if an MCP client needs it.
- Every tenant keeps its own layers, one class per file with an interface beside it, 100% branch coverage, and tests that do not depend on thread timing or the platform. Every new capability gets a real-run check, and checks that need a real service manager, container or Codex are written for the operator to run and are marked unverified until they have been.
- The sovereign default stays first: `gptossloop` gets the new capabilities in the same release as the paid loops, not after.

## Approaches considered

- **A. One shared vibey layer (chosen).** One bundle, one resolver, one snapshot, per-loop adapters. Most work, but behaviour, trust and tests are uniform, and a job can move between loops without surprises.
- **B. Native behaviour per tool.** vibey only configures what Claude Code and Codex already do and builds real support only for the local runner. Less work, but behaviour differs per loop and Codex's native support is unverified. Rejected.
- **C. MCP-only: a vibey capabilities MCP server that every loop mounts.** One integration surface, small per-loop code. Rejected as the only mechanism, because it cannot give `claudeloop` real plugin and marketplace semantics. It is kept as the delivery channel for the pieces a loop cannot do natively (search, fetch and on-demand skills for the local runner).

The operator chose A on 2026-11-22.

## Order of work (each its own pull request)

1. **Evidence first:** conformance probes, the corrected `cli.md` table, descriptors brought in line with the runners, `vibey loops` emitting `skills` and `web_search`.
2. **The shared library and the conductor commands:** the bundle schema, manifest parsing for marketplaces, plugins and skills, the lock file and `vibey loops marketplace | plugin | mcp | skills`.
3. **The input set** (plan, attachments, paste) for every loop.
4. **`claudeloop` and `claudeloop-local`:** plugins, explicit MCP, skills, `setting_sources`, attachments.
5. **The local runner:** the MCP client upgrade, skill tools, plugin skills.
6. **Per-session web principal and hub-served search** for every loop; sessions stop receiving the SearXNG address and marker.
7. **The research bundle by default.**
8. **`codexloop`**, after an operator-run verification of what the real Codex supports.

## Left to the builder

The bundle's schema and file names, the lock file format, exact flags and command names, the snapshot's directory layout, token budgets, and how each probe is run.

## Decisions I made while designing (my calls: please check them)

A fresh reviewer read this design as the builder and asked ten questions. These are the answers, with the reason for each. Items 1 to 4 follow from rulings you already made; items 5 to 10 are my calls.

1. **The default marketplace is the copy that ships in the installed wheel, locked automatically at first use.** No download is needed, so a fresh install gets the research skills at once. Its content hash goes in the lock. A marketplace that comes from the network is added, fetched and pinned only by an explicit `vibey loops marketplace add` and `update`. A run with no lock for a person-added marketplace refuses to start and says what to run.
2. **Search for every loop uses the local SearXNG only; the paid loops' built-in web tools are switched off.** You ruled that all search uses the local SearXNG with Brave only a backup, so `claudeloop` has `WebSearch` and `WebFetch` disallowed and `codexloop`'s own search is disabled once that is verified. They use `vibey_search` and `vibey_fetch` instead. This removes a built-in capability from the paid loops on purpose.
3. **Plugin, skill and MCP text from the locked bundle is instruction; everything else is data.** The person chose the bundle and its hash is pinned, like their own `CLAUDE.md`. MCP output, fetched pages, search results and project files stay untrusted data, bounded and marked.
4. **`claudeloop` loads no settings sources** (`setting_sources=[]`). The repo's hooks, `.mcp.json`, permissions and `.claude/` plugins and your `~/.claude` plugins and servers therefore never load outside the lock. vibey injects the repo's `CLAUDE.md` and `AGENTS.md` as plain instruction text, which BUILD already does for house rules. This keeps the repo from choosing capabilities, while BUILD still gets the repo's instructions.
5. **v1 is one machine.** The worker, the hub, the snapshot, the lock and the inputs are on the same disk. A cluster worker without a hub runs without search, says so, and does not try to start a hub (the ACP bootstrap, not the worker, starts services). Cluster workers are a later design.
6. **Pasted text and files:** v1 intake surfaces are the CLI and ACP embedded resources. They are written by the conductor into a hash-addressed inputs folder under the project's state, not into Postgres, with size limits. The ledger records their digests. A hub route and the krypton apps come later. Inputs do not follow a job to another machine in v1.
7. **A loop that cannot support a capability declares the gap, and rotation honours it.** A job that requires a capability is not routed to a loop that lacks it, and a vibey MCP channel stands in where it can. The release does not wait for the operator's Codex check: `codexloop` keeps its declared gaps until verified.
8. **"Plugins" for the local runner:** a new plugin-system value, `VIBEY_BUNDLE`, means skills, commands (as retrievable text) and MCP servers from the locked snapshot, with no hooks or agents. `full_access_gaps()` counts it as granting plugins. ADR-0092's definition is amended to say so. Hooks and agents are excluded from #1666 for every non-Claude loop.
9. **MCP trust levels are two:** `local` (a stdio server the person configured, run with a scrubbed environment) and `remote` (HTTP: its own egress, a per-session call budget, an output size cap). Output is always data. The level decides egress, budget and which sessions mount it; it never makes output instruction.
10. **The research skills are always available, but only their names and descriptions are loaded up front** (a few hundred tokens). Bodies are fetched on demand, and the DESIGN and REVIEW phases list them as required skills. This keeps a 32k-token model's context usable.

Still to be verified by the operator, not by this design: what the real Codex supports for MCP and skills, the SearXNG container and unit behaviour from the earlier series, and that a plugin from the root marketplace behaves the same through each loop in a real run.
