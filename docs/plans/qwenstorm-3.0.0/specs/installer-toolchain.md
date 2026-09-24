## Title
feat(install): the local stack declares the developer toolchain (git, uv, llama.cpp) and opt-in cluster tools

## Why
To run and develop vibey, a human developer also needs several tools:
- `git`, used by every worktree;
- `uv`, which runs the repository (CLAUDE.md "Commands worth memorizing");
- `llama-server`, the llama.cpp server that qwenloop starts when no Ollama is attached
  (`src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:249`, and `qwenloop doctor`
  at `cli/app.py:520`);
- for the opt-in cluster path, `helm`, `kubectl` and `minikube`.

The operator's standard (2026-09-22) requires all of them to be installable by `vibey install`
on Arch Linux and macOS, as declared data (sub-doctrine 12.c).

The package names were read on 2026-09-22 from archlinux.org and formulae.brew.sh:

| key | Arch (official `extra`) | macOS (Homebrew formula) |
|---|---|---|
| git | `git` | `git` |
| gh | `github-cli` | `gh` |
| uv | `uv` | `uv` |
| llama-server | `llama-cpp` (ships `/usr/bin/llama-server`) | `llama.cpp` |
| helm | `helm` | `helm` |
| kubectl | `kubectl` | `kubernetes-cli` |
| minikube | `minikube` | `minikube` |

`gh` is opt-in. Sub-doctrine 8.b (doctrines.md:122-123) makes Forgejo the forge default and
GitHub declared-only, so a GitHub client is not installed by default. The operator can flip
this one boolean.

## Required behaviour
1. Add these seven entries to `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py`,
   immediately after the `docker` entry, in this order. Every entry has installer `PACKAGE`.
   Arch recipes use `PackageSpec(PACMAN, (<arch name>,), (<binary>,))`, and macOS recipes use
   `PackageSpec(BREW_FORMULA, (<brew name>,), (<binary>,))`. No entry has a service, a probe
   or a post-install step.
   - git: title "git", group "toolchain", default True, binary `git`.
   - gh: title "GitHub CLI", group "toolchain", default False, binary `gh`.
     note: "opt-in: GitHub is declared-only under 8.b; Forgejo is the forge default".
   - uv: title "uv", group "toolchain", default True, binary `uv`.
   - llama-server: title "llama.cpp server", group "toolchain", default True, binary
     `llama-server`.
   - helm: title "Helm", group "cluster", default False, binary `helm`.
   - kubectl: title "kubectl", group "cluster", default False, binary `kubectl`.
   - minikube: title "minikube", group "cluster", default False, binary `minikube`,
     requires ("docker",).
2. `resolve(host, extra=("cluster",))` adds helm, kubectl and minikube, and minikube pulls in
   docker. `resolve(host)` includes git, uv and llama-server, and excludes gh and the cluster
   group.

## Where to change
- `src/vibey/domain/local_stack.py`: insert the entries. Use edit_file.
- `tests/domain/test_local_stack.py`: append tests.
- No other file.

## Acceptance criteria
- [ ] Both OSes' default resolutions contain git, uv and llama-server, after docker.
- [ ] gh and the cluster group are absent by default. `extra=("cluster",)` adds all three,
      and `extra=("gh",)` adds gh.
- [ ] Every new entry has a recipe for both OSes, with the exact names in the table.
- [ ] The guard tests (no shell or curl, and names present) pass. 100% domain coverage.

## Tests to write first (TDD)
Append to `tests/domain/test_local_stack.py`:
- `test_toolchain_defaults_are_git_uv_and_llama_server`
- `test_github_cli_is_opt_in_under_8b`
- `test_cluster_group_is_opt_in_and_minikube_requires_docker`
- `test_toolchain_package_names_per_os`, parametrized over the table.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Python itself: vibey is already running on it.
- vLLM.
- Any code outside the catalogue.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
