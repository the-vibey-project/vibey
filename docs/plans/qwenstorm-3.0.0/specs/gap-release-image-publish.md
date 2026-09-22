## Title
ci(release): every release pushes the contract-tested multi-arch runnable image to ghcr.io

## Why
Sub-doctrine 2.b (`src/vibey_tools/gh/docs/doctrines.md:30`): "a release is not finished when
the canonical index has the artifact; it is finished when every channel that carries the
project has it." ADR-0019's first consequence (`docs/architecture/decisions/0019-installable-wherever-its-users-are.md:112-113`)
is "OCI image to `ghcr.io`. Already built and contract-tested; only publishing is missing."
Today CI builds the image with `load: true` and `push: false` (`.github/workflows/ci.yml:745-754`,
`:839-850`) and throws it away. `release-surfaces.yml:145-158` pushes only the wheel and sdist,
as an OCI artifact at `ghcr.io/<repo>/python` (`issue-audit/gaps.md` G1, lines 386-393).

This lane adds an `image` job to `release.yml` for releases on `main`. `release.yml` is
repository-local: vibey-gh does not render it. The job:
1. pushes both architectures under a `sha-` tag only;
2. pulls the pushed amd64 image by digest;
3. runs the six `Image contract - …` steps from `ci.yml:761-835`, byte for byte;
4. only then gives that exact digest the release tags.

So the image users pull is the one that passed the contract, which a rebuild could not
promise. The job needs `pypi`, so an image never names a version that the canonical index
does not hold.

## Required behaviour
1. `.github/workflows/release.yml` gains a job `image`. Insert it immediately before the
   line `  realign:` (`:180`); the anchor `  realign:\n    name: Realign develop with main\n`
   is unique. Its header:
   ```yaml
     image:
       # ADR-0019 step 1; sub-doctrine 2.b. The image users pull is the digest that passed the
       # same Image contract steps as CI (ci.yml:761-835), never a rebuild of it.
       name: Publish the runnable image (amd64 + arm64)
       needs: [build, pypi]
       if: github.ref == 'refs/heads/main'
       runs-on: ubuntu-latest
       permissions:
         contents: read
         packages: write
       env:
         # A variant (for example gap-image-arch's) joins as a copy of this job with its own
         # DOCKERFILE and TAG_SUFFIX, and its own [[channel]] in packaging/channels.toml.
         DOCKERFILE: deploy/docker/Dockerfile
         TAG_SUFFIX: ""
         VERSION: ${{ needs.build.outputs.version }}
   ```
   Steps, in this order:
   1. `- uses: actions/checkout@v4`
   2. `- name: The checkout carries the released version`, with the run
      `grep -qx "version = \"${VERSION}\"" pyproject.toml || { echo "::error::pyproject.toml does not declare ${VERSION}"; exit 1; }`
   3. `- name: Set up QEMU` with `uses: docker/setup-qemu-action@v4`, and
      `- name: Set up Buildx` with `uses: docker/setup-buildx-action@v4` (as `ci.yml:739-743`).
   4. `- name: Log in to ghcr.io` with `uses: docker/login-action@v3`, `registry: ghcr.io`,
      `username: ${{ github.actor }}` and `password: ${{ github.token }}`.
   5. `- name: Name the image` with `id: name` and the run
      `echo "image=ghcr.io/${GITHUB_REPOSITORY,,}" >> "$GITHUB_OUTPUT"`.
   6. `- name: Build and push both architectures by digest`, with `id: push` and
      `uses: docker/build-push-action@v7`:
      - `context: .`, `file: ${{ env.DOCKERFILE }}`, `platforms: linux/amd64,linux/arm64` and `push: true`;
      - `tags: ${{ steps.name.outputs.image }}:sha-${{ github.sha }}${{ env.TAG_SUFFIX }}`;
      - `cache-from: type=gha` and `cache-to: type=gha,mode=max`;
      - `labels:`, as a block scalar with one per line:
        ```
        org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
        org.opencontainers.image.revision=${{ github.sha }}
        org.opencontainers.image.version=${{ env.VERSION }}
        org.opencontainers.image.licenses=MIT
        org.opencontainers.image.documentation=https://the-vibey-project.github.io/vibey/main/governance/constitution/
        ```
      - `annotations:` (the index carries the description ghcr.io shows):
        ```
        index:org.opencontainers.image.description=vibey, the runnable worker and server image. It does not include PostgreSQL or Ollama; point VIBEY_PG_URL at a database. Governance: https://the-vibey-project.github.io/vibey/main/governance/constitution/
        index:org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}
        ```
   7. `- name: Pull the pushed amd64 image by digest`, with `env: IMAGE: ${{ steps.name.outputs.image }}`
      and `DIGEST: ${{ steps.push.outputs.digest }}`, and the run:
      ```bash
      set -euo pipefail
      docker pull --platform linux/amd64 "${IMAGE}@${DIGEST}"
      docker tag "${IMAGE}@${DIGEST}" vibey:ci
      ```
   8. The six steps `Image contract - entrypoint runs` through
      `Image contract - every console script is on PATH`, copied byte for byte from
      `ci.yml:761-835`, with their comments. They test the local tag `vibey:ci`, so the
      bodies need no change.
   9. `- name: Release image - arm64 entrypoint runs under emulation`, with the same `env` as
      step 7 and the run:
      ```bash
      set -euo pipefail
      out=$(docker run --rm --platform linux/arm64 "${IMAGE}@${DIGEST}" --version)
      echo "$out"
      case "$out" in "vibey "*) ;; *) echo "::error::arm64 --version printed: $out"; exit 1 ;; esac
      ```
   10. `- name: Tag the tested digest as the release`, with the same `env` as step 7 and the run:
      ```bash
      set -euo pipefail
      docker buildx imagetools create \
        --tag "${IMAGE}:${VERSION}${TAG_SUFFIX}" \
        --tag "${IMAGE}:main${TAG_SUFFIX}" \
        --tag "${IMAGE}:latest${TAG_SUFFIX}" \
        "${IMAGE}@${DIGEST}"
      echo "tagged ${IMAGE}@${DIGEST} as ${VERSION}${TAG_SUFFIX}, main${TAG_SUFFIX}, latest${TAG_SUFFIX}"
      ```
