# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The local SearXNG vibey installs and runs itself, its pure half (ADR-0102).

All search vibey controls asks a local SearXNG first (the operator's ruling of 2026-11-21).
vibey runs that SearXNG in a container, from one image it names by digest, with one command line
fixed here: what reaches a container runtime is decided in this module and nowhere else.

- **The image** is `SEARXNG_IMAGE`, a reviewed constant: `docker.io/searxng/searxng` pinned by
  its multi-platform digest, never a tag, a setting or a project's value. It is refreshed by
  hand with `scripts/searxng_image_digest.py` and reviewed like any other change.
- **The provision record** (`provision.json` beside the settings, in the person's own
  configuration folder) says which image was pulled, the loopback port, the identity marker the
  SearXNG answers with, its unit's label and the runtime's absolute path. `parse` refuses any
  value vibey would not have written, so a record that was changed can never widen the command
  line: an image outside `IMAGE_REF`, a runtime that is not podman or docker, a label outside the
  service manager's closed alphabet, a port outside 1-65535.
- **The settings** are rendered from fixed text and two random hex values (`secret_key`, and the
  marker in `instance_name`), each checked against its alphabet, so neither can change the YAML's
  shape.
- **The command line** (`run_argv`): `--rm`, a fixed name, `--pull=never` (nothing downloads when
  the unit starts), a read-only root, every capability dropped, no new privileges, a process and
  memory limit, the person's own user (podman maps it with `--userns=keep-id`), the port published
  on 127.0.0.1 only, the settings mounted read-only, and tmpfs for what SearXNG writes. Never
  `--privileged`, never the host network, never the runtime's socket, never a home folder.

Pure: no I/O, no clock, no randomness (the random hex is handed in). Declared by
`interfaces/searxng_interface.py`.
"""

import re
from dataclasses import dataclass
from typing import Final

from vibey.domain.supervisor import LABEL, SEARXNG

__all__ = ["SEARXNG", "SEARXNG_IMAGE", "SearxngPlan", "SearxngProvision"]
SEARXNG_IMAGE: Final = "docker.io/searxng/searxng@sha256:fc1d81d7e9d04d3c8b3e23c7162feddf5c3d6aecd32e67a56eaabcb8d8747f79"
"""The image vibey pulls and runs. Read 2026-11-22 from registry-1.docker.io
(`searxng/searxng:latest`, an anonymous HEAD of its manifest index) by
`scripts/searxng_image_digest.py`; recorded in ADR-0102. A new digest is a reviewed change."""
IMAGE_REF: Final = re.compile(r"docker\.io/searxng/searxng@sha256:[0-9a-f]{64}")
"""What an image reference vibey runs must look like: SearXNG's own repository, by digest."""
MARKER: Final = re.compile(r"vibey-[0-9a-f]{32}")
"""The `instance_name` vibey's SearXNG answers on `/config`: how vibey knows it is its own."""
_SECRET: Final = re.compile(r"[0-9a-f]{64}")
_HEX32: Final = re.compile(r"[0-9a-f]{32}")
RUNTIMES: Final = ("podman", "docker")
"""The container runtimes vibey drives, in the order it prefers them."""
CONTAINER_NAME: Final = "vibey-searxng"
CONTAINER_PORT: Final = 8080
"""Where SearXNG listens inside its container (the image's default)."""
SETTINGS_IN_CONTAINER: Final = "/etc/searxng/settings.yml"
WRITABLE: Final = ("/etc/searxng", "/var/cache/searxng", "/tmp")  # nosec B108 - in the container
"""What the container may write, each a tmpfs: its root is read-only. `/etc/searxng` is where
the image's entrypoint keeps files it makes; the settings file is mounted over it, read-only."""
PIDS_LIMIT: Final = 256
MEMORY_LIMIT: Final = "512m"
_UNSAFE_PATH: Final = re.compile(r"[\x00-\x1f\x7f:,]")
"""Characters the `--volume` syntax would misread (`:` and `,` separate its fields)."""


def _name(path: str) -> str:
    """The last part of a POSIX path (pure string work: the domain imports no `pathlib`)."""
    # Module-level function: a one-line string helper both the plan's checks and its argv use.
    return path.rstrip("/").rpartition("/")[2]


@dataclass(frozen=True, slots=True)
class SearxngProvision:
    """What `provision.json` holds: the SearXNG vibey installed. A value type."""

    image: str
    port: int
    marker: str
    label: str
    runtime: str


class SearxngPlan:
    """Declared by `interfaces/searxng_interface.py::SearxngPlanInterface`."""

    def check(self, provision: SearxngProvision) -> None:
        self._image(provision.image)
        self._runtime(provision.runtime)
        port = provision.port
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("the port must be a whole number from 1 to 65535")
        if not isinstance(provision.marker, str) or not MARKER.fullmatch(provision.marker):
            raise ValueError("the marker must be vibey- and 32 lower-case hex digits")
        if not isinstance(provision.label, str) or not LABEL.fullmatch(provision.label):
            raise ValueError("the label must be letters, digits, '.', '_' or '-'")

    def record(self, provision: SearxngProvision) -> dict[str, object]:
        self.check(provision)
        return {
            "image": provision.image,
            "port": provision.port,
            "marker": provision.marker,
            "label": provision.label,
            "runtime": provision.runtime,
        }

    def parse(self, data: object) -> SearxngProvision:
        if not isinstance(data, dict):
            raise ValueError("the provision record is not a JSON object")
        try:
            provision = SearxngProvision(
                image=data["image"],
                port=data["port"],
                marker=data["marker"],
                label=data["label"],
                runtime=data["runtime"],
            )
        except KeyError as exc:
            raise ValueError(f"the provision record has no {exc.args[0]}") from None
        self.check(provision)
        return provision

    def new_marker(self, hex32: str) -> str:
        if not _HEX32.fullmatch(hex32):
            raise ValueError("a marker is made from 32 lower-case hex digits")
        return f"vibey-{hex32}"

    def settings_text(self, *, secret_key: str, marker: str) -> str:
        if not _SECRET.fullmatch(secret_key):
            raise ValueError("the secret key must be 64 lower-case hex digits")
        if not MARKER.fullmatch(marker):
            raise ValueError("the marker must be vibey- and 32 lower-case hex digits")
        return (
            "# Written by vibey for the SearXNG it runs on loopback (ADR-0102). vibey writes it\n"
            "# once and never again; `vibey searxng uninstall --purge` removes it.\n"
            "use_default_settings: true\n"
            "general:\n"
            f'  instance_name: "{marker}"\n'
            "  donation_url: false\n"
            "  contact_url: false\n"
            "  enable_metrics: false\n"
            "server:\n"
            f'  secret_key: "{secret_key}"\n'
            '  bind_address: "0.0.0.0"\n'
            f"  port: {CONTAINER_PORT}\n"
            "  limiter: false\n"
            "  public_instance: false\n"
            "  image_proxy: false\n"
            "search:\n"
            "  formats:\n"
            "    - html\n"
            "    - json\n"
        )

    def run_argv(
        self, provision: SearxngProvision, *, settings_path: str, uid: int, gid: int
    ) -> tuple[str, ...]:
        self.check(provision)
        if not settings_path.startswith("/") or _UNSAFE_PATH.search(settings_path):
            raise ValueError(
                "the settings file must be an absolute path without ':', ',' or control "
                "characters, which the --volume syntax would misread"
            )
        for value in (uid, gid):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("the container runs as your own user, never root")
        keep_id = ("--userns=keep-id",) if _name(provision.runtime) == "podman" else ()
        return (
            provision.runtime,
            "run",
            "--rm",
            "--name",
            CONTAINER_NAME,
            "--pull=never",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            str(PIDS_LIMIT),
            "--memory",
            MEMORY_LIMIT,
            *keep_id,
            "--user",
            f"{uid}:{gid}",
            "--publish",
            f"127.0.0.1:{provision.port}:{CONTAINER_PORT}",
            "--volume",
            f"{settings_path}:{SETTINGS_IN_CONTAINER}:ro",
            *(part for path in WRITABLE for part in ("--tmpfs", path)),
            provision.image,
        )

    def pull_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        return (self._runtime(runtime), "pull", self._image(image))

    def image_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        return (
            self._runtime(runtime),
            "image",
            "inspect",
            "--format",
            "{{.Id}}",
            self._image(image),
        )

    def remove_argv(self, runtime: str) -> tuple[str, ...]:
        return (self._runtime(runtime), "rm", "-f", CONTAINER_NAME)

    def remove_image_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        return (self._runtime(runtime), "rmi", self._image(image))

    def short(self, image: str) -> str:
        return self._image(image).rpartition(":")[2][:12]

    @staticmethod
    def _image(image: str) -> str:
        if not isinstance(image, str) or not IMAGE_REF.fullmatch(image):
            raise ValueError("the image must be docker.io/searxng/searxng pinned by its digest")
        return image

    @staticmethod
    def _runtime(runtime: str) -> str:
        if (
            not isinstance(runtime, str)
            or not runtime.startswith("/")
            or _name(runtime) not in RUNTIMES
            or re.search(r"[\x00-\x1f\x7f]", runtime)
        ):
            raise ValueError("the runtime must be the absolute path of podman or docker")
        return runtime
