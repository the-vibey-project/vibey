"""Greedy text wrapping."""


def wrap_text(text: str, width: int) -> list[str]:
    if width < 1:
        raise ValueError("width must be at least 1")
    lines: list[str] = []
    current = ""
    for word in text.split():
        if len(word) > width:
            if current:
                lines.append(current)
            chunks = [word[i : i + width] for i in range(0, len(word), width)]
            lines.extend(chunks[:-1])
            current = chunks[-1]
        elif not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
