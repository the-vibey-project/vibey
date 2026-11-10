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
