# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sub-doctrine 8.i: the Sabbath window, fitted to the host (vibey ADR-0070).

The EXAMPLE location below (Greenville, South Carolina) is a golden test fixture and
nothing else: the window is resolved per host at run time and no location is committed.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from vibey_gh import cli
from vibey_gh.cli import main
from vibey_gh.config import SabbathConfig, load_config
from vibey_gh.heartbeat_timer import BeatRecord
from vibey_gh.sabbath import RestWindow, SabbathWindow, SunsetCalculator
from vibey_gh.sabbath_guard import SabbathGuard, SabbathLanes, _run, resume_dispatch
from vibey_gh.sabbath_location import (
    LocationResolver,
    OsLocationService,
    OverrideLocation,
    ResolvedLocation,
    ZoneTabLocation,
    _run as location_run,
    host_zone,
)

NEW_YORK = ZoneInfo("America/New_York")
# EXAMPLE location: Greenville, SC 29690 -- a golden fixture only, never a default.
EXAMPLE_LAT, EXAMPLE_LON = 34.97, -82.44

# Published NOAA sunsets (Global Monitoring Laboratory solar calculator), local wall clock.
GOLDEN = [
    # (date, lat, lon, zone, expected local sunset)
    (date(2026, 9, 25), EXAMPLE_LAT, EXAMPLE_LON, "America/New_York", "19:23"),
    (date(2026, 9, 26), EXAMPLE_LAT, EXAMPLE_LON, "America/New_York", "19:22"),
    (date(2026, 6, 21), 40.7128, -74.0060, "America/New_York", "20:31"),
    (date(2026, 12, 5), 40.7128, -74.0060, "America/New_York", "16:28"),
    (date(2026, 3, 20), 51.5074, -0.1278, "Europe/London", "18:14"),
    (date(2026, 3, 20), -33.8688, 151.2093, "Australia/Sydney", "19:07"),
    (date(2026, 9, 25), 21.3069, -157.8583, "Pacific/Honolulu", "18:24"),
    (date(2026, 1, 16), 47.6062, -122.3321, "America/Los_Angeles", "16:48"),
]


def _at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=NEW_YORK)


def _example_window(**kwargs) -> SabbathWindow:
    return SabbathWindow(latitude=EXAMPLE_LAT, longitude=EXAMPLE_LON, zone=NEW_YORK, **kwargs)


@pytest.mark.parametrize("day, lat, lon, zone, expected", GOLDEN)
def test_sunset_matches_the_published_noaa_table_within_two_minutes(day, lat, lon, zone, expected):
    sunset = SunsetCalculator().sunset(day, lat, lon)
    assert sunset is not None
    local = sunset.astimezone(ZoneInfo(zone))
    hours, minutes = (int(part) for part in expected.split(":"))
    published = datetime.combine(day, time(hours, minutes), tzinfo=ZoneInfo(zone))
    assert abs(local - published) <= timedelta(minutes=2), local


def test_the_sun_does_not_set_in_the_polar_summer():
    assert SunsetCalculator().sunset(date(2026, 6, 21), 78.2, 15.6) is None


def test_the_second_pass_falling_off_the_edge_keeps_the_first_estimate():
    class Edge(SunsetCalculator):
        answers = iter((600.0, None))

        def _minutes(self, t, latitude, longitude):
            return next(self.answers)

    assert Edge().sunset(date(2026, 1, 1), 0, 0) == datetime(2026, 1, 1, 10, tzinfo=UTC)


def test_the_window_is_friday_sundown_to_saturday_sundown_at_the_example_location():
    window = _example_window()
    held = window.hold(_at("2026-09-25T20:00"))
    assert held is not None and held.computed
    assert held.opened.date() == date(2026, 9, 25) and held.resumes.date() == date(2026, 9, 26)
    assert window.next_resume(_at("2026-09-25T20:00")) == held.resumes
    assert "computed sundown" in held.basis
    assert window.hold(_at("2026-09-25T19:00")) is None
    assert window.hold(_at("2026-09-26T19:30")) is None
    assert window.is_resting(_at("2026-09-26T12:00"))
    assert not window.is_resting(_at("2026-09-23T12:00"))


