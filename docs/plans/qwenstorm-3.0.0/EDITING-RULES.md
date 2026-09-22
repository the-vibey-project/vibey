

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
3. Add tests by APPENDING to the existing test file (`open(path, "a")`), or by creating a
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
