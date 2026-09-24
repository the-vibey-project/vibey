#!/usr/bin/env bash
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
#
# Installed by `vibey-gh runner install` -- do not edit the installed copy; edit the template
# in vibey-gh (vibey_gh/templates/runner/) and re-install. `vibey-gh runner check` reports drift.
#
# Supervisor for the ephemeral self-hosted runner behind the sovereign review lane
# (`[pr_automation.fallback]`, sub-doctrine 8.a).
#
# Each iteration registers a runner that takes AT MOST ONE job and exits, per GitHub's
# just-in-time guidance. That bounds any compromise to a single job rather than letting it
# persist across them -- which matters here because this is a public repository, the one
# configuration GitHub says self-hosted runners "should almost never be used for."
#
# The containment that makes that tolerable is not in this file alone:
#   - the sovereign job never runs for a fork PR (`trusted_only`, enforced in the workflow),
#   - the review workflow is `pull_request_target`, so a PR cannot alter what reviews it,
#   - the job never executes repository code -- the diff reaches the model as text,
#   - the runner runs in a container, so a checkout never touches the host filesystem.
#
# Every setting arrives from the LaunchAgent, which `vibey-gh runner install` renders from
# the repository's `[runners]` table. None has a default here: a default in this file is a
# value nobody declared, and the last one (a retired repository's URL) kept registering
# against a repository that no longer existed.
#
# Requires: docker, `ollama serve` reachable on the host, and the runner's OWN gh login in
# $GH_CONFIG_DIR (see docs/runbooks/sovereign-review-runner.md).
set -euo pipefail

log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
refuse() {
  log "REFUSING TO START: $*"
  exit 1
}

for setting in VIBEY_REPO_URL VIBEY_RUNNER_LABEL VIBEY_RUNNER_IMAGE VIBEY_OLLAMA_URL \
  VIBEY_CONTAINER_OLLAMA_URL VIBEY_REQUIRE_AC VIBEY_MAX_FAILURES; do
  [ -n "${!setting:-}" ] || refuse "$setting is not set -- this script is started by the \
LaunchAgent 'vibey-gh runner install' renders, which sets it from [runners]"
done

REPO_URL="$VIBEY_REPO_URL"
RUNNER_LABEL="$VIBEY_RUNNER_LABEL"
RUNNER_IMAGE="$VIBEY_RUNNER_IMAGE"
OLLAMA_URL="$VIBEY_OLLAMA_URL"
CONTAINER_OLLAMA_URL="$VIBEY_CONTAINER_OLLAMA_URL"
REQUIRE_AC="$VIBEY_REQUIRE_AC"
MAX_FAILURES="$VIBEY_MAX_FAILURES"
GH_HOSTNAME="${REPO_URL#https://}"
GH_HOSTNAME="${GH_HOSTNAME%%/*}"
REPO_SLUG="${REPO_URL#https://"$GH_HOSTNAME"/}"
REPO_SLUG="${REPO_SLUG%.git}"

# ---------------------------------------------------------------------------------------
# Sleep suppression.
#
# Re-exec under `caffeinate` in its UTILITY form. With a utility argument the assertions
# are bound to that process's lifetime and released automatically when it exits, crashes,
# or is killed. A bare `caffeinate -i &` outlives its parent and leaves a machine that
# never sleeps and a daemon nobody remembers starting.
#
#   -i  prevent idle system sleep -- the one that matters. A sleeping runner does not poll
#       GitHub at all, so the job never arrives rather than arriving and failing.
#   -m  prevent disk idle sleep, so a job does not stall waking storage.
#   -s  prevent system sleep. AC only; silently inert on battery, harmless to pass.
#
# `caffeinate` does NOT survive a closed lid: clamshell sleep is enforced below the
# assertion layer. Lid-open (or true clamshell with an external display and power) is the
# availability window; there is no software fix for this from inside Actions.
# ---------------------------------------------------------------------------------------
if [ "${VIBEY_CAFFEINATED:-}" != "1" ]; then
  export VIBEY_CAFFEINATED=1
  exec caffeinate -i -m -s -- "$0" "$@"
fi