def test_every_friday_of_the_year_opens_friday_and_resumes_saturday():
    window = _example_window()
    friday = date(2026, 1, 2)
    while friday.year == 2026:
        rest = window.window_for(friday)
        assert rest.opened.weekday() == 4 and rest.resumes.weekday() == 5
        assert (
            timedelta(hours=23, minutes=50)
            < rest.resumes - rest.opened
            < timedelta(hours=24, minutes=10)
        )
        middle = rest.opened + (rest.resumes - rest.opened) / 2
        assert window.next_resume(middle) == rest.resumes
        friday += timedelta(days=7)


def test_next_resume_outside_a_window_is_the_one_that_ends_the_next_rest():
    window = _example_window()
    thursday = window.next_resume(_at("2026-09-24T12:00"))
    sunday = window.next_resume(_at("2026-09-27T12:00"))
    friday_noon = window.next_resume(_at("2026-09-25T12:00"))
    assert thursday.date() == date(2026, 9, 26) and friday_noon == thursday
    assert sunday.date() == date(2026, 10, 3)


def test_an_unconfigured_window_uses_the_declared_fallback_and_says_so():
    window = SabbathWindow(latitude=None, longitude=None, zone=NEW_YORK)
    assert not window.configured
    held = window.hold(_at("2026-09-25T18:30"))
    assert held is not None and not held.computed
    assert "declared fallback times" in held.basis
    assert held.resumes == _at("2026-09-26T23:00")


def test_a_zone_half_a_day_off_its_longitude_keeps_sundown_on_the_right_civil_day():
    kiritimati = ZoneInfo("Pacific/Kiritimati")
    window = SabbathWindow(latitude=1.87, longitude=-157.4, zone=kiritimati)
    rest = window.window_for(date(2026, 9, 25))
    assert rest.opened.date() == date(2026, 9, 25) and rest.resumes.date() == date(2026, 9, 26)


def test_a_re_anchored_sundown_that_does_not_exist_keeps_the_first():
    class Once:
        calls = iter((datetime(2026, 9, 26, 20, tzinfo=UTC), None))

        def sunset(self, day, latitude, longitude):
            return next(self.calls)

    window = SabbathWindow(latitude=0.0, longitude=0.0, zone=UTC, calculator=Once())
    opened, reason = window._edge(date(2026, 9, 25), time(14, 0))
    assert opened == datetime(2026, 9, 26, 20, tzinfo=UTC) and reason is None


def test_a_polar_date_falls_back_loudly():
    window = SabbathWindow(latitude=78.2, longitude=15.6, zone=ZoneInfo("Arctic/Longyearbyen"))
    rest = window.window_for(date(2026, 6, 19))
    assert not rest.computed and "does not set" in rest.basis


def test_margin_widens_toward_rest_and_names_the_location():
    window = _example_window(margin=timedelta(minutes=45), location="an example place")
    rest = window.window_for(date(2026, 9, 25))
    plain = _example_window().window_for(date(2026, 9, 25))
    assert rest.opened == plain.opened - timedelta(minutes=45)
    assert rest.resumes == plain.resumes + timedelta(minutes=45)
    assert "location: an example place" in rest.basis and "widened 45 min" in rest.basis


def test_a_window_opened_by_a_margin_on_thursday_is_found_from_thursday():
    window = SabbathWindow(
        latitude=None,
        longitude=None,
        zone=NEW_YORK,
        fallback_opens=time(0, 10),
        margin=timedelta(hours=1),
    )
    held = window.hold(_at("2026-09-24T23:30"))
    assert held is not None and held.opened.date() == date(2026, 9, 24)


