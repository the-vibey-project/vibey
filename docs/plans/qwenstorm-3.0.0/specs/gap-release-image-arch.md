## Title
ci(release): the Arch Linux image variant is published beside the Debian one, from its own tested digest

## Why
Sub-doctrine 8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`): "Arch Linux is always the
default sovereign operating system vibey supports ... every change is proven on it". Lane
`gap-image-arch` adds `deploy/docker/Dockerfile.arch` and its `Image contract - … (Arch Linux)`
steps to `ci.yml`'s `image` job, but publishes nothing. Sub-doctrine 2.b (`doctrines.md:30`)
says a built artifact that no automation publishes is not a channel. `gap-release-image-publish`
set the joining rule, which its meta-test enforces. A variant is:
- one `[[channel]]` with `ecosystem = "oci-image"`, `definition[0]` naming its Dockerfile, and
  `options.tag_suffix` and `options.contract_suffix`;
- one `release.yml` job with the matching `DOCKERFILE` and `TAG_SUFFIX` env, whose contract
  steps are byte-identical to `ci.yml`'s steps for that suffix.

This lane applies that rule to the Arch Linux variant.

**Gate:** this lane runs only after `gap-image-arch` is integrated. That lane is itself gated
on `gap-ops-canon-rulings` item 6. If `deploy/docker/Dockerfile.arch` does not exist, stop and
report BLOCKED.

## Required behaviour
1. `.github/workflows/release.yml`: add a job `image-arch`, inserted immediately before
   `  realign:`, as a copy of job `image` with exactly these differences:
   - `name: Publish the runnable image, Arch Linux variant`;
   - `env.DOCKERFILE: deploy/docker/Dockerfile.arch` and `env.TAG_SUFFIX: "-arch"`;
   - in the push step, `platforms` is `linux/amd64`, unless the header comment of
     `deploy/docker/Dockerfile.arch` records that an arm64 Arch base exists (the header
     `gap-image-arch` writes). In that case it is `linux/amd64,linux/arm64`. Name which, in a
     comment above `platforms`, quoting the header line;
   - the pull step tags the pulled image `vibey:ci-arch` (the tag `gap-image-arch`'s contract steps test);
   - the contract steps are the `ci.yml` steps whose names end with ` (Arch Linux)`, copied
     byte for byte;
   - the arm64 emulation step is kept only when `platforms` includes arm64;
   - the annotation description says `vibey, the runnable image on Arch Linux.` in place of
     `vibey, the runnable worker and server image.`;
   - no sovereign mirror steps (out of scope).
2. Append to `packaging/channels.toml`, preceded by one blank line:
   ```toml
   [[channel]]
   name = "oci-image-arch"
   ecosystem = "oci-image"
   publisher = "workflow"
   workflow = ".github/workflows/release.yml"
   job = "image-arch"
   branches = ["main"]
   definition = ["deploy/docker/Dockerfile.arch", ".github/workflows/release.yml"]
   excludes = "PostgreSQL and Ollama: point VIBEY_PG_URL at a database; codex is the only vendor engine CLI in the image."
   grace_hours = 2
   probe = { url = "https://ghcr.io/v2/the-vibey-project/vibey/manifests/{version}-arch", accept = "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json" }
   options = { tag_suffix = "-arch", contract_suffix = " (Arch Linux)" }
   enabled = true
   ```
3. No new test file: `tests/meta/test_release_image.py` (from `gap-release-image-publish`)
   already iterates every `oci-image` channel. Append one test to it:
   `test_the_arch_variant_is_published_when_it_is_built`. If `deploy/docker/Dockerfile.arch`
   exists, a channel named `oci-image-arch` exists, with `definition[0]` equal to that path.

## Where to change
- `.github/workflows/release.yml` (edit_file; insert before `  realign:`).
- `packaging/channels.toml` (append).
- `tests/meta/test_release_image.py` (append one test; do not rewrite the file).

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.
      `test_every_oci_image_channel_has_a_job_that_passes_ci_contracts` now covers two channels.
- [ ] Deleting one `(Arch Linux)` contract step from `image-arch` fails that test (scratch edit, then revert).
- [ ] The first `main` release after integration shows `ghcr.io/the-vibey-project/vibey:<version>-arch`
      (the reviewer records the run; unverified until then, 10.f).

## Tests to write first (TDD)
- `test_the_arch_variant_is_published_when_it_is_built` (appended to `tests/meta/test_release_image.py`).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- The Arch Dockerfile and its CI contract steps (`gap-image-arch`).
- The sovereign mirror of the variant, the chart's choice of image, and docs.

Commit as `ci(release): publish the Arch Linux image variant`. Do not push.

## Lane card
- **Depends on:** `gap-image-arch`, `gap-release-image-publish`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
