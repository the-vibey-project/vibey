# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Properties of the Sabbath window (sub-doctrine 8.i; ADR-0070).

The window is computed per host; no location is committed. Coordinates here are drawn
at random, or are the labelled EXAMPLE fixture (Greenville, SC) and nothing more.
"""

from datetime import UTC, date, datetime, timedelta, timezone

import vibey_gh.sabbath
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain import sabbath

LATITUDES = st.floats(min_value=-60.0, max_value=60.0)
LONGITUDES = st.floats(min_value=-179.0, max_value=179.0)
DAYS = st.dates(min_value=date(2000, 1, 7), max_value=date(2100, 12, 31))


def _friday(day: date) -> date:
    return day - timedelta(days=(day.weekday() - 4) % 7)


def _window(lat: float, lon: float) -> sabbath.SabbathWindow:
    return sabbath.SabbathWindow(latitude=lat, longitude=lon)


def test_the_domain_uses_the_one_implementation_in_the_family() -> None:
    assert sabbath.SabbathWindow is vibey_gh.sabbath.SabbathWindow
    assert sabbath.OFFICIAL_ZENITH == 90.833


@given(lat=LATITUDES, lon=LONGITUDES, day=DAYS)
def test_the_window_is_always_friday_sundown_to_saturday_sundown_in_local_solar_time(
    lat: float, lon: float, day: date
) -> None:
    window = _window(lat, lon)
    rest = window.window_for(_friday(day))
    solar = timezone(timedelta(minutes=round(lon * 4)))
    assert rest.opened.astimezone(solar).weekday() == 4
    assert rest.resumes.astimezone(solar).weekday() == 5
    assert rest.computed
    assert timedelta(hours=23) < rest.resumes - rest.opened < timedelta(hours=25)


@given(lat=LATITUDES, lon=LONGITUDES, day=DAYS, fraction=st.floats(0.0, 0.999))
def test_next_resume_is_always_the_saturday_sundown_ending_the_current_window(
    lat: float, lon: float, day: date, fraction: float
) -> None:
    window = _window(lat, lon)
    rest = window.window_for(_friday(day))
    inside = rest.opened + (rest.resumes - rest.opened) * fraction
    assert window.is_resting(inside)
    assert window.next_resume(inside) == rest.resumes
    assert not window.is_resting(rest.resumes)


@given(day=DAYS)
def test_a_date_with_no_sundown_fails_loud_to_the_declared_fallback(day: date) -> None:
    window = sabbath.SabbathWindow(latitude=89.9, longitude=0.0, zone=UTC)
    rest = window.window_for(_friday(day))
    if not rest.computed:
        assert "does not set" in rest.basis


def test_the_example_location_golden_check() -> None:
    # EXAMPLE location (Greenville, SC): NOAA publishes sunset 19:23 EDT on Friday
    # 2026-09-25 and 19:22 EDT on Saturday 2026-09-26.
    rest = _window(34.97, -82.44).window_for(date(2026, 9, 25))
    assert abs(rest.opened - datetime(2026, 9, 25, 23, 23, tzinfo=UTC)) <= timedelta(minutes=2)
    assert abs(rest.resumes - datetime(2026, 9, 26, 23, 22, tzinfo=UTC)) <= timedelta(minutes=2)
