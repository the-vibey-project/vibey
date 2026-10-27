# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Bitbucket transport (#298): URLs, credentials, paging and error mapping, with no network."""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request

import pytest

from vibey_gh.bitbucket_transport import MAX_PAGES, BitbucketTransport
from vibey_gh.interfaces import BitbucketTransportInterface, ForgeTransportInterface

HOST = "api.bitbucket.org"
BASE = f"https://{HOST}/2.0"


class Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload if isinstance(payload, str) else json.dumps(payload)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload.encode()


class Opener:
    """Answers each call from a script and records the request it was asked."""

    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float] = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        self.timeouts.append(timeout)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, BaseException):
            raise answer
        return Response(answer)

    @property
    def urls(self) -> list[str]:
        return [request.full_url for request in self.requests]


def http_error(code: int, reason: str, body: bytes | None) -> urllib.error.HTTPError:
    fp = io.BytesIO(body) if body is not None else None
    return urllib.error.HTTPError(f"{BASE}/x", code, reason, {}, fp)  # type: ignore[arg-type]


def listing(values: list, next_url: str | None = None) -> dict:
    page: dict = {"values": values, "pagelen": len(values)}
    if next_url:
        page["next"] = next_url
    return page


def test_the_transport_is_a_forge_transport_with_a_timeout():
    transport = BitbucketTransport()
    assert isinstance(transport, ForgeTransportInterface)
    assert isinstance(transport, BitbucketTransportInterface)
    assert transport.executable == "http (bitbucket)"
    assert transport.host == HOST and transport.timeout == 30.0
    assert transport.run(["git", "status"]) == (
        False,
        "BitbucketTransport.run is not implemented for direct API calls",
    )
    assert BitbucketTransport().survey([]) == ([], "No API path provided")


def test_two_transports_differing_only_in_opener_are_equal_and_the_opener_is_not_shown():
    def opener(request, timeout):
        return Response([])

    assert BitbucketTransport(opener=opener) == BitbucketTransport()
    assert "opener" not in repr(BitbucketTransport(opener=opener))
    assert BitbucketTransport().opener is urllib.request.urlopen


def test_a_read_asks_the_2_0_api_and_passes_its_timeout():
    opener = Opener({"slug": "r"})
    transport = BitbucketTransport(timeout=5.0, opener=opener)
    assert transport.survey(["repositories/w/r"]) == ({"slug": "r"}, "")
    [request] = opener.requests
    assert request.full_url == f"{BASE}/repositories/w/r"
    assert request.get_method() == "GET" and request.data is None
    assert not request.has_header("Content-type")
    assert opener.timeouts == [5.0]


def test_a_host_other_than_the_cloud_default_is_used():
    opener = Opener({})
    BitbucketTransport(host="bitbucket.example.test", opener=opener).survey(["user"])
    assert opener.urls == ["https://bitbucket.example.test/2.0/user"]


def test_a_token_is_sent_as_bearer_and_a_user_and_app_password_as_basic():
    bearer = Opener({})
    BitbucketTransport(token="abc123", opener=bearer).survey(["user"])
    assert bearer.requests[0].get_header("Authorization") == "Bearer abc123"

    basic = Opener({})
    BitbucketTransport(token="me:app-pass", opener=basic).survey(["user"])
    encoded = base64.b64encode(b"me:app-pass").decode()
    assert basic.requests[0].get_header("Authorization") == f"Basic {encoded}"


def test_no_token_sends_no_authorization_header():
    opener = Opener({})
    BitbucketTransport(opener=opener).survey(["user"])
    assert not opener.requests[0].has_header("Authorization")


def test_a_write_sends_its_method_and_json_body():
    opener = Opener({"id": 7})
    transport = BitbucketTransport(token="t", opener=opener)
    answer = transport.survey(["repositories/w/r/pullrequests/7/comments", "post", '{"a": 1}'])
    assert answer == ({"id": 7}, "")
    [request] = opener.requests
    assert request.get_method() == "POST"
    assert request.data == b'{"a": 1}'
    assert request.get_header("Content-type") == "application/json"


def test_an_empty_success_is_an_empty_object():
    for body in ("", "  \n"):
        answer = BitbucketTransport(opener=Opener(body)).survey(["x", "DELETE", ""])
        assert answer == ({}, "")


def test_a_listing_is_followed_to_its_last_page_and_returned_as_one_list():
    second = f"{BASE}/repositories/w/r/pullrequests?page=2"
    third = f"{BASE}/repositories/w/r/pullrequests?page=3"
    opener = Opener(
        listing([1, 2], second),
        listing([3], third),
        listing([4]),
    )
    transport = BitbucketTransport(token="secret", opener=opener)
    assert transport.survey(["repositories/w/r/pullrequests"]) == ([1, 2, 3, 4], "")
    assert opener.urls == [f"{BASE}/repositories/w/r/pullrequests", second, third]
    # Every page carries the credential: that is why the walk must stay on the host.
    assert {r.get_header("Authorization") for r in opener.requests} == {"Bearer secret"}


