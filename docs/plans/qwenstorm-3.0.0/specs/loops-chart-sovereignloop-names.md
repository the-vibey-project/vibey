## Title
feat(chart): the chart wires sovereignloop by its new names, and honours ollama.qwenloopFeature while the new key is unset

ADR-0046 lane L18g (slug `loops-chart-sovereignloop-names`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`): the chart's
`ollama.qwenloopFeature`, `worker.provider=qwenloop` and `worker.engines=qwenloop` become
`ollama.sovereignloopFeature` and `sovereignloop`, the old ones "honoured when the new key is
unset", through all of 3.x. 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`) keeps the chart
declared and never less configurable.

At integration `d3b4a388`:
- `deploy/helm/vibey/values.yaml:19-25` documents `worker.provider`/`worker.engines` with
  qwenloop, `:108-116` and `:124-130` name `QWENLOOP_BASE_URL/QWENLOOP_MODEL` and qwenloop,
  and `:189-193` declare `ollama.qwenloopFeature: true`;
- `deploy/helm/vibey/templates/worker.yaml:105-116` renders `QWENLOOP_BASE_URL`,
  `QWENLOOP_MODEL` and, under `if .Values.ollama.qwenloopFeature`, `VIBEY_FEATURE_QWENLOOP=1`;
- `deploy/helm/golden/render.sh:81-85` renders the profile `ollama-gpu-qwenloop` with
  `--set worker.provider=qwenloop --set worker.engines=qwenloop`, committed as
  `deploy/helm/golden/ollama-gpu-qwenloop.yaml` (its worker env at `:346-355`);
