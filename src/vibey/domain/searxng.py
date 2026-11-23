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
  line: an image other than the pinned one, a runtime that is not podman or docker in one of the
  trusted folders (`TRUSTED_RUNTIME_DIRS`), a label outside the service manager's closed alphabet,
  a port outside 1-65535. (Infrastructure checks the runtime's file again; the label is never
  taken from the record, only compared.) `parse_installed` reads a record of an earlier pin, to
  recognise its SearXNG and update it, never to run it.
- **The settings** are rendered from fixed text and two random hex values (`secret_key`, and the
  marker in `instance_name`), each checked against its alphabet, so neither can change the YAML's
  shape.
- **The command line** (`run_argv`): `--rm`, a name of the person's own (`vibey-searxng-<uid>`)
  and labels saying whose it is (`vibey.searxng.owner=<uid>`) and which image it runs, so vibey
  never removes a container it did not start; `--pull=never` (nothing downloads when
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
TRUSTED_RUNTIME_DIRS: Final[dict[str, tuple[str, ...]]] = {
    "darwin": (
        "/opt/homebrew/bin",
        "/usr/local/bin",
        "/usr/bin",
        "/Applications/Docker.app/Contents/Resources/bin",
    ),
    "linux": ("/usr/bin", "/usr/local/bin", "/bin", "/snap/bin"),
}
"""The only folders a runtime is taken from, per platform, in order: never the PATH, which an
editor may have taken from a project (a `bin/` it prepends, direnv). A record's runtime must lie
in one of them."""
TRUSTED_RUNTIME_ROOTS: Final[dict[str, tuple[str, ...]]] = {
    "darwin": ("/opt/homebrew/", "/usr/local/", "/usr/", "/Applications/Docker.app/"),
    "linux": ("/usr/", "/bin/", "/snap/"),
}
"""Where a runtime found in a trusted folder may point (Homebrew's links lead into its Cellar,
Docker Desktop's into its app bundle): a link leading anywhere else is refused."""
CONTAINER_PREFIX: Final = "vibey-searxng"
OWNER_LABEL: Final = "vibey.searxng.owner"
"""The label naming the uid whose container it is: vibey removes only a container carrying its own."""
IMAGE_LABEL: Final = "vibey.searxng.image"
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
    """Declared by `interfaces/searxng_interface.py::SearxngPlanInterface`.

    `pinned` is the one image it accepts (`SEARXNG_IMAGE`); `prefix` names the containers (a test
    run against a real runtime uses its own, so it never touches the person's); `runtime_dirs`
    are the folders a runtime may be in (every platform's trusted folders by default)."""

    def __init__(
        self,
        *,
        pinned: str = SEARXNG_IMAGE,
        prefix: str = CONTAINER_PREFIX,
        runtime_dirs: tuple[str, ...] | None = None,
    ) -> None:
        if not IMAGE_REF.fullmatch(pinned):
            raise ValueError("the pinned image must be docker.io/searxng/searxng by its digest")
        if not LABEL.fullmatch(prefix):
            raise ValueError("a container prefix must be letters, digits, '.', '_' or '-'")
        self._pinned = pinned
        self._prefix = prefix
        self._runtime_dirs = frozenset(
            runtime_dirs
            if runtime_dirs is not None
            else (folder for dirs in TRUSTED_RUNTIME_DIRS.values() for folder in dirs)
        )

    def check(self, provision: SearxngProvision) -> None:
        self._image(provision.image)
        self._installed(provision)

    def _installed(self, provision: SearxngProvision) -> None:
        """Every check but the pinned image's equality: what a record of an earlier pin holds."""
        if not isinstance(provision.image, str) or not IMAGE_REF.fullmatch(provision.image):
            raise ValueError("the image must be docker.io/searxng/searxng pinned by its digest")
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
        provision = self.parse_installed(data)
        self._image(provision.image)
        return provision

    def parse_installed(self, data: object) -> SearxngProvision:
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
        self._installed(provision)
        return provision

    def pinned(self, image: str) -> bool:
        return image == self._pinned

    def digest_of(self, image: str) -> str:
        if not isinstance(image, str) or not IMAGE_REF.fullmatch(image):
            raise ValueError("the image must be docker.io/searxng/searxng pinned by its digest")
        return image.rpartition(":")[2][:12]

    def container_name(self, uid: int) -> str:
        return f"{self._prefix}-{self._uid(uid)}"

    def marker_in(self, settings_text: str) -> str | None:
        found = re.search(r'^  instance_name: "(vibey-[0-9a-f]{32})"$', settings_text, re.MULTILINE)
        return found.group(1) if found else None

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
            self._uid(value)
        keep_id = ("--userns=keep-id",) if _name(provision.runtime) == "podman" else ()
        return (
            provision.runtime,
            "run",
            "--rm",
            "--name",
            self.container_name(uid),
            "--label",
            f"{OWNER_LABEL}={uid}",
            "--label",
            f"{IMAGE_LABEL}={self.short(provision.image)}",
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

    def labels_argv(self, runtime: str, uid: int) -> tuple[str, ...]:
        return (
            self._runtime(runtime),
            "container",
            "inspect",
            "--format",
            "{{json .Config.Labels}}",
            self.container_name(uid),
        )

    def remove_argv(self, runtime: str, uid: int) -> tuple[str, ...]:
        return (self._runtime(runtime), "rm", "-f", self.container_name(uid))

    def remove_image_argv(self, runtime: str, image: str) -> tuple[str, ...]:
        # An earlier pin's image may be removed too (after an update): SearXNG's by digest
        # only, never a tag and never another repository's.
        if not isinstance(image, str) or not IMAGE_REF.fullmatch(image):
            raise ValueError("the image must be docker.io/searxng/searxng pinned by its digest")
        return (self._runtime(runtime), "rmi", image)

    def info_argv(self, runtime: str) -> tuple[str, ...]:
        return (self._runtime(runtime), "info")

    def context_argv(self, runtime: str) -> tuple[str, ...] | None:
        checked = self._runtime(runtime)
        if _name(checked) != "docker":
            return None
        return (checked, "context", "inspect", "--format", "{{.Endpoints.docker.Host}}")

    def short(self, image: str) -> str:
        return self._image(image).rpartition(":")[2][:12]

    def _image(self, image: str) -> str:
        if not isinstance(image, str) or not IMAGE_REF.fullmatch(image):
            raise ValueError("the image must be docker.io/searxng/searxng pinned by its digest")
        if image != self._pinned:
            raise ValueError(
                "the image is not the one this vibey pins; `vibey searxng install` updates it"
            )
        return image

    @staticmethod
    def _uid(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("the container runs as your own user, never root")
        return value

    def _runtime(self, runtime: str) -> str:
        if (
            not isinstance(runtime, str)
            or _name(runtime) not in RUNTIMES
            or runtime.rpartition("/")[0] not in self._runtime_dirs
            or re.search(r"[\x00-\x1f\x7f]", runtime)
        ):
            raise ValueError(
                "the runtime must be podman or docker in one of vibey's trusted folders"
            )
        return runtime
