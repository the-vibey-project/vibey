# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Research evidence from the web: queries, quoting, and what is left out."""

from vibey.infrastructure.web.fetch import FetchedPage, WebFetchError
from vibey.infrastructure.web.research import BANNER, WebResearch, clean_context
from vibey.infrastructure.web.search import SearchHit


class FakeBackend:
    name = "fake"

    def __init__(self, hits: list[SearchHit]) -> None:
        self.hits = hits
        self.asked: list[tuple[str, int]] = []

    def search(self, query: str, limit: int) -> list[SearchHit]:
        self.asked.append((query, limit))
        return self.hits


class FakeFetcher:
    def __init__(self, pages: dict[str, str], broken: set[str] | None = None) -> None:
        self.pages = pages
        self.broken = broken or set()
        self.asked: list[tuple[str, int | None]] = []

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        self.asked.append((url, max_chars))
        if url in self.broken:
            raise WebFetchError("the page answered HTTP 404")
        return FetchedPage(url=url, title="", text=self.pages[url], truncated=False)


def _hits(*urls: str) -> list[SearchHit]:
    return [SearchHit(f"Title {n}", url, f"snippet {n}") for n, url in enumerate(urls, start=1)]


def test_the_context_loses_file_paths_backticks_and_markdown_but_keeps_a_route_and_is_short() -> (
    None
):
    raw = "# Fold `/ministry` from /Users/adam/git/humbleberger into this Next.js site " + "x" * 400
    cleaned = clean_context(raw)
    assert "/Users" not in cleaned and "`" not in cleaned and "#" not in cleaned
    assert cleaned.startswith("Fold /ministry from into this Next.js site") and len(cleaned) <= 160


def test_each_topic_has_its_own_query_and_an_unknown_one_uses_its_words() -> None:
    research = WebResearch(FakeBackend([]), FakeFetcher({}))
    assert (
        research.query_for("prior-art", "Build X") == "Build X existing implementations prior art"
    )
    assert research.query_for("libraries", "Build X") == "Build X libraries packages"
    assert research.query_for("api-docs", "Build X") == "Build X API documentation"
    assert research.query_for("rate_limit-design", "Build X") == "Build X rate limit design"


def test_pages_are_fetched_and_quoted_with_their_urls_not_summarized() -> None:
    backend = FakeBackend(_hits("https://a.example/1", "https://b.example/2"))
    fetcher = FakeFetcher({"https://a.example/1": "Alpha text", "https://b.example/2": "Beta text"})
    research = WebResearch(backend, fetcher, results=4, page_chars=900)

    found = research.research("libraries", "Build X")

    assert found is not None
    assert backend.asked == [("Build X libraries packages", 4)]
    assert fetcher.asked == [("https://a.example/1", 900), ("https://b.example/2", 900)]
    assert found.title == "Web research: libraries"
    assert found.source == "web search (fake): https://a.example/1, https://b.example/2"
    assert found.content.startswith(BANNER)
    assert "Source: https://a.example/1\nTitle: Title 1\n\nAlpha text" in found.content
    assert "---" in found.content and "Beta text" in found.content


def test_a_page_that_cannot_be_fetched_is_skipped_and_the_next_one_is_used() -> None:
    backend = FakeBackend(_hits("https://bad.example", "https://ok.example"))
    fetcher = FakeFetcher({"https://ok.example": "fine"}, broken={"https://bad.example"})
    found = WebResearch(backend, fetcher, pages=1).research("prior-art", "c")
    assert found is not None and found.source == "web search (fake): https://ok.example"


def test_no_more_pages_are_fetched_than_asked_for_and_a_long_source_list_is_cut() -> None:
    urls = [f"https://s{n}.example/" for n in range(1, 6)]
    fetcher = FakeFetcher({u: f"text {u}" for u in urls})
    found = WebResearch(FakeBackend(_hits(*urls)), fetcher, pages=5).research("prior-art", "c")
    assert found is not None and len(fetcher.asked) == 5
    assert found.source.endswith("https://s3.example/ and more")


def test_when_no_page_can_be_fetched_the_search_snippets_are_quoted_instead() -> None:
    hits = _hits("https://x.example", "https://y.example") + [
        SearchHit("No snippet", "https://z.example", "")
    ]
    fetcher = FakeFetcher({}, broken={h.url for h in hits})
    found = WebResearch(FakeBackend(hits), fetcher, pages=3).research("api-docs", "c")
    assert found is not None
    assert "Source: https://x.example\nTitle: Title 1\n\nsnippet 1" in found.content
    assert "z.example" not in found.content


def test_nothing_usable_is_none_not_an_invented_source() -> None:
    assert WebResearch(FakeBackend([]), FakeFetcher({})).research("prior-art", "c") is None
    only_empty = [SearchHit("t", "https://e.example", "")]
    broken = FakeFetcher({}, broken={"https://e.example"})
    assert WebResearch(FakeBackend(only_empty), broken).research("prior-art", "c") is None


def test_the_evidence_is_cut_to_the_total_budget() -> None:
    fetcher = FakeFetcher({"https://a.example": "a" * 5000})
    found = WebResearch(FakeBackend(_hits("https://a.example")), fetcher, total_chars=300).research(
        "prior-art", "c"
    )
    assert found is not None and len(found.content) == len(BANNER) + 2 + 300


def test_fetching_stops_once_enough_pages_are_in_even_when_the_search_found_more() -> None:
    urls = [f"https://s{n}.example/" for n in range(1, 6)]
    fetcher = FakeFetcher({u: u for u in urls})
    found = WebResearch(FakeBackend(_hits(*urls)), fetcher, pages=2).research("prior-art", "c")
    assert found is not None and [u for u, _ in fetcher.asked] == urls[:2]
