Create two files in the current directory.

1. slugify.py defining slugify(text: str) -> str. It lowercases the text, replaces every run of
   characters that are not letters or digits with a single hyphen, and removes hyphens from the
   start and end. slugify("Hello,  World!") returns "hello-world".
2. test_slugify.py with at least four assert statements about slugify, runnable with
   `python test_slugify.py` (plain asserts, no pytest, exit code 0 when they pass).

Run `python test_slugify.py` and fix anything until it passes. Then finish.
