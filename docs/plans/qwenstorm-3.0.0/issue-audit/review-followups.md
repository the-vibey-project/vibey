# Follow-ups to apply before filing (2026-09-22)

1. [DONE 12:30 — `_comments` helper in split-332-2, reused by 333-2/333-3, routes updated] Forgejo comment endpoints do not page (checked against Codeberg's Forgejo API, 16.0.0-dev):
   `repos/{R}/issues/{index}/comments` and `repos/{R}/pulls/{index}/reviews/{id}/comments` take no
   page/limit. `_pages` stops only on an empty page, so it walks 100 identical pages there.
   split-336-* use a single request. CHECK AND FIX: split-332-2-adapter-paging (get_issue_thread),
   split-333-2-change-request-reads, split-333-3-change-request-text.
2. [DONE — queue already carries it] split-331-4-worker-cloud-flag adds `fakes-job-wakeup` to its Depends-on: reconcile with
   split-queue.txt (validator) before `file-suite.py queue`.
3. split-324-2-visual-cli reuses the patching `_quiet_worker` fixture (audit's instruction);
   the fakes-cli-operational lanes convert it. Check at batch review that no NEW patch mechanism
   was added.
4. The 15 `loops-*` slugs the split children reference must be mapped onto the loops writer's
   real slugs (ALIASES in file-suite.py) once specs/loops-queue.txt exists; likewise
   harness-T21-amqp-consumer-count onto the harness splitter's T21 slug.
5. [DONE — fakes-process-spawner item 0 + queue dep] tests/fakes/process.py is created by THREE lanes: split-367-2-process-launcher (spawner +
   executable-resolver seams, its own ProcessSpawnerInterface shape), fakes-process-executor and
   fakes-process-spawner (declares its own ProcessSpawnerInterface + adapter `spawner` field).
   Resolve: one owner of ProcessSpawnerInterface. Make fakes-process-spawner depend on
   split-367-2-process-launcher and EXTEND its interface/fake instead of declaring another
   (edit specs/fakes-process-spawner.md + fakes-queue.txt).
6. [DONE — fakes-cli-composition item 6 absorbs DoctorSeams + LocalStackFactory] split-380-2-doctor-cli puts a DoctorSeams object in ctx.obj, which fakes-cli-composition
   gives to CliComposition. Resolve: doctor seams become fields of CliComposition (make
   split-380-2 depend on fakes-cli-composition, or define DoctorSeams inside it).
7. split-380-1/-2 assume loops/T21 interface names (LoopId, SeatSlug.of, LoopQueueNames.seat,
   LoopServiceClient.probe, queue_depth, consumer_count, EngineAdapterFactoryInterface,
   LoopServicesConfig.loop(...).models, InvocationSettings.from_sources): check them against the
   loops-* and harness-T21 specs once written; each spec also starts with a grep preflight that
   stops the lane on a mismatch.
8. [DONE] All 51 split-* child specs exist and validate; the remaining "…" are legitimate
   elisions (quoted command lines, heredoc markers, `repos/{owner}/{repo}/…`).
9. [DONE — fakes-tenant-qwen-2 now owns it] Self-critique: my #388 conftest (qwen tenant, integrated e219f9a2) substitutes the Ollama probe
   with `monkeypatch.setattr` on the module attribute `qwenloop.cli.app._ollama_probe` — against
   9.b's "never by patching". fakes-tenant-qwen-1 must convert it to injection (a probe parameter
   on the composition); check its spec says so.
10. [DONE for split-334-*/335-*] Heredoc appends (`cat >> file <<'PY'`) cannot run: the lane's
    `shell` tool takes an argv list. Replaced with `edit_file` appends. BEFORE FILING: lint every
    spec about to be filed (all *-queue.txt slugs + updates/*.md) for `<<'PY'`/`<<EOF`, "as above",
    "see specs/", missing `## Checks` block — the roadmap-* design specs had heredocs when checked.
11. [DONE] fakes-test-harness's module renamed tests/fakes/harness_fakes.py (a `test_` prefix would
    be collected by pytest); also in gap-measure-test-runs.md.
12. Harness T21 slug is harness-T21-amqp-consumer-count (matches split-380-1). Loops slugs still
    to map (follow-up 4/7).
13. OPERATOR-SIDE (mine): after harness-T20 (qwenloop shell timeout) lands, update qwenlane.py to
    pass shell_timeout_seconds from qwen-storm.toml.
14. [DONE] `sovereign-surfaces-ports` is SATISFIED: integration carries all 12 ports
    (application/interfaces/{blob,bus,cache,config_store,docs,email,files,messaging,secrets,siem,
    sms,tracker}.py) and their infrastructure/*/in_memory.py twins (#319). No spec needed.
15. ONE passive-declare method (surfaces writer's decision): `inspect_queue(queue) ->
    AmqpQueueState | None` (message + consumer counts), OWNED by the T21 pair. AMEND:
    harness-T21a-amqp-consumer-count-client + harness-T21-amqp-consumer-count (from
    `consumer_count` to `inspect_queue`), split-380-1-loop-doctor (read `.consumers` from
    `inspect_queue`), and the loops writer's queue-depth lane (L21: exclusive consume only; depth
    reads `inspect_queue(...).messages`). Do after the loops writer reports.
16. OPERATOR RULING NEEDED (batch): surfaces-default-flip is gated on the operator's WRITTEN
    acceptance of the 8.f cache cost (measured by surfaces-bench on macOS + Arch).
17. The loops helpers write `python3 - <<'PY'` … `PY` script blocks (argv-only shell cannot run
    them). Fixed by hand in loops-config-engine-names; loops-vibey-local-engine-names has one too.
    AFTER the last loops spec lands: one automated pass converting every such block into
    "write it with write_file to .qwenstorm/<name>.py, then run [\"python3\", \".qwenstorm/<name>.py\"]",
    then rerun lint-specs.py (must report only 0 problems).
