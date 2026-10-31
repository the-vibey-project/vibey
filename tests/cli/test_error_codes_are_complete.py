# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A new error type cannot merge without a code, a cause and a fix (#1691).

Every concrete `VibeyError` subclass under `src/vibey` needs an entry in the shipped catalog; every
entry must name a class that exists (a rename is a failure here, not a silent orphan); a code is
used once; a next-step hint must appear in its entry's fix; and every command a fix names exists.

Module-level test functions rather than a class: pytest collects `test_*` functions, and the
class-and-interface rule is about production code (ADR-0016).
"""

from __future__ import annotations

import importlib
import pkgutil
import re

import vibey
from vibey.cli.error_catalog import ErrorCatalog
from vibey.cli.errors import _NEXT_STEP
from vibey.cli.main import app
from vibey.domain.errors import VibeyError


def _import_everything() -> None:
    # An import failure FAILS the test: a module that cannot be imported is coverage of unknown
    # size, not a pass, so nothing here is skipped.
    for module in pkgutil.walk_packages(vibey.__path__, "vibey."):
        importlib.import_module(module.name)


def _subclasses(base: type) -> set[type]:
    found: set[type] = set()
    for child in base.__subclasses__():
        found |= {child} | _subclasses(child)
    return found


def _name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


def test_every_vibey_error_has_a_code_and_every_entry_names_a_real_class() -> None:
    _import_everything()
    classes = {_name(cls): cls for cls in _subclasses(VibeyError) | {VibeyError}}
    entries = {e.qualname: e for e in ErrorCatalog.shipped().entries()}

    missing = sorted(set(classes) - set(entries))
    assert not missing, f"add an entry to src/vibey/cli/error_codes.toml for: {missing}"
    stale = sorted(set(entries) - set(classes))
    assert not stale, f"these entries name no VibeyError class (renamed or removed?): {stale}"


def test_a_base_that_is_raised_itself_is_not_marked_abstract() -> None:
    # An abstract entry has no code, so an error raised directly as one would print none.
    _import_everything()
    for entry in ErrorCatalog.shipped().entries():
        if entry.abstract:
            cls = next(
                c for c in _subclasses(VibeyError) | {VibeyError} if _name(c) == entry.qualname
            )
            assert cls.__subclasses__(), f"{entry.qualname} has no subclasses; give it a code"


def test_codes_are_assigned_in_order_without_gaps_or_reuse() -> None:
    codes = [e.code for e in ErrorCatalog.shipped().entries() if e.code]
    assert codes == [f"E{n:04d}" for n in range(1, len(codes) + 1)]


def test_every_hint_is_contained_in_its_entry_fix() -> None:
    catalog = ErrorCatalog.shipped()
    for error, hint in _NEXT_STEP.items():
        entry = catalog.entry_for(error)
        assert entry is not None, error.__name__
        assert " ".join(hint.split()) in " ".join(entry.fix.split()), error.__name__


def test_no_fix_names_a_command_that_does_not_exist() -> None:
    registered = {command.name for command in app.registered_commands}
    registered |= {group.name for group in app.registered_groups}
    for entry in ErrorCatalog.shipped().entries():
        for name in re.findall(r"`vibey ([a-z-]+)", entry.fix):
            assert name in registered, f"{entry.code} names `vibey {name}`"
