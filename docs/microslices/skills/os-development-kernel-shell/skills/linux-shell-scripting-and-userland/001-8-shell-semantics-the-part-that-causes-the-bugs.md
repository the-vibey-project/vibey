---
id: skill-8-shell-semantics-the-part-that-causes-the-bugs-17db45c4f3
purpose: 8 shell semantics the part that causes the bugs
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-shell-scripting-and-userland/SKILL.md
requires: []
links: ["skill-9-choosing-a-shell-1420b58c65"]
---

## §8. Shell Semantics — the part that causes the bugs

**[DURABLE] The shell is a macro language over process execution, and its evaluation
order is the source of nearly every shell bug.** Learn the order and most mysteries
dissolve.

### 8.1 The expansion order

For each command word, in this exact sequence:
```
1. Brace expansion            {a,b}  {1..5}          (bash/zsh; NOT POSIX)
2. Tilde expansion            ~  ~user
3. Parameter expansion        $var  ${var:-def}  ${var#pat}  ${var//a/b}
   Command substitution       $(cmd)   `cmd`
   Arithmetic expansion       $(( ... ))
4. WORD SPLITTING             ← splits UNQUOTED results on $IFS   ★ the bug lives here
5. Pathname expansion (glob)  *  ?  [abc]           ← on UNQUOTED results   ★ and here
6. Quote removal
```
**Steps 4 and 5 do not happen inside double quotes.** That single fact is why the rule is
"quote everything."

```bash
file="my report.txt"
rm $file        # → rm my report.txt   → tries to remove TWO files. Data loss.
rm "$file"      # → rm 'my report.txt' → correct.

files=$(ls)     # word-splits AND globs the output. Filenames with spaces or * break it.
                # Also: NEVER parse ls. Use a glob or find -print0.
```

### 8.2 The traps, ranked by how much damage they cause

> **⚠️ 1. Unquoted variables.** Covered above. `shellcheck` flags every instance.
> This is the number one shell bug and it is 100% mechanically detectable.

> **⚠️ 2. `$@` vs `$*`.** `"$@"` expands to one word per argument, preserving them
> exactly. `"$*"` joins them into a single word with the first `$IFS` char. **Always
> `"$@"`, always quoted.** Unquoted `$@` word-splits again and defeats the purpose.

> **⚠️ 3. The pipeline exit status.** By default `$?` is the **last** command's status:
> `false | true` succeeds. `set -o pipefail` makes the pipeline fail if any element
> fails. `${PIPESTATUS[@]}` (bash) has the individual statuses.

> **⚠️ 4. Pipelines create subshells.** `... | while read x; do count=$((count+1)); done`
> leaves `count` unchanged in bash, because the loop ran in a subshell. Fix with process
> substitution: `while read x; do ...; done < <(cmd)`, or `shopt -s lastpipe`.
> **zsh does not have this problem** — it runs the last pipeline element in the current
> shell.

> **⚠️ 5. `set -e` does not do what you think.** It is full of exceptions: it doesn't
> trigger for commands in a condition (`if`, `while`, `&&`, `||`), or for any command
> except the last in a pipeline (without `pipefail`), or inside a function called in a
> condition context — where it is disabled for the *entire* function. It is a useful
> default, **not** a substitute for checking return codes on anything that matters.
> The `set -e` critique (the "BashFAQ 105" position) is worth reading before relying on it.

> **⚠️ 6. `[` vs `[[`.** `[` is the `test` command — its arguments undergo word splitting
> and globbing, so `[ $x = y ]` breaks when `$x` is empty or has spaces. `[[ ]]` is shell
> syntax (bash/zsh/ksh, **not POSIX**) with no splitting inside, plus `=~` and `&&`.
> **Use `[[ ]]` in bash/zsh; quote religiously in POSIX `sh`.**
> Note also: **POSIX.1-2024 removed `-a` and `-o` from `test`** — use `&&`/`||` between
> separate `[ ]` invocations.

> **⚠️ 7. Arithmetic and leading zeros.** `$((08))` is an error in bash — leading zero
> means octal. Bites date handling every August and September. Use `10#$var`.

> **⚠️ 8. `read` mangles input by default.** `read -r` (don't interpret backslashes),
> `IFS= read -r line` (don't strip leading/trailing whitespace). The canonical loop is
> `while IFS= read -r line; do ...; done < file`.

> **⚠️ 9. Filenames can contain anything except `/` and NUL** — including newlines,
> spaces, and leading `-`. Use `find -print0 | xargs -0`, or `find -exec ... +`, and
> `--` to end option parsing (`rm -- "$f"`).

> **⚠️ 10. `cd` can fail.** `cd /some/dir; rm -rf *` deletes the wrong thing when the
> `cd` fails. Always `cd /some/dir || exit 1`.

### 8.3 Parameter expansion — the underused half of the language

```bash
${var:-default}   # use default if unset/empty (doesn't assign)
${var:=default}   # assign default if unset/empty
${var:?message}   # ERROR OUT if unset/empty  ← excellent for required arguments
${var:+alt}       # use alt only if var IS set
${#var}           # length
${var#prefix}     ${var##prefix}    # strip shortest / longest matching prefix
${var%suffix}     ${var%%suffix}    # strip shortest / longest matching suffix
${var/old/new}    ${var//old/new}   # replace first / all (bash/zsh, not POSIX)
${var:offset:len}                   # substring
${array[@]}  ${#array[@]}  ${!array[@]}   # elements, count, indices
```
`${var#*/}` and `${var%/*}` replace `basename`/`dirname` without forking a process —
meaningful inside a loop.

---
