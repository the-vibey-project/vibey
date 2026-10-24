---
name: devex-cli-and-errors
description: "Use when designing or reviewing a command-line interface or the errors any developer tool prints: stdout versus stderr, exit codes, --help with examples, --json and --plain output, NO_COLOR, --no-input, --dry-run, --force, config precedence, flag naming, telemetry and DO_NOT_TRACK, typo suggestions, shell completion, stable error codes with --explain, error severity levels, or keeping CLI, API and UI errors in one shape. Triggers on CLI design, command line guidelines, clig, error message design, Rust diagnostics, exit codes, machine-readable output. Companion to the other developer-experience skills."
---

# Developer Experience: Command-Line Interfaces and Error Messages

> **Part 2 of 9** of the *Developer Experience Blueprint* (plugin `developer-experience`), covering: CLI; Error messages. Sibling skills: `devex-principles-and-feedback-loops`, `devex-api-sdk-and-docs`, `devex-interfaces-onboarding-and-agents`, `devex-surface-placement`, `devex-editor-and-desktop-surfaces`, `devex-mobile-and-web-surfaces`, `devex-non-developers-and-visual-design`, `devex-reference`. A reference into a sibling is written *Section name → `skill`*.
>
> **Currency:** the blueprint is dated Oct 23, 2026; its evidence base and the AI-tooling claims age fastest, so re-check those first.
>
> Evidence grades used throughout: **A** = peer-reviewed or large study, **B** = credible practitioner or single study, **C** = vendor or opinion. Thin evidence is flagged where it occurs, and collected under *Where the evidence is weak or conflicting* in `devex-reference`.

## CLI

The spec below follows the [Command Line Interface Guidelines](https://github.com/cli-guidelines/cli-guidelines) (read through a [condensed copy](https://cdn.jsdelivr.net/npm/@hacxy/skills@0.1.0/skills/create-cli/references/cli-guidelines.md), since clig.dev itself could not be fetched).

| Area | Rule |
| --- | --- |
| Output streams | Primary data to stdout; messages, progress and errors to stderr |
| Exit codes | 0 on success, non-zero on failure; use distinct codes for usage errors, not-found and transient failures, and document them |
| Help | `-h`/`--help` on every command; lead with examples; show the most common flags first; suggest the next command |
| Color and TTY | Color and spinners only on a TTY; honor [NO\_COLOR](https://no-color.org) and a `--no-color` flag |
| Machine output | `--json` for stable structured output; `--plain` for line-oriented text; never change field names without a version bump |
| Interactivity | Prompt only on a TTY; `--no-input` disables all prompts; never require a prompt for something a flag can supply |
| Safety | `--dry-run` for destructive or remote actions; confirm dangerous operations; `--force` skips confirmation |
| Config precedence | Flags, then environment variables, then project config, then user config, then defaults; print the effective value on request |
| Speed | Respond within about 100 ms; print something before slow work begins; show progress for anything longer |
| Naming | Verb-noun or noun-verb, picked once and applied everywhere; no ambiguous abbreviations; short flags only for the most common options |
| Compatibility | Additive changes only inside a major version; warn before removing anything |
| Telemetry | Opt-in, documented, disclosed on first run, and off when `DO_NOT_TRACK` is set |

**Typo and discovery help.** Suggest the closest command for a misspelling, offer shell completion for bash, zsh and fish, and ship a man page or `help` topic for each concept.

**Agent-friendly extras.** JSON output, semantic exit codes, no required prompts and self-describing commands make a CLI easy for AI agents to drive. This pattern is supported by weak, practitioner-only evidence, but it costs little and also helps scripts.

## Error messages

An error is the most-read text in your product: eye-tracking work finds developers spend roughly 13–25% of task time reading errors, and a [study of compiler messages](https://neverworkintheory.org/2021/09/02/compiler-error-messages-considered-unhelpful.html) found many unhelpful. The Rust compiler is the best-documented model ([diagnostics guide](https://rustc-dev-guide.rust-lang.org/diagnostics.html)).

1. **Say what failed, in the user's terms**, in one line, before any detail.
2. **Point at the exact place** (file, line, column, or the offending flag or field) and show the code or input.
3. **Say why** when the cause is not obvious.
4. **Give the fix**, as a command or a code change; mark suggestions as safe to auto-apply or as needing review, as Rust's suggestion applicability levels do.
5. **Give a stable code** (for example `E0382`) that links to a longer explanation, and support `--explain <code>`.
6. **Separate severity levels** (error, warning, note, help) and keep warnings rare enough that people read them.
7. **Never lead with a stack trace.** Put it behind a flag and write the location of the log file in the message.
8. **Keep the same shape** for CLI, API and UI errors so that people learn it once.

For API errors add a machine-readable `type`, a human `message`, a `request_id` for support and a docs link. An elm-style friendly tone helps, but clarity matters more than personality.

One study found that adding LLM-generated explanations to errors did not help; fix the message itself before adding a layer on top of it.
