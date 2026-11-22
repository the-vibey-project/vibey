# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's web tools, decided in the domain (ADR-0102, SP-ACP Task 9b): which URL may be
fetched, which address may be connected to, which host the person allows, how much a principal
may ask for, what a project may narrow, and what the ledger records.

Module-level test functions rather than a class with an interface beside it (ADR-0016): pytest
collects functions, and the tables here are data."""

import dataclasses

import pytest

from vibey.domain.interfaces.web_tools_interface import (
    WebToolPolicyInterface,
    WebToolTrustInterface,
)
from vibey.domain.web_tools import (
    DEFAULT_CONTENT_TYPES,
    MAX_URL_CHARS,
    WEB_TOOL_POLICY,
    WEB_TOOL_TRUST,
    WebToolRefused,
    WebToolSettings,
)

ANY = WebToolSettings()


def _refused(url: str, settings: WebToolSettings = ANY) -> str:
    with pytest.raises(WebToolRefused) as caught:
        WEB_TOOL_POLICY.target(url, settings)
    return str(caught.value)


def test_the_policy_and_the_trust_meet_their_seams() -> None:
    assert isinstance(WEB_TOOL_POLICY, WebToolPolicyInterface)
    assert isinstance(WEB_TOOL_TRUST, WebToolTrustInterface)


# -- what may be fetched -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "scheme", "host", "port", "target"),
    [
        ("https://example.com", "https", "example.com", 443, "/"),
        ("http://Example.COM./docs?q=1#top", "http", "example.com", 80, "/docs?q=1"),
        (
            "https://docs.python.org:8443/3/library/",
            "https",
            "docs.python.org",
            8443,
            "/3/library/",
        ),
        ("https://93.184.216.34/", "https", "93.184.216.34", 443, "/"),
        (
            "https://[2606:2800:220:1:248:1893:25c8:1946]/x",
            "https",
            "2606:2800:220:1:248:1893:25c8:1946",
            443,
            "/x",
        ),
    ],
)
def test_a_public_http_or_https_url_is_a_target(
    url: str, scheme: str, host: str, port: int, target: str
) -> None:
    found = WEB_TOOL_POLICY.target(url, ANY)
    assert (found.scheme, found.host, found.port, found.target) == (scheme, host, port, target)


def test_what_is_shown_of_a_target_never_carries_its_query_or_fragment() -> None:
    found = WEB_TOOL_POLICY.target("https://example.com/a/b?token=s3cret#frag", ANY)
    assert found.shown == "https://example.com/a/b"
    assert "s3cret" not in found.shown
    assert found.url == "https://example.com/a/b?token=s3cret"


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com/",
        "javascript:alert(1)",
        "data:text/html,hi",
        "ws://example.com/",
        "//example.com/",
        "example.com",
        "",
    ],
)
def test_only_http_and_https_are_fetched(url: str) -> None:
    assert "http" in _refused(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://user@example.com/",
        "https://user:pw@example.com/",
        "https://example.com@127.0.0.1/",
        "https://:@example.com/",
        "https://evil.com%40127.0.0.1/",
    ],
)
def test_a_url_carrying_credentials_is_refused(url: str) -> None:
    # Refused whichever rule reads it first: the user name, or the host it leaves behind.
    assert _refused(url).startswith("refused: ")
    assert "user name" in _refused(url) or "@" not in url


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/",
        "https://LOCALHOST/",
        "https://localhost./",
        "https://api.localhost/",
        "https://localhost.localdomain/",
        "https://printer.local/",
        "https://db.internal/",
        "https://nas.home.arpa/",
        "https://router.lan/",
        "https://intranet/",
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://metadata/",
        "https://instance-data/latest/",
        "https://instance-data.ec2.internal/",
    ],
)
def test_local_and_internal_names_are_refused(url: str) -> None:
    assert "public" in _refused(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://2130706433/",  # 127.0.0.1 as one decimal number
        "http://0x7f000001/",  # as one hex number
        "http://017700000001/",  # as one octal number
        "http://0177.0.0.1/",  # octal octet
        "http://0x7f.0.0.1/",  # hex octet
        "http://127.1/",  # shorthand
        "http://127.0.1/",
        "http://10.1/",
        "http://1.2.3.4.5/",
        "http://00127.0.0.1/",
        "http://example.123/",  # a name may not end in a number
    ],
)
def test_an_address_spelt_any_way_but_the_canonical_one_is_refused(url: str) -> None:
    assert "spelling" in _refused(url) or "public" in _refused(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://127.255.255.254/",
        "http://0.0.0.0/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://172.31.255.255/",
        "http://192.168.1.1/",
        "http://169.254.169.254/latest/meta-data/",  # AWS, Azure and GCP metadata
        "http://169.254.170.2/",  # ECS task metadata
        "http://100.64.0.1/",  # carrier-grade NAT
        "http://100.100.100.200/",  # Alibaba metadata, inside CGNAT space
        "http://192.0.0.192/",  # Oracle metadata, IETF protocol assignments
        "http://192.0.2.1/",  # documentation
        "http://198.18.0.1/",  # benchmarking
        "http://224.0.0.1/",  # multicast
        "http://239.255.255.250/",
        "http://240.0.0.1/",  # reserved
        "http://255.255.255.255/",
        "http://[::1]/",
        "http://[::]/",
        "http://[fe80::1]/",
        "http://[fe80::1%25en0]/",
        "http://[fc00::1]/",
        "http://[fd00:ec2::254]/",  # AWS metadata over IPv6
        "http://[ff02::1]/",
        "http://[::ffff:127.0.0.1]/",  # IPv4-mapped
        "http://[::ffff:7f00:1]/",
        "http://[::ffff:169.254.169.254]/",
        "http://[::127.0.0.1]/",  # IPv4-compatible (deprecated)
        "http://[64:ff9b::7f00:1]/",  # NAT64 to loopback
        "http://[64:ff9b::a9fe:a9fe]/",  # NAT64 to metadata
        "http://[2002:7f00:1::]/",  # 6to4 around loopback
        "http://[2001:0::1]/",  # Teredo
        "http://[2001:db8::1]/",  # documentation
        "http://[100::1]/",  # discard-only
    ],
)
def test_an_address_that_is_not_public_is_refused(url: str) -> None:
    assert "public" in _refused(url)


@pytest.mark.parametrize("port", ["0", "65536", "99999", "-1", "http"])
def test_a_port_outside_one_to_65535_is_refused(port: str) -> None:
    assert "port" in _refused(f"https://example.com:{port}/")


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/a b",
        "https://example.com/\x1b[2J",
        "https://example.com/‮",
        "https://exa\tmple.com/",
        "https://example.com/\n",
    ],
)
def test_a_url_with_a_space_or_a_control_character_is_refused(url: str) -> None:
    assert "space or a control character" in _refused(url)


def test_an_overlong_url_is_refused_before_it_is_read() -> None:
    assert "long" in _refused("https://example.com/" + "a" * MAX_URL_CHARS)


def test_a_host_named_in_unicode_is_kept_in_its_ascii_form() -> None:
    found = WEB_TOOL_POLICY.target("https://bücher.example/", ANY)
    assert found.host == "xn--bcher-kva.example"


# -- after every redirect ----------------------------------------------------------------------


def test_a_redirect_is_read_against_where_it_came_from_and_checked_again() -> None:
    here = WEB_TOOL_POLICY.target("https://example.com/a/b", ANY)
    assert WEB_TOOL_POLICY.follow(here, "../c?x=1", ANY).url == "https://example.com/c?x=1"
    assert WEB_TOOL_POLICY.follow(here, "https://other.example/", ANY).host == "other.example"
    for inward in (
        "http://127.0.0.1/",
        "https://169.254.169.254/",
        "https://localhost/",
        "https://[::ffff:10.0.0.1]/",
        "file:///etc/passwd",
        "https://user@example.com/",
    ):
        with pytest.raises(WebToolRefused):
            WEB_TOOL_POLICY.follow(here, inward, ANY)


def test_a_redirect_never_steps_down_from_https_to_http() -> None:
    secure = WEB_TOOL_POLICY.target("https://example.com/", ANY)
    with pytest.raises(WebToolRefused, match="https"):
        WEB_TOOL_POLICY.follow(secure, "http://example.com/", ANY)
    plain = WEB_TOOL_POLICY.target("http://example.com/", ANY)
    assert WEB_TOOL_POLICY.follow(plain, "https://example.com/", ANY).scheme == "https"


def test_a_redirect_is_held_to_the_hosts_the_person_allows() -> None:
    settings = WebToolSettings(allow_hosts=("example.com",))
    here = WEB_TOOL_POLICY.target("https://example.com/", settings)
    with pytest.raises(WebToolRefused, match="allow_hosts"):
        WEB_TOOL_POLICY.follow(here, "https://elsewhere.example/", settings)


# -- the addresses a name resolves to ------------------------------------------------------------


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.2.3.4",
        "169.254.169.254",
        "::1",
        "fd00:ec2::254",
        "::ffff:192.168.0.1",
        "nonsense",
        "",
    ],
)
def test_an_address_a_name_resolved_to_is_refused_unless_public(address: str) -> None:
    assert WEB_TOOL_POLICY.address_problem(address) is not None


@pytest.mark.parametrize("address", ["93.184.216.34", "1.1.1.1", "2606:4700:4700::1111"])
def test_a_public_address_is_one_a_fetch_may_connect_to(address: str) -> None:
    assert WEB_TOOL_POLICY.address_problem(address) is None


# -- the hosts the person allows ----------------------------------------------------------------


def test_any_public_host_unless_the_person_lists_them() -> None:
    assert WEB_TOOL_POLICY.host_problem("example.com", ANY) is None
    listed = WebToolSettings(allow_hosts=("python.org", "docs.rs"))
    assert WEB_TOOL_POLICY.host_problem("python.org", listed) is None
    assert WEB_TOOL_POLICY.host_problem("docs.python.org", listed) is None
    assert WEB_TOOL_POLICY.host_problem("evilpython.org", listed) is not None
    assert WEB_TOOL_POLICY.host_problem("python.org.evil.com", listed) is not None
    none = WebToolSettings(allow_hosts=())
    assert WEB_TOOL_POLICY.host_problem("example.com", none) is not None


def test_a_denied_host_is_refused_even_when_it_is_allowed() -> None:
    settings = WebToolSettings(allow_hosts=("example.com",), deny_hosts=("ads.example.com",))
    assert WEB_TOOL_POLICY.host_problem("example.com", settings) is None
    assert "deny_hosts" in str(WEB_TOOL_POLICY.host_problem("ads.example.com", settings))
    assert "deny_hosts" in str(WEB_TOOL_POLICY.host_problem("x.ads.example.com", settings))
    assert "deny_hosts" in _refused("https://ADS.example.com./", settings)


@pytest.mark.parametrize(
    "entry",
    [
        "*.example.com",
        "https://example.com",
        "example.com/path",
        "exa mple.com",
        "",
        "example.com:443",
        "127.0.0.1",
    ],
)
def test_a_host_list_entry_must_be_a_plain_host_name(entry: str) -> None:
    with pytest.raises(ValueError, match="host"):
        WebToolSettings(deny_hosts=(entry,))
    with pytest.raises(ValueError, match="host"):
        WebToolSettings(allow_hosts=(entry,))


def test_host_list_entries_are_kept_lowercase_without_a_trailing_dot() -> None:
    settings = WebToolSettings(allow_hosts=("Example.COM.",), deny_hosts=("ADS.example.com",))
    assert settings.allow_hosts == ("example.com",)
    assert settings.deny_hosts == ("ads.example.com",)


# -- budgets and bounds -------------------------------------------------------------------------


def test_the_defaults_are_the_documented_ones() -> None:
    assert ANY.searches_per_hour == 60
    assert ANY.fetches_per_hour == 30
    assert ANY.allow_hosts is None
    assert ANY.deny_hosts == ()
    assert ANY.max_bytes == 1_000_000
    assert ANY.max_chars == 20_000
    assert ANY.timeout_seconds == 15.0
    assert ANY.max_redirects == 3
    assert ANY.content_types == DEFAULT_CONTENT_TYPES
    assert "application/pdf" not in DEFAULT_CONTENT_TYPES


@pytest.mark.parametrize(
    "change",
    [
        {"searches_per_hour": -1},
        {"fetches_per_hour": 100_001},
        {"max_bytes": 0},
        {"max_bytes": 50_000_001},
        {"max_chars": 99},
        {"timeout_seconds": 0.0},
        {"timeout_seconds": 601.0},
        {"timeout_seconds": float("nan")},
        {"max_redirects": -1},
        {"max_redirects": 11},
        {"content_types": ("text/html", "Text/Plain ")},
        {"content_types": ("text/*",)},
    ],
)
def test_a_bound_outside_its_range_is_refused(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        dataclasses.replace(ANY, **change)  # type: ignore[arg-type]


def test_nothing_is_refused_until_the_hour_holds_the_budget() -> None:
    assert WEB_TOOL_POLICY.budget_wait((), now=10_000.0, per_hour=2) is None
    assert WEB_TOOL_POLICY.budget_wait((9_000.0,), now=10_000.0, per_hour=2) is None
    wait = WEB_TOOL_POLICY.budget_wait((7_000.0, 9_000.0), now=10_000.0, per_hour=2)
    assert wait == pytest.approx(600.0)  # the 7_000 use leaves the hour at 10_600
    assert WEB_TOOL_POLICY.budget_wait((5_000.0, 6_000.0), now=10_000.0, per_hour=2) is None


def test_a_budget_of_zero_refuses_every_request() -> None:
    assert WEB_TOOL_POLICY.budget_wait((), now=1.0, per_hour=0) == pytest.approx(3600.0)


# -- what a project may say ---------------------------------------------------------------------


def test_a_project_may_only_lower_a_budget_or_a_bound() -> None:
    user = WebToolSettings(searches_per_hour=10, max_bytes=500_000, timeout_seconds=10.0)
    lower = WebToolSettings(searches_per_hour=5, max_bytes=100_000, timeout_seconds=5.0)
    higher = WebToolSettings(searches_per_hour=1000, max_bytes=5_000_000, timeout_seconds=60.0)
    keys = frozenset({"searches_per_hour", "max_bytes", "timeout_seconds"})
    narrowed = WEB_TOOL_TRUST.merge(user, lower, keys)
    assert (narrowed.searches_per_hour, narrowed.max_bytes, narrowed.timeout_seconds) == (
        5,
        100_000,
        5.0,
    )
    kept = WEB_TOOL_TRUST.merge(user, higher, keys)
    assert (kept.searches_per_hour, kept.max_bytes, kept.timeout_seconds) == (10, 500_000, 10.0)


def test_a_key_the_project_does_not_name_is_the_users() -> None:
    user = WebToolSettings(fetches_per_hour=3)
    assert WEB_TOOL_TRUST.merge(user, WebToolSettings(), frozenset()) == user


def test_a_project_may_add_denied_hosts_and_never_remove_one() -> None:
    user = WebToolSettings(deny_hosts=("tracker.example",))
    project = WebToolSettings(deny_hosts=("paste.example",))
    merged = WEB_TOOL_TRUST.merge(user, project, frozenset({"deny_hosts"}))
    assert set(merged.deny_hosts) == {"tracker.example", "paste.example"}
    cleared = WEB_TOOL_TRUST.merge(user, WebToolSettings(), frozenset({"deny_hosts"}))
    assert cleared.deny_hosts == ("tracker.example",)


def test_a_project_may_narrow_the_allowed_hosts_and_never_widen_them() -> None:
    anywhere = WebToolSettings()
    some = WebToolSettings(allow_hosts=("python.org", "example.com"))
    keys = frozenset({"allow_hosts"})
    # From any host to the project's list.
    assert WEB_TOOL_TRUST.merge(anywhere, some, keys).allow_hosts == ("python.org", "example.com")
    # A project that says nothing, or "any", keeps the person's list.
    assert WEB_TOOL_TRUST.merge(some, anywhere, keys).allow_hosts == ("python.org", "example.com")
    # Both name hosts: a host must be inside both.
    project = WebToolSettings(allow_hosts=("docs.python.org", "rust-lang.org"))
    merged = WEB_TOOL_TRUST.merge(some, project, keys)
    assert merged.allow_hosts == ("docs.python.org",)
    broader = WebToolSettings(allow_hosts=("org",))
    assert WEB_TOOL_TRUST.merge(some, broader, keys).allow_hosts == ("python.org",)
    # Nothing in common is nothing allowed, never anything allowed.
    disjoint = WebToolSettings(allow_hosts=("rust-lang.org",))
    assert WEB_TOOL_TRUST.merge(some, disjoint, keys).allow_hosts == ()


def test_a_project_may_drop_content_types_and_never_add_one() -> None:
    user = WebToolSettings(content_types=("text/html", "text/plain"))
    project = WebToolSettings(content_types=("text/plain", "application/json"))
    merged = WEB_TOOL_TRUST.merge(user, project, frozenset({"content_types"}))
    assert merged.content_types == ("text/plain",)


# -- what the ledger is told --------------------------------------------------------------------


def test_the_audit_record_names_who_what_and_where_and_never_the_query_or_the_url() -> None:
    search = WEB_TOOL_POLICY.audit("search", principal="agent", outcome="ok", backend="brave")
    assert search == {
        "tool": "search",
        "principal": "agent",
        "outcome": "ok",
        "backend": "brave",
    }
    fetch = WEB_TOOL_POLICY.audit(
        "fetch",
        principal="device-1",
        outcome="refused",
        backend="direct",
        hosts=("example.com", "cdn.example.net"),
        reason="not a public address",
    )
    assert fetch["hosts"] == ["example.com", "cdn.example.net"]
    assert fetch["reason"] == "not a public address"
    assert set(fetch) == {"tool", "principal", "outcome", "backend", "hosts", "reason"}
    with pytest.raises(ValueError):
        WEB_TOOL_POLICY.audit(
            "search", principal="agent", outcome="ok", backend="x", hosts=("a.b",)
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://[::1/",  # a bracket left open: not a URL at all
        "https://" + "a" * 64 + ".example/",  # a label IDNA refuses
        "https://a..example/",
        "https://bad-.example/",
        "https://-bad.example/",
        "https://exa$mple.com/",
    ],
)
def test_a_url_or_host_name_that_cannot_be_read_is_refused(url: str) -> None:
    assert _refused(url).startswith("refused: ")


def test_a_timeout_that_is_not_a_number_is_refused() -> None:
    with pytest.raises(ValueError, match="seconds"):
        WebToolSettings(timeout_seconds="15")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="whole number"):
        WebToolSettings(searches_per_hour=True)


def test_an_audit_record_for_an_unknown_tool_or_outcome_is_refused() -> None:
    with pytest.raises(ValueError):
        WEB_TOOL_POLICY.audit("crawl", principal="a", outcome="ok", backend="x")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        WEB_TOOL_POLICY.audit("search", principal="a", outcome="maybe", backend="x")  # type: ignore[arg-type]


def test_a_failure_says_which_backends_it_asked() -> None:
    from vibey.domain.web_tools import WebToolFailed

    assert WebToolFailed("both failed", tried=("searxng", "brave")).tried == ("searxng", "brave")
    assert WebToolFailed("down").tried == ()
    assert WebToolFailed("reset", hosts=("a.example",)).hosts == ("a.example",)
    assert WebToolRefused("inward", hosts=("a.example",)).hosts == ("a.example",)
    assert WebToolRefused("inward").hosts == ()