def test_no_zone_reads_local_mean_solar_time():
    window = SabbathWindow(latitude=0.0, longitude=90.0)
    rest = window.window_for(date(2026, 9, 25))
    assert rest.opened.utcoffset() == timedelta(hours=6)


def test_disabled_never_holds():
    window = _example_window(enabled=False)
    assert not window.enabled and window.hold(_at("2026-09-25T21:00")) is None


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"latitude": 1.0, "longitude": None}, "together"),
        ({"latitude": 91.0, "longitude": 0.0}, "latitude"),
        ({"latitude": 0.0, "longitude": 181.0}, "longitude"),
        ({"latitude": 0.0, "longitude": 0.0, "margin": timedelta(minutes=-1)}, "negative"),
    ],
)
def test_a_bad_declaration_is_refused(kwargs, message):
    with pytest.raises(ValueError, match=message):
        SabbathWindow(**kwargs)


def test_only_a_friday_opens_and_only_an_aware_instant_is_judged():
    with pytest.raises(ValueError, match="not a Friday"):
        _example_window().window_for(date(2026, 9, 24))
    with pytest.raises(ValueError, match="timezone-aware"):
        _example_window().hold(datetime.fromisoformat("2026-09-25T20:00"))


def test_a_rest_window_reports_and_summarises_paused_not_failed():
    rest = _example_window().window_for(date(2026, 9, 25))
    assert "sub-doctrine 8.i" in rest.report() and rest.resumes.isoformat() in rest.report()
    assert "paused, not failed" in rest.summary()


# -- where the host stands -----------------------------------------------------------------


def test_host_zone_reads_tz_then_localtime(tmp_path):
    assert host_zone({"TZ": ":Europe/Paris"}) == "Europe/Paris"
    zoneinfo = tmp_path / "zoneinfo" / "Asia"
    zoneinfo.mkdir(parents=True)
    (zoneinfo / "Tokyo").write_text("", encoding="utf-8")
    link = tmp_path / "localtime"
    link.symlink_to(zoneinfo / "Tokyo")
    assert host_zone({"TZ": "UTC"}, localtime=link) == "Asia/Tokyo"
    assert host_zone({}, localtime=tmp_path / "plain") == ""
    assert isinstance(host_zone(), str)


def test_the_override_answers_only_when_both_coordinates_are_set():
    assert OverrideLocation(None, 1.0).locate() is None
    found = OverrideLocation(1.0, 2.0).locate()
    assert found is not None and found.source == "configured override" and not found.coarse


def test_core_location_through_its_helper():
    def which(name):
        return "/opt/CoreLocationCLI"

    ok = OsLocationService(platform="darwin", which=which, run=lambda argv: (0, "35.0 -82.0 65\n"))
    found = ok.locate()
    assert found is not None and found.accuracy_km == 0.065 and found.source == "macOS CoreLocation"
    assert (
        OsLocationService(platform="darwin", which=which, run=lambda argv: (1, "")).locate() is None
    )
    assert OsLocationService(platform="darwin", which=lambda name: None).locate() is None


def test_geoclue_through_its_agent(tmp_path):
    agent = tmp_path / "where-am-i"
    agent.write_text("", encoding="utf-8")
    text = "Latitude:    51.50\nLongitude:   -0.12\nAccuracy:    2000.0 meters\n"
    found = OsLocationService(
        platform="linux", run=lambda argv: (0, text), geoclue_agents=(tmp_path / "no", agent)
    ).locate()
    assert found is not None and found.accuracy_km == 2.0 and found.source == "GeoClue"
    bare = OsLocationService(
        platform="linux",
        run=lambda argv: (0, "Latitude: 1\nLongitude: 2\n"),
        geoclue_agents=(agent,),
    ).locate()
    assert bare is not None and bare.accuracy_km == 10.0
    assert (
        OsLocationService(
            platform="linux", run=lambda argv: (1, text), geoclue_agents=(agent,)
        ).locate()
        is None
    )
    assert OsLocationService(platform="linux", geoclue_agents=()).locate() is None
    assert OsLocationService(platform="win32").locate() is None


