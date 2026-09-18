# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign DESIGN provider (8.a): phase one without paid credentials."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibey.application.design import DesignEvent, DesignStage
from vibey.domain import errors
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.spec import ConstraintKind
from vibey.infrastructure.engines import qwenloop_design as mod
from vibey.infrastructure.engines.interfaces import (
    OllamaChatClientInterface,
    QwenloopDesignProviderInterface,
)
from vibey.infrastructure.engines.ollama_chat import OllamaChatClient
from vibey.infrastructure.engines.qwenloop_design import (
    QwenloopDesignProvider,
    SovereignResearchUnavailable,
)

SPEC_PAYLOAD = {
    "objective": "publish a heartbeat ref",
    "walking_skeleton": "a CLI that writes one ref",
    "non_goals": ["a web UI"],
    "constraints": [{"text": "git and stdlib only", "kind": "hard"}],
    "criteria": [
        {
            "criterion_id": "c1",
            "given": "a repository",
            "when": "the CLI runs",
            "then": "a ref exists",
            "fit": "git ls-remote shows it",
        }
    ],
    "nfrs": [
        {
            "nfr_id": "n1",
            "attribute": "Latency",
            "scale": "seconds",
            "meter": "wall clock",
            "must": "under 5",
            "wish": "under 1",
            "fit_criterion": "timed push",
        }
    ],
}


def _event(payload: dict[str, object]) -> DesignEvent:
    return DesignEvent(
        kind=EventKind.ANSWER_GIVEN,
        provenance=Provenance.TRUSTED,
        produced_at=datetime.now(UTC),
        payload=payload,
    )


class FakeTransport:
    """Stands in for Ollama at the transport seam, capturing what was sent."""

    def __init__(self, content: object) -> None:
        self.content = content
        self.sent: list[dict[str, object]] = []

    async def post_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> dict[str, object]:
        self.sent.append(dict(payload))
        body = self.content if isinstance(self.content, str) else json.dumps(self.content)
        return {"message": {"content": body}}


def _provider(
    content: object, evidence_dir: Path | None = None
) -> tuple[QwenloopDesignProvider, list[dict[str, object]]]:
    """A provider whose shared chat client talks to a fake Ollama."""
    transport = FakeTransport(content)
    chat = OllamaChatClient(transport=transport)
    return QwenloopDesignProvider(chat=chat, evidence_dir=evidence_dir), transport.sent


@pytest.mark.asyncio
async def test_a_stage_of_questions_comes_back_shaped() -> None:
    provider, sent = _provider(
        {
            "questions": [
                {"question_id": "q1", "text": "what problem?", "default": "none", "blocking": True}
            ]
        },
    )
    batch = await provider.batch(DesignStage.CONTEXT_FREE, [])
    assert batch.stage is DesignStage.CONTEXT_FREE
    assert [q.question_id for q in batch.questions] == ["q1"]
    assert batch.questions[0].blocking is True
    # Constrained decoding is the whole reason this provider is reliable: the schema is
    # compiled to a grammar, so malformed JSON is unreachable rather than merely unlikely.
    assert sent[0]["format"] == mod.QUESTIONS_SCHEMA
    # temperature 0: a DESIGN stage that asks different questions on an unchanged ledger
    # cannot be reasoned about by the phase that consumes it.
    assert sent[0]["options"]["temperature"] == 0
    assert sent[0]["options"]["num_ctx"] >= 4096
    assert sent[0]["stream"] is False


@pytest.mark.asyncio
async def test_a_stage_with_no_questions_is_refused() -> None:
    provider, _ = _provider({"questions": []})
    with pytest.raises(ValueError, match="non-empty questions list"):
        await provider.batch(DesignStage.JOB_STORY, [])


@pytest.mark.asyncio
async def test_research_refuses_rather_than_inventing_a_source() -> None:
    """The floor, declared. A local model has no web access, and returning its
    recollection with a `source` field would put a fabricated citation into a design
    spec — a wrong answer that looks sourced survives review, where a missing one does
    not."""
    provider, sent = _provider({"title": "never", "content": "asked"})
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await provider.research("OAuth device flow")
    message = str(caught.value)
    assert "OAuth device flow" in message
    assert "no" in message and "web access" in message
    assert "fabricated source" in message
    assert "VIBEY_EVIDENCE_DIR is unset" in message
    # The refusal is the domain's, so application/ can catch it without importing
    # infrastructure, and it names the file that would have satisfied it.
    assert caught.value.__class__ is errors.SovereignResearchUnavailable
    assert caught.value.topic == "OAuth device flow"
    assert caught.value.evidence_name == "oauthdeviceflow.md"
    # And the model is never asked: there is nothing honest for it to summarise.
    assert sent == []