- lane `rmq-r30-chart-loop-services` (#377, `issue-audit/updates/377.md` behaviour 2) adds
  `templates/loop-services.yaml`, whose sovereign pods render the same three `QWENLOOP_*` /
  `VIBEY_FEATURE_QWENLOOP` names and read `ollama.qwenloopFeature` ("The `QWENLOOP_*` names stay
  until ADR-0046's rename lane").

Since lanes `loops-tenant-legacy-env` (L18c) and `loops-vibey-local-engine-names` (L18e) the
runner and vibey read `SOVEREIGNLOOP_BASE_URL`, `SOVEREIGNLOOP_MODEL` and
`VIBEY_FEATURE_SOVEREIGNLOOP` first; lanes `loops-engine-id-sovereignloop` and
`loops-cli-provider-name` accept `sovereignloop` in `--engines` and `--provider`.

## Required behaviour
1. **One helper** decides the switch, so the worker and the loops cannot disagree. In
   `templates/_helpers.tpl`, after `vibey.ollamaURL`:
   ```
   {{- /*
   The sovereign loop's feature switch, "true" or "false" (ADR-0046 Migration table):
   ollama.sovereignloopFeature when it is set, else the legacy ollama.qwenloopFeature (honoured
   through 3.x), else true. hasKey guards each read, so `helm lint --strict` never meets a
   missing key.
   */}}
   {{- define "vibey.sovereignloopFeature" -}}
   {{- $o := .Values.ollama -}}
   {{- if and (hasKey $o "sovereignloopFeature") (not (kindIs "invalid" $o.sovereignloopFeature)) -}}
   {{- $o.sovereignloopFeature | toString -}}
   {{- else if and (hasKey $o "qwenloopFeature") (not (kindIs "invalid" $o.qwenloopFeature)) -}}
   {{- $o.qwenloopFeature | toString -}}
   {{- else -}}
   true
   {{- end -}}
   {{- end -}}
   ```
2. **`values.yaml`** under `ollama:` replaces the `qwenloopFeature` block (`:189-193`) with:
   ```yaml
     # Renders VIBEY_FEATURE_SOVEREIGNLOOP=1 into the worker and the sovereign loop's pods.
     # sovereignloop is always on (sub-doctrine 8.b); false renders nothing. null means true,
     # unless the legacy ollama.qwenloopFeature is set, which is honoured while this is null
     # (through 3.x, ADR-0046).
     sovereignloopFeature: null
   ```
   and its comments name the new spellings: `:19-25` becomes
   ```yaml
     # DESIGN/decompose provider: scripted, claudeloop, or sovereignloop (qwenloop is its
     # legacy spelling through 3.x). sovereignloop is the sovereign path; with ollama.enabled
     # it talks to the in-cluster server below.
     provider: scripted
     # Comma-separated engine allow-list (--engines); empty means all. sovereignloop is always
     # in the pool (sub-doctrine 8.b); qwenloop is accepted as its legacy spelling.
     engines: ""
   ```
   (keep the lines between them that are not about qwenloop exactly as they are), and in the
   `ollama:` header comment `QWENLOOP_BASE_URL/QWENLOOP_MODEL for qwenloop's` becomes
   `SOVEREIGNLOOP_BASE_URL/SOVEREIGNLOOP_MODEL for sovereignloop's`.
3. **`templates/worker.yaml`**: the block after `VIBEY_OLLAMA_MODEL` (`:105-116`) becomes
   ```
               # sovereignloop's openai-compat backend wants the OpenAI base URL, /v1
               # included; a base URL alone is what makes `auto` select it.
               - name: SOVEREIGNLOOP_BASE_URL
                 value: {{ printf "%s/v1" $ollamaURL | quote }}
               - name: SOVEREIGNLOOP_MODEL
                 value: {{ .Values.ollama.model | quote }}
               {{- if eq (include "vibey.sovereignloopFeature" .) "true" }}
               # The sovereign loop's switch in the worker (ADR-0015, ADR-0046): a
               # project's [features] table never makes it into the record.
               - name: VIBEY_FEATURE_SOVEREIGNLOOP
                 value: "1"
               {{- end }}
   ```
4. **`templates/loop-services.yaml`** (from #377): in its sovereign environment block, the names
   `QWENLOOP_BASE_URL` → `SOVEREIGNLOOP_BASE_URL`, `QWENLOOP_MODEL` → `SOVEREIGNLOOP_MODEL`,
   `VIBEY_FEATURE_QWENLOOP` → `VIBEY_FEATURE_SOVEREIGNLOOP`, and its condition on
   `.Values.ollama.qwenloopFeature` becomes `eq (include "vibey.sovereignloopFeature" $) "true"`
   (use `$`, the root context, because the block sits inside `range`; use `.` only if it does
   not). The values are unchanged (a seat host's model variable still holds that seat's model).
   Comments in that block that say qwenloop say sovereignloop.
5. **`deploy/helm/golden/render.sh`**: the profile comment and name become
   ```
   # The GPU branch and the sovereignloop worker wiring, narrowed to what they touch.
   profile ollama-gpu-sovereignloop \
     --show-only templates/ollama.yaml --show-only templates/worker.yaml -- \
     --set ollama.enabled=true --set ollama.gpu.enabled=true \
     --set worker.provider=sovereignloop --set worker.engines=sovereignloop
   # The legacy switch key (ADR-0046 Migration table): honoured while the new one is unset.
   profile ollama-legacy-feature-off --show-only templates/worker.yaml -- \
     --set ollama.enabled=true --set ollama.qwenloopFeature=false
   ```
   and the comment on the `ollama` profile says "points vibey and sovereignloop at it". If
   #377's profiles list `templates/loop-services.yaml` for the GPU profile, keep them.
6. **Goldens** are regenerated, never hand-edited:
   `git mv deploy/helm/golden/ollama-gpu-qwenloop.yaml deploy/helm/golden/ollama-gpu-sovereignloop.yaml`,
   then `deploy/helm/golden/render.sh --update`. Expected diff: `ollama`,
   `ollama-gpu-sovereignloop` change (names only, plus the worker args in the GPU profile);
   `ollama-legacy-feature-off` is new; `default`, `surfaces-off`, `keda-latest`,
   `keda-project` and #377's `paidloop` and `worktrees-rwx` do not change.
7. The CRD enum is not touched here (lane `loops-engine-id-sovereignloop` keeps `qwenloop`
   beside `sovereignloop`).

## Where to change
- `deploy/helm/vibey/templates/_helpers.tpl`, `deploy/helm/vibey/values.yaml`,
  `deploy/helm/vibey/templates/worker.yaml`, `deploy/helm/vibey/templates/loop-services.yaml`,
  `deploy/helm/golden/render.sh`: `edit_file` with text anchors (`values.yaml` and
  `worker.yaml` are over 100 lines; #377 edits the same files first).
- The goldens: `git mv` then `render.sh --update` only.
- **Stop and report** when: `templates/loop-services.yaml` does not exist (lane
  `rmq-r30-chart-loop-services` has not landed); `helm` on `PATH` is not v4.2.4 (the `chart`
  job's pin, `.github/workflows/ci.yml:864-866`); or `render.sh --update` changes any golden the
  list in behaviour 6 says must not change.
- New test `tests/infrastructure/test_chart_sovereignloop_names.py`, line 1 the provenance line
  from `tests/infrastructure/db/test_keda_scaler_query.py`. It reads files only (no helm, no
  cluster), with module-level test functions like that file (`:35-40`): documents from
  `yaml.safe_load_all`, the worker found as the `Deployment` whose
  `metadata.labels["app.kubernetes.io/component"] == "worker"`, and its container's `env` as a
  `{name: value}` dict.

## Acceptance criteria
- [ ] `values.yaml` has `ollama.sovereignloopFeature` and no `ollama.qwenloopFeature` key.
- [ ] In the `ollama` golden, the worker has `SOVEREIGNLOOP_BASE_URL` ending in `/v1`, `SOVEREIGNLOOP_MODEL: gpt-oss:20b` and `VIBEY_FEATURE_SOVEREIGNLOOP: "1"`, and no env name starting `QWENLOOP_` and no `VIBEY_FEATURE_QWENLOOP`; so does every sovereign loop pod in it.
- [ ] `deploy/helm/golden/ollama-gpu-sovereignloop.yaml` exists, `ollama-gpu-qwenloop.yaml` does not, and its worker args contain `--provider`, `sovereignloop`, `--engines`, `sovereignloop`.
- [ ] In `ollama-legacy-feature-off.yaml` the worker has no `VIBEY_FEATURE_SOVEREIGNLOOP`.
- [ ] `git grep -n "QWENLOOP_\|VIBEY_FEATURE_QWENLOOP" -- deploy/helm` prints nothing.
- [ ] `render.sh` passes; the unchanged goldens are byte-identical.

## Tests to write first (TDD)
`tests/infrastructure/test_chart_sovereignloop_names.py`:
- `test_values_rename_the_feature_key` (`yaml.safe_load` of `values.yaml`: `"sovereignloopFeature" in ollama`, its value `None`, `"qwenloopFeature" not in ollama`).
- `test_the_ollama_worker_gets_the_sovereignloop_names`.
- `test_the_sovereign_loop_pods_get_the_sovereignloop_names` (every `Deployment` in the `ollama` golden whose component label starts with `sovereignloop-`).
- `test_the_gpu_profile_is_renamed_and_passes_the_new_spellings`.
- `test_the_legacy_feature_key_is_honoured_while_the_new_one_is_unset`.
- `test_no_golden_renders_a_qwenloop_variable`: across every `deploy/helm/golden/*.yaml`, no env entry named `QWENLOOP_*` or `VIBEY_FEATURE_QWENLOOP`.

## Checks the lane must run (all must pass)
    helm version --short
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/default.yaml deploy/helm/golden/surfaces-off.yaml deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    helm template vibey deploy/helm/vibey --set ollama.enabled=true --set ollama.sovereignloopFeature=false --show-only templates/worker.yaml | grep -c VIBEY_FEATURE_SOVEREIGNLOOP
    git grep -n "QWENLOOP_\|VIBEY_FEATURE_QWENLOOP" -- deploy/helm
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_sovereignloop_names.py tests/infrastructure/test_chart_loop_services_golden.py tests/infrastructure/db/test_keda_scaler_query.py

`helm version --short` must print `v4.2.4`. The fourth command must print `0`; the fifth must
print nothing. `test_keda_scaler_query.py` needs PostgreSQL (it is `integration` after
`fakes-harness-decouple`); if none is available, record that it was skipped.

## Out of scope
- The CRD enum (lane `loops-engine-id-sovereignloop`), the loop-service templates' structure (#377),
  KEDA (#378) and the defaults flip (#381).
- `templates/ollama.yaml`'s comments that mention qwenloop (they render into goldens; a docs-wave
  follow-up renames them).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vibey-local-engine-names`, `rmq-r30-chart-loop-services`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
