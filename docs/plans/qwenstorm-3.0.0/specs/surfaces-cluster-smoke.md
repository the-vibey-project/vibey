## Title
ci(cluster-smoke): the minikube install runs the surface lanes — every lane becomes Available and answers a ping from the worker pod

## Why
Draft ADR-0047 §14 (`specs/ADR-surface-lanes.md`): "**cluster-smoke** gains two contracts (lane
S31): every lane Deployment becomes Available, and `vibey surface ping --all` answers from inside
the worker pod." §15: "The chart renders no lanes until `surfaceLanes.transport=queue` is set,
and cluster-smoke sets it explicitly (S31)", and the flip waits until "cluster-smoke is green in
`queue` mode". Each `Contract - …` step asserts one cluster behaviour (CLAUDE.md, "CI"). The
job lives at `.github/workflows/ci.yml:871-1060` at integration `d3b4a388`; its install is
`helm install vibey deploy/helm/vibey -n vibey --create-namespace --wait --timeout 20m`
(`:897-900`). ADR-0047 lane S31.

## Required behaviour
1. The `helm install` step gains `--set surfaceLanes.transport=queue` (explicit, so the smoke
   keeps testing queue mode after the default flips).
2. A new step, directly after "Contract - all sovereign surface deployments become Available":
   ```yaml
   - name: Contract - every surface lane becomes Available
     run: |
       for lane in tracker docs secrets files email sms messaging configuration cache blob siem; do
         echo "asserting deployment/vibey-vibey-surface-$lane is available..."
         kubectl wait --for=condition=available "deployment/vibey-vibey-surface-$lane" -n vibey --timeout=5m
         replicas=$(kubectl get deployment "vibey-vibey-surface-$lane" -n vibey -o jsonpath='{.status.replicas}')
         test "$replicas" = "1"
       done
   ```
3. A second new step:
   ```yaml
   - name: Contract - every surface lane answers a ping from the worker pod
     run: |
       kubectl exec -n vibey deploy/vibey-vibey-worker -- vibey surface ping --all | tee /tmp/ping
       test "$(grep -c ': ok ' /tmp/ping)" = "11"
   ```
4. **Diagnostics on failure** also prints
   `kubectl logs -n vibey -l app.kubernetes.io/component=surface-tracker --tail=50 || true` for
   each lane (a loop over the same eleven names).
5. Every existing contract keeps passing: the worker still parks without a project, picks up a
   project, reconciles KEDA, and drains on SIGTERM, now with `queue` transport.
6. Record in the commit body, as manual evidence the ADR owes and CI cannot produce: whether a
   transient read message survives a broker restart (ADR "Verification owed", item 5) — run it by
   hand on minikube (`kubectl rollout restart deploy/vibey-vibey-rabbitmq` with the cache lane
   scaled to 0 and one read published) or state that it was not run.

## Where to change
- `.github/workflows/ci.yml` (the `cluster-smoke` job only).
- Append to `tests/meta/` only if a workflow test pins the step names; otherwise none.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes (the workflow still parses; any step-name pin is updated).
- [ ] `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` succeeds.
- [ ] The two new steps assert eleven lanes and eleven `ok` lines exactly.
- [ ] The job's other steps are byte-identical apart from the `--set` and the diagnostics loop.
- [ ] Evidence (reviewer): the job passes on the PR's CI run; a lane step failing is a real failure, never retried into green.

## Tests to write first (TDD)
- None beyond the parse and meta checks: the CI job is the test. If `tests/meta/` has a test listing cluster-smoke step names, append the two new names to it.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- The chart (earlier lanes). R32's CI RabbitMQ service (`rmq-r32-ci-rabbitmq`), which edits other
  jobs. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-chart-surface-health`, `surfaces-cli-serve-ping`.
- **Shares a file with:** `.github/workflows/ci.yml` (R32, R34, T19 edit other parts). Keep their changes.
- **Must keep passing unchanged:** every existing cluster-smoke contract, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file; `ci.yml` is long: `edit_file` only.
  - Never loosen an existing contract to make the new ones pass.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
