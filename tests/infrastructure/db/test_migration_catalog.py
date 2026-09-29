# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`MigrationCatalog`: the migrations resolve through the package, and none is a refusal.

The published 3.0.0 wheel carried no `.sql`, so an installed `vibey migrate` applied an
empty set, printed `applied 0 migration(s)`, and left a database with no schema. These
pin both halves of the fix: the packaged directory is the one the code reads, and an
empty or missing directory raises instead of returning `()`.
"""

from pathlib import Path

import pytest

import vibey.infrastructure.db as db_package
from vibey.bootstrap import migrations_dir
from vibey.domain.errors import VibeyError
from vibey.infrastructure.db.interfaces.migration_catalog_interface import (
    MigrationCatalogInterface,
)
from vibey.infrastructure.db.migration_catalog import MigrationCatalog, NoMigrationsFound


def test_the_packaged_catalog_reads_the_directory_inside_the_package() -> None:
    catalog = MigrationCatalog.packaged()

    assert catalog.directory == Path(db_package.__file__).parent / "migrations"
    assert catalog.directory.is_dir()


def test_bootstrap_resolves_the_same_directory_the_catalog_does() -> None:
    assert migrations_dir() == MigrationCatalog.packaged().directory


def test_the_packaged_catalog_lists_every_sql_file_in_apply_order() -> None:
    catalog = MigrationCatalog.packaged()

    migrations = catalog.migrations()

    on_disk = sorted(path.stem for path in catalog.directory.glob("*.sql"))
    assert [m.version for m in migrations] == on_disk
    assert migrations[0].version == "0001_project"


def test_the_catalog_satisfies_its_interface() -> None:
    assert isinstance(MigrationCatalog.packaged(), MigrationCatalogInterface)


def test_an_empty_directory_is_refused_rather_than_applied_as_nothing(tmp_path: Path) -> None:
    catalog = MigrationCatalog(tmp_path)

    with pytest.raises(NoMigrationsFound) as raised:
        catalog.migrations()

    assert raised.value.directory == tmp_path
    assert f"no migrations found at {tmp_path}" in str(raised.value)
    assert isinstance(raised.value, VibeyError)


def test_a_missing_directory_is_refused_too(tmp_path: Path) -> None:
    absent = tmp_path / "not-installed"

    with pytest.raises(NoMigrationsFound):
        MigrationCatalog(absent).migrations()


def test_a_directory_of_non_sql_files_holds_no_migrations(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("not a migration\n")

    with pytest.raises(NoMigrationsFound):
        MigrationCatalog(tmp_path).migrations()


def test_a_directory_the_caller_names_is_read_as_given(tmp_path: Path) -> None:
    (tmp_path / "0002_b.sql").write_text("SELECT 2;\n")
    (tmp_path / "0001_a.sql").write_text("SELECT 1;\n")

    migrations = MigrationCatalog(tmp_path).migrations()

    assert [m.version for m in migrations] == ["0001_a", "0002_b"]
    assert MigrationCatalog(tmp_path).directory == tmp_path