def test_a_helper_that_cannot_start_is_absent():
    assert location_run(("/nonexistent/helper",)) == (127, "")
    assert location_run(("true",))[0] == 0


def test_the_zone_table_maps_a_zone_to_its_reference_city(tmp_path):
    table = tmp_path / "zone1970.tab"
    table.write_text(
        "# comment\nshort\nUS\t+404251-0740023\tAmerica/New_York\tEastern\nXX\tgarbage\tEtc/Bad\n",
        encoding="utf-8",
    )
    found = ZoneTabLocation("America/New_York", (tmp_path / "missing", table)).locate()
    assert found is not None and found.coarse and round(found.latitude, 2) == 40.71
    assert ZoneTabLocation("Etc/Bad", (table,)).locate() is None
    assert ZoneTabLocation("", (table,)).locate() is None
    assert ZoneTabLocation.parse("-3352+15113") == pytest.approx((-33.8667, 151.2167), abs=1e-3)
    assert ZoneTabLocation.parse("nope") is None


class _Source:
    def __init__(self, answer):
        self.answer = answer
        self.asked = 0

    def locate(self):
        self.asked += 1
        return self.answer


def test_the_resolver_prefers_the_override_then_caches_a_week_per_zone(tmp_path):
    cache = tmp_path / "state" / "location.json"
    here = ResolvedLocation(1.0, 2.0, "zone", 500.0, True)
    now = [1000.0]
    fallback = _Source(here)
    resolver = LocationResolver(
        [_Source(None), fallback], zone="Z", clock=lambda: now[0], cache=cache
    )
    assert resolver.resolve() == here and cache.is_file()
    assert resolver.resolve() == here and fallback.asked == 1
    assert resolver.resolve(refresh=True) == here and fallback.asked == 2
    now[0] += 8 * 24 * 3600
    assert resolver.resolve() == here and fallback.asked == 3
    other = LocationResolver([_Source(None), fallback], zone="Y", clock=lambda: now[0], cache=cache)
    assert other.resolve() == here and fallback.asked == 4
    override = ResolvedLocation(5.0, 6.0, "configured override", 0.0, False)
    assert LocationResolver([_Source(override)], zone="Z", clock=lambda: 0.0).resolve() == override
    cache.write_text("{", encoding="utf-8")
    assert resolver.resolve() == here


def test_the_resolver_without_a_cache_or_any_answer(tmp_path):
    assert LocationResolver([], zone="Z", clock=lambda: 0.0).resolve() is None
    plain = LocationResolver([_Source(None), _Source(None)], zone="Z", clock=lambda: 0.0)
    assert plain.resolve() is None
    found = ResolvedLocation(1.0, 2.0, "zone", 500.0, True)
    assert (
        LocationResolver([_Source(None), _Source(found)], zone="Z", clock=lambda: 0.0).resolve()
        == found
    )
    duck = _Source(object())
    assert (
        LocationResolver(
            [_Source(None), duck], zone="Z", clock=lambda: 0.0, cache=tmp_path / "c.json"
        ).resolve()
        is duck.answer
    )
    blocked = tmp_path / "file"
    blocked.write_text("", encoding="utf-8")
    here = ResolvedLocation(1.0, 2.0, "zone", 500.0, True)
    stuck = LocationResolver(
        [_Source(None), _Source(here)], zone="Z", clock=lambda: 0.0, cache=blocked / "c.json"
    )
    assert stuck.resolve() == here
    assert "coarse" in here.describe()
    assert "fine" in ResolvedLocation(1.0, 2.0, "x", 0.0, False).describe()


# -- the guard on this host ---------------------------------------------------------------


def _guard(tmp_path, config=None, **kwargs):
    kwargs.setdefault("environ", {"TZ": "America/New_York"})
    kwargs.setdefault("zone_tables", ())
    kwargs.setdefault("os_service", _Source(None))
    config = config or SabbathConfig(lanes_dir=str(tmp_path / "lanes"))
    return SabbathGuard(config, home=tmp_path, **kwargs)


