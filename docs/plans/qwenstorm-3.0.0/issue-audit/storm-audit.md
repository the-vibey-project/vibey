# QwenStorm 3.0.0 — audit of the 65 open `qwenstorm` issues (INTERIM)

Checked against: the canon at integration `cce648ef` (#392 ratified); code at integration `739536ea`
(#387 was integrated while this audit ran). GitHub was only read, never edited.

**Status of this file: interim.** The rows marked *pending* belong to four parallel audit agents that
were still running when the report was handed back:
- the forge agents (#332–#344);
- the deploy/visual agent (#324, #326, #327, #330, #331);
- the R01–R18 agent (#348–#365);
- the R19–R34 agent (#366–#381).

They write their replacement bodies into `updates/`. Each finished file's first line records its
status, so run `head -1 updates/3*.md` to finish this table.

The `updates/` directory is shared with a separate audit of non-qwenstorm issues (114, 121, 133, 134,
136, 138, 145, 298, and `gaps.md`). Those files are not part of this audit.

| issue | title | status | reason | update file |
|---|---|---|---|---|
| 321 | feat(engines)!: each project's engine pool follows ratified sub-doctrine 8.b | STALE | Makes the repealed `opencode` always on (pool, doctor, preflight, tests; `config.py:21`, `:406-409`). 8.b as ratified by #392 keeps only sovereignloop/qwenloop always on. Cites #319 | updates/321.md |
| 322 | feat(cli)!: DESIGN and DECOMPOSE default to the sovereign qwenloop provider | DONE-IN-STORM | `4e57f56b`. Still lists `opencode` as a provider; ADR-0046 L38 must refuse it later | — |
| 323 | fix(surfaces): apply the surface environment overlay when no vibey.toml exists | STALE | `parse_config` of an empty document raises `ConfigError("project.name")` (`config.py:367-370`). Its tests need `build_app`, whose only seam is a patched `asyncpg.create_pool` (9.b) | updates/323.md |
| 324 | feat(visual): sovereign QwenloopVisualProvider … | *pending* (deploy/visual agent) | | |
| 326 | feat(deploy)!: run the kopf operator by default … | *pending* | | |
| 327 | feat(deploy)!: the forge surface runs Forgejo … | *pending* | | |
| 330 | feat(deploy)!: the deployment scope's provider follows [deploy].target | *pending* (note: `config.deploy.target` defaults to `"azure"`, `tests/domain/test_config.py:107`; 8.b says OpenStack, with AWS as the paid default) | | |
| 331 | feat(openstack)!: a real OpenStack CLI client … | *pending* | | |
| 332 | feat(gh): forge-adapter foundation … | TOO-BIG | 11 production files, about 7 behaviours; its timeout test monkeypatches `urllib.request.urlopen` (9.b) | updates/332.md |
| 333 | feat(gh): the forge adapter reads a change request's facts … | TOO-BIG | 9 production files; also THIN: the V5–V10 signatures exist only in `specs/forge-adapter.md` | updates/333.md |
| 334–344 | forge-0c … forge-6 | *pending* (forge agents) | | |
| 345 | fix(qwenloop): a model request waits idle_timeout_seconds | DONE-IN-STORM | `c24b4f7b` | — |
| 346 | feat(qwenloop): an edit_file tool … | DONE-IN-STORM | `610f3cfa` | — |
| 348–365 | R01–R18 | *pending* (R01–R18 agent). Expected: #348 STALE (`[loop_services.<engine_id>]`, per ADR-0046's migration table); SQL-adding lanes STALE under the ORM rule | | |
| 366 | feat(domain): the loop-service wire protocol (R19) | SUPERSEDED | ADR-0046 §3/§10 `domain/run_protocol.py` ("replaces R19") | updates/366.md (closing comment) |
| 367 | refactor(engines): extract the run-directory tailer … (R20) | *pending*. Kept by ADR-0046; likely STALE (it deliberately preserves module-attribute monkeypatching) | | |
| 368 | R21 local run executor | SUPERSEDED | ADR-0046 seat host, `local_run_executor.py` + `result_store.py` | updates/368.md |
| 369 | R22 loop-service host | SUPERSEDED | ADR-0046 §3 router + per-model seat host, §6 worktree fence (rule 3g cannot supersede at prefetch 1) | updates/369.md |
| 370 | R23 control, probes, dead letters | SUPERSEDED | ADR-0046 `control.py`, loop-keyed | updates/370.md |
| 371 | R24 client | SUPERSEDED | ADR-0046 `client.py` (route, then run) | updates/371.md |
| 372 | R25 LoopServiceAdapter | SUPERSEDED | ADR-0046 `adapter.py` + `LoopSelector`/`LoopRoutingPort` | updates/372.md |
| 373 | R26 DESIGN/DECOMPOSE via loop service | SUPERSEDED | ADR-0046 pinned runs + `command_executor.py`; also pins opencodeloop | updates/373.md |
| 374 | R27 `vibey loop-service --engine` CLI | SUPERSEDED | ADR-0046 `--loop` / `loop submit`; `--engine` means one service per engine, which 8.c forbids | updates/374.md |
| 375 | R28 invocation selection | SUPERSEDED | ADR-0046 §2 subprocess kept + `adapter_factory.py` | updates/375.md |
| 376–381 | R29–R34 | *pending* (R19–R34 agent). Expected: R30 STALE (ADR-0046 §11); R33 STALE (installer wave `installer-broker-cache` + two-loop doctor); R34 STALE | | |
| 382 | feat(qwenloop): record per-turn timing … | DONE-IN-STORM | `d76c2e20` | — |
| 383 | feat(models): support Qwen3.8-27B … RAM-tiered defaults | TOO-BIG | 5 models × 2 backends, pinning, probe, tiers, parsers, verify and doctor. Also STALE: the tier table picks non-GPT-OSS defaults on 48–128 GB, against 8.d; cites 8.c "per deployment" | updates/383.md (6 child lanes) |
| 386 | fix(qwenloop): retry a turn when the server cannot parse the model's tool call | DONE-IN-STORM | `cb1aa6af` | — |
| 387 | feat(models)!: GPT-OSS 20B on Ollama is the default local model | DONE-IN-STORM | `ddf2bf05` / `739536ea`, integrated during this audit | — |
| 388 | feat(qwenloop)!: … attaches to a running local Ollama | STALE | 8.c cited as "per deployment"; the probe has no declared seam or switch, so the tenant suite would reach a live Ollama or need patching. Its lane is running now | updates/388.md |
| 389 | feat(gh)!: vibey-gh's local reviewer and fit default to gpt-oss:20b | THIN | Never re-renders the managed workflows that embed the model (root `pr-review.yml:345,363,1408`; tenant `pr-review.yml`, `issue-automation.yml:611`), so its own drift check fails | updates/389.md |
| 391 | feat(install): vibey install sets up local Ollama … | TOO-BIG | install + service + pull + flags + default + doctor in one lane. Also STALE: a bespoke `OllamaLocalService`, no pacman/Arch (8.h). Replaced by `specs/installer-ollama.md` + the installer wave | updates/391.md (9 child lanes) |
| 393 | fix(gh): a staged bump is raised when the range later owes a higher level | CURRENT | Accurate against `versioning.py:212-245`. Already implemented on `fix/staged-bump-raised` (`09c449ab`, pushed); PR pending. Its template lacks Where/Checks, which no longer matters | — |

## Cross-cutting problems (found so far)
1. **OpenCode repeal vs ADR-0046.** Ratified 8.b (`doctrines.md:133-135`) repeals OpenCode. #321 and
   `config.py:21`/`:406-409` still make `opencode` always on. Draft ADR-0046 §9 keeps it in the
   defaults until its lane L38. The canon outranks the draft, and ADR-0046 needs a status note.
2. **8.d vs the operator's RAM tiers.** 8.d keeps `gpt-oss:20b` wherever it fits. #383's table makes
   other models the default on 48–128 GB, and puts custom-licence models (Gemma, Llama) ahead in lower
   tiers. This needs an operator decision.
3. **8.c's unit changed.** It is now one instance *per model*. #383, #388 and ADR-0044 text still say
   "per deployment", and all per-engine loop-service lanes (R19, R21–R28) are superseded.
4. **The fakes rule is violated by construction.** `build_app` can only be tested by patching
   `asyncpg.create_pool`, the qwen tenant's CLI tests monkeypatch module attributes, and forge tests
   patch `urlopen`. New lanes copy these patterns unless the spec names a seam.
5. **Rendered automation.** Model and config defaults are baked into managed workflows. Specs must say
   to re-render them with `install()`.
6. **Stale line numbers.** Specs written before #392 cite pre-#392 doctrine line numbers
   (installer-catalogue `:364`/`:200`, installer-host-runner `:258`, installer-container-runtime
   `:88-107`; now `:455`/`:236`/`:349`/`:99-118`).
7. **Stale template audience.** SPEC-TEMPLATE.md still targets `qwen3:14b` at 32k. The era's model is
   `gpt-oss:20b` at 131k.
8. **Code - OSS vs Microsoft's build.** installer-vscode installs Microsoft's VS Code cask on macOS,
   while ADR-0046 §8 requires Code - OSS (`codium`) for the sovereign `vscode` adapter.
9. **Deploy target default.** `config.deploy.target` still defaults to `"azure"`
   (`tests/domain/test_config.py:107`), against 8.b (OpenStack default, AWS the paid default).
