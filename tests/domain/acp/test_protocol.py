# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ACP protocol constants and enums, held against the official SDK's schema (SP-ACP, Task 2)."""

from enum import StrEnum
from typing import Any, get_args

import pytest
from acp import schema

from vibey.domain.acp import protocol
from vibey.domain.acp.protocol import (
    NoticeSeverity,
    PermissionKind,
    PlanEntryStatus,
    StopReason,
    ToolCallStatus,
    ToolKind,
)


def _literal_values(annotation: Any) -> set[str]:
    """Every string a (possibly nested, possibly optional) `Literal` annotation admits."""
    found: set[str] = set()
    for arg in get_args(annotation):
        if isinstance(arg, str):
            found.add(arg)
        else:
            found |= _literal_values(arg)
    return found


@pytest.mark.parametrize(
    ("enum", "sdk_values"),
    [
        (StopReason, get_args(schema.StopReason)),
        (ToolCallStatus, get_args(schema.ToolCallStatus)),
        (ToolKind, get_args(schema.ToolKind)),
        (PlanEntryStatus, get_args(schema.PlanEntryStatus)),
        (PermissionKind, get_args(schema.PermissionOptionKind)),
    ],
)
def test_enums_match_the_sdk_schema_literals(
    enum: type[StrEnum], sdk_values: tuple[str, ...]
) -> None:
    assert {member.value for member in enum} == set(sdk_values)


def test_enum_values_validate_through_the_sdk_models() -> None:
    for reason in StopReason:
        schema.PromptResponse.model_validate({"stopReason": reason.value})
    for status in ToolCallStatus:
        schema.ToolCallUpdate.model_validate({"toolCallId": "t", "status": status.value})
    for kind in ToolKind:
        schema.ToolCallUpdate.model_validate({"toolCallId": "t", "kind": kind.value})
    for plan_status in PlanEntryStatus:
        schema.PlanEntry.model_validate(
            {"content": "c", "priority": "medium", "status": plan_status.value}
        )
    for permission in PermissionKind:
        schema.PermissionOption.model_validate(
            {"optionId": "o", "name": "n", "kind": permission.value}
        )


def test_notice_severities_validate_through_the_sdk_notice() -> None:
    assert {s.value for s in NoticeSeverity} == _literal_values(
        schema.Notice.model_fields["severity"].annotation
    ) - {"str"}
    for severity in NoticeSeverity:
        schema.Notice.model_validate({"severity": severity.value, "title": "t"})


def test_protocol_version_is_the_sdks() -> None:
    import acp

    assert protocol.PROTOCOL_VERSION == acp.PROTOCOL_VERSION == 1


def test_error_codes_are_ones_the_sdk_schema_admits() -> None:
    annotation = schema.Error.model_fields["code"].annotation
    codes = {value for arg in get_args(annotation) for value in get_args(arg)}
    assert {
        protocol.RESOURCE_NOT_FOUND,
        protocol.AUTH_REQUIRED,
        protocol.REQUEST_CANCELLED,
    } <= codes


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("INITIALIZE", "initialize"),
        ("AUTHENTICATE", "authenticate"),
        ("SESSION_NEW", "session/new"),
        ("SESSION_LOAD", "session/load"),
        ("SESSION_RESUME", "session/resume"),
        ("SESSION_LIST", "session/list"),
        ("SESSION_CLOSE", "session/close"),
        ("SESSION_PROMPT", "session/prompt"),
        ("SESSION_CANCEL", "session/cancel"),
        ("SESSION_SET_MODE", "session/set_mode"),
        ("SESSION_UPDATE", "session/update"),
        ("REQUEST_PERMISSION", "session/request_permission"),
    ],
)
def test_method_names_are_the_protocol_spellings(name: str, value: str) -> None:
    assert getattr(protocol, name) == value


def test_method_names_exist_in_the_sdk_method_tables() -> None:
    from acp.meta import AGENT_METHODS, CLIENT_METHODS

    agent = set(AGENT_METHODS.values())
    client = set(CLIENT_METHODS.values())
    for name in (
        protocol.INITIALIZE,
        protocol.AUTHENTICATE,
        protocol.SESSION_NEW,
        protocol.SESSION_LOAD,
        protocol.SESSION_RESUME,
        protocol.SESSION_LIST,
        protocol.SESSION_CLOSE,
        protocol.SESSION_PROMPT,
        protocol.SESSION_CANCEL,
        protocol.SESSION_SET_MODE,
    ):
        assert name in agent
    assert protocol.SESSION_UPDATE in client
    assert protocol.REQUEST_PERMISSION in client


def test_error_code_values() -> None:
    assert protocol.RESOURCE_NOT_FOUND == -32002
    assert protocol.AUTH_REQUIRED == -32000
    assert protocol.REQUEST_CANCELLED == -32800
