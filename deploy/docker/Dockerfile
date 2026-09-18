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

FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm-slim AS build

# The context-engine release is temporarily locked to an immutable Git commit
# until it has a newly versioned wheel. Git remains confined to this disposable
# build stage; only the resolved virtual environment is copied into runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

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
# was found. So the list grew to exactly those paths and no further: ten package roots,
# five force-include sources, and the nine tenant manifests uv's workspace globs
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
COPY src/vibey_runners/common/pyproject.toml ./src/vibey_runners/common/
COPY src/vibey_tools/gh/pyproject.toml ./src/vibey_tools/gh/
COPY src/vibey_tools/bootstrap/pyproject.toml ./src/vibey_tools/bootstrap/
COPY src/vibey_tools/skills/pyproject.toml ./src/vibey_tools/skills/
COPY src/vibey_runners/claude/src/claudeloop/ ./src/vibey_runners/claude/src/claudeloop/
COPY src/vibey_runners/codex/src/codexloop/ ./src/vibey_runners/codex/src/codexloop/
COPY src/vibey_runners/cursor/src/cursorloop/ ./src/vibey_runners/cursor/src/cursorloop/
COPY src/vibey_runners/agy/src/agyloop/ ./src/vibey_runners/agy/src/agyloop/
COPY src/vibey_runners/qwen/src/qwenloop/ ./src/vibey_runners/qwen/src/qwenloop/
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
