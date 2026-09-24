# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where the chart puts the database owner's credentials (ADR-0055, review of #1100).

The owner can disable the ledger's triggers, so its DSN goes to one place: the `migrate`
init container. The review found it in the Plane pods (their `database-url` Secret) and
in Infisical (an inline `DB_CONNECTION_URI`): each surface database was reached as the
owner. Each now has a login role of its own.

Read from the committed goldens, which the `chart` CI job keeps equal to what the chart
renders (deploy/helm/golden/render.sh), so this needs no helm binary.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "deploy" / "helm" / "golden"
VALUES = yaml.safe_load((REPO / "deploy" / "helm" / "vibey" / "values.yaml").read_text())
OWNER = f"{VALUES['postgres']['user']}:{VALUES['postgres']['password']}@"
FULL_PROFILES = ("default", "ollama", "surfaces-off")


def _documents(profile: str) -> list[dict[str, Any]]:
    text = (GOLDEN / f"{profile}.yaml").read_text(encoding="utf-8")
    return [d for d in yaml.safe_load_all(text) if d]


def _strings(node: object, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _strings(value, f"{path}[{index}]")
    elif isinstance(node, str):
        yield path, node


def _containers(doc: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    spec = doc.get("spec", {}).get("template", {}).get("spec", {})
    for kind in ("initContainers", "containers"):
        for container in spec.get(kind) or []:
            yield f"{doc['kind']}/{doc['metadata']['name']}/{kind}/{container['name']}", container


@pytest.mark.parametrize("profile", FULL_PROFILES)
def test_the_owners_credentials_are_rendered_only_into_the_dsn_secret(profile: str) -> None:
    where = [
        f"{doc['kind']}/{doc['metadata']['name']}{path}"
        for doc in _documents(profile)
        for path, value in _strings(doc, "")
        if OWNER in value
    ]

    assert where == ["Secret/vibey-vibey-dsn.stringData.migrate-dsn"], where


@pytest.mark.parametrize("profile", FULL_PROFILES)
def test_only_the_migrate_init_container_mounts_the_owners_dsn(profile: str) -> None:
    mounted = [
        name
        for doc in _documents(profile)
        for name, container in _containers(doc)
        for env in container.get("env") or []
        if (env.get("valueFrom") or {}).get("secretKeyRef", {}).get("key") == "migrate-dsn"
    ]

    assert mounted, "no workload runs `vibey migrate`"
    assert all(name.endswith("/initContainers/migrate") for name in mounted), mounted


@pytest.mark.parametrize("profile", ("default",))
def test_each_surface_database_is_reached_as_its_own_role(profile: str) -> None:
    urls = {
        path: value
        for doc in _documents(profile)
        for path, value in _strings(doc, "")
        if "-postgres:5432/" in value and value.startswith("postgres")
    }
    plane = next(v for p, v in urls.items() if v.endswith("/plane?sslmode=disable"))
    infisical = next(v for p, v in urls.items() if v.endswith("/infisical?sslmode=disable"))

    assert plane.startswith("postgres://plane:")
    assert infisical.startswith("postgres://infisical:")


def test_an_existing_secret_install_gets_no_migrate_step_unless_it_names_one() -> None:
    """Review finding 4: an existing `dsn.existingSecret` without a `migrate-dsn` key
    must not strand the worker in CreateContainerConfigError after an upgrade."""
    docs = _documents("existing-secret")
    names = [name for doc in docs for name, _ in _containers(doc)]

    assert names and not any(name.endswith("/migrate") for name in names), names
