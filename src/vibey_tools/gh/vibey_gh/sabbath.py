# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Sabbath window, computed from where the operator stands (sub-doctrine 8.i).

8.i: "from sundown Friday to sundown Saturday, nothing in this family writes, merges, tests,
or ships code". Sundown is astronomical, so this module computes it: the NOAA solar-position
algorithm (the Global Monitoring Laboratory's solar calculator, after Meeus, *Astronomical
Algorithms*), with the standard "official" zenith of 90.833 degrees -- the geometric horizon
plus 34' of atmospheric refraction and the sun's 16' semi-diameter.

Everything here is pure: no clock, no file, no network, no time-zone database. The caller
passes the instant to judge and a `tzinfo` for the operator's civil day; building that
`tzinfo` (from an IANA name) is the configuration's job. So `vibey.domain` can import this
module unchanged -- `vibey-gh` declares no dependencies, which is what makes it importable
there (CLAUDE.md, "`domain/` stays pure") -- and there is exactly one implementation of the
window in the family.

The formula, per civil date (y, m, d) at longitude L (east positive) and latitude phi:

    JD  = Julian day of 0h UT on that date;  T = (JD - 2451545) / 36525
    L0  = 280.46646 + T(36000.76983 + 0.0003032 T)            mean longitude
    M   = 357.52911 + T(35999.05029 - 0.0001537 T)            mean anomaly
    e   = 0.016708634 - T(0.000042037 + 0.0000001267 T)       orbital eccentricity
    C   = sin M (1.914602 - T(0.004817 + 0.000014 T))
          + sin 2M (0.019993 - 0.000101 T) + sin 3M (0.000289)  equation of centre
    lam = L0 + C - 0.00569 - 0.00478 sin(125.04 - 1934.136 T)  apparent longitude
    eps = 23 deg 26' (21.448 - T(46.815 + T(0.00059 - 0.001813 T)))"
          + 0.00256 cos(125.04 - 1934.136 T)                    corrected obliquity
    dec = asin(sin eps sin lam)                                 declination
    y   = tan^2(eps / 2)
    EoT = 4 deg(y sin 2L0 - 2e sin M + 4ey sin M cos 2L0
                - y^2/2 sin 4L0 - 5e^2/4 sin 2M)                equation of time, minutes
    H   = acos(cos 90.833 / (cos phi cos dec) - tan phi tan dec)  hour angle at sunset
    sunset (minutes after 0h UT) = 720 - 4 (L - H) - EoT

evaluated twice, the second time with T taken at the first estimate, as NOAA's calculator
does. When the acos argument leaves [-1, 1] the sun does not set that day (polar day or
night): the window then uses the declared fallback times and says so -- never silently.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone, tzinfo

from vibey_gh.interfaces.sabbath_window_interface import (
    RestWindowInterface,
    SabbathWindowInterface,
    SunsetCalculatorInterface,
)

__all__ = ["OFFICIAL_ZENITH", "RestWindow", "SabbathWindow", "SunsetCalculator"]

OFFICIAL_ZENITH = 90.833
# `date.weekday()`: Friday is 4. The window opens on it and closes the next day.
_FRIDAY = 4
_SATURDAY = 5


