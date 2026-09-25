# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""No tool, default, doc or skill here keeps durable work on volatile storage (10.h, ADR-0057).

On 2026-09-24 a reboot emptied /private/tmp and took the storm with it. The storm's tools,
docs and briefs had put everything there because a path under /private/tmp was written into
them. The durability gate stops a tool from doing that at run time. This test stops the text
from saying it at all: it reads every tracked text file for a literal volatile path (/tmp,
/private/tmp, /var/tmp, /var/folders, /dev/shm, /run/user, or the machine-specific
claude-501 scratch tree).

A hit is one of three things:

  (a) durable work at a volatile path. Move it under the storm home;
  (c) documentation telling people to use one. Reword it;
  (b) something genuinely ephemeral: a pipe, a CI runner's scratch, a throwaway render, or
      a sentence stating the rule. That belongs in ALLOWED below, with the reason beside it.

Whole trees are exempt only where scanning them would be wrong, with the reason beside each
(`EXEMPT`). An ALLOWED entry that no longer matches anything fails too, so the list shrinks
when its reason goes away instead of quietly outliving it (12.e).

Module-level test functions rather than a class with an interface beside it (ADR-0016): pytest
collects `test_*` functions, and ADR-0016's class rule is about production code.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Assembled from parts so the pattern does not match its own source line.
VOLATILE = re.compile(
    r"(?<![\w.~/$])(?:/private)?/(?:tmp|var/tmp|var/folders|dev/shm|run/user)(?![\w-])"
    r"|claude-" + r"501"
)

#: Trees never scanned, and why.
EXEMPT: tuple[tuple[str, str], ...] = (
    ("tests/*", "test code: a fixture string or a test's own tmp_path, never a place work is kept"),
    ("src/*/tests/*", "test code, as above"),
    ("src/*/test/*", "test code, as above"),
    ("src/*/*/tests/*", "test code, as above"),
    ("src/*/*/test/*", "test code, as above"),
    (
        "clients/*/test/*",
        "the editor clients' test code: fixture strings and each test's own scratch directory",
    ),
    (
        "packages/*/test/*",
        "the shared client packages' test code: fixture strings, as in the clients' own tests",
    ),
    ("*.jsonl", "append-only records of what happened (7.c); rewriting them falsifies them"),
    ("*.log", "append-only records of what happened (7.c); rewriting them falsifies them"),
    (
        "src/vibey_tools/skills/plugins/*",
        "third-party domain skills describing an OS's own directories, not this project's work",
    ),
    ("uv.lock", "a generated lock file"),
    ("*/uv.lock", "a generated lock file"),
)

#: The rule's own texts name the locations they forbid. A line there is allowed only when it is
#: saying that the location is volatile, never when it is using one.
RULE_TEXTS = (
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "src/vibey_tools/gh/docs/doctrines.md",
    "docs/plans/qwenstorm-3.0.0/README.md",
    "docs/plans/qwenstorm-3.0.0/STORM-CONTEXT.md",
    "docs/plans/qwenstorm-3.0.0/tools/storm_durability.py",
    # The VS Code extension's port of storm_durability.py: the same volatile locations, each
    # listed with the reason it is volatile, so the gate refuses what the storm refuses.
    "clients/vscode/src/core/storage.ts",
    "docs/plans/qwenstorm-3.0.0/tools/storm_checkpoint.py",
    "docs/plans/qwenstorm-3.0.0/tools/storm-queue.sh",
    "docs/plans/qwenstorm-3.0.0/tools/storm-watch.py",
    ".claude/skills/vibey-quality-gates/SKILL.md",
    ".cursor/rules/vibey-quality-gates.mdc",
    ".agents/skills/vibey-quality-gates/SKILL.md",
    ".agent/rules/vibey-quality-gates.md",
)
STATES_THE_RULE = re.compile(
    r"(?i)reboot|empt(y|ies|ied)|volatile|never|wiped|lost|refus|aged out|tmpfs|temporary"
    r"|memory-backed|logout|periodic|symlink|is really"
)

