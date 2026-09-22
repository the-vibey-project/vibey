## Title
feat(install): vibey install sets up local Ollama and this era's default model

## Why
The operator wants local Ollama in the installer (2026-09-22). Ratified sub-doctrine 8.d designates
GPT-OSS 20B served by Ollama as this era's default model (#390), and 8.b keeps the sovereign path
always on — but `vibey install` (src/vibey/cli/main.py, the `install` command) handles one target,
`--postgres`, through `PostgresLocalService`, and exits 2 without it. Nothing installs, starts or
checks Ollama, so a fresh machine has no sovereign engine until the operator does it by hand.

## Required behaviour
1. `vibey install --ollama` installs Ollama with the host package manager (macOS: Homebrew; Linux:
   the distribution's package where one exists, otherwise Ollama's published release archive
   verified against its published SHA-256 — never a remote script piped into a shell), starts it
   as a service (brew services / systemd), and waits for `GET http://127.0.0.1:11434/api/version`.
2. It then pulls the default model — `gpt-oss:20b` today, read from the same catalogue constant as
   #387, never hard-coded twice — after printing the download size and asking to confirm; `--yes`
   confirms up front, `--no-model` skips the pull, `--model NAME` pulls another.
3. Already installed and running: say so and do nothing (idempotent under replay).
4. `vibey install` with no target installs the sovereign local stack: PostgreSQL (as `--postgres`
   does today) and Ollama with the default model; any explicit flag narrows it. RabbitMQ joins this
   set when its installer lands (ADR-0044 lane R33).
5. `vibey doctor` reports Ollama's state (not installed / installed but stopped / running) and
   whether the default model is present, with the command that fixes each.
6. Follow `PostgresLocalService`'s shape: an `OllamaLocalService` class with its interface beside it
   (ADR-0016) in infrastructure/, a subprocess boundary the tests fake, and a result object with
   `ok`, `status` and `detail`.

## Acceptance criteria
- [ ] Faked package managers: install, start, wait and pull on macOS and Linux paths; the checksum
      path refuses a mismatched archive.
- [ ] Idempotent: a second run changes nothing and says so.
- [ ] The pull asks before downloading unless `--yes`; `--no-model` and `--model` work.
- [ ] `vibey install` with no flags runs both targets; `doctor` reports Ollama and the model.
- [ ] Root gates at 100% per layer.

## Tests to write first (TDD)
tests/infrastructure/ for OllamaLocalService (fake subprocess and HTTP); tests/cli/ for the
install flags, the no-flag default, the confirmation and the doctor lines.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src/vibey && uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure tests/cli
    (and the four per-layer coverage gates)

## Out of scope
RabbitMQ install (R33), llama.cpp, the model catalogue (#383), docs. Commit as `feat(install): ...`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
