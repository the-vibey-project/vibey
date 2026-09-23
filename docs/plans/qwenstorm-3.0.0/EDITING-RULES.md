

## Your tools (there are exactly four)

`read_file`, `write_file`, `edit_file`, `shell`. **Nothing else exists.** There is no `search`,
`find`, `grep`, `ls`, `glob` or `codebase_search` tool: calling one spends a turn and returns
`unknown tool`. Turns are capped, and a lane that spends them on tools that do not exist
finishes nothing.

`shell` takes `argv`, an array of strings, and runs that program directly — **there is no
shell**. So no `&&`, no `|`, no `>`, no `*` globs, no `$VAR` expansion, no heredoc. One program
per call:

- search file contents: `["grep", "-rn", "load_config_from_path", "src/vibey"]`
- list a directory: `["ls", "src/vibey/infrastructure"]`
- find a file by name: `["find", "src", "-name", "config_loader.py"]`
- run one check: `["python", "-m", "pytest", "-q", "tests/domain/test_config.py"]`

A check written as `cd somewhere && cmd` is two facts, not one command: run `cmd` with its own
argv. Read a file with `read_file`, never with `["cat", ...]`.

## Lane editing rules (read before changing any file)

1. `write_file` REPLACES the whole file. Never use it on a file that already exists unless
   you write back its complete content with your change applied. Every line you do not mean
   to change must still be there. For any existing file longer than 100 lines, do not use
   `write_file` at all.
2. Change an existing file with the `edit_file` tool: `path`, an `old_string` copied exactly
   from `read_file` output (enough lines to be unique), and the `new_string`. It replaces one
   occurrence and tells you if the text is missing or not unique. `write_file` now refuses to
   shrink a long existing file. Only if edit_file cannot express a change, use a checked
   replacement through the `shell` tool (an argv list, not a shell string):
   `["python3", "-c", "from pathlib import Path\np = Path('src/vibey/cli/main.py')\ns = p.read_text()\nold = '''exact old text'''\nnew = '''new text'''\nassert s.count(old) == 1, s.count(old)\np.write_text(s.replace(old, new))"]`
   Copy `old` exactly from `read_file` output, including indentation. If the assert fails,
   read the file again and fix `old`; never fall back to rewriting the file.
3. **Write the tests named under "Tests to write first (TDD)" — first, and always.** That
   section is the issue's obligation, not a suggestion: `domain/`, `application/`,
   `infrastructure/` and `cli/` each fail the build under 100% branch coverage, so an
   implementation that arrives without its tests cannot be merged at all and the lane has
   achieved nothing. If you write only the implementation you have **not** finished, however
   clean it looks and whatever else passes. Write each named test file with the named cases,
   watch them fail, then make them pass.
   Add tests by APPENDING to the existing test file (`open(path, "a")`), or by creating a
   new test file. Never rewrite an existing test file.
4. Every source file begins with the provenance header line
   `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), ...`. Keep it on
   every file you touch, and put it on every file you create (copy it from a neighbour).
5. Only edit the files named under "Where to change" and the tests named under "Tests to
   write first". If you believe another file must change, say so in your verdict instead.
6. After each change, run the focused tests. If a test you did not mean to affect fails,
   undo your change with a targeted replacement and try again.
7. Before your final verdict, run `git diff --stat` and confirm no file lost lines you did
   not mean to remove.
8. **Every file you create or change must import.** For each one, run
   `["python", "-c", "import vibey.the.module.you.touched"]` and read the output. An
   annotation you add needs its own import: writing `Sequence[DesignEvent]` in a file that
   imports only `Mapping` reads perfectly in the diff and raises `NameError` the moment
   anything loads it — and if the file is inside a package, it takes that package's
   `__init__.py` down with it. A lane has finished this way, claiming completion over code
   that could not be imported at all.
9. **Run the block under "Checks the lane must run" before you claim completion**, one argv
   per command, and read each exit code. If any of them fails, you have not finished: fix it
   or say in your verdict which check fails and why. A verdict is not evidence
   (sub-doctrine 10.f) — the commands are.
10. Do not declare the same class or function in two files. If the issue asks for an
    interface beside a class, the class module **imports** it from the interface module;
    writing it out again in both leaves two definitions that drift apart immediately.
11. **Python has no braces, and a file ends at its last line of code.** Never close a file
    with `}`, and never write a marker such as `*** End Of File ***`, `<end>` or a closing
    fence into the file itself — those belong to your message, not to the source. Two lanes
    ended a freshly written `*_interface.py` with a stray `}` (one also appended
    `*** End Of File ***`), and `SyntaxError: unmatched '}'` made the whole module
    unimportable. A new file's last line is the last line of real code, nothing after it.
