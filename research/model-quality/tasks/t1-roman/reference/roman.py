"""Roman numeral conversion."""

_TABLE = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]  # fmt: skip


def to_roman(n: int) -> str:
    if not 1 <= n <= 3999:
        raise ValueError(f"out of range: {n}")
    out = []
    for value, symbol in _TABLE:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)


def from_roman(s: str) -> int:
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    text = s.upper()
    if not text or any(ch not in values for ch in text):
        raise ValueError(f"not a Roman numeral: {s!r}")
    total = 0
    for i, ch in enumerate(text):
        if i + 1 < len(text) and values[ch] < values[text[i + 1]]:
            total -= values[ch]
        else:
            total += values[ch]
    if not 1 <= total <= 3999 or to_roman(total) != text:
        raise ValueError(f"not canonical: {s!r}")
    return total
