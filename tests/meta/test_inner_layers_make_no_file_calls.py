# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`domain/` and `application/` make no low-level file call of their own (SP-LOOPS Phase 3, fix
round 2: N4).

Opening, writing, syncing, renaming, linking and removing files is infrastructure's: the run
inputs service writes a run's folder through `RunFolderWriterInterface`, and the domain does no
I/O at all (ADR-0017). This walks every module of the two layers and refuses a call to one of
the `os` file functions below in any spelling -- `os.open(...)`, `import os as o; o.open(...)`,
`from os import open` -- so a later change cannot slip one back in.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "vibey"
LAYERS = ("domain", "application")
FILE_CALLS = frozenset(
    {
        "open",
        "replace",
        "mkdir",
        "makedirs",
        "unlink",
        "rename",
        "link",
        "symlink",
        "fsync",
        "write",
    }
)


def _scan(source: str) -> list[str]:
    """Every `os` file call, and every such name imported from `os`, in `source`."""
    tree = ast.parse(source)
    aliases = {"os"}
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases |= {a.asname or a.name for a in node.names if a.name == "os"}
        elif isinstance(node, ast.ImportFrom) and node.module == "os":
            found += [f"from os import {a.name}" for a in node.names if a.name in FILE_CALLS]
    for node in ast.walk(tree):
        func = node.func if isinstance(node, ast.Call) else None
        if (
            isinstance(func, ast.Attribute)
            and isinstance(func.value, ast.Name)
            and func.value.id in aliases
            and func.attr in FILE_CALLS
        ):
            found.append(f"{func.value.id}.{func.attr}(...) at line {func.lineno}")
    return found


def test_domain_and_application_make_no_os_file_call() -> None:
    offences = [
        f"{path.relative_to(SRC)}: {offence}"
        for layer in LAYERS
        for path in sorted((SRC / layer).rglob("*.py"))
        for offence in _scan(path.read_text(encoding="utf-8"))
    ]
    assert offences == [], "move these into an infrastructure adapter behind a port"


def test_the_check_sees_every_spelling() -> None:
    sample = (
        "import os\n"
        "import os as o\n"
        "from os import replace, path\n"
        "os.open('x', 0)\n"
        "o.fsync(3)\n"
        "os.path.join('a')\n"
        "os.getcwd()\n"
    )
    assert _scan(sample) == [
        "from os import replace",
        "os.open(...) at line 4",
        "o.fsync(...) at line 5",
    ]
