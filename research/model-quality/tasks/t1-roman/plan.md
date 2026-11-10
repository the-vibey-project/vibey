Create roman.py in the current directory with two functions.

1. to_roman(n: int) -> str converts an integer from 1 to 3999 to an upper-case Roman numeral using
   subtractive notation (4 is "IV", 9 is "IX", 40 is "XL", 90 is "XC", 400 is "CD", 900 is "CM").
   to_roman(1994) returns "MCMXCIV". Any integer outside 1 to 3999 raises ValueError.
2. from_roman(s: str) -> int converts a Roman numeral back to an integer. It accepts lower-case or
   upper-case input and surrounding whitespace is not allowed. It only accepts the canonical form:
   the string must be exactly what to_roman would produce for its value. So "IIII", "VX", "IC",
   "MMMM" and the empty string all raise ValueError, as does any string containing a character
   that is not a Roman numeral letter.

For every n from 1 to 3999, from_roman(to_roman(n)) must equal n.
Quickly check a few values yourself before finishing.
