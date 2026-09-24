## Title
docs(reference): give every `vibey` command in cli.md a fenced, copy-pasteable example

## Why
`docs/reference/cli.md` is 417 lines with excellent heading structure (one `##` per
command, `###` for sub-topics, a Global-options/Exit-codes/Environment-variables
scaffold) and dense, accurate `| Option | Default | What it does |` tables — but it has
only 2 literal ` ``` ` fences in the whole file (`grep -c '```' docs/reference/cli.md`),
neither of which is a runnable example of the command it documents. Every one of the 16
`## \`vibey <command>\`` sections is prose plus a flags table with no single, realistic,
copy-pasteable invocation shown as a block. This is exactly the surface an LLM coding
assistant is asked to cite when a user asks "how do I run vibey worker with two local
engines" — a fenced example directly under the heading is what a RAG chunker keys on and
what a human copies verbatim; a flags table alone makes the assistant synthesize the
invocation itself, which it usually gets right but need not.

## Required behaviour
1. Immediately after each `## \`vibey <command>\`` heading's introductory prose
   paragraph(s) and before that section's own flags table (or, for a heading with no
   table, before its first sub-heading or the next `## `), insert one fenced ` ```bash `
   block containing one realistic invocation of that exact command, using at least one
   non-default flag already documented in that same section. Six of the sixteen are
   given here exactly; apply the identical pattern (one command, one code fence,
   directly under the prose, using flags the section already documents) to the
   remaining ten.

   Under `## \`vibey install\`` (`cli.md:72`):
   ```bash
   vibey install --postgres
   ```

   Under `## \`vibey new NAME\`` (`cli.md:100`):
   ```bash
   vibey new my-app --repo ~/src/my-app --max-cycle-dollars 15 --max-cycle-turns 40
   ```

   Under `## \`vibey answer GATE_ID [QUESTION_ID=ANSWER ...]\`` (`cli.md:116`):
   ```bash
   vibey answer 3f9c2a1e --defaults
   vibey answer 3f9c2a1e --raw '{"max_dollars": 25}'
   ```

   Under `## \`vibey doctor\`` (`cli.md:295`):
   ```bash
   vibey doctor --conformance --record
   ```

   Under `## \`vibey design\`` (`cli.md:165`):
   ```bash
   vibey design accept <project-id> --no-visual
   ```

   Under `## \`vibey worker\`` (`cli.md:360`):
   ```bash
   vibey worker --provider claudeloop --engines claudeloop,agyloop -j 2
   ```
2. For each of the remaining ten headings (`vibey work PROJECT_ID`,
   `vibey visual`, `vibey watch [PROJECT_ID]`, `vibey recover`,
   `vibey status [PROJECT_ID]`, `vibey engines [PROJECT_ID]`,
   `vibey cost [PROJECT_ID]`, `vibey ledger`, `vibey deploy`, `vibey operator`), read
   that section's own flags table and prose, and add one fenced ` ```bash ` block the
   same way: a real subcommand name where the section documents one (e.g. `vibey design
   resume`, `vibey deploy status`, `vibey ledger show`), and at least one flag from that
   section's own table where one exists and is not purely a placeholder ID.
3. Do not alter any existing prose or table row — this lane only inserts fenced blocks;
   it does not rewrite explanations.

## Where to change
- `docs/reference/cli.md` only.

## Acceptance criteria
- [ ] `grep -c '^```bash$' docs/reference/cli.md` is at least 16 (one per command
      heading; a command needing more than one example, like `vibey answer`, may have more).
- [ ] Every one of the 16 `^## \`vibey ` headings is followed, within the next 15 lines
      (or before the next `^## ` heading, whichever comes first), by a ` ```bash ` fence.
- [ ] Every command shown inside a new fence starts with `vibey ` and names a real
      subcommand/flag already documented somewhere in `cli.md` — no invented flag.
- [ ] `git diff --stat` touches only `docs/reference/cli.md`, and the diff is pure
      insertion — no existing line is removed or reworded.
- [ ] The six worked examples in behaviour 1 appear verbatim.

## Tests to write first (TDD)
No project test suite parses `cli.md`'s prose today. Verification is the script below,
run as this lane's own check rather than added as a permanent pytest (a heading-coverage
grep does not warrant a new permanent test file for one documentation page):
```python
import re
from pathlib import Path

text = Path("docs/reference/cli.md").read_text(encoding="utf-8")
lines = text.splitlines()
heading_re = re.compile(r"^## `vibey ")
fence_re = re.compile(r"^```bash$")
any_heading_re = re.compile(r"^## ")

missing = []
for i, line in enumerate(lines):
    if not heading_re.match(line):
        continue
    window = lines[i + 1 : i + 16]
    if not any(fence_re.match(w) for w in window):
        # allow the fence to appear anywhere before the next `##` heading, not just in 15 lines
        j = i + 1
        found = False
        while j < len(lines) and not any_heading_re.match(lines[j]):
            if fence_re.match(lines[j]):
                found = True
                break
            j += 1
        if not found:
            missing.append(line)

assert not missing, f"{len(missing)} command heading(s) with no fenced example:\n" + "\n".join(missing)
print("ok: every `vibey <command>` heading has a fenced example")
```
If this script is still useful after the lane lands, promote it to
`tests/meta/test_cli_reference_examples.py`; whether to do so is this lane's own call,
made once the file is in its final state.

## Checks the lane must run (all must pass)
    grep -c '^```bash$' docs/reference/cli.md
    python3 -c 'import re; from pathlib import Path; lines = Path("docs/reference/cli.md").read_text(encoding="utf-8").splitlines(); idx = [i for i, l in enumerate(lines) if re.match(r"^## ", l)]; heads = [i for i in idx if re.match(r"^## `vibey ", lines[i])]; ends = {i: (idx[idx.index(i)+1] if idx.index(i)+1 < len(idx) else len(lines)) for i in heads}; missing = [lines[i] for i in heads if not any(re.match(r"^```bash$", lines[j]) for j in range(i+1, ends[i]))]; assert not missing, missing; print("ok")'

## Out of scope
- `docs/reference/configuration.md` — its own lane, `seo-configuration-reference-examples`.
- Rewriting any flags table, prose paragraph, or the Global options/Exit codes/
  Environment variables sections — those are already accurate and are not this lane's
  concern.
- Adding runnable-example CI enforcement beyond this lane's own check (see Tests to
  write first) unless it is trivially cheap to keep; do not invent a heavier gate for a
  documentation-formatting lane.

Commit as `docs(reference): add a fenced example to every vibey command in cli.md`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