class SunsetCalculator(SunsetCalculatorInterface):
    """NOAA's sunset, to within a minute or two of the published tables at mid-latitudes."""

    def __init__(self, zenith: float = OFFICIAL_ZENITH) -> None:
        self._zenith = zenith

    @staticmethod
    def _julian_day(day: date) -> float:
        year, month = day.year, day.month
        if month <= 2:
            year -= 1
            month += 12
        century = year // 100
        correction = 2 - century + century // 4
        return (
            math.floor(365.25 * (year + 4716))
            + math.floor(30.6001 * (month + 1))
            + day.day
            + correction
            - 1524.5
        )

    def _minutes(self, t: float, latitude: float, longitude: float) -> float | None:
        """Sunset in minutes after 0h UT for the Julian century `t`, or None."""
        mean_long = (280.46646 + t * (36000.76983 + 0.0003032 * t)) % 360
        anomaly = math.radians(357.52911 + t * (35999.05029 - 0.0001537 * t))
        ecc = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
        centre = (
            math.sin(anomaly) * (1.914602 - t * (0.004817 + 0.000014 * t))
            + math.sin(2 * anomaly) * (0.019993 - 0.000101 * t)
            + math.sin(3 * anomaly) * 0.000289
        )
        omega = math.radians(125.04 - 1934.136 * t)
        apparent = math.radians(mean_long + centre - 0.00569 - 0.00478 * math.sin(omega))
        seconds = 21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))
        obliquity = math.radians(23 + (26 + seconds / 60) / 60 + 0.00256 * math.cos(omega))
        declination = math.asin(math.sin(obliquity) * math.sin(apparent))
        y = math.tan(obliquity / 2) ** 2
        l0 = math.radians(mean_long)
        eq_time = 4 * math.degrees(
            y * math.sin(2 * l0)
            - 2 * ecc * math.sin(anomaly)
            + 4 * ecc * y * math.sin(anomaly) * math.cos(2 * l0)
            - 0.5 * y * y * math.sin(4 * l0)
            - 1.25 * ecc * ecc * math.sin(2 * anomaly)
        )
        phi = math.radians(latitude)
        cos_h = math.cos(math.radians(self._zenith)) / (
            math.cos(phi) * math.cos(declination)
        ) - math.tan(phi) * math.tan(declination)
        if not -1.0 <= cos_h <= 1.0:
            return None
        hour_angle = math.degrees(math.acos(cos_h))
        return 720 - 4 * (longitude - hour_angle) - eq_time

    def sunset(self, day: date, latitude: float, longitude: float) -> datetime | None:
        """The UTC instant of sunset on civil date `day`, or None when the sun does not set."""
        jd = self._julian_day(day)
        first = self._minutes((jd - 2451545.0) / 36525.0, latitude, longitude)
        if first is None:
            return None
        second = self._minutes((jd + first / 1440.0 - 2451545.0) / 36525.0, latitude, longitude)
        minutes = first if second is None else second
        return datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(minutes=minutes)


@dataclass(frozen=True)
class RestWindow:
    """One Sabbath: when it opened, when it resumes, and whether sundown was computed or
    declared. Satisfies `RestWindowInterface` by shape (a frozen dataclass cannot inherit a
    protocol's read-only properties)."""

    opened: datetime
    resumes: datetime
    computed: bool
    basis: str

    def contains(self, at: datetime) -> bool:
        return self.opened <= at < self.resumes

    def report(self) -> str:
        return (
            "held for the Sabbath (sub-doctrine 8.i): the window opened "
            f"{self.opened.isoformat()} and resumes {self.resumes.isoformat()} ({self.basis});"
            " nothing merges or ships until then"
        )

    def summary(self) -> str:
        return (
            "## Held for the Sabbath\n\n"
            "Sub-doctrine 8.i: nothing writes, merges, tests or ships code from sundown Friday"
            " to sundown Saturday.\n\n"
            f"- Window opened: `{self.opened.isoformat()}`\n"
            f"- Resumes: `{self.resumes.isoformat()}`\n"
            f"- Sundown: {self.basis}\n"
            "- Nothing was merged, shipped, labelled or commented on. This run is paused,"
            " not failed (10.f); the heartbeat re-fires held work when the window closes.\n"
        )


