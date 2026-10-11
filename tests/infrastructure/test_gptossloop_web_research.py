# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign provider's web research: the operator's reading wins, and a refusal says why."""

from pathlib import Path

import pytest

from vibey.application.design import ResearchResult
from vibey.domain.config import ConfigError
from vibey.domain.errors import SovereignResearchUnavailable
from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.web.research import WebEvidence
from vibey.infrastructure.web.search import WebSearchError


class FakeWeb:
    def __init__(self, found: WebEvidence | None = None, error: Exception | None = None) -> None:
        self.found = found
        self.error = error
        self.asked: list[tuple[str, str]] = []

    def research(self, topic: str, context: str) -> WebEvidence | None:
        self.asked.append((topic, context))
        if self.error is not None:
            raise self.error
        return self.found


EVIDENCE = WebEvidence(
    "Web research: prior-art", "web search (fake): https://a.example", "quoted text", "q"
)


async def test_with_search_configured_and_no_reading_the_provider_quotes_the_web() -> None:
    web = FakeWeb(EVIDENCE)
    provider = GptossloopDesignProvider(web=web)  # type: ignore[arg-type]

    result = await provider.research_with_context("prior-art", "Build the ministry section.")

    assert result == ResearchResult(
        "Web research: prior-art", "web search (fake): https://a.example", "quoted text"
    )
    assert web.asked == [("prior-art", "Build the ministry section.")]


async def test_plain_research_is_research_with_no_context() -> None:
    web = FakeWeb(EVIDENCE)
    await GptossloopDesignProvider(web=web).research("prior-art")  # type: ignore[arg-type]
    assert web.asked == [("prior-art", "")]


async def test_the_operators_own_reading_always_beats_the_web(tmp_path: Path) -> None:
    (tmp_path / "prior-art.md").write_text("source: my notes\nthe operator's reading")
    web = FakeWeb(EVIDENCE)

    class Asker:
        async def ask(
            self, system: str, user: str, schema: object, *, subject: str, decode: object
        ) -> object:
            return ResearchResult("summary", "my notes", "summarized")

    provider = GptossloopDesignProvider(evidence_dir=tmp_path, web=web, asker=Asker())  # type: ignore[arg-type]
    result = await provider.research_with_context("prior-art", "ctx")

    assert result.source == "my notes"
    assert web.asked == []


async def test_a_search_that_finds_nothing_says_so_and_still_refuses_to_invent() -> None:
    provider = GptossloopDesignProvider(web=FakeWeb(None))  # type: ignore[arg-type]
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await provider.research_with_context("libraries", "ctx")
    assert "Web search found nothing usable for it." in caught.value.detail
    assert "fabricated source" in caught.value.detail


async def test_a_search_that_fails_says_what_failed_without_a_url_or_key() -> None:
    provider = GptossloopDesignProvider(
        web=FakeWeb(error=WebSearchError("brave answered HTTP 429"))
    )  # type: ignore[arg-type]
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await provider.research_with_context("api-docs", "ctx")
    assert "Web search failed: brave answered HTTP 429." in caught.value.detail


async def test_with_no_search_and_no_reading_the_refusal_says_how_to_configure_one() -> None:
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await GptossloopDesignProvider().research("prior-art")
    assert "Web search is not configured (VIBEY_SEARXNG_URL" in caught.value.detail
    assert "VIBEY_BRAVE_API_KEY" in caught.value.detail
    assert caught.value.evidence_name == "prior-art.md"


def test_the_environment_builds_the_web_researcher_only_when_search_is_configured() -> None:
    assert GptossloopDesignProvider.from_environment({})._web is None
    configured = GptossloopDesignProvider.from_environment(
        {"VIBEY_SEARXNG_URL": "http://127.0.0.1:8080", "VIBEY_SEARCH_RESULTS": "7"}
    )
    assert configured._web is not None
    with pytest.raises(ConfigError, match="VIBEY_SEARCH_PROVIDER"):
        GptossloopDesignProvider.from_environment(
            {"VIBEY_SEARCH_PROVIDER": "bing", "VIBEY_BRAVE_API_KEY": "k"}
        )
