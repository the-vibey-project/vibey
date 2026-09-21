# vibey worker/server image.
#
# Two stages so the runtime layer carries no build toolchain and no uv:
# a compromised engine session running inside a worker should not find a
# compiler or a package manager waiting for it. The base image's own pip
# is removed below for the same reason. CI asserts every part of this,
# because a property stated only in a comment is one careless refactor
# away from silently lapsing -- pip was in fact present until the check
# was written.
#
# Both stages use /app as WORKDIR deliberately. `uv sync` installs the
# project in editable mode, so the venv holds an absolute path back to
# the source tree; building under /src and copying to /app would leave
# that pointer dangling. Same path in both stages, no rewriting needed.
#
# Migrations ship in the image because the worker applies them at startup
# (bootstrap resolves them relative to its own file: /app/src/vibey/…
# -> /app/migrations), so a chart install never depends on someone
# running SQL by hand first.
#
# One vendor engine binary ships too: `codex`, which codexloop drives. It is
# upstream's static musl build, verified by digest in the build stage and
# copied into the runtime stage alone -- no Node, no npm, no installer. CI
# asserts that as well: `codex --version` prints the pinned version, and
# neither node nor npm is on PATH.

FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim AS build

# The context-engine release is temporarily locked to an immutable Git commit
# until it has a newly versioned wheel. Git remains confined to this disposable
# build stage; only the resolved virtual environment is copied into runtime.
# curl is here for the codex fetch below and, like git, never leaves this stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# codex, the vendor CLI codexloop drives (`codex exec`, `codex app-server`), as
# upstream's static musl build: one self-contained executable, where the npm
# package would have brought Node and npm into the runtime layer -- the very
# package manager this image exists not to carry.
#
# Pinned by version and by the sha256 of each architecture's release tarball.
# Before those digests were written here they were checked two independent
# ways: each is the digest GitHub records for the asset
# (`gh api repos/openai/codex/releases/tags/rust-v<version>`, assets[].digest)
# and was recomputed over a fresh download; and the binary inside each tarball
# hashes to the entry OpenAI's release workflow
# (.github/workflows/rust-release.yml at that tag) signed into Rekor -- the
# `.sigstore` bundle published beside the asset, verified with sigstore-python
# against that workflow identity. LICENSE and NOTICE come from the same tag,
# digest-pinned too, because Apache-2.0 asks for both to travel with the binary.
#
# `dpkg --print-architecture`, not TARGETARCH: cluster-smoke builds with the
# classic builder (DOCKER_BUILDKIT=0), which never sets TARGETARCH, and dpkg
# reports the architecture this stage really runs as, emulated or not.
#
# Placed before the dependency layer so it caches across every source change.
# To bump, change CODEX_VERSION and every digest together; a stale digest
# fails the build here, at `sha256sum -c`, and never later.
ARG CODEX_VERSION=0.154.0
ARG CODEX_SHA256_AMD64=d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02
ARG CODEX_SHA256_ARM64=583b48df32804213bdcd338c2e5adb06b34340821fa757a726cc0a524fa33c27
ARG CODEX_LICENSE_SHA256=d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc
ARG CODEX_NOTICE_SHA256=9d71575ecfd9a843fc1677b0efb08053c6ba9fd686a0de1a6f5382fd3c220915
RUN set -eu; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) triple=x86_64-unknown-linux-musl; sha="$CODEX_SHA256_AMD64" ;; \
      arm64) triple=aarch64-unknown-linux-musl; sha="$CODEX_SHA256_ARM64" ;; \
      *) echo "no pinned codex build for $arch" >&2; exit 1 ;; \
    esac; \
    tag="rust-v${CODEX_VERSION}"; \
    mkdir -p /opt/codex/bin /opt/codex/share /tmp/codex; \
    cd /tmp/codex; \
    curl --proto '=https' --tlsv1.2 -fsSL -o codex.tar.gz \
      "https://github.com/openai/codex/releases/download/${tag}/codex-${triple}.tar.gz"; \
    curl --proto '=https' --tlsv1.2 -fsSL -o LICENSE \
      "https://raw.githubusercontent.com/openai/codex/${tag}/LICENSE"; \
    curl --proto '=https' --tlsv1.2 -fsSL -o NOTICE \
      "https://raw.githubusercontent.com/openai/codex/${tag}/NOTICE"; \
    printf '%s  %s\n' \
      "$sha" codex.tar.gz \
      "$CODEX_LICENSE_SHA256" LICENSE \
      "$CODEX_NOTICE_SHA256" NOTICE \
      | sha256sum -c -; \
    tar -xzf codex.tar.gz "codex-${triple}"; \
    install -m 0755 "codex-${triple}" /opt/codex/bin/codex; \
    install -m 0644 LICENSE NOTICE /opt/codex/share/; \
    cd /; \
    rm -rf /tmp/codex

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Dependency layer first: the lockfile changes far less often than source,
# so this caches across almost every rebuild.
COPY pyproject.toml uv.lock README.md ./
# No workspace member is needed here any more. It used to be: `vibey[skills]` required
# `vibey-skills`, uv had to BUILD that member to satisfy it, and the sync failed with
# "Distribution not found at: .../src/vibey_tools/skills" without the subtree. Since
# ADR-0037 no family package is a REQUIREMENT of anything -- they are packages of this
# wheel -- so `--no-install-project` resolves third-party dependencies alone and this
# layer caches on the lockfile by itself.
# --extra operator: the same image serves the worker and the operator
# Deployment, so kopf has to be present. --extra skills is now an empty compatibility
# alias (the context compiler ships in the wheel); the flag stays because removing it
# would be a silent behaviour change to every chart and script that passes it.
RUN uv sync --frozen --no-install-project --no-dev --extra operator --extra skills