# On battery, `pmset -g custom` reports `sleep 1` -- asleep one minute after you walk away.
# Holding an assertion against that drains the battery to keep a runner idle-polling. Exit
# 0: launchd's KeepAlive retries after ThrottleInterval, so it comes back on AC by itself.
if [ "$REQUIRE_AC" = "1" ] && ! pmset -g batt | grep -q "AC Power"; then
  log "on battery power -- not starting the runner ([runners] require_ac = false overrides)"
  exit 0
fi

# ---------------------------------------------------------------------------------------
# The credential.
#
# The supervisor mints a registration token per job (a token lives about an hour; one
# minted at startup 404s every re-registration after it expires). Minting needs a durable
# GitHub credential, and the ONLY one this script may use is the runner's own gh login in
# $GH_CONFIG_DIR: a fine-grained token limited to this repository with Administration
# read/write, stored in a file by `gh auth login --insecure-storage`.
#
# Why not the operator's own `gh` login: it keeps its token in the macOS keyring, which a
# LaunchAgent cannot read -- `gh auth status` fails under launchd while passing in every
# shell, which is how this runner stayed down unnoticed. And a login that can administer
# every repository the operator owns is far more than a runner needs.
#
# So there is no fallback of any kind. GH_TOKEN and friends are cleared because gh prefers
# them over any stored login; an unset GH_CONFIG_DIR is refused because gh would then read
# the operator's default directory; a directory whose token went to the keyring is refused
# because that is the keyring again. The token itself is never printed.
# ---------------------------------------------------------------------------------------
unset GH_TOKEN GITHUB_TOKEN GH_ENTERPRISE_TOKEN GITHUB_ENTERPRISE_TOKEN
if [ -z "${GH_CONFIG_DIR:-}" ]; then
  refuse "GH_CONFIG_DIR is not set, so gh would use the operator's own login (and the macOS \
keyring, which launchd cannot read). 'vibey-gh runner install' sets it from [runners] gh_config_dir"
fi
export GH_CONFIG_DIR
LOGIN="env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=$GH_CONFIG_DIR gh auth login \
--hostname $GH_HOSTNAME --with-token --insecure-storage   (paste the runner's fine-grained \
token for $REPO_SLUG -- Administration: Read and write -- then Ctrl-D; see \
docs/runbooks/sovereign-review-runner.md)"
[ -d "$GH_CONFIG_DIR" ] || refuse "the runner's gh config directory $GH_CONFIG_DIR does not \
exist. Create it and log in: mkdir -m 700 -p $GH_CONFIG_DIR && $LOGIN"
HOSTS="$GH_CONFIG_DIR/hosts.yml"
[ -f "$HOSTS" ] || refuse "$GH_CONFIG_DIR holds no gh login (no hosts.yml). Log in: $LOGIN"
grep -Eq '^[[:space:]]+oauth_token:[[:space:]]*[^[:space:]]' "$HOSTS" || refuse "$HOSTS holds \
no token of its own: it went to the macOS keyring, which a LaunchAgent cannot read. Log in \
again with --insecure-storage: $LOGIN"
if [ -n "$(find "$HOSTS" \( -perm -040 -o -perm -004 \) 2>/dev/null)" ]; then
  refuse "$HOSTS is readable by other users; it holds a token. Run: chmod 600 $HOSTS"
fi
gh auth status --hostname "$GH_HOSTNAME" > /dev/null 2>&1 || refuse "the token in \
$GH_CONFIG_DIR is not accepted by $GH_HOSTNAME (expired or revoked?). Replace it: $LOGIN"

# Fail closed on a missing model. A lane that cannot reach its model must skip so the gate
# stays red and a human looks, never emit a default pass.
if ! curl -fsS --max-time 5 "${OLLAMA_URL}/api/version" > /dev/null 2>&1; then
  refuse "ollama is not reachable at ${OLLAMA_URL} -- run 'ollama serve' first"
fi

