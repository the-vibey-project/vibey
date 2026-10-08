# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sealed copy `vibey state sync` uploads opens in the ledger explorer, byte for byte.

The explorer (docs-src/explorer.ts) downloads `state.vibey` from the `vibey-state` branch and
opens it in the browser with WebCrypto, then recomputes each project's hash chain itself. That
is two implementations of one format (ADR-0086 and src/vibey/domain/ledger_chain.py in Python,
the explorer in TypeScript), so this test makes them agree: it seals a ledger with the real
`AesGcmStateCipher`, opens it with the *compiled* `docs/javascripts/explorer.js` under Node's
WebCrypto, and requires the same hash-chain head Python computed. A wrong key, a changed byte
and a file that is not a sealed state must each be refused, with the reason the page shows.

Everything here is synthetic: a key made for the test and invented events. Node is needed.
Without it a developer's run is skipped; in CI it fails (a check that quietly does not run
reports a success it did not observe).
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest

from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_chain import LEDGER_CHAIN
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.phase import Phase
from vibey.infrastructure.state.aes_gcm_cipher import AesGcmStateCipher

REPO = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")

PROJECT_ID = uuid5(NAMESPACE_URL, "vibey:sealed-state-test")

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), { webcrypto } = require("crypto");
const [, , explorer, sealedPath, keyText, projectId] = process.argv;
const sealed = fs.readFileSync(sealedPath);
const seam = {};
const window = { crypto: webcrypto, __vibeyExplorerTest: seam };
const fetchStub = async (url) => ({
  ok: !url.includes("missing"),
  status: url.includes("missing") ? 404 : 200,
  arrayBuffer: async () => sealed.buffer.slice(sealed.byteOffset, sealed.byteOffset + sealed.byteLength),
});
const document = { getElementById: () => null };
vm.runInNewContext(fs.readFileSync(explorer, "utf8"), {
  window, document, fetch: fetchStub, TextEncoder, Blob, Response, DecompressionStream, atob, URLSearchParams, console,
});
(async () => {
  const out = {};
  const attempt = async (name, run) => {
    try { await run(); out[name] = "opened"; } catch (e) { out[name] = e.failure ?? String(e.message); }
  };
  const vault = new seam.SealedVault();
  await attempt("good", () => vault.open("https://x/state.vibey", keyText));
  if (out.good === "opened") {
    out.listing = vault.listing();
    const ledger = vault.ledger(projectId);
    out.records = ledger.records.length;
    out.newest = ledger.records[0].seq;
    out.chain = await vault.chain(projectId);
    const first = ledger.records[ledger.records.length - 1];
    out.neighbour = ledger.docs.get(first.id).next.seq;
    out.search = ledger.records.filter((r) => r.tokens.includes("shifts")).length;
  }
  const other = Buffer.alloc(32, 7).toString("base64url");
  await attempt("wrongKey", () => new seam.SealedVault().open("https://x/state.vibey", other));
  await attempt("notAKey", () => new seam.SealedVault().open("https://x/state.vibey", "not a key"));
  await attempt("missing", () => new seam.SealedVault().open("https://x/missing", keyText));
  console.log(JSON.stringify(out));
})();
"""


def _events() -> list[LedgerEvent]:
    start = datetime(2026, 8, 19, 8, 24, 0, 123456, tzinfo=UTC)
    shapes: list[tuple[EventKind, Phase, dict[str, object], EngineId | None]] = [
        (
            EventKind.SESSION_SEEDED,
            Phase.INTAKE,
            {"prompt": "A page for volunteers to pick shifts"},
            None,
        ),
        (
            EventKind.QUESTION_ASKED,
            Phase.DESIGN,
            {"text": "Can a volunteer cancel shifts?", "n": 3},
            None,
        ),
        (
            EventKind.DECISION_RECORDED,
            Phase.DESIGN,
            {"title": "Café ☕ storage", "choice": "sqlite"},
            None,
        ),
        (
            EventKind.TURN_COMPLETED,
            Phase.BUILD,
            {"tokens": 4120, "ok": True, "note": None},
            EngineId.GPTOSSLOOP,
        ),
        (
            EventKind.BUDGET_SPENT,
            Phase.BUILD,
            # The numbers a digest is sensitive to. Python writes 1.0 and 1e-05; Postgres' jsonb
            # spells the second 0.00001. Both must hash as Python's text, which `JSON.parse`
            # alone does not reproduce (it turns 1.0 into 1 and 1e-05 into 0.00001).
            {
                "usd": 0.1,
                "whole": 1.0,
                "tiny": 0.00001,
                "ratio": 2.5,
                "big": 123456789012345678901,
                "n": 3,
            },
            None,
        ),
    ]
    events: list[LedgerEvent] = []
    for seq, (kind, phase, payload, engine) in enumerate(shapes, start=1):
        events.append(
            LedgerEvent(
                event_id=uuid5(PROJECT_ID, f"event:{seq}"),
                project_id=PROJECT_ID,
                cycle=1,
                phase=phase,
                seq=seq,
                kind=kind,
                engine_id=engine,
                job_id=None,
                causation_id=events[-1].event_id if events else None,
                correlation_id=uuid5(PROJECT_ID, "run"),
                provenance=Provenance.TRUSTED,
                # Whole seconds on odd events, a full fraction on even ones, so both the padded
                # and the unpadded timestamp forms are hashed.
                produced_at=(start + timedelta(minutes=seq)).replace(
                    microsecond=0 if seq % 2 else 654321
                ),
                payload=payload,
                digest=digest_event(payload),
            )
        )
    return events


def _document(events: list[LedgerEvent], *, postgres_style: bool = False) -> bytes:
    document = {
        "format": "vibey-state/1",
        "schema": ["0001_init"],
        "tables": {
            "project": [
                {
                    "id": str(PROJECT_ID),
                    "name": "shift-signup",
                    "phase": "build",
                    "created_at": "2026-08-19T08:00:00+00:00",
                    "updated_at": "2026-08-19T09:00:00+00:00",
                }
            ],
            "event": [LEDGER_RECORDS.to_fields(event) for event in events],
        },
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    if postgres_style:
        # jsonb prints a numeric without an exponent, so the state document carries 0.00001.
        assert text.count("1e-05") == 1
        text = text.replace("1e-05", "0.00001")
    return text.encode()


def _run(tmp_path: Path, sealed: bytes, key: str) -> dict[str, object]:
    explorer = REPO / "docs" / "javascripts" / "explorer.js"
    sealed_path = tmp_path / "state.vibey"
    sealed_path.write_bytes(sealed)
    driver = tmp_path / "driver.js"
    driver.write_text(DRIVER, encoding="utf-8")
    done = subprocess.run(  # noqa: S603 -- node, running a driver this test just wrote
        [str(NODE), str(driver), str(explorer), str(sealed_path), key, str(PROJECT_ID)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(done.stdout)


@pytest.fixture
def node_available() -> None:
    if NODE is None:
        if os.environ.get("CI"):
            pytest.fail(
                "node is missing in CI: the explorer's sealed-state reader cannot be tested"
            )
        pytest.skip("node is not installed here")


@pytest.mark.parametrize("postgres_style", [False, True], ids=["python-text", "jsonb-text"])
def test_the_explorer_opens_what_the_python_cipher_sealed(
    tmp_path: Path, node_available: None, postgres_style: bool
) -> None:
    raw = secrets.token_bytes(32)
    key = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    events = _events()
    sealed = AesGcmStateCipher(raw).seal(_document(events, postgres_style=postgres_style))

    got = _run(tmp_path, sealed, key)

    assert got["good"] == "opened"
    assert got["listing"] == [
        {
            "id": str(PROJECT_ID),
            "name": "shift-signup",
            "phase": "build",
            "events": 5,
            "updated": "2026-08-19T09:00:00+00:00",
        }
    ]
    assert got["records"] == 5 and got["newest"] == 5 and got["neighbour"] == 2
    assert got["search"] == 2  # "shifts" is a word of the seed prompt and of the question
    verification = LEDGER_CHAIN.verify(PROJECT_ID, events)
    assert verification.findings == ()
    chain = got["chain"]
    assert isinstance(chain, dict)
    assert chain["ok"] is True, chain
    assert chain["head"] == verification.head, "the browser's hash chain must equal Python's"


def test_a_wrong_key_a_changed_byte_and_a_foreign_file_are_each_refused(
    tmp_path: Path, node_available: None
) -> None:
    raw = secrets.token_bytes(32)
    key = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    sealed = bytearray(AesGcmStateCipher(raw).seal(_document(_events())))

    got = _run(tmp_path, bytes(sealed), key)
    assert got["wrongKey"] == "key"
    assert got["notAKey"] == "key"
    assert got["missing"] == "missing"

    sealed[-1] ^= 1  # one bit of the authentication tag
    assert _run(tmp_path, bytes(sealed), key)["good"] == "key"

    assert _run(tmp_path, b"hello, this is not a sealed state at all", key)["good"] == "format"
