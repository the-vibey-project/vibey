# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Installed by `vibey-gh runner install`; edit the template in vibey-gh, not this copy.
#
# Ephemeral GitHub Actions runner for the sovereign review lane.
#
# The container is the isolation boundary. An untrusted diff is fetched inside it and never
# reaches the host filesystem, keychain, or SSH keys -- which is what makes running this
# against a public repository defensible at all. It is disposable by construction: the
# supervisor starts one per job and `--rm` destroys it afterwards.
#
# Build with the command `vibey-gh runner install` prints; it passes RUNNER_VERSION from
# `[runners] runner_version`. There is no default here, so the release is always declared.
FROM ubuntu:24.04

ARG RUNNER_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# libicu is not optional: the runner host is a .NET binary and refuses to start without it
# ("Libicu's dependencies is missing for Dotnet Core"). The runner ships an
# `installdependencies.sh` that wants sudo at runtime; installing here instead keeps the
# container's runtime privileges minimal, which is the point of running as `runner`.
#
# The native libraries are the ones that script asks apt for, spelled as noble spells them:
# ubuntu:24.04 renamed liblttng-ust1 and libssl3 in the 64-bit time_t transition, to
# liblttng-ust1t64 and libssl3t64 (the old names are "not available in this suite" on
# packages.ubuntu.com/noble). libkrb5-3, zlib1g and libicu74 kept their names.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git jq python3 python3-pip python3-venv \
      libicu74 liblttng-ust1t64 libkrb5-3 zlib1g libssl3t64 \
    && rm -rf /var/lib/apt/lists/*

# gh, for the diff fetch. The runner's own GITHUB_TOKEN authorises it; no PAT is baked in.
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] \
https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

# The runner refuses to execute as root, and that refusal is worth keeping rather than
# working around with --allow-runasroot: it is the last privilege boundary inside a
# container that is deliberately handling untrusted input.
RUN useradd -m -s /bin/bash runner
USER runner
WORKDIR /home/runner

RUN test -n "$RUNNER_VERSION" || { echo "build with --build-arg RUNNER_VERSION=X.Y.Z" >&2; exit 1; } \
    && ARCH=$(dpkg --print-architecture) \
    && case "$ARCH" in \
         amd64) RUNNER_ARCH=x64 ;; \
         arm64) RUNNER_ARCH=arm64 ;; \
         *) echo "unsupported architecture: $ARCH" >&2; exit 1 ;; \
       esac \
    && curl -fsSL -o runner.tar.gz \
      "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-${RUNNER_ARCH}-${RUNNER_VERSION}.tar.gz" \
    && tar xzf runner.tar.gz \
    && rm runner.tar.gz

COPY --chown=runner:runner entrypoint.sh /home/runner/entrypoint.sh
ENTRYPOINT ["/home/runner/entrypoint.sh"]