#: (file glob, what the line contains, why it may stay). Category (b) only.
ALLOWED: tuple[tuple[str, str, str], ...] = (
    (
        "docs/architecture/decisions/0058-*.md",
        r"/private/tmp",
        "the record of the 2026-09-24 reboot that erased the lanes' payloads: history, not a path in use",
    ),
    (
        "docs/architecture/evidence/slots-*",
        r"/private/tmp",
        "the sweep's evidence says why the lanes' payloads were lost: history, not a path in use",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/tools/storm_turn_pool.py",
        r"/private/tmp",
        "a comment recording why the pool replays specs, the payloads having gone with /private/tmp; not a path in use",
    ),
    (
        "src/vibey/infrastructure/db/local_auth.py",
        r"`/tmp`",
        "the Postgres unix socket directory, as a DSN's libpq host names it: where the server"
        " listens, not where work is kept",
    ),
    (
        ".claude/settings.json",
        r"\.s\.PGSQL\.5432",
        "the Postgres unix socket: a rendezvous point the server recreates at start",
    ),
    (
        ".github/workflows/*.yml",
        r"/tmp/",
        "a CI runner's scratch: the runner is destroyed after the job, whose product is published",
    ),
    (
        "src/vibey_tools/gh/.github/workflows/*.yml",
        r"/tmp/",
        "a CI runner's scratch, as above (vibey-gh's managed copy)",
    ),
    (
        "src/vibey_tools/gh/vibey_gh/templates/workflows/*.yml",
        r"/tmp/",
        "a CI runner's scratch, as above (the template vibey-gh renders)",
    ),
    (
        "deploy/docker/Dockerfile",
        r"/tmp/codex",
        "an image build's scratch, deleted in the same layer",
    ),
    (
        "deploy/helm/*",
        r'log-file = "/tmp/',
        "a pod's own log inside its container; the pod's filesystem does not outlive the pod",
    ),
    (
        "deploy/helm/golden/render.sh",
        r"mktemp",
        "a throwaway render, compared and deleted by the same script",
    ),
    (
        "docs/plans/fleet/*.md",
        r"/tmp/",
        "a smoke test's scratch directory, created and discarded by the recipe it is in",
    ),
    (
        "src/vibey_runners/agy/docs/plans/research-notes.md",
        r"/tmp/",
        "a reproduction of a sandbox escape: the files are the probe, not work",
    ),
    (
        "src/vibey_tools/bootstrap/examples/07_local_settings.py",
        r"/tmp/nonexistent\.json",
        "a path chosen because it does not exist",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/tools/lane_environment.py",
        r"\(/tmp is /private/tmp\)",
        "explains symlink resolution; names no place to keep work",
    ),
    (
        "docs/architecture/decisions/0057-*.md",
        r".",
        "the decision record of the incident: it names what was lost and where, to forbid it",
    ),
    (
        "docs/architecture/decisions/0051-*.md",
        r"`/private/tmp` literal",
        "a ratified record of the literal it removed",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/gap-docs-adr-land.md",
        r"/private/tmp",
        "a finished spec whose checks forbid the path: it removed it from ADRs 0045-0049",
    ),
    (
        "src/vibey/infrastructure/container/config.py",
        r'"/tmp:rw,noexec,nosuid',
        "the sandboxed container's own tmpfs mount, which by design holds nothing past the run",
    ),
    (
        "SECURITY.md",
        r"`/tmp` is mounted as a restricted tmpfs",
        "describes the sandboxed container's own tmpfs, which by design outlives nothing",
    ),
    (
        "docs/project.mmd",
        r"tmpfs /tmp",
        "the container sandbox's tmpfs in the architecture diagram, which outlives nothing",
    ),
    (
        "src/vibey/infrastructure/db/*.py",
        r"DEFAULT_SOCKET_DIRS",
        "PostgreSQL's socket directories, probed read-only; a socket is recreated at start",
    ),
    (
        "src/vibey_tools/gh/vibey_gh/heartbeat_timer.py",
        r'^\s+"(?:/private)?/(?:tmp|var/tmp|var/folders|dev/shm|run/user)",$',
        "the directories the heartbeat timer refuses to run from (ADR-0060): named to forbid them",
    ),
    (
        "docs/architecture/decisions/0055-*.md",
        r"/tmp -d postgres",
        "psql pointed at PostgreSQL's socket directory; a socket, not stored work",
    ),
    (
        "deploy/helm/*",
        r"value: /tmp$",
        "HOME for a one-shot model-pull client that keeps nothing; the pod is its lifetime",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/loops-runid-common.md",
        r"/tmp/l19_ci\.py",
        "a one-shot edit script the spec prints in full, run once and regenerable from the spec",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/loops-weighted-candidates.md",
        r"/tmp/l11_splice\.py",
        "a one-shot edit script the spec prints in full, run once and regenerable from the spec",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/roadmap-114-postgres-tier-store-p4.md",
        r'"/tmp/segment-contract-other"',
        "a test fixture's repo_path string inside the spec's test code, never created on disk",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/seo-robots-sitemap.md",
        r"--site-dir /tmp/vibey-seo-check",
        "a throwaway site build that the same check line inspects and discards",
    ),
    (
        "docs/plans/qwenstorm-3.0.0/specs/surfaces-cluster-smoke.md",
        r"/tmp/ping",
        "a CI step's captured output, read by the next line on a runner destroyed after the job",
    ),
)