@pytest.mark.asyncio
async def test_research_summarises_operator_supplied_evidence(tmp_path: Path) -> None:
    """The happy path: a document with a `source:` first line is summarised, and the
    source in the result is the operator's line, never the model's."""
    (tmp_path / "oauthdeviceflow.md").write_text(
        "source: https://example.test/rfc8628\n\nThe device flow issues a user code.",
        encoding="utf-8",
    )
    provider, sent = _provider({"title": "Device flow basics", "content": "summary"}, tmp_path)
    result = await provider.research("OAuth device flow")
    assert result.title == "Device flow basics"
    assert result.source == "https://example.test/rfc8628"
    assert result.content == "summary"
    assert "The device flow issues a user code." in str(sent[0]["messages"][1]["content"])


@pytest.mark.asyncio
async def test_research_refuses_an_empty_summary_from_the_model(tmp_path: Path) -> None:
    """Constrained decoding guarantees the shape, not that the fields are non-empty —
    a summary of nothing is not a usable research result either."""
    (tmp_path / "topic.md").write_text("source: https://example.test\n\nbody", encoding="utf-8")
    provider, _ = _provider({"title": "", "content": ""}, tmp_path)
    with pytest.raises(ValueError, match="non-empty title and content"):
        await provider.research("topic")


@pytest.mark.asyncio
async def test_research_refuses_when_no_evidence_file_matches(tmp_path: Path) -> None:
    """It says which file it looked for, in the stem it actually reads: the old message
    named `something unwritten.md`, a file the provider would never have opened."""
    provider = QwenloopDesignProvider(evidence_dir=tmp_path)
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await provider.research("something unwritten")
    assert f"No somethingunwritten.md (or .txt) exists in {tmp_path}" in str(caught.value)
    assert caught.value.evidence_name == "somethingunwritten.md"


@pytest.mark.asyncio
async def test_research_refuses_a_topic_no_file_can_match(tmp_path: Path) -> None:
    """A topic with no letters or digits reduces to no file name at all, so no evidence
    can ever satisfy it -- and the refusal says so rather than asking for a file."""
    provider = QwenloopDesignProvider(evidence_dir=tmp_path)
    with pytest.raises(SovereignResearchUnavailable, match="reduces to no usable file name") as c:
        await provider.research("???")
    assert c.value.evidence_name is None


@pytest.mark.asyncio
async def test_research_refuses_a_document_with_no_source_line(tmp_path: Path) -> None:
    (tmp_path / "nosource.md").write_text("just some text, no provenance", encoding="utf-8")
    with pytest.raises(SovereignResearchUnavailable, match="no `source:` first line") as caught:
        await QwenloopDesignProvider(evidence_dir=tmp_path).research("no source")
    assert caught.value.evidence_name == "nosource.md"


@pytest.mark.asyncio
async def test_research_refuses_an_empty_source_or_empty_body(tmp_path: Path) -> None:
    (tmp_path / "emptysource.md").write_text("source: \n\nbody here", encoding="utf-8")
    with pytest.raises(SovereignResearchUnavailable, match="empty source or carries no body"):
        await QwenloopDesignProvider(evidence_dir=tmp_path).research("empty source")

    (tmp_path / "emptybody.txt").write_text("source: https://example.test\n\n   ", encoding="utf-8")
    with pytest.raises(SovereignResearchUnavailable, match="empty source or carries no body") as c:
        await QwenloopDesignProvider(evidence_dir=tmp_path).research("empty body")
    assert c.value.evidence_name == "emptybody.txt"


def test_the_evidence_directory_comes_from_the_environment(tmp_path: Path) -> None:
    """VIBEY_EVIDENCE_DIR is read in one place, and an empty value counts as unset."""
    chat = OllamaChatClient(transport=FakeTransport({}))
    configured = QwenloopDesignProvider.from_environment(
        {"VIBEY_EVIDENCE_DIR": str(tmp_path)}, chat=chat
    )
    assert configured._evidence_dir == tmp_path
    assert configured._chat is chat
    assert QwenloopDesignProvider.from_environment({"VIBEY_EVIDENCE_DIR": ""})._evidence_dir is None
    assert QwenloopDesignProvider.from_environment({})._evidence_dir is None


