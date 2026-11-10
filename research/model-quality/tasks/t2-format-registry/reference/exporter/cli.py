from exporter.registry import FormatRegistry, default_registry
from exporter.render import Row


def run(
    argv: list[str], rows: list[Row], registry: FormatRegistry | None = None
) -> tuple[int, str]:
    """Render rows in the format named by `--format NAME` (default json).

    Returns (exit_code, output_text).
    """
    registry = registry if registry is not None else default_registry()
    name = "json"
    if "--format" in argv:
        index = argv.index("--format")
        if index + 1 >= len(argv):
            return 2, "usage: --format NAME\n"
        name = argv[index + 1].lower()
    try:
        renderer = registry.get(name)
    except KeyError:
        return 2, f"unknown format: {name}\n"
    return 0, renderer(rows)
