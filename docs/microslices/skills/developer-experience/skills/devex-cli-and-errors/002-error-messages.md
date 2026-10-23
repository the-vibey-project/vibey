---
id: skill-error-messages-270856393a
purpose: error messages
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-cli-and-errors/SKILL.md
requires: ["skill-cli-89b494e62e"]
links: []
---

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