# What the root wheel is built from. ADR-0021 cut this back to `src/vibey` because
# `COPY src/ ./src/` shipped roughly 160 MB of tests, docs and marketplace Markdown into
# a runtime image that could not execute any of it. ADR-0037 reverses the premise, not
# the discipline: the runners and tools are now PACKAGES of this wheel, so the final
# `uv sync` below builds the project and hatchling demands every path
# `[tool.hatch.build.targets.wheel]` names -- a missing one fails the build outright
# ("Forced include not found: .../gh/docs/javascripts/channel.js"), which is how this
# was found. So the list grew to exactly those paths and no further: eleven package roots,
# five force-include sources, and the ten tenant manifests uv's workspace globs
# (`src/vibey_runners/*`, `src/vibey_tools/*`) require of any member directory that
# exists in the context at all. Each tenant's tests/, docs/ and README still stay out.
#
# tests/meta/test_shipped_trees_are_reachable.py binds this list to the
# pyproject, so adding a package root without a COPY line fails in CI rather than in the
# `image` job's build log.
COPY src/vibey/ ./src/vibey/
COPY src/vibey_runners/claude/pyproject.toml ./src/vibey_runners/claude/
COPY src/vibey_runners/codex/pyproject.toml ./src/vibey_runners/codex/
COPY src/vibey_runners/cursor/pyproject.toml ./src/vibey_runners/cursor/
COPY src/vibey_runners/agy/pyproject.toml ./src/vibey_runners/agy/
COPY src/vibey_runners/qwen/pyproject.toml ./src/vibey_runners/qwen/
COPY src/vibey_runners/opencode/pyproject.toml ./src/vibey_runners/opencode/
COPY src/vibey_runners/common/pyproject.toml ./src/vibey_runners/common/
COPY src/vibey_tools/gh/pyproject.toml ./src/vibey_tools/gh/
COPY src/vibey_tools/bootstrap/pyproject.toml ./src/vibey_tools/bootstrap/
COPY src/vibey_tools/skills/pyproject.toml ./src/vibey_tools/skills/
COPY src/vibey_runners/claude/src/claudeloop/ ./src/vibey_runners/claude/src/claudeloop/
COPY src/vibey_runners/codex/src/codexloop/ ./src/vibey_runners/codex/src/codexloop/
COPY src/vibey_runners/cursor/src/cursorloop/ ./src/vibey_runners/cursor/src/cursorloop/
COPY src/vibey_runners/agy/src/agyloop/ ./src/vibey_runners/agy/src/agyloop/
COPY src/vibey_runners/qwen/src/qwenloop/ ./src/vibey_runners/qwen/src/qwenloop/
COPY src/vibey_runners/opencode/src/opencodeloop/ ./src/vibey_runners/opencode/src/opencodeloop/
COPY src/vibey_runners/common/src/vibey_runners/ ./src/vibey_runners/common/src/vibey_runners/
COPY src/vibey_tools/gh/vibey_gh/ ./src/vibey_tools/gh/vibey_gh/
COPY src/vibey_tools/bootstrap/vibey_bootstrap/ ./src/vibey_tools/bootstrap/vibey_bootstrap/
COPY src/vibey_tools/skills/src/vibey_skills/ ./src/vibey_tools/skills/src/vibey_skills/
COPY src/vibey_tools/skills/plugins/ ./src/vibey_tools/skills/plugins/
COPY src/vibey_tools/skills/.claude-plugin/marketplace.json ./src/vibey_tools/skills/.claude-plugin/
COPY src/vibey_tools/gh/docs/stylesheets/vibey.css ./src/vibey_tools/gh/docs/stylesheets/
COPY src/vibey_tools/gh/docs/javascripts/channel.js ./src/vibey_tools/gh/docs/javascripts/
COPY src/vibey_tools/gh/docs/javascripts/math.js ./src/vibey_tools/gh/docs/javascripts/
COPY migrations/ ./migrations/
RUN uv sync --frozen --no-dev --extra operator --extra skills