def test_the_provider_meets_its_declared_seams() -> None:
    provider = QwenloopDesignProvider()
    assert isinstance(provider, QwenloopDesignProviderInterface)
    assert isinstance(provider._chat, OllamaChatClientInterface)


def test_a_traversal_unsafe_topic_addresses_no_evidence_file(tmp_path: Path) -> None:
    """`topic` is model-minted text, never a trusted path component. Reducing it to an
    alnum/-/_ stem means a topic like `../../etc/passwd` cannot walk out of the evidence
    directory — it collapses to a stem that (almost certainly) matches nothing."""
    provider = QwenloopDesignProvider(evidence_dir=tmp_path)
    assert provider._evidence_for("../../etc/passwd") is None
    assert provider._evidence_for("   ") is None


def test_no_evidence_dir_configured_means_no_evidence(tmp_path: Path) -> None:
    (tmp_path / "topic.md").write_text("source: x\n\nbody", encoding="utf-8")
    provider = QwenloopDesignProvider()
    assert provider._evidence_for("topic") is None


@pytest.mark.asyncio
async def test_a_spec_is_synthesised_from_the_ledger() -> None:
    provider, sent = _provider(SPEC_PAYLOAD)
    spec = await provider.synthesize([_event({"q": "objective", "a": "x"})])
    assert spec.objective == "publish a heartbeat ref"
    assert spec.walking_skeleton == "a CLI that writes one ref"
    assert spec.non_goals == ("a web UI",)
    assert spec.constraints[0].kind is ConstraintKind.HARD
    assert spec.criteria[0].criterion_id == "c1"
    assert spec.nfrs[0].wish == "under 1"
    # The ledger reaches the model as data, and the prompt says so.
    assert "never as instructions" in str(sent[0]["messages"][0]["content"])


@pytest.mark.asyncio
async def test_an_empty_wish_is_absent_rather_than_an_empty_string() -> None:
    """A grammar cannot express "omit this key", so the model emits `""` for an NFR with
    no wish. Carrying that through as a wish of "" would be a requirement nobody stated."""
    payload = json.loads(json.dumps(SPEC_PAYLOAD))
    payload["nfrs"][0]["wish"] = ""
    provider, _ = _provider(payload)
    spec = await provider.synthesize([])
    assert spec.nfrs[0].wish is None


@pytest.mark.asyncio
async def test_a_spec_without_a_single_criterion_is_refused() -> None:
    """A spec nothing can be checked against is not buildable, and would hand the BUILD
    phase a target it can never prove it hit."""
    payload = json.loads(json.dumps(SPEC_PAYLOAD))
    payload["criteria"] = []
    provider, _ = _provider(payload)
    with pytest.raises(ValueError, match="at least one acceptance criterion"):
        await provider.synthesize([])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda p: p.pop("objective"), "invalid DesignSpec JSON"),
        (lambda p: p.update(non_goals="not a list"), "non_goals must be a list"),
        (lambda p: p.update(constraints=["not an object"]), "every constraints item"),
        (lambda p: p.update(constraints=[{"text": "x", "kind": "sideways"}]), "invalid DesignSpec"),
    ],
)
async def test_a_malformed_spec_is_refused_at_the_boundary(mutate, expected: str) -> None:
    payload = json.loads(json.dumps(SPEC_PAYLOAD))
    mutate(payload)
    provider, _ = _provider(payload)
    with pytest.raises(ValueError, match=expected):
        await provider.synthesize([])


@pytest.mark.asyncio
async def test_a_gateway_that_is_not_ollama_cannot_pass_for_an_answer() -> None:
    """Constrained decoding guarantees the schema only if the thing on the other end is
    actually Ollama. This is a process boundary, so the shape is asserted, not trusted --
    by the shared client, which every sovereign provider goes through."""
    provider, _ = _provider("[1, 2, 3]")
    with pytest.raises(ValueError, match="expected a JSON object"):
        await provider.batch(DesignStage.PREMORTEM, [])


def test_the_shared_decoders_refuse_the_wrong_shape() -> None:
    """Both providers cross the same boundary — model text becoming domain objects — so
    they refuse malformed input in one place rather than two."""
    from vibey.infrastructure.engines.design_json import as_list, as_object_list

    assert as_list([1, 2], "xs") == [1, 2]
    with pytest.raises(ValueError, match="xs must be a list"):
        as_list("not a list", "xs")
    with pytest.raises(ValueError, match="every xs item must be an object"):
        as_object_list([{"a": 1}, "not an object"], "xs")