def test_the_guard_reads_the_environment_override(tmp_path):
    env = {
        "TZ": "America/New_York",
        "VIBEY_SABBATH_LATITUDE": str(EXAMPLE_LAT),
        "VIBEY_SABBATH_LONGITUDE": str(EXAMPLE_LON),
    }
    guard = _guard(tmp_path, environ=env, clock=lambda: _at("2026-09-25T20:00").astimezone(UTC))
    held = guard.hold()
    assert held is not None and held.computed and "configured override" in held.basis
    assert guard.location() is guard.location()
    lines = guard.describe()
    assert any(line.startswith("resting now: until") for line in lines)


@pytest.mark.parametrize(
    "body",
    ["[sabbath]\nlatitude = 34.97\nlongitude = -82.44\n", "latitude = 34.97\nlongitude = -82.44\n"],
)
def test_the_guard_reads_a_local_never_committed_file(tmp_path, body):
    local = tmp_path / ".config" / "vibey" / "sabbath.toml"
    local.parent.mkdir(parents=True)
    local.write_text(body, encoding="utf-8")
    where = _guard(tmp_path).location()
    assert where is not None and where.source == "configured override"


def test_coordinates_from_a_local_vibey_toml_come_first(tmp_path):
    config = SabbathConfig(
        latitude=EXAMPLE_LAT, longitude=EXAMPLE_LON, lanes_dir=str(tmp_path / "lanes")
    )
    env = {"TZ": "America/New_York", "VIBEY_SABBATH_LATITUDE": "0", "VIBEY_SABBATH_LONGITUDE": "0"}
    where = _guard(tmp_path, config=config, environ=env).location()
    assert where is not None and where.latitude == EXAMPLE_LAT


def test_a_local_file_without_coordinates_falls_through_to_the_zone(tmp_path):
    local = tmp_path / ".config" / "vibey" / "sabbath.toml"
    local.parent.mkdir(parents=True)
    local.write_text("[sabbath]\nlatitude = 1.0\n", encoding="utf-8")
    table = tmp_path / "zone.tab"
    table.write_text("US\t+404251-0740023\tAmerica/New_York\n", encoding="utf-8")
    guard = _guard(
        tmp_path, zone_tables=(table,), clock=lambda: _at("2026-09-23T12:00").astimezone(UTC)
    )
    rest = guard.window().window_for(date(2026, 9, 25))
    assert "widened 90 min" in rest.basis and "reference city" in rest.basis
    assert any(line.startswith("next rest ends") for line in guard.describe())


def test_an_unresolved_host_uses_the_fallback_widened_and_says_so(tmp_path):
    config = SabbathConfig(location_service=False, lanes_dir=str(tmp_path / "lanes"), enabled=False)
    guard = _guard(tmp_path, config=config, environ={}, clock=lambda: _at("2026-09-23T12:00"))
    assert guard.location() is None
    lines = guard.describe()
    assert "DISABLED" in lines[0] and "unresolved" in lines[2]


def test_the_default_sources_are_built_when_none_are_injected(tmp_path):
    guard = SabbathGuard(
        SabbathConfig(lanes_dir=str(tmp_path / "lanes")),
        home=tmp_path,
        environ={},
        platform="win32",
    )
    guard.location()


def test_an_unknown_zone_is_refused_by_name(tmp_path):
    guard = _guard(tmp_path, config=SabbathConfig(timezone="Mars/Olympus"))
    with pytest.raises(ValueError, match="Mars/Olympus"):
        guard.window()


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"fallback_opens": "6pm"}, "fallback_opens"),
        ({"offset_minutes": -1}, "offset_minutes"),
        ({"coarse_margin_minutes": 999}, "coarse_margin_minutes"),
        ({"timezone": "not a zone"}, "IANA"),
        ({"latitude": 1.0}, "together"),
        ({"latitude": 91.0, "longitude": 0.0}, "latitude must"),
        ({"latitude": 0.0, "longitude": 181.0}, "longitude must"),
    ],
)
def test_the_sabbath_config_refuses_a_bad_declaration_at_load(kwargs, message):
    with pytest.raises(ValueError, match=message):
        SabbathConfig(**kwargs)


