# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The published wheel carries the schema, and code imported from it finds the schema.

Measured on 2026-09-29: neither a locally built wheel nor PyPI's `vibey-engine` 3.0.0
contained a single `.sql`. The migrations lived at the repository root, resolved by
walking up from `bootstrap.py`, which reached them from a checkout and from the image --
the Dockerfile copied them by hand -- and from nowhere a user actually installs to. On an
empty database, `vibey migrate` printed `applied 0 migration(s)`, and the first `vibey new`
failed on `relation "project" does not exist`. Every test passed, because every test ran
from the checkout.

So this builds the real wheel, the artifact PyPI receives, and asserts on it: that every
migration in the tree is inside it, and that `MigrationCatalog.packaged()` -- imported from
the wheel's own contents, not from `src/` -- lists them from inside that same layout.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
following tests/meta/test_shipped_trees_are_reachable.py: pytest collects `test_*`
functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PACKAGED = "vibey/infrastructure/db/migrations"
SOURCE = REPO / "src" / PACKAGED

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The wheel `uv build` produces from this checkout, built once for the module."""
    uv = shutil.which("uv")
    assert uv is not None, "uv is not on PATH; the release builds the wheel with it"
    out = tmp_path_factory.mktemp("wheel")
    subprocess.run(  # noqa: S603 -- a fixed argv; uv's path comes from shutil.which
        [uv, "build", "--wheel", "--out-dir", str(out), str(REPO)],
        check=True,
        capture_output=True,
        text=True,
    )
    built = sorted(out.glob("vibey_engine-*.whl"))
    assert len(built) == 1, f"expected one vibey_engine wheel, found {built}"
    return built[0]


def _source_migrations() -> list[str]:
    names = sorted(path.name for path in SOURCE.glob("*.sql"))
    assert names, f"no migrations in {SOURCE}; the tree moved and this test did not"
    return names


def test_the_wheel_carries_every_migration_in_the_tree(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        shipped = sorted(
            name.removeprefix(f"{PACKAGED}/")
            for name in archive.namelist()
            if name.startswith(f"{PACKAGED}/") and name.endswith(".sql")
        )

    assert shipped == _source_migrations()


def test_the_wheel_carries_the_migrations_byte_for_byte(wheel: Path) -> None:
    """A migration's checksum is recorded when it is applied, and an edited one fails
    the start (`MigrationChecksumError`); a wheel that shipped different bytes would fail
    every database the checkout had migrated."""
    with zipfile.ZipFile(wheel) as archive:
        for name in _source_migrations():
            assert archive.read(f"{PACKAGED}/{name}") == (SOURCE / name).read_bytes(), name


def test_code_imported_from_the_wheel_finds_the_packaged_migrations(
    wheel: Path, tmp_path: Path
) -> None:
    """The resolution, run from the wheel's layout rather than from `src/`.

    The wheel is unpacked and put first on `PYTHONPATH`, so `vibey` imports from it and
    the third-party dependencies still come from this environment. Nothing here can reach
    the checkout's migrations: had the catalog walked up from its own file as
    `bootstrap.py` used to, it would land in `tmp_path`'s parents and find nothing.
    """
    unpacked = tmp_path / "site-packages"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(unpacked)
    probe = (
        "import json\n"
        "from vibey.infrastructure.db.migration_catalog import MigrationCatalog\n"
        "catalog = MigrationCatalog.packaged()\n"
        "print(json.dumps({'directory': str(catalog.directory),"
        " 'versions': [m.version for m in catalog.migrations()]}))\n"
    )
    env = {**os.environ, "PYTHONPATH": str(unpacked)}
    result = subprocess.run(  # noqa: S603 -- a fixed argv: this interpreter and a literal probe
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
    )
    found = json.loads(result.stdout)

    assert Path(found["directory"]).resolve() == (unpacked / PACKAGED).resolve()
    assert found["versions"] == [name.removesuffix(".sql") for name in _source_migrations()]