def test_an_empty_listing_is_an_empty_list():
    assert BitbucketTransport(opener=Opener(listing([]))).survey(["x"]) == ([], "")


def test_an_object_without_values_and_a_bare_list_are_returned_as_they_are():
    assert BitbucketTransport(opener=Opener({"values": "no"})).survey(["x"]) == (
        {"values": "no"},
        "",
    )
    assert BitbucketTransport(opener=Opener([1, 2])).survey(["x"]) == ([1, 2], "")


def test_a_write_answer_that_looks_like_a_listing_is_not_paged():
    opener = Opener(listing([1], f"{BASE}/more"))
    answer = BitbucketTransport(opener=opener).survey(["x", "POST", "{}"])
    assert answer == (listing([1], f"{BASE}/more"), "")
    assert len(opener.requests) == 1


@pytest.mark.parametrize(
    "link",
    (
        "https://evil.example.test/2.0/repositories?page=2",
        f"http://{HOST}/2.0/repositories?page=2",
        f"https://{HOST}.evil.example.test/2.0/x",
    ),
)
def test_a_paging_link_that_leaves_the_host_is_not_followed_and_the_token_stays_home(link):
    opener = Opener(listing([1], link))
    answer = BitbucketTransport(token="secret", opener=opener).survey(["x"])
    assert answer == ([], f"Bitbucket paging link leaves {HOST}; not following it")
    assert len(opener.requests) == 1


def test_a_later_page_that_fails_fails_the_whole_listing_rather_than_returning_part_of_it():
    opener = Opener(listing([1], f"{BASE}/x?page=2"), http_error(500, "Server Error", None))
    answer = BitbucketTransport(opener=opener).survey(["x"])
    assert answer == ([], "Bitbucket API error 500: Server Error")


@pytest.mark.parametrize("page", ({"detail": "no values"}, [1, 2]))
def test_a_later_page_that_is_not_a_listing_is_a_problem(page):
    opener = Opener(listing([1], f"{BASE}/x?page=2"), page)
    answer = BitbucketTransport(opener=opener).survey(["x"])
    assert answer == ([], "Bitbucket API returned a page that is not a listing")


def test_a_listing_of_exactly_the_page_cap_is_whole():
    pages = [listing([n], f"{BASE}/x?page={n + 1}") for n in range(MAX_PAGES - 1)]
    pages.append(listing([MAX_PAGES - 1]))
    opener = Opener(*pages)
    answer = BitbucketTransport(opener=opener).survey(["x"])
    assert answer == (list(range(MAX_PAGES)), "")
    assert len(opener.requests) == MAX_PAGES


def test_a_listing_that_never_ends_stops_at_the_cap_with_a_problem_not_a_partial_list():
    opener = Opener(listing([0], f"{BASE}/x?page=2"))
    answer = BitbucketTransport(opener=opener).survey(["x"])
    assert answer == ([], f"Bitbucket listing runs past {MAX_PAGES} pages; stopped")
    assert len(opener.requests) == MAX_PAGES


def test_json_that_is_neither_a_list_nor_an_object_is_a_problem():
    answer = BitbucketTransport(opener=Opener("42")).survey(["x"])
    assert answer == ([], "Bitbucket API returned JSON that is neither a list nor an object")


@pytest.mark.parametrize(
    ("body", "suffix"),
    (
        (
            json.dumps({"type": "error", "error": {"message": "Repository not found"}}).encode(),
            ": Repository not found",
        ),
        (None, ""),
        (b"<html>no</html>", ""),
        (b"{}", ""),
        (b'{"error": "text"}', ""),
        (b'{"error": {"message": 7}}', ""),
        (b'{"error": {"message": ""}}', ""),
    ),
)
def test_an_http_error_is_a_problem_carrying_bitbucket_own_sentence_when_it_gave_one(body, suffix):
    opener = Opener(http_error(404, "Not Found", body))
    answer = BitbucketTransport(opener=opener).survey(["repositories/w/missing"])
    assert answer == ([], f"Bitbucket API error 404: Not Found{suffix}")


@pytest.mark.parametrize(
    "failure",
    (urllib.error.URLError("refused"), TimeoutError("slow"), ValueError("bad json")),
)
def test_a_network_failure_or_unreadable_body_is_a_transport_problem(failure):
    answer = BitbucketTransport(opener=Opener(failure)).survey(["x"])
    assert answer[0] == []
    assert answer[1].startswith("Bitbucket transport failure: ")


def test_a_body_that_is_not_json_is_a_transport_problem():
    answer = BitbucketTransport(opener=Opener("not json")).survey(["x"])
    assert answer[1].startswith("Bitbucket transport failure: ")
