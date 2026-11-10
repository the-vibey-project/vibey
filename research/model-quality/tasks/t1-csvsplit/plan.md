Create csvsplit.py in the current directory defining split_csv_line(line: str) -> list[str], which
splits one line of comma-separated values into fields. Do not use the csv module.

- Fields are separated by commas. "a,b,c" gives ["a", "b", "c"].
- Empty fields are kept: "a,,c" gives ["a", "", "c"], "a,b," gives ["a", "b", ""], and the empty
  string "" gives [""].
- A field may be wrapped in double quotes. The quotes are removed, and commas inside them do not
  split: '"a,b",c' gives ["a,b", "c"].
- Inside a quoted field, two double quotes in a row stand for one literal double quote:
  '"say ""hi"""' gives ['say "hi"'].
- Spaces are data and are never stripped: "a, b" gives ["a", " b"]. A quote character that appears
  in the middle of an unquoted field is just an ordinary character.
- A quote opened at the start of a field that is never closed raises ValueError. A quoted field must
  be followed by a comma or the end of the line, otherwise raise ValueError.
- The line has no newline characters in it.
Quickly check a few cases yourself before finishing.