def _tracked() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout
    return [name for name in listed.split("\0") if name]


def _matches(name: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)


def _hits() -> list[tuple[str, int, str, str]]:
    """Every (file, line number, line, the line with its neighbours) naming a volatile path.

    The neighbours are there for the rule's own texts: a sentence that says "never use /tmp"
    is often wrapped, and the word that makes it a prohibition lands on the next line.
    """
    found = []
    for name in _tracked():
        if _matches(name, tuple(glob for glob, _ in EXEMPT)):
            continue
        path = REPO / name
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if VOLATILE.search(line):
                context = "\n".join(lines[max(0, index - 1) : index + 2])
                found.append((name, index + 1, line, context))
    return found


def _allowed_by(name: str, line: str, context: str) -> str | None:
    """The reason this hit may stay, or None."""
    if _matches(name, RULE_TEXTS) and STATES_THE_RULE.search(context):
        return "the rule's own text, naming a location it forbids"
    for glob, contains, why in ALLOWED:
        if fnmatch.fnmatch(name, glob) and re.search(contains, line):
            return why
    return None


def test_the_pattern_recognises_every_volatile_spelling() -> None:
    for sample in (
        "/private/tmp/" + "claude-" + "501/storm/x",
        "cd /tmp/work",
        "`/var/folders/xx/T`",
        "/var/tmp/bench",
        "/dev/shm/lock",
        "/run/user/1000",
    ):
        assert VOLATILE.search(sample), sample
    for sample in ("docs/tmp/x", "$TMPDIR/uv", "tmp_path", "~/tmp", "/tmpfs", "a/var/tmp"):
        assert not VOLATILE.search(sample), sample


def test_no_tracked_text_keeps_durable_work_on_volatile_storage() -> None:
    offenders = [
        f"{name}:{number}: {line.strip()[:140]}"
        for name, number, line, context in _hits()
        if _allowed_by(name, line, context) is None
    ]
    assert not offenders, (
        "a volatile path is written into the tree. Move durable work under the storm home "
        "(storm_durability.py), reword docs that tell people to use it, or, if it is genuinely "
        "ephemeral, add it to ALLOWED with the reason:\n  " + "\n  ".join(offenders)
    )


def test_every_allow_list_entry_is_still_needed() -> None:
    hits = _hits()
    stale = [
        f"{glob} / {contains}"
        for glob, contains, _ in ALLOWED
        if not any(fnmatch.fnmatch(n, glob) and re.search(contains, ln) for n, _, ln, _ in hits)
    ]
    assert not stale, f"ALLOWED entries that match nothing any more; remove them: {stale}"


def test_every_allowance_says_why() -> None:
    for glob, contains, why in ALLOWED:
        assert len(why.split()) >= 5, f"{glob} / {contains}: the reason is the entry"
    for glob, why in EXEMPT:
        assert len(why.split()) >= 2, f"{glob}: the reason is the entry"
