"""Run-length coding."""


def encode(text: str) -> str:
    if any(ch.isdigit() for ch in text):
        raise ValueError("input must not contain digits")
    out = []
    i = 0
    while i < len(text):
        j = i
        while j < len(text) and text[j] == text[i]:
            j += 1
        out.append(f"{j - i}{text[i]}")
        i = j
    return "".join(out)


def decode(data: str) -> str:
    out = []
    i = 0
    while i < len(data):
        j = i
        while j < len(data) and data[j].isdigit():
            j += 1
        digits = data[i:j]
        if not digits or j >= len(data):
            raise ValueError("malformed input")
        if digits.startswith("0"):
            raise ValueError("count must be positive without leading zeros")
        out.append(data[j] * int(digits))
        i = j + 1
    return "".join(out)
