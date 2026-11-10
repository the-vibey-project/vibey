"""Split one CSV line."""


def split_csv_line(line: str) -> list[str]:
    fields: list[str] = []
    i = 0
    n = len(line)
    while True:
        if i < n and line[i] == '"':
            i += 1
            buf = []
            while True:
                if i >= n:
                    raise ValueError("unterminated quote")
                if line[i] == '"':
                    if i + 1 < n and line[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    break
                buf.append(line[i])
                i += 1
            if i < n and line[i] != ",":
                raise ValueError("text after closing quote")
            fields.append("".join(buf))
        else:
            j = line.find(",", i)
            if j == -1:
                j = n
            fields.append(line[i:j])
            i = j
        if i >= n:
            return fields
        i += 1  # skip the comma
        if i >= n:
            fields.append("")
            return fields
