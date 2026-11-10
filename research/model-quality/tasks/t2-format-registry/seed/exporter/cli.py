from exporter.render import Row, render_csv, render_json


def run(argv: list[str], rows: list[Row]) -> tuple[int, str]:
    """Render rows in the format named by `--format NAME` (default json).

    Returns (exit_code, output_text).
    """
    name = "json"
    if "--format" in argv:
        index = argv.index("--format")
        if index + 1 >= len(argv):
            return 2, "usage: --format NAME\n"
        name = argv[index + 1].lower()
    if name == "json":
        return 0, render_json(rows)
    elif name == "csv":
        return 0, render_csv(rows)
    return 2, f"unknown format: {name}\n"