class SabbathWindow(SabbathWindowInterface):
    """Decides whether 8.i holds a given instant, and when the rest ends.

    `zone` is the operator's civil zone: it decides which calendar day is Friday and
    anchors the fallback times. With no `zone`, local mean solar time at `longitude` is
    used (UTC plus four minutes per degree east). `latitude`/`longitude` of None mean the
    location is not configured: every window is the declared fallback, and `configured`
    is False so a doctor can say so out loud. `margin` widens every window toward rest,
    opening earlier and resuming later; it can never narrow one.
    """

    def __init__(
        self,
        *,
        latitude: float | None,
        longitude: float | None,
        zone: tzinfo | None = None,
        margin: timedelta = timedelta(0),
        fallback_opens: time = time(18, 0),
        fallback_closes: time = time(19, 0),
        enabled: bool = True,
        calculator: SunsetCalculatorInterface | None = None,
        location: str = "",
    ) -> None:
        if (latitude is None) != (longitude is None):
            raise ValueError("sabbath: latitude and longitude are set together or not at all")
        if latitude is not None and not -90.0 <= latitude <= 90.0:
            raise ValueError("sabbath.latitude must be between -90 and 90")
        if longitude is not None and not -180.0 <= longitude <= 180.0:
            raise ValueError("sabbath.longitude must be between -180 and 180")
        if margin < timedelta(0):
            raise ValueError("sabbath.offset_minutes must not be negative: it widens toward rest")
        if zone is None:
            solar = timedelta(minutes=round((longitude or 0.0) * 4))
            zone = timezone(solar, "local mean solar time")
        self._lat = latitude
        self._lon = longitude
        self._zone = zone
        self._margin = margin
        self._opens = fallback_opens
        self._closes = fallback_closes
        self._enabled = enabled
        self._calc = calculator if calculator is not None else SunsetCalculator()
        self._location = location

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def configured(self) -> bool:
        """Whether sundown is computed from a location rather than declared."""
        return self._lat is not None

    def _edge(self, day: date, fallback: time) -> tuple[datetime, str | None]:
        """Sundown on `day`, or the declared fallback and the reason it was used."""
        if self._lat is None or self._lon is None:
            reason = "no [sabbath] latitude/longitude configured"
        else:
            sunset = self._calc.sunset(day, self._lat, self._lon)
            if sunset is not None:
                return sunset, None
            reason = f"the sun does not set on {day.isoformat()} at this latitude"
        return datetime.combine(day, fallback, tzinfo=self._zone).astimezone(UTC), reason

    def window_for(self, friday: date) -> RestWindow:
        """The window that opens on `friday` (which must be a Friday)."""
        if friday.weekday() != _FRIDAY:
            raise ValueError(f"{friday.isoformat()} is not a Friday")
        opened, why_open = self._edge(friday, self._opens)
        resumes, why_close = self._edge(friday + timedelta(days=1), self._closes)
        reasons = [reason for reason in (why_open, why_close) if reason]
        basis = (
            "declared fallback times: " + "; ".join(reasons)
            if reasons
            else "computed sundown (NOAA, zenith 90.833)"
        )
        if self._location:
            basis = f"{basis}; location: {self._location}"
        if self._margin:
            basis = f"{basis}; widened {int(self._margin.total_seconds() // 60)} min toward rest"
        return RestWindow(
            opened=(opened - self._margin).astimezone(self._zone),
            resumes=(resumes + self._margin).astimezone(self._zone),
            computed=not reasons,
            basis=basis,
        )

    def _friday_on_or_before(self, at: datetime) -> date:
        local = at.astimezone(self._zone).date()
        return local - timedelta(days=(local.weekday() - _FRIDAY) % 7)

    def hold(self, at: datetime) -> RestWindowInterface | None:
        """The window holding `at`, or None when the caller may proceed."""
        if at.tzinfo is None:
            raise ValueError("sabbath: the instant to judge must be timezone-aware")
        if not self._enabled:
            return None
        friday = self._friday_on_or_before(at)
        # A margin can pull Friday's window open before Friday's own sundown, or push
        # Saturday's close past midnight into Sunday, so the windows either side are asked too.
        for candidate in (friday, friday - timedelta(days=7), friday + timedelta(days=7)):
            window = self.window_for(candidate)
            if window.contains(at):
                return window
        return None

    def is_resting(self, at: datetime) -> bool:
        return self.hold(at) is not None

    def next_resume(self, at: datetime) -> datetime:
        """The Saturday sundown ending the window that holds `at`, or -- when none does --
        the one ending the next window to open."""
        held = self.hold(at)
        if held is not None:
            return held.resumes
        friday = self._friday_on_or_before(at)
        window = self.window_for(friday)
        if window.resumes <= at:
            window = self.window_for(friday + timedelta(days=7))
        return window.resumes
