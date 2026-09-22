## Title
docs(reference): give every `vibey.toml` table in configuration.md a fenced TOML snippet

## Why
`docs/reference/configuration.md` is 515 lines with excellent heading structure (one
`##` per `[table]`, keyword-rich, each with a `| Field | Type | Default | Notes |`
table) but only 6 literal ` ``` ` fences in the whole file
(`grep -c '```' docs/reference/configuration.md`), most of which belong to the one
`## Full example` section at the very end (`configuration.md:459`) rather than to the 24
individual `[table]` sections above it. A reader — human or an LLM coding assistant
answering "how do I set a budget cap in vibey.toml" — currently has to reconstruct a
minimal snippet from a table row by hand; the ideal retrieved chunk for that query is a
three-line fenced TOML block directly under the `## \`[budget]\`` heading, not a table
cell. Reference documentation this well-structured deserves the same fencing discipline
its command reference is getting in the sibling lane `seo-cli-reference-examples`.

## Required behaviour
1. Immediately after each `## \`[section]\`` heading's field table (and before that
   section's own explanatory prose that follows the table, if any — the snippet sits
   right against the table it illustrates), insert one fenced ` ```toml ` block showing
   that exact table written out with realistic, non-default values wherever the table
   documents a default worth overriding, and the bare defaults otherwise. Six of the
   twenty-four are given here exactly; apply the identical pattern (one fenced snippet,
   directly under the table, using only field names/types the table already documents)
   to the remaining eighteen.

   Under `## \`[project]\`` (`configuration.md:130`):
   ```toml
   [project]
   name = "my-app"
   repo = "~/src/my-app"
   ```

   Under `## \`[budget]\`` (`configuration.md:159`):
   ```toml
   [budget]
   max_dollars_per_cycle = 15.0
   max_dollars_total = 250.0
   ```

   Under `## \`[engines]\`` (`configuration.md:189`):
   ```toml
   [engines]
   enabled = ["claudeloop", "agyloop"]

   [engines.weights]
   claudeloop = 3
   agyloop = 1
   ```

   Under `## \`[features]\`` (`configuration.md:266`):
   ```toml
   [features]
   qwenloop = true
   claudeloop_local = false
   ```

   Under `## \`[qwenloop]\`` (`configuration.md:278`):
   ```toml
   [qwenloop]
   ollama_url = "http://localhost:11434"
   ```

   Under `## \`[notifications]\`` (`configuration.md:231`):
   ```toml
   [notifications]
   enabled = true
   ```
2. For each of the remaining eighteen headings (`[isolation]`, `[verify]`,
   `[phases.design]`/`[phases.build]`/`[phases.review]`, `[provision]`, `[deploy]`,
   `[telemetry]`, `[tracker]`, `[docs]`, `[secrets]`, `[files]`, `[email]`, `[sms]`,
   `[messaging]`, `[config_store]`, `[cache]`, `[bus]`, `[blob]`, `[siem]`), read that
   section's own field table, and add one fenced ` ```toml ` block the same way: the
   table's own header line plus every field it documents, using the field's own stated
   default value unless the field is exactly the kind meant to be overridden (a URL, a
   cap, a boolean switch), in which case show one realistic overridden value instead of
   repeating the default verbatim — a snippet that just repeats every default adds
   little; a snippet that shows one field switched on is the one worth quoting.
3. Do not alter any existing prose, field table, or the `## Full example` section — this
   lane only inserts new fenced blocks; it does not rewrite explanations or duplicate
   the full-file example that already exists at the end.

## Where to change
- `docs/reference/configuration.md` only.

## Acceptance criteria
- [ ] `grep -c '^```toml$' docs/reference/configuration.md` is at least 24 (one per
      `[section]` heading covered by this lane).
- [ ] Every one of the 24 `^## \`\[` headings is followed, before the next `^## ` heading,
      by a ` ```toml ` fence whose first non-blank line is that exact table header
      (e.g. `[budget]`, `[phases.design]`).
- [ ] Every field name inside a new fence already appears in that same section's own
      `| Field | ... |` table — no invented key.
- [ ] The six worked examples in behaviour 1 appear verbatim.
- [ ] `git diff --stat` touches only `docs/reference/configuration.md`, and the diff is
      pure insertion.
- [ ] The pre-existing `## Full example` section's fenced block is unchanged.

## Tests to write first (TDD)
No project test suite parses `configuration.md`'s prose today. Verification is the
script below, run as this lane's own check:
```python
import re
from pathlib import Path

text = Path("docs/reference/configuration.md").read_text(encoding="utf-8")
lines = text.splitlines()
section_re = re.compile(r"^## `(\[[^`]+\])`")
fence_start_re = re.compile(r"^```toml$")
any_heading_re = re.compile(r"^## ")

missing = []
for i, line in enumerate(lines):
    m = section_re.match(line)
    if not m:
        continue
    table = m.group(1)
    j = i + 1
    found = False
    while j < len(lines) and not any_heading_re.match(lines[j]):
        if fence_start_re.match(lines[j]) and j + 1 < len(lines) and table.split(",")[0].strip() in lines[j + 1]:
            found = True
            break
        j += 1
    if not found:
        missing.append(table)

assert not missing, f"{len(missing)} config table(s) with no fenced example:\n" + "\n".join(missing)
print("ok: every [section] heading has a fenced TOML example")
```
The `[phases.design]`/`[phases.build]`/`[phases.review]` combined heading needs one
fence per phase name, or one fence covering all three explicitly — either satisfies the
check as written, since it only requires the first table name (`[phases.design`) to
appear inside the fence. If this script is still useful after the lane lands, promote
it to `tests/meta/test_configuration_reference_examples.py`; that decision belongs to
this lane, made once the file is final.

## Checks the lane must run (all must pass)
    grep -c '^```toml$' docs/reference/configuration.md
    python3 -c 'import re; from pathlib import Path; lines = Path("docs/reference/configuration.md").read_text(encoding="utf-8").splitlines(); idx = [i for i, l in enumerate(lines) if re.match(r"^## ", l)]; secs = [(i, re.match(r"^## `(\[[^`]+\])`", lines[i]).group(1)) for i in idx if re.match(r"^## `(\[[^`]+\])`", lines[i])]; ends = {i: (idx[idx.index(i)+1] if idx.index(i)+1 < len(idx) else len(lines)) for i, _ in secs}; missing = [t for i, t in secs if not any(re.match(r"^```toml$", lines[j]) and j+1 < len(lines) and t.split(",")[0].strip() in lines[j+1] for j in range(i+1, ends[i]))]; assert not missing, missing; print("ok")'

## Out of scope
- `docs/reference/cli.md` — its own lane, `seo-cli-reference-examples`.
- The `## Full example` section, and every field table's own explanatory prose.
- Any TOML key not already documented in the table it illustrates — do not add a new
  configuration surface while writing an example of an existing one.

Commit as `docs(reference): add a fenced TOML example to every [section] in configuration.md`.
Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