def test_the_sabbath_table_loads_from_the_repository_config(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[sabbath]\nfallback_opens = "16:00"\ncoarse_margin_minutes = 60\n', encoding="utf-8"
    )
    cfg = load_config(tmp_path)
    assert cfg.sabbath.fallback_opens == "16:00" and cfg.sabbath.coarse_margin_minutes == 60
    assert cfg.sabbath.enabled


# -- lanes paused for the Sabbath ---------------------------------------------------------


def test_a_lane_registers_and_resumes_once_its_command_succeeds(tmp_path):
    ran = []

    def run(argv, cwd):
        ran.append((list(argv), cwd))
        return (0, "") if argv[0] == "ok" else (3, "line one\nit broke")

    lanes = SabbathLanes(tmp_path / "lanes", run=run)
    assert lanes.pending() == []
    lanes.register("good", ["ok", "go"], cwd="/w")
    lanes.register("bad", ["no"])
    (tmp_path / "lanes" / "junk.json").write_text("{", encoding="utf-8")
    lines = lanes.resume()
    assert "lane good: resumed" in lines
    assert any("lane bad: resume exited 3" in line and "it broke" in line for line in lines)
    assert "lane junk: unreadable registration, left in place" in lines
    assert [name for name, _, _ in lanes.pending()] == ["bad", "junk"]
    silent = SabbathLanes(tmp_path / "lanes", run=lambda argv, cwd: (4, ""))
    assert any(line.endswith("kept for the next beat: ") for line in silent.resume())


def test_a_lane_needs_a_safe_name_and_a_command(tmp_path):
    lanes = SabbathLanes(tmp_path)
    with pytest.raises(ValueError, match="lane name"):
        lanes.register("../x", ["a"])
    with pytest.raises(ValueError, match="resume"):
        lanes.register("x", [])


def test_the_guard_runner_reports_what_ran():
    assert _run(("true",), None)[0] == 0
    assert _run(("/nonexistent/x",), None)[0] == 127


def test_resume_dispatch_re_fires_the_held_workflows(tmp_path):
    cfg = load_config(tmp_path)
    calls = []

    def run(argv, cwd):
        calls.append(tuple(argv))
        return (0, "") if "Merge train" in argv else (1, "")

    lines = resume_dispatch(cfg, cwd=None, run=run)
    assert lines == ["Merge train: dispatched", "Promote: not dispatched (1)"]
    assert calls[0] == ("gh", "workflow", "run", "Merge train")
    worded = resume_dispatch(cfg, cwd=None, run=lambda argv, cwd: (1, "HTTP 403\nforbidden"))
    assert worded[0] == "Merge train: not dispatched (forbidden)"


# -- the command line ---------------------------------------------------------------------

_REST = RestWindow(_at("2026-09-25T19:23"), _at("2026-09-26T19:22"), True, "computed")


class _Guard:
    def __init__(self, held):
        self.held = held

    def hold(self, at=None):
        return self.held

    def describe(self):
        return ["sabbath: enabled"]


