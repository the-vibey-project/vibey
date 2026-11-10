Create wrap.py in the current directory defining wrap_text(text: str, width: int) -> list[str], which
wraps text into lines and returns them as a list of strings.

- Words are separated by any whitespace (spaces, tabs, newlines); runs of whitespace count as one
  separator. Leading and trailing whitespace is ignored. Lines never have leading or trailing spaces,
  and words on one line are joined by a single space.
- Wrapping is greedy: put as many words on a line as fit within width characters, then start a new
  line.
- A word longer than width is split into consecutive chunks of exactly width characters, the last
  chunk possibly shorter. The first chunk always starts a new line (the line before it is finished),
  and the last chunk is treated as a normal word on the current line, so following words may join it
  if they fit.
- Text that is empty or only whitespace returns an empty list.
- If width is less than 1, raise ValueError.

Example: wrap_text("the quick brown fox", 9) returns ["the quick", "brown fox"].
Example: wrap_text("a abcdefgh bc", 5) returns ["a", "abcde", "fgh", "bc"]: the last chunk "fgh"
cannot take " bc" because that would be 6 characters. With width 6 it returns
["a", "abcdef", "gh bc"].
Quickly check a few cases yourself before finishing.
