# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where this machine stands, for the Sabbath window (sub-doctrines 8.i, 8.j, 10.f).

The window is fitted to the host it runs on, never to one operator's home: sundown moves
with the machine. The location is resolved per host, in order, and every answer carries its
source and its accuracy so a window computed from it can say what it rests on (10.f):

1. **An explicit override** -- `latitude`/`longitude` in a local, never-committed file
   (`[sabbath] local_config`) or the `VIBEY_SABBATH_LATITUDE`/`_LONGITUDE` environment.
2. **The operating system's location service**, where one is installed and permitted:
   macOS CoreLocation through the small `CoreLocationCLI` helper, Linux GeoClue through its
   `where-am-i` agent. Both are absent unless installed, and absence is not an error.
3. **The host's IANA time zone mapped to its reference city** from the system's own
   `zone1970.tab` (or `zone.tab`) -- no network. It can be tens of minutes off
   (America/New_York is New York City), so it is marked *coarse*, and the window widens by
   a declared margin (`coarse_margin_minutes`, default 45) toward rest.

There is no IP geolocation (8.a: sovereignty). A resolution is cached for a week and
dropped at once when the host's zone changes (8.j: fitted to the iron).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from vibey_gh.interfaces.sabbath_location_interface import (
    LocationSourceInterface,
    ResolvedLocationInterface,
)

__all__ = [
    "LocationResolver",
    "OsLocationService",
    "OverrideLocation",
    "ResolvedLocation",
    "ZoneTabLocation",
    "host_zone",
]

Runner = Callable[[Sequence[str]], tuple[int, str]]
ZONE_TABLES = (
    Path("/usr/share/zoneinfo/zone1970.tab"),
    Path("/usr/share/zoneinfo/zone.tab"),
    Path("/var/db/timezone/zoneinfo/zone1970.tab"),
)
GEOCLUE_AGENTS = (
    Path("/usr/libexec/geoclue-2.0/demos/where-am-i"),
    Path("/usr/lib/geoclue-2.0/demos/where-am-i"),
)
_WEEK_SECONDS = 7 * 24 * 3600


@dataclass(frozen=True)
class ResolvedLocation:
    """A place, where it came from, and how far it may be off."""

    latitude: float
    longitude: float
    source: str
    accuracy_km: float
    coarse: bool

    def describe(self) -> str:
        grain = "coarse" if self.coarse else "fine"
        return (
            f"{self.source} ({self.latitude:.2f}, {self.longitude:.2f};"
            f" about {self.accuracy_km:g} km, {grain})"
        )


def _run(argv: Sequence[str]) -> tuple[int, str]:
    """Run a location helper; a helper that hangs or cannot start is simply absent."""
    try:
        done = subprocess.run(list(argv), capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.SubprocessError):
        return 127, ""
    return done.returncode, done.stdout


def host_zone(environ: Mapping[str, str] | None = None, localtime: Path | None = None) -> str:
    """The host's IANA zone name: `$TZ`, else the target of `/etc/localtime`, else ''."""
    env = os.environ if environ is None else environ
    declared = env.get("TZ", "").lstrip(":")
    if declared and "/" in declared:
        return declared
    link = Path("/etc/localtime") if localtime is None else localtime
    target = str(link.resolve())
    marker = "zoneinfo/"
    return target.split(marker, 1)[1] if marker in target else ""


class OverrideLocation(LocationSourceInterface):
    """The operator's explicit coordinates, from a local file or the environment."""

    def __init__(self, latitude: float | None, longitude: float | None) -> None:
        self._lat = latitude
        self._lon = longitude

    def locate(self) -> ResolvedLocationInterface | None:
        if self._lat is None or self._lon is None:
            return None
        return ResolvedLocation(self._lat, self._lon, "configured override", 0.0, False)


