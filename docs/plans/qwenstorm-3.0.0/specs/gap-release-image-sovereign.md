## Title
ci(release): the tested image digest is mirrored to the sovereign forge's registry when one is declared

## Why
`issue-audit/gaps.md` G1 (lines 386-393) requires the runnable image "pushed to ghcr.io on every
release, and to the sovereign forge's registry". Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:120`)
makes Forgejo the sovereign forge default, and Forgejo carries an OCI registry. Whether this
project runs its own Forgejo host is still open (`specs/gap-ops-canon-rulings.md` item 8).
So this lane adds the machinery, declared and off. It declares a disabled channel with an
empty registry in `packaging/channels.toml`, and adds `release.yml` steps that copy the exact
tested digest there once the channel is enabled. Enabling it is a one-line, reviewed change
(12.c, `doctrines.md:455`) that `gap-ops-packaging-credentials` makes after the ruling. The
copy uses `skopeo copy --all --preserve-digests`, so the sovereign registry serves
byte-identical manifests: the contract-tested digest, never a rebuild.

## Required behaviour
1. Append to `packaging/channels.toml`, preceded by one blank line:
   ```toml
   [[channel]]
   name = "oci-image-sovereign"
   ecosystem = "oci-image-mirror"
   publisher = "workflow"
   workflow = ".github/workflows/release.yml"
   job = "image"
   branches = ["main"]
   definition = [".github/workflows/release.yml"]
   excludes = "The same image as oci-image: PostgreSQL and Ollama are not included; point VIBEY_PG_URL at a database."
   credential = "SOVEREIGN_REGISTRY_TOKEN"
   grace_hours = 2
   probe_reason = "No sovereign registry is declared yet (gap-ops-canon-rulings item 8); enabling this channel replaces this line with a probe."
   options = { source_channel = "oci-image", registry = "", registry_user = "" }
   enabled = false
   ```
2. In `.github/workflows/release.yml`, job `image` (added by `gap-release-image-publish`),
   insert two steps after `Tag the tested digest as the release`:
   ```yaml
         - name: Read the sovereign registry declaration
           id: sovereign
           run: |
             python -c 'import pathlib; import tomllib; data = tomllib.loads(pathlib.Path("packaging/channels.toml").read_text(encoding="utf-8")); entry = next((c for c in data.get("channel", []) if c.get("name") == "oci-image-sovereign"), {}); options = entry.get("options", {}); enabled = bool(entry.get("enabled")) and bool(options.get("registry")); print("enabled=" + ("true" if enabled else "false")); print("registry=" + str(options.get("registry", ""))); print("user=" + str(options.get("registry_user", "")))' >> "$GITHUB_OUTPUT"
         - name: Mirror the tested digest to the sovereign registry
           env:
             ENABLED: ${{ steps.sovereign.outputs.enabled }}
             SOURCE: ${{ steps.name.outputs.image }}@${{ steps.push.outputs.digest }}
             TARGET: ${{ steps.sovereign.outputs.registry }}
             REGISTRY_USER: ${{ steps.sovereign.outputs.user }}
             REGISTRY_TOKEN: ${{ secrets.SOVEREIGN_REGISTRY_TOKEN }}
             GHCR_TOKEN: ${{ github.token }}
           run: |
             set -euo pipefail
             if [ "$ENABLED" != "true" ]; then
               echo "::notice::oci-image-sovereign is not enabled in packaging/channels.toml; nothing mirrored (gap-ops-canon-rulings item 8)"
               exit 0
             fi
             if [ -z "$REGISTRY_TOKEN" ]; then
               echo "::error::oci-image-sovereign is enabled but the SOVEREIGN_REGISTRY_TOKEN secret is empty"
               exit 1
             fi
             for tag in "${VERSION}${TAG_SUFFIX}" "main${TAG_SUFFIX}" "latest${TAG_SUFFIX}"; do
               skopeo copy --all --preserve-digests \
                 --src-creds "${GITHUB_ACTOR}:${GHCR_TOKEN}" \
                 --dest-creds "${REGISTRY_USER}:${REGISTRY_TOKEN}" \
                 "docker://${SOURCE}" "docker://${TARGET}:${tag}"
             done
             echo "mirrored ${SOURCE} to ${TARGET} as ${VERSION}${TAG_SUFFIX}, main${TAG_SUFFIX}, latest${TAG_SUFFIX}"
   ```
   The secret name in `secrets.SOVEREIGN_REGISTRY_TOKEN` must equal the channel's `credential`.
3. New meta-test `tests/meta/test_release_image_sovereign.py` (provenance line 1; docstring
   cites G1 and 8.b):
   - `test_the_mirror_follows_the_tested_tags`: in job `image`, the `Mirror the tested digest
     to the sovereign registry` step comes after `Tag the tested digest as the release`. Its
     run holds `skopeo copy --all --preserve-digests` and the three tags.
   - `test_the_mirror_reads_its_secret_by_the_declared_name`: the step's `REGISTRY_TOKEN`
     env is `${{ secrets.<credential> }}`, where `<credential>` is the `oci-image-sovereign`
     channel's `credential` in the registry.
   - `test_a_disabled_or_undeclared_mirror_is_a_notice_not_a_failure`: extract the
     declaration step's Python and run it (`subprocess.run([sys.executable, "-c", code], cwd=tmp)`)
     against three `packaging/channels.toml` copies in `tmp_path`: disabled, enabled with an
     empty registry, and enabled with `registry = "forge.example/acme/vibey"`. Assert
     `enabled=false`, `enabled=false` and `enabled=true` plus `registry=forge.example/acme/vibey`.
   - `test_an_enabled_mirror_declares_a_probe`: when `oci-image-sovereign` is enabled, it has a
     `probe` whose URL holds the declared registry's host. This passes trivially while it is
     disabled, and binds the ops change that enables it.
   - `test_the_new_run_blocks_are_valid_bash`: `bash -n` over the mirror step's run.

## Where to change
- `packaging/channels.toml` (append).
- `.github/workflows/release.yml` (edit_file; insert after the step named `Tag the tested digest as the release`).
- New `tests/meta/test_release_image_sovereign.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes, including `test_packaging_channels.py` and `test_release_image.py`.
- [ ] Renaming the secret in the workflow fails `test_the_mirror_reads_its_secret_by_the_declared_name` (scratch edit, then revert).
- [ ] With the channel disabled, the next `main` release logs the notice and stays green (the reviewer records the run).

## Tests to write first (TDD)
`tests/meta/test_release_image_sovereign.py`, with the five tests in item 3.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Choosing or running the Forgejo host, creating its token, and enabling the channel
  (`gap-ops-canon-rulings` item 8, then `gap-ops-packaging-credentials`).
- Mirroring the Arch Linux variant (a later copy of these two steps in `image-arch`).
- Docs.

Commit as `ci(release): mirror the tested image digest to a declared sovereign registry`. Do not push.

## Lane card
- **Depends on:** `gap-release-image-publish`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
