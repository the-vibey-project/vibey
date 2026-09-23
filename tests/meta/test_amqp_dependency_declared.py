# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests related to the AMQP client dependency.

These tests follow the TDD plan from the issue description.
"""

import configparser
import pathlib
import tomllib

ROOT_PYPROJECT = pathlib.Path("pyproject.toml")
BOOTSTRAP_PYPROJECT = pathlib.Path("src/vibey_tools/bootstrap/pyproject.toml")
IMPORTLINTER = pathlib.Path(".importlinter")


def _load_toml(path: pathlib.Path) -> dict:
    return tomllib.loads(path.read_text())


def test_root_distribution_requires_aio_pika():
    data = _load_toml(ROOT_PYPROJECT)
    deps = data["project"]["dependencies"]
    assert any("aio-pika" in dep for dep in deps), "aio-pika not in root dependencies"


def test_bootstrap_amqp_and_all_extras_require_aio_pika():
    data = _load_toml(BOOTSTRAP_PYPROJECT)
    # dependencies
    deps = data["project"]["dependencies"]
    assert any("aio-pika" in dep for dep in deps), "aio-pika not in bootstrap dependencies"
    # all extra
    extras = data["project"]["optional-dependencies"]
    assert "all" in extras, "missing 'all' extra in bootstrap"
    all_deps = extras["all"]
    assert any("aio-pika" in dep for dep in all_deps), "aio-pika not in bootstrap all extra"


def test_domain_forbids_the_amqp_client():
    conf = configparser.ConfigParser()
    conf.read(IMPORTLINTER)
    forb = set(conf["importlinter:contract:domain-independence"]["forbidden_modules"].splitlines())
    for mod in ("aio_pika", "aiormq", "pamqp"):
        assert mod in forb, f"{mod} not forbidden in domain contract"
