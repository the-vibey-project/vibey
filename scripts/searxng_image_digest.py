# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SearXNG image vibey runs, refreshed by hand and reviewed before it is pinned (ADR-0102).

    python scripts/searxng_image_digest.py            # print the current `latest` digest
    python scripts/searxng_image_digest.py --tag TAG  # another tag's

vibey never runs a SearXNG image named by a tag, a setting or a project: the image is the
reviewed constant `SEARXNG_IMAGE` in `src/vibey/domain/searxng.py`, pinned by digest. This
script is how that constant is refreshed. It asks Docker Hub's read-only registry API, as
anyone may, with no credentials: an anonymous pull token, then a `HEAD` of the tag's manifest,
whose `Docker-Content-Digest` header is the digest of the multi-platform index (the one value
that names the same image on every machine). It prints the line to paste, with the date it was
read. A person reviews the change (the upstream release notes for that date) and commits it;
nothing pins a digest on its own, and no test calls the network (the format is pinned by
`tests/domain/test_searxng.py`).

Standard library only, so it runs anywhere Python does.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

try:
    from scripts.interfaces.searxng_image_digest_interface import RegistryDigestInterface
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.searxng_image_digest_interface import (  # type: ignore[import-not-found,no-redef]
        RegistryDigestInterface,
    )

REPOSITORY = "searxng/searxng"
TOKEN_URL = "https://auth.docker.io/token"
REGISTRY = "https://registry-1.docker.io"
ACCEPT = ", ".join(
    (
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    )
)
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
TIMEOUT_SECONDS = 30


class RegistryDigest:
    """Declared by `RegistryDigestInterface`. `open_url` is the network seam."""

    def __init__(self, open_url: Callable[..., Any] = urllib.request.urlopen) -> None:
        self._open = open_url

    def digest(self, repository: str, tag: str) -> str:
        query = urllib.parse.urlencode(
            {"service": "registry.docker.io", "scope": f"repository:{repository}:pull"}
        )
        with self._open(f"{TOKEN_URL}?{query}", timeout=TIMEOUT_SECONDS) as answer:  # nosec B310
            token = json.loads(answer.read(1 << 16)).get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("the registry gave no anonymous pull token")
        request = urllib.request.Request(  # nosec B310 - a fixed https registry
            f"{REGISTRY}/v2/{repository}/manifests/{urllib.parse.quote(tag, safe='')}",
            method="HEAD",
            headers={"Authorization": f"Bearer {token}", "Accept": ACCEPT},
        )
        with self._open(request, timeout=TIMEOUT_SECONDS) as answer:
            found = answer.headers.get("Docker-Content-Digest", "")
        if not DIGEST.fullmatch(found):
            raise RuntimeError(f"the registry answered no sha256 digest for {repository}:{tag}")
        return str(found)


def main(argv: Sequence[str] | None = None, registry: RegistryDigestInterface | None = None) -> int:
    """Print the pinned reference for a tag."""
    # Module-level function because it is the script's command-line entry point.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else None)
    parser.add_argument("--tag", default="latest", help="the tag to read (default: latest)")
    args = parser.parse_args(argv)
    try:
        digest = (registry or RegistryDigest()).digest(REPOSITORY, args.tag)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"could not read {REPOSITORY}:{args.tag}: {exc}", file=sys.stderr)
        return 1
    today = datetime.datetime.now(datetime.UTC).date().isoformat()
    print(f'SEARXNG_IMAGE: Final = "docker.io/{REPOSITORY}@{digest}"')
    print(f"# read {today} from {REGISTRY} ({REPOSITORY}:{args.tag}, anonymous HEAD)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
