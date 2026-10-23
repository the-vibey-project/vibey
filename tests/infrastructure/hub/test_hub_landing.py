# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's front door: what `krypton` opens in a browser.

A person who is not a developer lands on this page, so it is tested as a page (it says what
the hub is and where to go, it has no script and no data) and as part of the hub's hardening
(no credential asked, the one relaxed policy admits exactly its own style block and nothing
else, every other route keeps the hub's own policy).
"""

import base64
import hashlib
import re

from tests.infrastructure.hub.test_hub_app import HOST, SECURITY_HEADERS, _app, _client
from vibey.infrastructure.hub.interfaces.landing_interface import HubLandingPageInterface
from vibey.infrastructure.hub.landing import HUB_LANDING_PAGE, STYLE, HubLandingPage

CSP = "content-security-policy"


def test_the_page_says_what_the_hub_is_and_where_to_go() -> None:
    page = HubLandingPage().render()
    assert "The vibey hub is running" in page
    assert "Nothing is broken" in page
    for next_step in ("vibey hub pair", "@krypton /new", "vibey new", "[hub] projects_root"):
        assert next_step in page
    assert "/health/ready" in page


def test_the_page_carries_no_script_and_loads_nothing() -> None:
    page = HubLandingPage().render()
    assert "<script" not in page.lower()
    assert " onclick" not in page.lower()
    # The only addresses in it are links a person may follow, never something it fetches.
    assert re.findall(r'(?:src|srcset|href)="(https?:[^"]+)"', page) == [
        "https://the-vibey-project.github.io/vibey/"
    ]
    assert "src=" not in page


def test_the_policy_admits_this_pages_one_style_block_by_hash_and_nothing_else() -> None:
    policy = HubLandingPage().content_security_policy()
    digest = base64.b64encode(hashlib.sha256(STYLE.encode()).digest()).decode()
    assert f"style-src 'sha256-{digest}'" in policy
    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy
    assert policy.startswith("default-src 'none'")
    for kept in ("frame-ancestors 'none'", "base-uri 'none'", "form-action 'none'"):
        assert kept in policy
    # One style element, and it is the one hashed.
    page = HubLandingPage().render()
    assert page.count("<style>") == 1
    assert f"<style>{STYLE}</style>" in page


def test_the_page_is_a_hub_landing_page() -> None:
    assert isinstance(HUB_LANDING_PAGE, HubLandingPageInterface)


async def test_a_browser_gets_the_page_with_no_credential() -> None:
    async with _client(_app()) as client:
        response = await client.get("/", headers={"host": HOST})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "The vibey hub is running" in response.text
    # Its own, narrower-than-default-for-styling policy; every other hardening header stays.
    assert response.headers[CSP] == HUB_LANDING_PAGE.content_security_policy()
    for name, value in SECURITY_HEADERS.items():
        if name != CSP:
            assert response.headers[name] == value


async def test_the_front_door_holds_no_data_and_the_api_still_needs_a_credential() -> None:
    async with _client(_app()) as client:
        door = await client.get("/", headers={"host": HOST})
        api = await client.get("/api/v1/projects", headers={"host": HOST})
    assert door.status_code == 200 and api.status_code == 401
    # Every route that is not the front door keeps the hub's own policy, refusals included.
    assert api.headers[CSP] == SECURITY_HEADERS[CSP]


async def test_the_page_answers_only_a_host_the_hub_answers() -> None:
    async with _client(_app()) as client:
        response = await client.get("/", headers={"host": "evil.example"})
    assert response.status_code == 421
    assert response.headers[CSP] == SECURITY_HEADERS[CSP]


async def test_the_front_door_is_not_part_of_the_contract() -> None:
    async with _client(_app()) as client:
        document = (await client.get("/api/v1/openapi.json", headers={"host": HOST})).json()
    assert "/" not in document["paths"]
