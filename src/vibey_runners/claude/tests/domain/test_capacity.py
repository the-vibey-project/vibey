# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from claudeloop.domain.capacity import (
    AuthenticationFailed,
    Available,
    BackendMisconfigured,
    CreditsExhausted,
    WindowExhausted,
    is_waitable,
)


def test_available_is_waitable_trivially_true():
    assert is_waitable(Available()) is True


def test_window_exhausted_is_waitable():
    assert is_waitable(WindowExhausted(rate_limit_type="five_hour")) is True


def test_credits_exhausted_is_waitable():
    assert is_waitable(CreditsExhausted()) is True


def test_authentication_failed_is_not_waitable():
    assert is_waitable(AuthenticationFailed(detail="bad key")) is False


def test_backend_misconfigured_is_not_waitable():
    """No clock pulls a model or starts a server: it needs a human."""
    assert is_waitable(BackendMisconfigured(reason="unreachable")) is False


def test_backend_misconfigured_describes_itself_with_the_cli_prefix():
    state = BackendMisconfigured(reason="model_not_found", detail="model 'x'\n  not found")
    assert state.describe() == "backend misconfigured (model_not_found): model 'x' not found"


def test_backend_misconfigured_without_detail():
    assert BackendMisconfigured(reason="unreachable").describe() == (
        "backend misconfigured (unreachable)"
    )
