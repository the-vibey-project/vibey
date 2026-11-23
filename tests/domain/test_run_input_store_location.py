# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[inputs]` names where the run input store is, never its credentials (SP-LOOPS Phase 3c,
Task 2; ADR-0105). Module-level test functions: pytest collects them, and the class-and-interface
rule is about production code (ADR-0016)."""

from __future__ import annotations

from typing import Any

import pytest

from vibey.domain.run_input import InputStoreLocation, RunInputsSettings

SEAWEED: dict[str, Any] = {
    "store": "seaweedfs",
    "endpoint": "https://files.example.test:8333",
    "bucket": "vibey-inputs",
}


def test_the_default_is_local_in_the_persons_state_folder() -> None:
    assert RunInputsSettings().store == InputStoreLocation()
    assert RunInputsSettings.from_table({}).store == InputStoreLocation()
    location = InputStoreLocation()
    assert location.kind == "local" and location.store_dir is None
    assert location.prefix == "vibey/inputs" and location.region == "us-east-1"
    assert location.access_key_env == "VIBEY_INPUTS_ACCESS_KEY"
    assert location.secret_key_env == "VIBEY_INPUTS_SECRET_KEY"
    assert location.timeout_seconds == 10.0


def test_a_seaweedfs_table_parses() -> None:
    settings = RunInputsSettings.from_table(
        {
            **SEAWEED,
            "endpoint": "https://files.example.test:8333/",
            "prefix": "team/inputs",
            "region": "garage",
            "access_key_env": "MY_KEY",
            "secret_key_env": "MY_SECRET",
            "timeout_seconds": 3,
            "max_items": 9,
        }
    )
    assert settings.max_items == 9
    assert settings.store == InputStoreLocation(
        kind="seaweedfs",
        endpoint="https://files.example.test:8333",
        bucket="vibey-inputs",
        prefix="team/inputs",
        region="garage",
        access_key_env="MY_KEY",
        secret_key_env="MY_SECRET",
        timeout_seconds=3,
    )


def test_a_local_table_with_a_store_dir_parses() -> None:
    settings = RunInputsSettings.from_table({"store": "local", "store_dir": "/srv/vibey/inputs"})
    assert settings.store == InputStoreLocation(store_dir="/srv/vibey/inputs")


@pytest.mark.parametrize(
    "endpoint",
    ["http://localhost:8333", "http://127.0.0.1:8333", "http://[::1]:8333", "https://h.test/"],
)
def test_loopback_http_and_any_https_endpoint_are_accepted(endpoint: str) -> None:
    location = InputStoreLocation.from_table({**SEAWEED, "endpoint": endpoint})
    assert location.endpoint == endpoint.rstrip("/")


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"store": "s3"}, "store must be one of local, seaweedfs"),
        ({"store": 1}, "store must be one of"),
        ({"endpoint": "https://h.test"}, "endpoint does nothing with store = 'local'"),
        ({"bucket": "vibey-inputs"}, "bucket does nothing with store = 'local'"),
        ({"prefix": "a"}, "prefix does nothing"),
        ({"timeout_seconds": 1}, "timeout_seconds does nothing"),
        ({"store_dir": "relative/inputs"}, "store_dir must be an absolute path"),
        ({"store_dir": 3}, "store_dir must be a string"),
        ({**SEAWEED, "store_dir": "/srv"}, "store_dir does nothing with store = 'seaweedfs'"),
        ({"store": "seaweedfs", "bucket": "vibey-inputs"}, "needs an endpoint and a bucket"),
        ({"store": "seaweedfs", "endpoint": "https://h.test"}, "needs an endpoint and a bucket"),
        ({**SEAWEED, "endpoint": "ftp://h.test"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "https://"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "https://h.test/path"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "https://h.test?q=1"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "https://h.test#f"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "https://h.test:port"}, "endpoint must be http"),
        ({**SEAWEED, "endpoint": "http://files.example.test"}, "plain http only for localhost"),
        ({**SEAWEED, "endpoint": "http://10.0.0.1"}, "plain http only for localhost"),
        ({**SEAWEED, "endpoint": 8333}, "endpoint must be a string"),
        ({**SEAWEED, "bucket": "Vibey"}, "is not an S3 bucket name"),
        ({**SEAWEED, "bucket": "ab"}, "is not an S3 bucket name"),
        ({**SEAWEED, "bucket": "-bucket"}, "is not an S3 bucket name"),
        ({**SEAWEED, "prefix": ""}, "prefix"),
        ({**SEAWEED, "prefix": "a//b"}, "none empty"),
        ({**SEAWEED, "prefix": "a/../b"}, "none empty"),
        ({**SEAWEED, "prefix": "a/./b"}, "none empty"),
        ({**SEAWEED, "prefix": "a b"}, "must be '/'-separated segments"),
        ({**SEAWEED, "region": ""}, "is not a region name"),
        ({**SEAWEED, "region": "us east"}, "is not a region name"),
        ({**SEAWEED, "timeout_seconds": 0}, "timeout_seconds must be a positive number"),
        ({**SEAWEED, "timeout_seconds": -1.5}, "timeout_seconds must be a positive number"),
        ({**SEAWEED, "timeout_seconds": True}, "timeout_seconds must be a positive number"),
        ({**SEAWEED, "timeout_seconds": "10"}, "timeout_seconds must be a positive number"),
        ({**SEAWEED, "access_key_env": "lower"}, "access_key_env must name an environment"),
        ({**SEAWEED, "secret_key_env": "1ABC"}, "secret_key_env must name an environment"),
        ({**SEAWEED, "access_key_env": 7}, "access_key_env must be a string"),
    ],
)
def test_each_store_rule_refuses(table: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RunInputsSettings.from_table(table)


def test_an_endpoint_with_user_info_is_refused_without_echoing_it() -> None:
    with pytest.raises(ValueError) as caught:
        RunInputsSettings.from_table({**SEAWEED, "endpoint": "https://AKID:hunter2@h.test"})
    assert "no user info" in str(caught.value)
    assert "hunter2" not in str(caught.value) and "AKID" not in str(caught.value)


def test_a_location_built_directly_holds_the_same_rules() -> None:
    with pytest.raises(ValueError, match="store must be one of"):
        InputStoreLocation(kind="nfs")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="a local store has neither"):
        InputStoreLocation(endpoint="https://h.test")
    with pytest.raises(ValueError, match="a local store has neither"):
        InputStoreLocation(bucket="vibey-inputs")
    with pytest.raises(ValueError, match='store_dir is for store = "local" only'):
        InputStoreLocation(
            kind="seaweedfs", store_dir="/srv", endpoint="https://h.test", bucket="vibey-inputs"
        )


@pytest.mark.parametrize("key", ["access_key", "secret_key", "password", "token"])
def test_a_credential_in_the_inputs_table_is_refused_without_echoing_it(key: str) -> None:
    with pytest.raises(ValueError) as caught:
        RunInputsSettings.from_table({**SEAWEED, key: "s3cr3t-sentinel"})
    message = str(caught.value)
    assert "s3cr3t-sentinel" not in message
    assert "holds no credential" in message and key in message
    assert "access_key_env / secret_key_env" in message


def test_an_unknown_key_beside_the_store_keys_is_still_refused() -> None:
    with pytest.raises(ValueError, match="'endpiont' is not a setting"):
        RunInputsSettings.from_table({**SEAWEED, "endpiont": "x"})


def test_describe_names_scheme_host_bucket_and_prefix_only() -> None:
    location = InputStoreLocation.from_table(
        {**SEAWEED, "access_key_env": "KEY_VAR", "secret_key_env": "SECRET_VAR"}
    )
    assert location.describe() == (
        "seaweedfs store https://files.example.test:8333/vibey-inputs/vibey/inputs"
    )
    assert "KEY_VAR" not in location.describe() and "SECRET_VAR" not in location.describe()
    assert InputStoreLocation().describe() == "local store at your state folder"
    assert InputStoreLocation(store_dir="/srv/in").describe() == "local store at /srv/in"


SECRET_40 = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
UPPER_40 = "AKIAIOSFODNN7EXAMPLEAKIAIOSFODNN7EXAMPLE"
UPPER_20 = "AKIAIOSFODNN7EXAMPLE"


@pytest.mark.parametrize("secret", [SECRET_40, UPPER_40, UPPER_20, "A" * 65])
@pytest.mark.parametrize("key", ["access_key_env", "secret_key_env"])
def test_a_credential_written_where_its_variable_belongs_is_never_echoed(
    key: str, secret: str
) -> None:
    """Review B2: the refusal names the key, never the value it refused."""
    with pytest.raises(ValueError) as caught:
        RunInputsSettings.from_table({**SEAWEED, key: secret})
    message = str(caught.value)
    assert secret not in message
    assert key in message and "the value given is not shown" in message


@pytest.mark.parametrize(
    "name", ["MY_KEY", "VIBEY_INPUTS_SECRET_KEY", "AWS_SECRET_ACCESS_KEY", "SHORTNAME"]
)
def test_ordinary_variable_names_are_still_accepted(name: str) -> None:
    location = InputStoreLocation.from_table({**SEAWEED, "secret_key_env": name})
    assert location.secret_key_env == name


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_a_timeout_that_is_not_finite_is_refused(value: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be a positive number"):
        RunInputsSettings.from_table({**SEAWEED, "timeout_seconds": value})


@pytest.mark.parametrize("rows", [0, -1, True, "10", 1.5])
def test_max_listed_rows_must_be_a_positive_integer(rows: object) -> None:
    with pytest.raises(ValueError, match="max_listed_rows must be a positive integer"):
        RunInputsSettings.from_table({**SEAWEED, "max_listed_rows": rows})


def test_max_listed_rows_is_a_seaweedfs_key() -> None:
    assert InputStoreLocation.from_table({**SEAWEED, "max_listed_rows": 9}).max_listed_rows == 9
    with pytest.raises(ValueError, match="max_listed_rows does nothing"):
        RunInputsSettings.from_table({"max_listed_rows": 9})
