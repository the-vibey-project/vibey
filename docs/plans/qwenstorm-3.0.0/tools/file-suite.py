"""File the QwenStorm 3.0.0 issue suite: new lanes, rewritten bodies, closures, wave epics, queue.

Resumable and paced. Every GitHub write is recorded in issue-audit/filing-log.tsv the moment it
succeeds, and a slug that already has an issue number in issue-audit/issue-map.tsv is never filed
twice, so a crash or a rate limit simply means running it again. GitHub allows about 500
content-creating requests an hour, so writes are spaced PACE seconds apart.

    python3 file-suite.py plan            # print every action, write nothing
    python3 file-suite.py file            # new lane issues (specs/*-queue.txt)
    python3 file-suite.py rewrite         # edit bodies, close superseded, parent epics
    python3 file-suite.py epics           # one tracking epic per wave
    python3 file-suite.py queue           # rebuild queue.txt from the map, in dependency order
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
import time
from pathlib import Path

STORM = Path(__file__).resolve().parent.parent
SPECS = STORM / "specs"
AUDIT = STORM / "issue-audit"
MAP = AUDIT / "issue-map.tsv"
LOG = AUDIT / "filing-log.tsv"
REPO = "the-vibey-project/vibey"
PACE = 8.0

PREAMBLE = (
    "Part of the **QwenStorm for vibey 3.0.0**. A sovereign-loop lane (gpt-oss:20b, one instance "
    "per model under sub-doctrine 8.c) implements this issue; the result is reviewed and "
    "verified before it becomes a pull request. Shared context for every lane: the ratified "
    "canon, and the standards this suite enforces (ORM always behind interfaces, comprehensive "
    "in-memory fakes so tests need no outside service, the installer installs everything on "
    "Arch Linux and macOS).\n\n"
)

WAVES = {
    "installer": "the installer installs everything a developer needs on Arch Linux and macOS",
    "orm": "ORM always, behind interfaces (SQLAlchemy 2 async)",
    "fakes": "comprehensive in-memory fakes: tests need no outside service",
    "loops": "two loops, one instance per model (ADR-0046)",
    "surfaces": "every sovereign surface in one lane on the bus (ADR-0047)",
    "harness": "the test harness runs once, fed by a queue (ADR-0045)",
    "job-queue": "the job queue on RabbitMQ (ADR-0044)",
    "forge": "vibey-gh fully on the forge adapter",
    "deploy": "deployment: OpenStack default, operator, Forgejo",
    "models": "the living model standard (8.d)",
    "gaps": "requirements of the ratified law no other wave covers",
    "roadmap": "the roadmap epics, broken into lanes",
    "core": "the sovereign defaults, true at runtime",
    "release": "release and CI operations for 3.0.0",
    "seo": "SEO and LLM-engine discoverability for the repo and its docs",
}

# Waves of the lanes filed before this suite (queue.txt), by issue number.
WAVE_BY_ISSUE = {
    **{n: "core" for n in (321, 322, 323, 345, 346, 382, 386)},
    **{n: "deploy" for n in (324, 326, 327, 330, 331)},
    **{n: "forge" for n in range(332, 345)},
    **{n: "job-queue" for n in range(348, 382)},
    **{n: "models" for n in (383, 387, 388, 389, 391)},
    393: "release",
}
ROADMAP = (
    85,
    86,
    87,
    88,
    89,
    90,
    114,
    121,
    133,
    134,
    136,
    138,
    139,
    143,
    145,
    148,
    155,
    165,
    226,
    290,
    297,
    298,
    301,
)

# Dependency names the spec writers used for lanes that exist under another slug, or for work
# the integration branch already carries.
ALIASES = {
    "orm-unit-of-work": "orm-test-harness",  # the ORM seam plus its FakeOrm
    # Names other waves used for ADR-0046 lanes before its writer chose slugs (loops-queue.txt).
    "loops-run-protocol": "loops-run-protocol-messages",
    "loops-route-store": "loops-state-stores",
    "loops-router": "loops-router-forwarding",
    "loops-seat-host": "loops-seat-host-drain",
    "loops-residency": "loops-resident-schedule",
    "loops-control": "loops-control-and-dead-letters",
    "loops-adapter": "loops-service-adapter-control",
    "loops-cli": "loops-cli-loop-service",
    "loops-queue-depth": "loops-amqp-queue-depth",
    "loops-invocation": "loops-invocation-composition",
    "loops-config": "loops-config-loop-services",
    "loops-submit-cli": "loops-cli-loop-submit",
    "loops-vscode-paid": "loops-vscode-paid-config",
    "loops-vscode-verification": "loops-vscode-spike",
    "loops-rename": "loops-tenant-rename",
    # Superseded job-queue lanes (#374, #375) that ADR-0046 replaced.
    "rmq-r27-loop-service-cli": "loops-cli-loop-service",
    "rmq-r28-invocation-selection": "loops-invocation-composition",
}
SATISFIED = {
    "sovereign-surfaces-ports",  # the 12 surface ports and in-memory twins landed with #319
}

SPLIT_WAVE = {
    range(332, 345): "forge",
    range(348, 382): "job-queue",
    range(324, 332): "deploy",
    range(383, 392): "models",
}

# Lanes the sovereign loop never runs: operator checklists (funding a key, registering a
# runner) and canon drafting, which is the operator's alone to ratify. They are still filed
# as issues (labelled `operator`) and still counted as valid dependencies, but they never
# appear as a runnable entry in queue.txt — a lane depending on one keeps that dependency
# and simply waits, exactly as storm-queue.sh already waits on anything not yet in
# integrated.txt, until a human does the operator lane and appends its slug there by hand.
OPERATOR_PREFIXES = ("gap-ops-", "gap-canon-")


def wave_of(slug: str) -> str:
    prefix = slug.split("-", 1)[0]
    if prefix == "split":
        parent = int(slug.split("-")[1])
        return next((w for r, w in SPLIT_WAVE.items() if parent in r), "gaps")
    if prefix == "gap":
        return "gaps"
    # The wave-1 slugs predate the wave names, so they carry their own prefixes; each belongs
    # to a wave that already exists rather than to one invented for it. Every prefix must land
    # on a WAVES key — `epics` raises KeyError on one that does not, after filing everything.
    return {
        "install": "installer",
        "rmq": "job-queue",
        "qwenloop": "core",
        "engines": "core",
        "opencodeloop": "core",
        "default": "models",
        "chart": "deploy",
    }.get(prefix, prefix)


def gh(*args: str) -> str:
    run = subprocess.run(["gh", *args], capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {run.stderr.strip()}")
    return run.stdout.strip()


def load_map() -> dict[str, int]:
    if not MAP.is_file():
        return {}
    return {row[0]: int(row[1]) for row in csv.reader(MAP.open(), delimiter="\t") if row}


def record(path: Path, *row: object) -> None:
    with path.open("a", newline="") as out:
        csv.writer(out, delimiter="\t").writerow(row)


def title_of(spec: Path) -> str:
    match = re.search(r"^## Title\n(.+)$", spec.read_text(), re.M)
    if not match:
        raise ValueError(f"{spec.name} has no '## Title'")
    return match.group(1).strip()


RULES = (
    (STORM / "SPEC-TEMPLATE.md")
    .read_text()
    .split("## Hard repository rules (always)", 1)[1]
    .strip()
)
TEMPLATE_POINTER = re.compile(r"See /private/tmp/\S*SPEC-TEMPLATE\.md\.?")
SPEC_POINTER = re.compile(
    r"(?:/private/tmp/claude-501/storm/qwenstorm-3\.0\.0/|STORM/)?specs/([a-z0-9][a-z0-9-]*)\.md"
)


def visible(text: str) -> str:
    """What a lane on GitHub can actually read: the repository rules inlined, and every pointer
    at a storm spec file turned into the issue that carries it (or the lane's slug, if unfiled)."""
    mapping = {**existing_numbers(), **load_map()}
    text = TEMPLATE_POINTER.sub(lambda _m: RULES, text)

    def link(m: re.Match[str]) -> str:
        slug = m.group(1)
        return f"#{mapping[slug]} (`{slug}`)" if slug in mapping else f"lane `{slug}`"

    return SPEC_POINTER.sub(link, text)


def body_of(spec: Path, preamble: str = PREAMBLE) -> str:
    text = re.sub(r"^<!-- audit:.*-->\n", "", spec.read_text(), count=1)
    text = re.sub(r"^## Title\n.+\n", "", text, count=1, flags=re.M)
    return preamble + visible(text.strip()) + "\n"


def optional_title(spec: Path) -> str | None:
    match = re.search(r"^## Title\n(.+)$", spec.read_text(), re.M)
    return match.group(1).strip() if match else None


def lane_wave(slug: str, number: int | None) -> str:
    if number is not None and number in WAVE_BY_ISSUE:
        return WAVE_BY_ISSUE[number]
    return wave_of(slug)


def queue_lines() -> list[tuple[str, list[str]]]:
    """Every unfiled lane from specs/*-queue.txt, in file order: (slug, deps)."""
    lanes = []
    for fragment in sorted(SPECS.glob("*-queue.txt")):
        for line in fragment.read_text().splitlines():
            parts = line.split()
            if not parts or parts[0].startswith("#"):
                continue
            deps = parts[2].split(",") if len(parts) > 2 else []
            lanes.append((parts[0], [ALIASES.get(d, d) for d in deps if d and d != "-"]))
    return lanes


def existing_numbers() -> dict[str, int]:
    """Slugs whose queue line already names an issue: filed before, never filed again."""
    found: dict[str, int] = {}
    for source in [STORM / "queue.txt", *sorted(SPECS.glob("*-queue.txt"))]:
        for line in source.read_text().splitlines():
            parts = line.split()
            if len(parts) > 1 and parts[1].isdigit():
                found[parts[0]] = int(parts[1])
    return found


def ensure_labels() -> None:
    have = set(
        gh(
            "label", "list", "-R", REPO, "--limit", "200", "--json", "name", "-q", ".[].name"
        ).split()
    )
    if "epic" not in have:
        gh(
            "label",
            "create",
            "epic",
            "-R",
            REPO,
            "--color",
            "3e4b9e",
            "--description",
            "tracks a set of lane issues",
        )
        time.sleep(PACE)
    if "operator" not in have:
        gh(
            "label",
            "create",
            "operator",
            "-R",
            REPO,
            "--color",
            "b60205",
            "--description",
            "for a human, not the sovereign loop: a checklist item or a canon ratification",
        )
        time.sleep(PACE)
    for wave in WAVES:
        if f"wave:{wave}" not in have:
            gh(
                "label",
                "create",
                f"wave:{wave}",
                "-R",
                REPO,
                "--color",
                "5319e7",
                "--description",
                WAVES[wave][:100],
            )
            time.sleep(PACE)


def file_lanes(dry: bool) -> None:
    mapping = {**existing_numbers(), **load_map()}
    lanes = dict(queue_lines())
    # dependency order, so a lane's dependencies already have numbers when its body links them
    todo = [(s, lanes[s]) for s in ordered(lanes) if s not in mapping]
    missing = [s for s, _ in todo if not (SPECS / f"{s}.md").is_file()]
    if missing:
        sys.exit(f"queue slugs with no spec file: {', '.join(missing)}")
    print(f"{len(todo)} lane issue(s) to file ({len(mapping)} already mapped)")
    if not dry:
        ensure_labels()
    for slug, _ in todo:
        spec = SPECS / f"{slug}.md"
        labels = f"qwenstorm,wave:{wave_of(slug)}"
        if slug.startswith(OPERATOR_PREFIXES):
            labels += ",operator"
        if dry:
            print(f"  new  {slug:48} [{labels}] {title_of(spec)[:70]}")
            continue
        url = gh(
            "issue",
            "create",
            "-R",
            REPO,
            "--title",
            title_of(spec),
            "--label",
            labels,
            "--body",
            body_of(spec),
        )
        number = int(url.rsplit("/", 1)[-1])
        record(MAP, slug, number)
        record(LOG, "create", slug, number, time.strftime("%Y-%m-%dT%H:%M:%S"))
        print(f"  #{number} {slug}", flush=True)
        time.sleep(PACE)


def done(action: str, target: object) -> bool:
    if not LOG.is_file():
        return False
    return any(row[:2] == [action, str(target)] for row in csv.reader(LOG.open(), delimiter="\t"))


def write(dry: bool, action: str, target: object, argv: list[str], note: str) -> None:
    """One GitHub write, skipped when the log says it already happened."""
    if done(action, target):
        return
    print(f"  {action:16} #{target}  {note}", flush=True)
    if dry:
        return
    gh(*argv)
    record(LOG, action, target, "", time.strftime("%Y-%m-%dT%H:%M:%S"))
    time.sleep(PACE)


def rewrite(dry: bool) -> None:
    """Existing issues: rewrite, retitle, close the superseded, and turn the oversized into epics."""
    mapping = {**existing_numbers(), **load_map()}
    rows = list(csv.reader((AUDIT / "storm-disposition.tsv").open(), delimiter="\t"))
    for issue, status, action, detail in (r[:4] for r in rows if r and r[0].isdigit()):
        n = int(issue)
        if action == "edit-body":
            spec = AUDIT / "updates" / f"{n}.md"
            argv = ["issue", "edit", str(n), "-R", REPO, "--body", body_of(spec)]
            if (t := optional_title(spec)) is not None:
                argv += ["--title", t]
            write(dry, "edit-body", n, argv, f"{status}: {spec.name}")
        elif action == "replace-body":
            spec = STORM / detail
            write(
                dry,
                "edit-body",
                n,
                [
                    "issue",
                    "edit",
                    str(n),
                    "-R",
                    REPO,
                    "--title",
                    title_of(spec),
                    "--body",
                    body_of(spec),
                ],
                f"replaced by {detail}",
            )
        elif action == "close-superseded":
            comment = (AUDIT / "updates" / f"{n}.md").read_text()
            comment = re.sub(r"^<!-- audit:.*-->\n", "", comment, count=1).strip()
            write(
                dry,
                "comment",
                n,
                ["issue", "comment", str(n), "-R", REPO, "--body", comment],
                "closing comment",
            )
            write(
                dry,
                "close",
                n,
                ["issue", "close", str(n), "-R", REPO, "--reason", "not planned"],
                "superseded",
            )
        elif action == "parent-epic":
            children = [c for c in detail.split(",") if c]
            lines = []
            for child in children:
                number = mapping.get(child)
                title = (
                    title_of(SPECS / f"{child}.md") if (SPECS / f"{child}.md").is_file() else child
                )
                lines.append(
                    f"- [ ] {'#' + str(number) if number else '(unfiled) ' + child} — {title}"
                )
            spec = AUDIT / "updates" / f"{n}.md"
            body = (
                "**This issue is now a tracking epic.** The QwenStorm audit of 2026-09-22 found it "
                "too large for one sovereign-loop lane, so it is split into the lanes below, in "
                "dependency order. Each lane is its own issue with a complete spec; this issue "
                "closes when they all do.\n\n## Lanes\n\n"
                + "\n".join(lines)
                + "\n\n## The audit's rewrite and the reasons for the split\n\n"
                + body_of(spec, preamble="")
            )
            if not dry and any("(unfiled)" in line for line in lines):
                sys.exit(f"#{n}: file the child lanes first (run `file`)")
            write(
                dry,
                "epic-body",
                n,
                ["issue", "edit", str(n), "-R", REPO, "--body", body, "--add-label", "epic"],
                f"epic over {len(children)} lanes",
            )
    for n in ROADMAP:
        spec = AUDIT / "updates" / f"{n}.md"
        if spec.is_file():
            write(
                dry,
                "edit-body",
                n,
                ["issue", "edit", str(n), "-R", REPO, "--body", body_of(spec, preamble="")],
                "roadmap rewrite",
            )


def ordered(lanes: dict[str, list[str]]) -> list[str]:
    """Dependency order, stable within the file order; a cycle stops the build."""
    result: list[str] = []
    state: dict[str, int] = {}

    def visit(slug: str, path: tuple[str, ...]) -> None:
        if state.get(slug) == 2:
            return
        if state.get(slug) == 1:
            sys.exit(f"dependency cycle: {' -> '.join((*path, slug))}")
        state[slug] = 1
        for dep in lanes.get(slug, []):
            if dep in lanes:
                visit(dep, (*path, slug))
        state[slug] = 2
        result.append(slug)

    for slug in lanes:
        visit(slug, ())
    return result


def build_queue(dry: bool) -> None:
    """queue.txt from every lane that is still a lane: `slug issue deps`, dependency-ordered."""
    mapping = {**existing_numbers(), **load_map()}
    existing = {}
    deps_file = AUDIT / "existing-deps.tsv"
    overrides = (
        {
            r[0]: [ALIASES.get(d, d) for d in r[2].split(",") if d and d != "-"]
            for r in csv.reader(deps_file.open(), delimiter="\t")
            if r
        }
        if deps_file.is_file()
        else {}
    )
    closed = {
        r[0]
        for r in csv.reader((AUDIT / "storm-disposition.tsv").open(), delimiter="\t")
        if r and len(r) > 2 and r[2] in ("close-superseded", "parent-epic")
    }
    for line in (STORM / "queue.txt").read_text().splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[1] in closed:
            continue
        deps = parts[2].split(",") if len(parts) > 2 else []
        existing[parts[0]] = overrides.get(parts[0], [ALIASES.get(d, d) for d in deps if d])
    lanes = {**existing, **dict(queue_lines())}
    operator = {s for s in lanes if s.startswith(OPERATOR_PREFIXES)}
    for slug in operator:
        del lanes[slug]
    waiting = sorted(s for s, deps in lanes.items() if set(deps) & operator)
    if waiting:
        print(
            f"{len(waiting)} lane(s) wait on an operator lane (filed, never auto-run): "
            + ", ".join(waiting[:8])
            + (" …" if len(waiting) > 8 else "")
        )
    known = (
        set(lanes)
        | operator
        | {line.strip() for line in (STORM / "integrated.txt").read_text().splitlines()}
    )
    known |= SATISFIED
    # a dependency on an epic parent means: all of its lanes
    parents = {
        r[0]: r[3].split(",")
        for r in csv.reader((AUDIT / "storm-disposition.tsv").open(), delimiter="\t")
        if r and len(r) > 3 and r[2] == "parent-epic"
    }
    for slug, deps in lanes.items():
        expanded = []
        for dep in deps:
            issue = str(mapping.get(dep, ""))
            expanded.extend(parents.get(issue, [dep]) if issue in parents else [dep])
        lanes[slug] = expanded
    unknown = sorted({d for deps in lanes.values() for d in deps if d not in known})
    if unknown:
        print("UNKNOWN dependencies (fix before the storm runs):")
        for dep in unknown:
            users = [s for s, ds in lanes.items() if dep in ds]
            print(f"  {dep}  <- {', '.join(users[:6])}{' …' if len(users) > 6 else ''}")
    unfiled = [s for s in lanes if s not in mapping]
    print(f"{len(lanes)} lanes, {len(unfiled)} not yet filed, {len(unknown)} unknown dependencies")
    if dry or unknown or unfiled:
        return
    order = ordered(lanes)
    (STORM / "queue.txt").write_text(
        "".join(
            f"{s} {mapping[s]} {','.join(d for d in lanes[s] if d not in SATISFIED)}".rstrip()
            + "\n"
            for s in order
        )
    )
    print(f"queue.txt rewritten: {len(order)} lanes")


def epics(dry: bool) -> None:
    """One tracking epic per wave, listing its lanes in queue order."""
    mapping = {**existing_numbers(), **load_map()}
    by_wave: dict[str, list[str]] = {}
    for line in (STORM / "queue.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[1].isdigit():
            by_wave.setdefault(lane_wave(parts[0], int(parts[1])), []).append(parts[0])
    for wave, slugs in by_wave.items():
        key = f"epic-{wave}"
        if key in mapping:
            continue
        lines = [f"- [ ] #{mapping[s]} `{s}`" for s in slugs]
        body = (
            f"Tracking epic for the QwenStorm 3.0.0 wave **{wave}**: {WAVES[wave]}.\n\n"
            "The lanes below are in the storm's dependency order; each is its own issue with "
            "a complete spec, implemented by the sovereign loop and reviewed in batches.\n\n"
            + "\n".join(lines)
            + "\n"
        )
        print(f"  epic  {wave:12} {len(slugs)} lanes")
        if dry:
            continue
        url = gh(
            "issue",
            "create",
            "-R",
            REPO,
            "--title",
            f"epic({wave}): {WAVES[wave]} — QwenStorm 3.0.0",
            "--label",
            f"qwenstorm,epic,wave:{wave}",
            "--body",
            body,
        )
        record(MAP, key, int(url.rsplit("/", 1)[-1]))
        time.sleep(PACE)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "plan"
    dry = "--dry" in sys.argv
    if command in ("plan", "file"):
        file_lanes(dry=command == "plan")
    elif command == "rewrite":
        rewrite(dry)
    elif command == "queue":
        build_queue(dry)
    elif command == "epics":
        epics(dry)
    else:
        sys.exit(f"unknown command: {command}")
