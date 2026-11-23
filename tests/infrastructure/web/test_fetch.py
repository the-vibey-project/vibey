# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What every fetch is made of: HTML turned into text, and a connection pinned to the address
that was checked. The fetch itself is tested in test_guarded_fetch.py and test_page_fetcher.py."""

import http.client
import socket
from typing import Any

import pytest

from vibey.infrastructure.web.fetch import html_to_text, pinned_connect

HTML = (
    "<html><head><title> The  Page </title><style>p{color:red}</style></head><body>"
    "<nav>Menu Home About</nav><script>alert(1)</script><h1>Heading</h1>"
    "<p>First   paragraph &amp; more.</p><p>Second.</p><footer>Copyright</footer></body></html>"
)


def test_html_becomes_plain_text_without_scripts_styles_or_navigation() -> None:
    title, text = html_to_text(HTML)
    assert title == "The Page"
    assert text == "Heading\n\nFirst paragraph & more.\n\nSecond."
    assert (
        "alert" not in text
        and "Menu" not in text
        and "Copyright" not in text
        and "color" not in text
    )


def test_an_unclosed_skipped_tag_never_goes_below_zero() -> None:
    assert html_to_text("</nav></script>plain")[1] == "plain"


@pytest.mark.parametrize("scheme", ["http", "https"])
def test_the_real_connection_is_pinned_to_the_checked_ip_but_still_names_the_host(
    scheme: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    reached: list[tuple[str, int]] = []

    def create_connection(
        address: tuple[str, int], timeout: float | None = None, source_address: Any = None
    ) -> socket.socket:
        reached.append(address)
        raise OSError("stop here: no network in a unit test")

    monkeypatch.setattr(socket, "create_connection", create_connection)
    conn = pinned_connect(
        scheme, "docs.example", 443 if scheme == "https" else 80, "93.184.216.34", 5
    )

    assert conn.host == "docs.example"
    assert isinstance(conn, http.client.HTTPSConnection) == (scheme == "https")
    with pytest.raises(OSError, match="stop here"):
        conn.connect()
    assert reached == [("93.184.216.34", 443 if scheme == "https" else 80)]
