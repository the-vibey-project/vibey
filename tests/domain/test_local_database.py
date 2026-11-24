# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The names a local vibey database is made with, and the password file that keeps its secrets.

Pure rules: what a role or database may be called, the DSN each role connects with (never a
password in it), and how `~/.pgpass` lines are read and added, in libpq's own format.
"""

import pytest

from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.local_database_interface import (
    LocalDatabaseNamesInterface,
    PgPassInterface,
)
from vibey.domain.local_database import (
    InvalidDatabaseName,
    LocalDatabaseNames,
    PgPass,
    PgPassEntry,
)


def _names(**overrides: object) -> LocalDatabaseNames:
    values: dict[str, object] = {
        "database": "vibey",
        "owner_role": "vibey",
        "app_role": "vibey_app",
        "host": "localhost",
        "port": 5432,
    }
    values.update(overrides)
    return LocalDatabaseNames(**values)  # type: ignore[arg-type]


def test_the_names_and_the_password_file_satisfy_their_interfaces() -> None:
    assert isinstance(_names(), LocalDatabaseNamesInterface)
    assert isinstance(PgPass(), PgPassInterface)


def test_each_role_connects_with_a_dsn_that_carries_no_password() -> None:
    names = _names()
    assert names.owner_dsn == "postgresql://vibey@localhost:5432/vibey"
    assert names.app_dsn == "postgresql://vibey_app@localhost:5432/vibey"
    assert names.roles == ("vibey", "vibey_app")


@pytest.mark.parametrize(
    ("field", "label"),
    [("database", "database"), ("owner_role", "owner role"), ("app_role", "application role")],
)
@pytest.mark.parametrize(
    "bad", ["", "Vibey", "1vibey", "vi-bey", "vi bey", "v'; drop", "x" * 64, "vibey\x00"]
)
def test_a_name_that_is_not_a_plain_lowercase_identifier_is_refused(
    field: str, label: str, bad: str
) -> None:
    with pytest.raises(InvalidDatabaseName, match=label) as caught:
        _names(**{field: bad})
    assert isinstance(caught.value, VibeyError)


def test_the_longest_plain_identifier_postgres_keeps_is_accepted() -> None:
    assert _names(database="v" * 63).database == "v" * 63


def test_the_owner_and_the_application_role_must_differ() -> None:
    with pytest.raises(InvalidDatabaseName, match="must differ"):
        _names(owner_role="vibey", app_role="vibey")


@pytest.mark.parametrize("host", ["", "a:b", "a/b", "a@b", "a b"])
def test_a_host_that_would_break_a_dsn_is_refused(host: str) -> None:
    with pytest.raises(InvalidDatabaseName, match="host"):
        _names(host=host)


@pytest.mark.parametrize("port", [0, 65536, -1])
def test_a_port_outside_tcp_s_range_is_refused(port: int) -> None:
    with pytest.raises(InvalidDatabaseName, match="port"):
        _names(port=port)


# ------------------------------------------------------------------ ~/.pgpass


def test_a_password_is_found_by_host_port_database_and_user() -> None:
    text = (
        "# a comment\n"
        "\n"
        "localhost:5432:other:vibey:nope\n"
        "localhost:5432:vibey:vibey:s3cret\n"
        "localhost:5432:vibey:vibey:second-is-never-read\n"
    )
    assert PgPass().password_for(text, "localhost", 5432, "vibey", "vibey") == "s3cret"
    assert PgPass().password_for(text, "localhost", 5432, "vibey", "vibey_app") is None


def test_wildcards_match_as_libpq_matches_them() -> None:
    text = "*:*:*:vibey_app:any\n"
    assert PgPass().password_for(text, "localhost", 5432, "vibey", "vibey_app") == "any"


def test_escaped_colons_and_backslashes_are_read_back_whole() -> None:
    entry = PgPassEntry("localhost", 5432, "vibey", "vibey", r"a:b\c")
    text = PgPass().with_entry("", entry)
    assert text == "localhost:5432:vibey:vibey:a\\:b\\\\c\n"
    assert PgPass().password_for(text, "localhost", 5432, "vibey", "vibey") == r"a:b\c"


def test_a_line_without_five_fields_is_skipped_not_misread() -> None:
    text = "localhost:5432:vibey\nlocalhost:5432:vibey:vibey:ok\n"
    assert PgPass().entries(text) == (PgPassEntry("localhost", "5432", "vibey", "vibey", "ok"),)


def test_an_entry_is_appended_after_what_is_there_and_ends_the_file_with_a_newline() -> None:
    entry = PgPassEntry("localhost", 5432, "vibey", "vibey_app", "pw")
    assert PgPass().with_entry("other:1:a:b:c", entry) == (
        "other:1:a:b:c\nlocalhost:5432:vibey:vibey_app:pw\n"
    )
    assert PgPass().with_entry("other:1:a:b:c\n", entry).count("\n") == 2
