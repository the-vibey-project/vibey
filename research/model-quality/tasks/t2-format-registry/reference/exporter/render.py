import csv
import io
import json

Row = dict[str, str]


def render_json(rows: list[Row]) -> str:
    return json.dumps(rows) + "\n"


def render_csv(rows: list[Row]) -> str:
    if not rows:
        return ""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def render_markdown(rows: list[Row]) -> str:
    if not rows:
        return ""
    columns = list(rows[0])

    def line(cells: list[str]) -> str:
        return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |\n"

    lines = [line(columns), line(["---"] * len(columns))]
    lines.extend(line([row.get(column, "") for column in columns]) for row in rows)
    return "".join(lines)
