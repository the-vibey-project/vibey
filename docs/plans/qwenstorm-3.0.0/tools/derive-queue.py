"""Derive a wave's queue fragment from its specs' `Depends on` lines.

    python3 derive-queue.py gap --write        # writes specs/gaps-queue.txt
    python3 derive-queue.py roadmap --write    # writes specs/roadmap-queue.txt
    python3 derive-queue.py seo --write         # writes specs/seo-queue.txt

Several waves' spec writers were interrupted before they hand-assembled a queue file, but
every spec still states its own dependencies in a `**Depends on:**` line. This script reads
that line back out of every `<prefix>-*.md` spec and writes the fragment, so no dependency is
retyped by hand and drifts from what the spec itself says. A dependency that resolves to no
known lane (in any *-queue.txt, any spec file, or integrated.txt) is reported and the fragment
is written only when there are none, unless --force is given.
"""

import re
import sys
from pathlib import Path

STORM = Path(__file__).resolve().parent.parent
SPECS = STORM / "specs"
PREFIX = sys.argv[1]
OUT = (
    SPECS / f"{PREFIX}s-queue.txt"
    if PREFIX in ("gap", "roadmap")
    else SPECS / f"{PREFIX}-queue.txt"
)

ALIASES: dict[str, str] = {}
SATISFIED: set[str] = set()
# Files that match a wave's glob but are not lanes: registers and notes that must never become
# an issue. roadmap-blocked.md records which roadmap children were deliberately NOT specced
# (blocked on an operator question, excluded by ratified law, waiting on a spike) — it is the
# reason a lane is absent, not a lane.
NOT_LANES = {"roadmap-blocked"}
# Only the explicit lane-card line, and the LAST one in the file: prose elsewhere in a spec
# ("this depends on the operator's ruling on X") says "depends on" too, and is not the line.
DEPENDS = re.compile(r"^[-*]?\s*\*\*Depends on:?\*\*:?\s*(.+)$", re.M)
SLUG = re.compile(r"`?([a-z][a-z0-9]*(?:-[a-zA-Z0-9]+)+)`?")


def load_file_suite_constants() -> None:
    """Reuse file-suite.py's own ALIASES/SATISFIED so a dependency written under an older
    placeholder name (e.g. a loops-* slug guessed before that wave's writer chose its own)
    resolves the same way here as it will at filing time."""
    global ALIASES, SATISFIED
    import importlib.util

    path = STORM / "tools" / "file-suite.py"
    if not path.is_file():
        return
    spec = importlib.util.spec_from_file_location("fs", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    ALIASES = getattr(module, "ALIASES", {})
    SATISFIED = getattr(module, "SATISFIED", set())


def known_slugs() -> set[str]:
    slugs = {p.stem for p in SPECS.glob("*.md")}
    for source in [STORM / "queue.txt", *SPECS.glob("*-queue.txt")]:
        if source.is_file():
            slugs |= {line.split()[0] for line in source.read_text().splitlines() if line.split()}
    integrated = STORM / "integrated.txt"
    if integrated.is_file():
        slugs |= {line.strip() for line in integrated.read_text().splitlines() if line.strip()}
    return slugs | SATISFIED


def deps_of(spec: Path, known: set[str]) -> tuple[list[str], list[str]]:
    text = spec.read_text()
    matches = list(DEPENDS.finditer(text))
    if not matches:
        return [], []
    match = matches[-1]
    # the line, and any continuation bullet lines directly under it
    block = match.group(1)
    tail = text[match.end() :].splitlines()
    for line in tail[1:]:
        if re.match(r"^\s*[-*] `?[a-z]", line):
            block += " " + line
        else:
            break
    if re.fullmatch(r"\s*(none|nothing|n/a|—|-)\.?\s*", block.split(".")[0], re.I):
        return [], []
    found = [m.group(1) for m in SLUG.finditer(block)]
    mapped = dict.fromkeys(ALIASES.get(s, s) for s in found)
    deps = [s for s in mapped if s in known and s != spec.stem]
    unknown = [
        s
        for s in mapped
        if s not in known
        and s.count("-") >= 2
        and not s.startswith(("sub-", "file-", "one-", "doctrines"))
    ]
    return deps, unknown


def main() -> int:
    load_file_suite_constants()
    known = known_slugs()
    specs = [p for p in sorted(SPECS.glob(f"{PREFIX}-*.md")) if p.stem not in NOT_LANES]
    lines, problems = [], []
    for spec in specs:
        deps, unknown = deps_of(spec, known)
        lines.append(f"{spec.stem} - {','.join(deps)}".rstrip(" -") if deps else f"{spec.stem} -")
        problems += [f"{spec.stem}: unknown dependency {u!r}" for u in unknown]
    print(f"{len(specs)} {PREFIX} specs; {len(problems)} unknown dependencies")
    for problem in problems[:40]:
        print("  " + problem)
    if "--write" in sys.argv and (not problems or "--force" in sys.argv):
        OUT.write_text("\n".join(lines) + "\n")
        print(f"wrote {OUT.name}")
    elif "--write" in sys.argv:
        print("not written: fix the unknown dependencies first, or pass --force")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