2. Append this block to the end of `packaging/channels.toml`, preceded by one blank line
   (a Python `open(path, "a")` is fine, since TOML is order-free):
   ```toml
   [[channel]]
   name = "oci-image"
   ecosystem = "oci-image"
   publisher = "workflow"
   workflow = ".github/workflows/release.yml"
   job = "image"
   branches = ["main"]
   definition = ["deploy/docker/Dockerfile", ".github/workflows/release.yml"]
   excludes = "PostgreSQL and Ollama: point VIBEY_PG_URL at a database; codex is the only vendor engine CLI in the image."
   grace_hours = 2
   probe = { url = "https://ghcr.io/v2/the-vibey-project/vibey/manifests/{version}", accept = "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json" }
   options = { tag_suffix = "", contract_suffix = "" }
   enabled = true
   ```
3. New meta-test `tests/meta/test_release_image.py` (provenance line 1; docstring cites 2.b
   and ADR-0019 step 1). It loads `release.yml` and `ci.yml` with `yaml.safe_load`, and the
   registry with `vibey_gh.channels.CHANNEL_REGISTRY_LOADER`. A helper,
   `_contract_steps(steps, suffix)`, returns `{name: run}` for steps whose name starts with
   `Image contract - `: when `suffix` is empty, those with no ` (` in the name; otherwise
   those whose name ends with `suffix`.
   - `test_the_release_publishes_the_runnable_image`: job `image` exists and its `needs`
     contains `build` and `pypi`. Its `if` names `refs/heads/main`. Its permissions are
     `packages: write` and `contents: read`. Its push step has
     `platforms: linux/amd64,linux/arm64` and `push: true`, and its `tags` hold only a `sha-` tag.
   - `test_every_oci_image_channel_has_a_job_that_passes_ci_contracts`: for every channel
     with `ecosystem == "oci-image"`, there is exactly one `release.yml` job whose
     `env.DOCKERFILE == channel.definition[0]` and whose
     `env.TAG_SUFFIX == channel.option("tag_suffix")`. Its contract steps
     (`option("contract_suffix")`) equal `ci.yml`'s `image`-job contract steps for that suffix:
     the same names and identical `run` text. The set is non-empty.
   - `test_release_tags_follow_the_contracts`: in each such job, the step whose run holds
     `imagetools create` comes after every contract step, and tags
     `${VERSION}${TAG_SUFFIX}`, `main${TAG_SUFFIX}` and `latest${TAG_SUFFIX}`.
   - `test_the_image_names_the_governance`: the push step's `labels` contain the
     registry's `governance_url` (7.b), and its `annotations` contain `does not include`.
   - `test_the_new_run_blocks_are_valid_bash`: `bash -n` over each `run` in job `image`.
   Each failure message names ADR-0019 step 1 or the sub-doctrine.

## Where to change
- `.github/workflows/release.yml` (edit_file only; insert before `  realign:`).
- `packaging/channels.toml` (append).
- New `tests/meta/test_release_image.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes, including `test_packaging_channels.py` with the new channel.
- [ ] Changing one character of a copied contract step's `run` fails
      `test_every_oci_image_channel_has_a_job_that_passes_ci_contracts` (scratch edit, then revert).
- [ ] Moving the tag step above a contract step fails `test_release_tags_follow_the_contracts`.
- [ ] `python -c "import yaml;yaml.safe_load(open('.github/workflows/release.yml'))"` succeeds.
- [ ] The first `main` release after integration shows `ghcr.io/the-vibey-project/vibey:<version>`
      (the reviewer records the run URL; 10.f: until then the channel is unverified).

## Tests to write first (TDD)
`tests/meta/test_release_image.py`, with the five tests in item 3.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- The sovereign forge's registry (`gap-release-image-sovereign`) and the Arch Linux variant's
  job (`gap-release-image-arch`, after `gap-image-arch`).
- Images for `develop` builds: the build job stamps a dev version into its own workspace only
  (`release.yml:31-79`), so a develop image would misreport its version.
- `ci.yml` (unchanged; its steps are the source of truth), the chart's image reference, and docs.
- The package's public visibility on ghcr.io, which is set once (`gap-ops-packaging-credentials`).

Commit as `ci(release): publish the contract-tested runnable image on every release`. Do not push.

## Lane card
- **Depends on:** `gap-pkg-channels`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
