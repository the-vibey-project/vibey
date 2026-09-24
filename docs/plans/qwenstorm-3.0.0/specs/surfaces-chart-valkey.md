## Title
feat(chart): the cache surface runs Valkey, the BSD-licensed server of the Redis protocol, pinned by digest

## Why
The operator's ruling of 2026-09-22 (`STORM-CONTEXT.md`, "Operator rulings"): "The cache is
**Valkey** everywhere: installer and chart. 8.b's 'Redis' names the protocol." Draft ADR-0047's
Decision opens with it (`specs/ADR-surface-lanes.md`: "the installer and the chart run Valkey …
the adapter, its commands and everything below are unchanged"). The installer already installs
Valkey (`specs/installer-broker-cache.md`: Arch's `extra/valkey` 9.1.2, Homebrew `valkey`), but
the chart still runs `redis:8-alpine` (`deploy/helm/vibey/values.yaml:419-433`,
`templates/surfaces.yaml:62-63`). Sub-doctrine 8.a prefers the freer licence: Valkey is
BSD-3-Clause, Redis 8 is AGPL-3.0, RSAL or SSPL. The ADR's §10 measurement is re-taken against
this image (`surfaces-bench`).

Nothing but the image changes. Keys, resource names and URLs stay (`surfaces.redis.*`,
`<fullName>-redis`, `redis://…:6379/0`) — they name the protocol, and renaming them would break
every override an adopter has (12.c: never less configurable).

## Required behaviour
1. **Pick and pin the image.** Valkey's official image is `valkey/valkey`. Use the Alpine tag of
   the Valkey minor the installer pins (`9.1`, from `specs/installer-broker-cache.md`):
   `9.1-alpine`. If that tag does not exist, use the newest `9.x-alpine` tag that does, and say
   which in the commit body. Resolve its multi-arch index digest (amd64 and arm64 are both
   needed: CI's `image` job builds both):
   ```sh
   TOKEN=$(curl -fsS "https://auth.docker.io/token?service=registry.docker.io&scope=repository:valkey/valkey:pull" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
   curl -fsSI -H "Authorization: Bearer $TOKEN" \
     -H "Accept: application/vnd.oci.image.index.v1+json" \
     -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
     https://registry-1.docker.io/v2/valkey/valkey/manifests/9.1-alpine | grep -i '^docker-content-digest'
   ```
   Record both commands and their output in the commit body. If the registry cannot be reached,
   stop and report; never invent a digest.
2. **`values.yaml`** (`:419-433`): the comment becomes
   `# 9. Cache: Valkey — serves the Redis protocol (the operator's ruling of 2026-09-22; 8.a: BSD-3-Clause)`,
   and `image` becomes `repository: valkey/valkey`, `tag: <the tag>`, `digest: "<sha256:…>"`.
   Every other key under `surfaces.redis` is unchanged.
3. **`templates/surfaces.yaml`**: the section comment `1. Redis (Cache)` becomes
   `1. Valkey (Cache, Redis protocol)`. Nothing else changes: the container still listens on
   6379, mounts `/data`, and uses the same probes (the Valkey image's default command is
   `valkey-server`, with its data in `/data`).
4. **Goldens.** Regenerate with `deploy/helm/golden/render.sh --update` and review: only the
   `image:` line changes in `default.yaml` and `ollama.yaml`. `keda-latest`, `keda-project`,
   `ollama-gpu-qwenloop` and `surfaces-off` must not change.

## Where to change
- `deploy/helm/vibey/values.yaml`, `deploy/helm/vibey/templates/surfaces.yaml` (one comment),
  `deploy/helm/golden/default.yaml`, `deploy/helm/golden/ollama.yaml` (regenerated).
- New `tests/infrastructure/test_chart_valkey_golden.py`.

## Acceptance criteria
- [ ] `deploy/helm/golden/render.sh` passes; `git diff --stat deploy/helm/golden` touches only `default.yaml` and `ollama.yaml`, one line each.
- [ ] The rendered cache Deployment's image is `valkey/valkey:<tag>@sha256:<64 hex>`; the Service is still `vibey-vibey-redis` on 6379; the worker's `VIBEY_CACHE_URL` is unchanged.
- [ ] `helm lint --strict` passes; cluster-smoke's deployment list is unchanged (`vibey-vibey-redis`).
- [ ] The commit body holds the digest commands and their output.

## Tests to write first (TDD)
`tests/infrastructure/test_chart_valkey_golden.py` (reads the goldens with `yaml.safe_load_all`, as `tests/infrastructure/db/test_keda_scaler_query.py:34-39` does):
- `test_the_cache_runs_a_pinned_valkey_image`
- `test_the_cache_keeps_its_names_and_port`
- `test_the_worker_cache_url_is_unchanged`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml deploy/helm/golden/surfaces-off.yaml deploy/helm/golden/ollama-gpu-qwenloop.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_valkey_golden.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- The installer (`installer-broker-cache`). Renaming any key or resource. The Plane cache (it
  shares the server, database 1, `templates/plane.yaml:21`). CHANGELOG.md, docs/, ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open
  PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `rmq-r29-chart-broker-core` (the chart chain starts there; it also edits `values.yaml` and `surfaces.yaml`).
- **Shares a file with:** the chart and its goldens (R29 → R30 → R31 → R34 → T27 → T28, and the other `surfaces-chart-*` lanes). Keep everything earlier lanes added; never hand-edit a golden.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_keda_scaler_query.py`, `tests/infrastructure/test_chart_broker_golden.py`, all protected tests.
- **Standing constraints (every surfaces chart lane):**
  - `helm` must be v4.2.4, the version the `chart` job pins (`.github/workflows/ci.yml`). If it is not on `PATH`, stop and report.
  - Read `STORM/EDITING-RULES.md` before changing a file; `values.yaml` is long: `edit_file` only.
  - Line 1 of every new Python file is the provenance comment, copied byte-for-byte from a sibling.
  - Protected tests are never edited.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
