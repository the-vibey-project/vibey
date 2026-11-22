# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign provider's web research: the operator's reading wins, and a refusal says why."""

from pathlib import Path

import pytest

from vibey.application.design import ResearchResult
from vibey.domain.config import ConfigError
from vibey.domain.errors import SovereignResearchUnavailable
from vibey.infrastructure.engines.gptossloop_design import GptossloopDesignProvider
from vibey.infrastructure.web.backup_notice import BackupNotice
from vibey.infrastructure.web.fetch import FetchedPage, WebFetchError
from vibey.infrastructure.web.local_first import LocalFirstSearch
from vibey.infrastructure.web.research import WebEvidence, WebResearch
from vibey.infrastructure.web.search import DEFAULT_SEARXNG_URL, SearchHit, WebSearchError


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
        web=FakeWeb(error=WebSearchError("brave answered HTTP 429", reason="answered HTTP 429"))
    )  # type: ignore[arg-type]
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await provider.research_with_context("api-docs", "ctx")
    assert "Web search failed: brave answered HTTP 429." in caught.value.detail


async def test_a_provider_built_without_search_says_so_when_it_refuses() -> None:
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await GptossloopDesignProvider().research("prior-art")
    assert "Web search is not set up for this provider" in caught.value.detail
    assert "VIBEY_SEARXNG_URL" in caught.value.detail
    assert caught.value.evidence_name == "prior-art.md"


def test_from_the_environment_research_always_asks_the_local_searxng_first() -> None:
    plain = GptossloopDesignProvider.from_environment({})
    assert plain._web is not None
    search = plain._web._search
    assert isinstance(search, LocalFirstSearch)
    assert search._searxng_url == DEFAULT_SEARXNG_URL and search._backup is None
    configured = GptossloopDesignProvider.from_environment(
        {"VIBEY_SEARXNG_URL": "http://127.0.0.1:8081", "VIBEY_SEARCH_RESULTS": "7"}
    )
    assert configured._web is not None and configured._web._results == 7
    assert configured._web._search._searxng_url == "http://127.0.0.1:8081"
    with_key = GptossloopDesignProvider.from_environment({"BRAVE_SEARCH_API_KEY": "fake-k"})
    assert with_key._web is not None and with_key._web._search._backup is not None
    with pytest.raises(ConfigError, match="VIBEY_SEARCH_PROVIDER"):
        GptossloopDesignProvider.from_environment({"VIBEY_SEARCH_PROVIDER": "bing"})
    with pytest.raises(ConfigError, match="backup"):
        GptossloopDesignProvider.from_environment(
            {"VIBEY_SEARCH_PROVIDER": "brave", "VIBEY_BRAVE_API_KEY": "fake-k"}
        )


class _Searx:
    name = "searxng"

    def __init__(self, error: Exception | None) -> None:
        self.error = error
        self.asked = 0

    def search(self, query: str, limit: int) -> list[SearchHit]:
        self.asked += 1
        if self.error is not None:
            raise self.error
        return [SearchHit("Local", "https://local.example", "from searxng")]


class _Brave:
    name = "brave"

    def __init__(self) -> None:
        self.asked = 0

    def search(self, query: str, limit: int) -> list[SearchHit]:
        self.asked += 1
        return [SearchHit("Remote", "https://remote.example", "from brave")]


class _Pages:
    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        raise WebFetchError("not fetched in this test")


def _provider(searx: _Searx, brave: _Brave | None, said: list[str]) -> GptossloopDesignProvider:
    search = LocalFirstSearch(
        searx,
        brave,
        notice=BackupNotice(write=said.append),
        searxng_url="http://127.0.0.1:8080",
    )
    return GptossloopDesignProvider(web=WebResearch(search, _Pages()))  # type: ignore[arg-type]


async def test_the_design_stage_uses_searxng_when_it_answers_and_never_brave() -> None:
    searx, brave, said = _Searx(None), _Brave(), []
    result = await _provider(searx, brave, said).research_with_context("prior-art", "ctx")
    assert result.source == "web search (searxng): https://local.example"
    assert (searx.asked, brave.asked, said) == (1, 0, [])


async def test_the_design_stage_falls_back_to_brave_only_when_searxng_fails_and_says_so() -> None:
    down = WebSearchError("searxng answered HTTP 502", reason="answered HTTP 502")
    searx, brave, said = _Searx(down), _Brave(), []
    result = await _provider(searx, brave, said).research_with_context("prior-art", "ctx")
    assert result.source == (
        "web search (brave, the backup: local SearXNG unavailable): https://remote.example"
    )
    assert said == [
        "local SearXNG unavailable (answered HTTP 502); this query went to Brave Search"
    ]
    assert (searx.asked, brave.asked) == (1, 1)


async def test_the_design_stage_with_searxng_down_and_no_key_refuses_and_says_why() -> None:
    down = WebSearchError(
        "searxng could not be reached (ConnectionRefusedError)",
        reason="could not be reached (ConnectionRefusedError)",
    )
    with pytest.raises(SovereignResearchUnavailable) as caught:
        await _provider(_Searx(down), None, []).research_with_context("prior-art", "ctx")
    assert "Web search failed: the local SearXNG at http://127.0.0.1:8080 did not answer" in (
        caught.value.detail
    )
    assert "vibey doctor" in caught.value.detail