# Checked explicitly: under `set -e` a dead daemon used to end this script silently at the
# first `docker ps`, leaving a log of nothing but "supervisor stopping" every two minutes.
docker info > /dev/null 2>&1 || refuse "docker is not running -- start Docker Desktop (the \
runner is a container)"
docker image inspect "$RUNNER_IMAGE" > /dev/null 2>&1 || refuse "the image $RUNNER_IMAGE is \
not built -- run the 'docker build' command 'vibey-gh runner install' printed"

mint_token() {
  gh api -X POST "repos/${REPO_SLUG}/actions/runners/registration-token" --jq .token 2> /dev/null
}

# Reap offline runners left behind by a container that was killed mid-life. The container
# cannot do this itself: `config.sh remove` needs a REMOVAL token, a different credential
# from the registration token it holds. The host has gh, so it does the reaping.
reap_offline() {
  local ids
  ids=$(gh api "repos/${REPO_SLUG}/actions/runners" \
    --jq ".runners[] | select(.status == \"offline\" and (.labels[].name | contains(\"${RUNNER_LABEL}\"))) | .id" \
    2> /dev/null | sort -u) || true
  for id in $ids; do
    gh api -X DELETE "repos/${REPO_SLUG}/actions/runners/${id}" > /dev/null 2>&1 \
      && log "reaped offline runner ${id}"
  done
}

cleanup() {
  log "supervisor stopping; sleep assertions released"
  reap_offline
}
trap cleanup EXIT INT TERM

# Stop any container this supervisor left behind. `docker run` is owned by the Docker
# daemon, not by this shell, so a SIGKILL here (launchd restarting the job, a hard kill)
# orphans a container that stays registered and listening. Filtered by LABEL, not by image:
# several supervisors may share the image, and filtering on it would make each one stop the
# others' containers on startup.
stray=$(docker ps -q --filter "label=vibey-runner-label=${RUNNER_LABEL}" 2> /dev/null) || true
if [ -n "$stray" ]; then
  log "stopping $(wc -w <<< "$stray" | tr -d ' ') orphaned runner container(s) from a previous supervisor"
  # shellcheck disable=SC2086 # one container id per word, deliberately split
  docker stop $stray > /dev/null 2>&1 || true
fi

log "supervisor starting: label=${RUNNER_LABEL} repo=${REPO_URL} gh-config=${GH_CONFIG_DIR}"
log "sleep assertions held -- verify with: pmset -g assertions | grep -i caffeinate"

failures=0
while true; do
  token=$(mint_token) || token=""
  if [ -z "$token" ]; then
    log "could not mint a registration token for ${REPO_SLUG} with the login in \
${GH_CONFIG_DIR} -- its token needs Administration: Read and write on that repository"
    exit 1
  fi

  reap_offline
  log "registering an ephemeral runner (one job, then exit)"
  # --rm and --ephemeral together are what make this single-use. --add-host lets the
  # container reach Ollama on the host; that port is the one hole through the isolation,
  # so keep Ollama bound to loopback and treat it as the trust boundary. The registration
  # token goes over the environment (`-e RUNNER_TOKEN` with no value copies it from this
  # process), never the argv, where any local user's `ps` could read it.
  if RUNNER_TOKEN="$token" docker run --rm \
    --label "vibey-runner-label=${RUNNER_LABEL}" \
    --add-host host.docker.internal:host-gateway \
    -e RUNNER_REPOSITORY_URL="$REPO_URL" \
    -e RUNNER_TOKEN \
    -e RUNNER_LABELS="$RUNNER_LABEL" \
    -e RUNNER_EPHEMERAL=1 \
    -e VIBEY_OLLAMA_URL="$CONTAINER_OLLAMA_URL" \
    "$RUNNER_IMAGE"; then
    failures=0
  else
    # Give up rather than spin. A loop that re-registers forever on a permanent fault -- a
    # revoked credential, a moved repository, a broken image -- burns a container every few
    # seconds and buries the real error thousands of lines up its own log.
    failures=$((failures + 1))
    log "runner exited non-zero (${failures} consecutive)"
    if [ "$failures" -ge "$MAX_FAILURES" ]; then
      log "${failures} consecutive failures -- stopping. The cause is in the log above."
      exit 1
    fi
  fi
  token=""
  sleep 5
done
