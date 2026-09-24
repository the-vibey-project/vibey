## Title
feat(chart): KEDA scales on the project's RabbitMQ queue

## Why
ADR-0044 §12. KEDA today scales on a PostgreSQL copy of the claim's SELECT arm
(`templates/keda-scaledobject.yaml:49-66`), bound to the real claim by
`tests/infrastructure/db/test_keda_scaler_query.py`.

In the RabbitMQ backend the queue holds only due work whose dependencies are met, so
its length (ready plus unacknowledged) is claimable work plus in-flight work. That
honours ADR-0025's rule against scaling on raw depth, and a pod mid-session is not
scaled in under its running job.

A broker cannot know which project is "newest", so the unbound worker mode cannot be
followed. The chart must fail loudly and name the fixes, rather than scale on
something no worker will claim.

## Required behaviour
1. `keda-scaledobject.yaml`:
   - When `queue.backend` is `postgres`, it renders **exactly** today's text.
   - When it is `rabbitmq`:
     - With `worker.project` empty, fail with:
       `"keda.enabled with queue.backend=rabbitmq needs worker.project: a broker cannot follow 'the newest project'. Set worker.project, or set queue.backend=postgres."`
     - Otherwise render a `TriggerAuthentication` `<fullName>-worker-rabbitmq`, whose
       `secretTargetRef` has parameter `host`. It points at the broker Secret's
       `keda-host` key, or at `broker.existingSecret` / `existingSecretKedaHostKey`.
     - Render the trigger:
       ```yaml
       - type: rabbitmq
         metadata:
           protocol: http
           mode: QueueLength
           value: "<worker.parallelism>"
           activationValue: "0"
           queueName: "<broker.prefix>.jobs.<canonical lower-case project uuid>"
           vhostName: "<broker.vhost>"
           excludeUnacknowledged: "false"
         authenticationRef:
           name: <fullName>-worker-rabbitmq
       ```
2. `queueName` must equal `QueueNames(prefix).project_queue(UUID(worker.project))`
   (R06). Add a `vibey.workerProjectUuid` helper next to `vibey.workerProjectHex` if
   the existing helper does not already give the canonical dashed lower-case form.
3. `render.sh`:
   - `keda-latest` and `keda-project` add `--set queue.backend=postgres`, so their
     goldens are unchanged.
   - A new profile:
     `profile keda-rabbitmq --show-only templates/keda-scaledobject.yaml -- --set keda.enabled=true --set queue.backend=rabbitmq --set worker.project="$PROJECT"`.
   - A new `expect_fail NAME ARGS…` function asserts that `helm template` fails. It is
     used once, for `--set keda.enabled=true --set queue.backend=rabbitmq`.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] `render.sh` passes, and the `keda-latest` and `keda-project` goldens are byte-identical.
- [ ] The `keda-rabbitmq` golden holds the trigger and the TriggerAuthentication.
- [ ] The unbound rabbitmq render fails with the message.
- [ ] The new test binds `queueName` to `QueueNames`.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_keda_rabbitmq_trigger.py`, reading the
  `keda-rabbitmq` golden:
  - `test_queue_name_is_the_projects_queue`
  - `test_counts_in_flight_work`
  - `test_value_is_the_worker_parallelism`
  - `test_authentication_uses_the_qualified_keda_host`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue/test_keda_rabbitmq_trigger.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- The cluster contract (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R29, R30.
- **Wave:** 9.
- **Files touched:**
  - `deploy/helm/vibey/templates/keda-scaledobject.yaml`
  - `deploy/helm/vibey/templates/_helpers.tpl` (at most one helper)
  - `deploy/helm/golden/render.sh`
  - `deploy/helm/golden/keda-rabbitmq.yaml` (new golden)
  - `tests/infrastructure/queue/test_keda_rabbitmq_trigger.py` (new)
- **Parallel-safe with:** R33.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - the `keda-latest` and `keda-project` goldens, byte for byte
  - all protected tests
- **Standing constraints:** see the header list. helm v4.2.4; never hand-edit goldens.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