FROM python:3.12-slim-bookworm AS runtime

# tini is here for one reason, and it is not tidiness. Linux discards a signal sent to
# PID 1 while its disposition is still SIG_DFL, so whatever runs as PID 1 must have its
# handlers installed before the orchestrator can possibly signal it. A Python process
# cannot meet that bar: interpreter start and imports take hundreds of milliseconds on a
# cold container, and measured on minikube a pod was deleted ~600ms after its container
# started -- inside that window. The signal was not delivered late, it was discarded, and
# the worker then sat out its full 7200s grace period claiming jobs nobody wanted.
#
# tini is ready in microseconds and forwards to the child, which turns an unwinnable race
# into an ordinary one: SIGTERM during boot terminates a worker that has claimed nothing,
# which is both correct and prompt; SIGTERM after boot is drained gracefully.
#
# Git is independently a genuine runtime dependency: BUILD phase work happens
# in real git worktrees the worker creates itself.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

# python:slim ships a system pip that this image never uses -- everything
# runs from /app/.venv, which uv built without one. Left in place it is
# the single package manager a compromised session could actually reach:
# uid 10001 owns a writable $HOME, so `pip install --user` would succeed.
# apt-get stays, since it installs git above, and is inert by comparison
# -- it needs root, and the chart runs the pod non-root with
# allowPrivilegeEscalation false.
RUN rm -rf /usr/local/bin/pip /usr/local/bin/pip3 /usr/local/bin/pip3.* \
           /usr/local/lib/python3.12/site-packages/pip \
           /usr/local/lib/python3.12/site-packages/pip-*.dist-info

# Non-root by default. The worktree volume is chowned to this uid in the
# chart; nothing in the image itself needs write access to /app.
RUN useradd --create-home --uid 10001 vibey

WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/migrations /app/migrations
COPY --from=build /app/src /app/src

# The codex executable alone, plus the license and notice it ships under.
# Nothing it was fetched with -- curl, the tarball -- follows it here.
COPY --from=build /opt/codex/bin/codex /usr/local/bin/codex
COPY --from=build /opt/codex/share/ /usr/share/doc/codex/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER vibey

# No default subcommand: the chart's worker and server Deployments supply
# their own args, and an image that silently starts a worker is a footgun
# when someone runs it just to inspect the filesystem.
# `-g` forwards to the whole process group, so an engine subprocess the worker started is
# signalled too rather than being orphaned onto init.
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "vibey"]
CMD ["--help"]
