#!/usr/bin/env bash
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Installed by `vibey-gh runner install`; edit the template in vibey-gh, not this copy.
#
# Registers one ephemeral runner, takes at most one job, exits. The supervisor on the host
# starts the next one. Single-use is the containment: a job that compromises this container
# gets a container that is about to be destroyed, with no state carried to the next.
set -euo pipefail

: "${RUNNER_REPOSITORY_URL:?RUNNER_REPOSITORY_URL is required}"
: "${RUNNER_TOKEN:?RUNNER_TOKEN is required}"
: "${RUNNER_LABELS:?RUNNER_LABELS is required}"

# A registration token is short-lived, so a fresh one per container is normal rather than a
# workaround. `--ephemeral` is what makes the runner deregister itself after one job.
./config.sh \
  --unattended \
  --ephemeral \
  --replace \
  --url "$RUNNER_REPOSITORY_URL" \
  --token "$RUNNER_TOKEN" \
  --labels "$RUNNER_LABELS" \
  --name "${RUNNER_LABELS%%,*}-$(hostname)-$$" \
  --work _work
unset RUNNER_TOKEN

# `config.sh remove` wants a REMOVAL token, a different credential from the registration
# token this container was given, so a container killed mid-life cannot deregister itself;
# the supervisor reaps those from the host, where it has gh. `run.sh` exits on its own after
# one job because the runner is ephemeral.
exec ./run.sh
