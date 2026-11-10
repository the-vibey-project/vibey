Create rle.py in the current directory with two functions for run-length coding.

1. encode(text: str) -> str replaces every run of the same character with its length in decimal
   followed by the character. encode("aaabccdddd") returns "3a1b2c4d". A single character still gets
   a count of 1. A run of twelve "x" is "12x". encode("") returns "". The input must not contain any
   digit character; if it does, encode raises ValueError.
2. decode(data: str) -> str is the inverse. The count may have several digits ("12x" is twelve
   x characters). decode("") returns "". decode raises ValueError for malformed input: a count with
   no character after it ("3a2"), a character with no count ("a3b"), a count with a leading zero
   ("01a") or a count of 0 ("0a"). The character after a count can be any non-digit character,
   including spaces and punctuation.

For any digit-free text, decode(encode(text)) must equal text.
Quickly check a few values yourself before finishing.
