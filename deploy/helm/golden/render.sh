#!/usr/bin/env bash
# deploy/helm/golden/render.sh [--update]
#
# Lint the vibey chart under every profile below, render it, and compare each
# render with its committed golden file. CI runs it with no argument (the
# `chart` job in .github/workflows/ci.yml); after an intended chart change,
# run it with --update and review the golden diff like any other change.
#
# Why goldens, when cluster-smoke already installs the chart: cluster-smoke
# only ever installs the DEFAULTS (plus keda.enabled). Everything else -- the
# in-cluster Ollama, the worker wiring it adds, the KEDA query's project
# scoping -- would otherwise reach a cluster without anything having looked at
# what it renders to. A golden turns "the defaults stay unchanged" and "this
# is the manifest ollama.enabled produces" into facts a diff can refute.
#
# The profiles are declared here and nowhere else, so CI and a contributor
# regenerating goldens can never disagree about what was rendered. Rendered
# with the helm version the `chart` job pins; another version may format
# differently, which is a reason to bump the pin, not to loosen the check.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CHART="$ROOT/deploy/helm/vibey"
GOLDEN="$ROOT/deploy/helm/golden"
# A fixed, obviously-synthetic project id for the profiles that bind one.
PROJECT=6f1c2a4e-0000-4000-8000-000000000000

UPDATE=0
case "${1:-}" in
  "") ;;
  --update) UPDATE=1 ;;
  *) echo "usage: $0 [--update]" >&2; exit 2 ;;
esac

command -v helm >/dev/null 2>&1 || { echo "helm is not on PATH" >&2; exit 1; }

failed=0
scratch="$(mktemp -d "${TMPDIR:-/tmp}/vibey-golden.XXXXXX")"
trap 'rm -rf "$scratch"' EXIT

# profile NAME [--show-only TEMPLATE ...] -- [VALUE ARGS ...]
#
# The value arguments are linted against the whole chart; --show-only narrows
# only what is compared, so a focused golden still proves the full chart
# renders with those values.
profile() {
  local name="$1"; shift
  local show=()
  while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
    show+=("$1"); shift
  done
  [ "$#" -gt 0 ] && shift
  local values=("$@")

  helm lint "$CHART" --strict --namespace vibey ${values[@]+"${values[@]}"} >/dev/null \
    || { echo "FAIL lint     $name" >&2; failed=1; return; }

  local rendered="$scratch/$name.yaml"
  helm template vibey "$CHART" --namespace vibey \
    ${values[@]+"${values[@]}"} ${show[@]+"${show[@]}"} > "$rendered" \
    || { echo "FAIL template $name" >&2; failed=1; return; }

  local golden="$GOLDEN/$name.yaml"
  if [ "$UPDATE" = 1 ]; then
    cp "$rendered" "$golden"
    echo "wrote   $name"
  elif diff -u "$golden" "$rendered"; then
    echo "ok      $name"
  else
    echo "FAIL golden   $name: the render differs from $golden (run $0 --update if intended)" >&2
    failed=1
  fi
}

# The install cluster-smoke performs. Must change only when a chart change
# is meant to reach every default install.
profile default --
# The in-cluster Ollama, whole: its volume, Service, Deployment, pull Job, and
# the worker environment that points vibey and gptossloop at it.
profile ollama -- --set ollama.enabled=true
# The GPU branch and the local-runner worker wiring, narrowed to what they
# touch: gptossloop as the provider, and qwenloop switched on beside it, so
# its Qwen model is pulled and handed to it (ADR-0062).
profile ollama-gpu-gptossloop \
  --show-only templates/ollama.yaml --show-only templates/worker.yaml -- \
  --set ollama.enabled=true --set ollama.gpu.enabled=true \
  --set ollama.qwenloopFeature=true \
  --set worker.provider=gptossloop --set 'worker.engines=gptossloop\,qwenloop'
# The KEDA claimable-work query, scoped to the project the worker serves:
# unbound (the newest project, as the worker itself resolves it) and bound.
profile keda-latest --show-only templates/keda-scaledobject.yaml -- \
  --set keda.enabled=true
profile keda-project --show-only templates/keda-scaledobject.yaml -- \
  --set keda.enabled=true --set worker.project="$PROJECT"
# All sovereign surfaces disabled: proves the chart still installs without
# them and matches the non-surfaces baseline.
profile surfaces-off -- --set surfaces.enabled=false
# A managed database through an existing Secret (ADR-0055, review of #1100): no
# `migrate` init container and no owner key unless the Secret names one, so an
# upgrade never strands the worker on a key the Secret does not have.
profile existing-secret --show-only templates/worker.yaml -- \
  --set postgres.enabled=false --set dsn.existingSecret=vibey-db

exit "$failed"