@pytest.fixture
def resting(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text(
        f'[sabbath]\nlanes_dir = "{tmp_path / "lanes"}"\n', encoding="utf-8"
    )
    guard = _Guard(_REST)
    monkeypatch.setattr(cli, "_sabbath_guard", lambda cfg: guard)
    return guard


@pytest.mark.sabbath
@pytest.mark.parametrize("command", [["merge-train"], ["promote"]])
def test_a_held_writer_stands_down_visibly_and_exits_zero(resting, tmp_path, capsys, command):
    summary = tmp_path / "summary.md"
    assert main([*command, "--summary", str(summary)]) == 0
    assert "held for the Sabbath" in capsys.readouterr().out
    assert "paused, not failed" in summary.read_text(encoding="utf-8")


@pytest.mark.sabbath
def test_the_heartbeat_rests_through_the_window_and_stays_alive(resting, tmp_path, capsys):
    record = tmp_path / "beat.json"
    assert main(["sovereign", "--beat", "--record", str(record)]) == 0
    body = json.loads(record.read_text(encoding="utf-8"))
    assert body["resting_until"] == _REST.resumes.timestamp() and body["published"] is False
    assert "resting for the Sabbath until" in capsys.readouterr().out
    assert main(["sovereign", "--beat"]) == 0


@pytest.mark.sabbath
def test_the_probe_offers_no_lane_while_resting(resting, tmp_path, monkeypatch, capsys):
    assert main(["sovereign"]) == 0
    output = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert main(["sovereign"]) == 0
    assert "ready=false" in output.read_text(encoding="utf-8")


@pytest.mark.sabbath
@pytest.mark.parametrize("dispatch", [True, False])
def test_the_first_beat_after_the_window_re_arms_what_it_held(
    resting, tmp_path, monkeypatch, capsys, dispatch
):
    (tmp_path / ".vibey-gh.toml").write_text(
        f'[sabbath]\nlanes_dir = "{tmp_path / "lanes"}"\nresume_dispatch = {str(dispatch).lower()}\n',
        encoding="utf-8",
    )
    resting.held = None
    record = tmp_path / "beat.json"
    BeatRecord(1.0, False, "resting", 2.0).write(record)
    fired = []
    monkeypatch.setattr(
        "vibey_gh.sabbath_guard.resume_dispatch",
        lambda cfg, cwd: fired.append(cwd) or ["Merge train: dispatched"],
    )
    main(["sovereign", "--beat", "--record", str(record)])
    out = capsys.readouterr().out
    assert "SabbathEnded" in out
    assert bool(fired) is dispatch
    assert BeatRecord.read(record).resting_until is None
    main(["sovereign", "--beat", "--record", str(record)])
    assert "SabbathEnded" not in capsys.readouterr().out


@pytest.mark.sabbath
def test_the_sabbath_command(resting, tmp_path, capsys, monkeypatch):
    assert main(["sabbath", "register-lane"]) == 2
    assert main(["sabbath", "register-lane", "--name", "docs", "--", "echo", "hi"]) == 0
    assert main(["sabbath", "status"]) == 0
    out = capsys.readouterr().out
    assert "paused lane: docs: echo hi" in out
    assert main(["sabbath", "resume"]) == 0
    assert "still resting" in capsys.readouterr().out
    resting.held = None
    monkeypatch.setattr("vibey_gh.sabbath_guard.resume_dispatch", lambda cfg, cwd: ["dispatched"])
    assert main(["sabbath", "resume", "--dispatch"]) == 0
    out = capsys.readouterr().out
    assert "lane docs: resumed" in out and "dispatched" in out


@pytest.mark.sabbath
def test_the_real_guard_is_built_from_the_configuration(tmp_path):
    guard = cli._sabbath_guard(load_config(tmp_path))
    assert isinstance(guard, SabbathGuard)
    assert isinstance(cli._sabbath_lanes(load_config(tmp_path)), SabbathLanes)


def test_every_other_test_runs_under_a_guard_that_never_holds():
    assert cli._sabbath_guard(None).hold() is None


def test_a_beat_record_carries_its_rest(tmp_path):
    path = tmp_path / "r.json"
    BeatRecord(1.0, False, "resting", 5.0).write(path)
    assert BeatRecord.read(path) == BeatRecord(1.0, False, "resting", 5.0)
    path.write_text("[]", encoding="utf-8")
    assert BeatRecord.read(path) is None