class OsLocationService(LocationSourceInterface):
    """macOS CoreLocation or Linux GeoClue, through their command-line helpers."""

    _NUMBER = r"(-?\d+(?:\.\d+)?)"

    def __init__(
        self,
        *,
        platform: str,
        which: Callable[[str], str | None] = shutil.which,
        run: Runner = _run,
        geoclue_agents: Sequence[Path] = GEOCLUE_AGENTS,
    ) -> None:
        self._platform = platform
        self._which = which
        self._run = run
        self._agents = geoclue_agents

    def _core_location(self) -> ResolvedLocationInterface | None:
        helper = self._which("CoreLocationCLI")
        if helper is None:
            return None
        code, out = self._run((helper, "-once", "-format", "%latitude %longitude %h_accuracy"))
        match = re.fullmatch(rf"\s*{self._NUMBER}\s+{self._NUMBER}\s+{self._NUMBER}\s*", out)
        if code != 0 or match is None:
            return None
        lat, lon, metres = (float(part) for part in match.groups())
        return ResolvedLocation(lat, lon, "macOS CoreLocation", round(metres / 1000, 3), False)

    def _geoclue(self) -> ResolvedLocationInterface | None:
        helper = next((path for path in self._agents if path.is_file()), None)
        if helper is None:
            return None
        code, out = self._run((str(helper), "-t", "10"))
        lat = re.search(rf"Latitude:\s*{self._NUMBER}", out)
        lon = re.search(rf"Longitude:\s*{self._NUMBER}", out)
        acc = re.search(rf"Accuracy:\s*{self._NUMBER}", out)
        if code != 0 or lat is None or lon is None:
            return None
        metres = float(acc.group(1)) if acc else 10000.0
        return ResolvedLocation(
            float(lat.group(1)), float(lon.group(1)), "GeoClue", round(metres / 1000, 3), False
        )

    def locate(self) -> ResolvedLocationInterface | None:
        if self._platform == "darwin":
            return self._core_location()
        if self._platform.startswith("linux"):
            return self._geoclue()
        return None


class ZoneTabLocation(LocationSourceInterface):
    """The reference city of the host's IANA zone, from the system zone table. Coarse."""

    _COORD = re.compile(r"([+-])(\d{2})(\d{2})(\d{2})?([+-])(\d{3})(\d{2})(\d{2})?")

    def __init__(self, zone: str, tables: Sequence[Path] = ZONE_TABLES) -> None:
        self._zone = zone
        self._tables = tables

    @classmethod
    def parse(cls, coordinates: str) -> tuple[float, float] | None:
        """ISO 6709 `+DDMM[SS]+DDDMM[SS]` as decimal degrees."""
        match = cls._COORD.fullmatch(coordinates)
        if match is None:
            return None
        s1, d1, m1, x1, s2, d2, m2, x2 = match.groups()
        lat = int(d1) + int(m1) / 60 + int(x1 or 0) / 3600
        lon = int(d2) + int(m2) / 60 + int(x2 or 0) / 3600
        return (-lat if s1 == "-" else lat, -lon if s2 == "-" else lon)

    def locate(self) -> ResolvedLocationInterface | None:
        if not self._zone:
            return None
        for table in self._tables:
            try:
                lines = table.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in lines:
                fields = line.split("\t")
                if line.startswith("#") or len(fields) < 3 or fields[2] != self._zone:
                    continue
                point = self.parse(fields[1])
                if point is not None:
                    source = f"time zone {self._zone} reference city ({table.name})"
                    return ResolvedLocation(point[0], point[1], source, 500.0, True)
        return None


class LocationResolver:
    """Tries each source in order and caches the answer for a week, per zone."""

    def __init__(
        self,
        sources: Sequence[LocationSourceInterface],
        *,
        zone: str,
        clock: Callable[[], float],
        cache: Path | None = None,
    ) -> None:
        self._sources = sources
        self._zone = zone
        self._clock = clock
        self._cache = cache

    def _cached(self) -> ResolvedLocationInterface | None:
        if self._cache is None:
            return None
        try:
            body = json.loads(self._cache.read_text(encoding="utf-8"))
            if body["zone"] != self._zone or self._clock() - float(body["at"]) > _WEEK_SECONDS:
                return None
            fields = body["location"]
            return ResolvedLocation(
                float(fields["latitude"]),
                float(fields["longitude"]),
                str(fields["source"]),
                float(fields["accuracy_km"]),
                bool(fields["coarse"]),
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _store(self, location: ResolvedLocation) -> None:
        if self._cache is None:
            return
        body = {"at": self._clock(), "zone": self._zone, "location": asdict(location)}
        try:
            self._cache.parent.mkdir(parents=True, exist_ok=True)
            partial = self._cache.with_name(f".{self._cache.name}.partial")
            partial.write_text(json.dumps(body) + "\n", encoding="utf-8")
            os.replace(partial, self._cache)
        except OSError:
            return

    def resolve(self, *, refresh: bool = False) -> ResolvedLocationInterface | None:
        """The first source that answers, or None when none does. An override is never
        cached: it is read fresh, so editing it takes effect on the next beat."""
        first = self._sources[0].locate() if self._sources else None
        if first is not None:
            return first
        if not refresh:
            cached = self._cached()
            if cached is not None:
                return cached
        for source in self._sources[1:]:
            found = source.locate()
            if found is not None:
                if isinstance(found, ResolvedLocation):
                    self._store(found)
                return found
        return None
