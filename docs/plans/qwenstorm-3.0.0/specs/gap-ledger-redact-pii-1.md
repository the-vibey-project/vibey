## Title
feat(domain): one pure catalogue of people's private details (emails, phone numbers, street addresses)

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) says "secrets, credentials
and people's private details are redacted where they would appear". SD-01 §1 forbids gathering
or relaying private details such as home addresses and phone numbers. The ledger redactor
matches credential key names and vendor token shapes only
(`src/vibey/infrastructure/ledger/redact.py:17-32`), so an email address, a phone number or a
street address in a payload reaches the append-only `event` table unredacted.

One email pattern already exists, in the domain's publication policy
(`src/vibey/domain/publication_policy.py:156`, `_EMAIL`), which strips addresses from the
public export. Under 10.e a second copy is not written. This lane moves that pattern into one
pure domain module, adds phone and street-address patterns and private-detail key names, and
makes the policy import the pattern from there. The next lane (`gap-ledger-redact-pii-2`)
applies the catalogue in the ledger redactor.

## Required behaviour
1. New module `src/vibey/domain/private_details.py` (pure: `re`, `dataclasses`, `enum`,
   `typing` only; provenance header on line 1). It defines:
   - `class PrivateDetailClass(StrEnum)` with members `EMAIL = "email"`, `PHONE = "phone"`,
     `STREET_ADDRESS = "street-address"`.
   - `@dataclass(frozen=True, slots=True) class PrivateDetailMatch` with fields
     `detail_class: PrivateDetailClass`, `start: int`, `end: int`.
   - `EMAIL_PATTERN: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")`.
     This is exactly the regex at `publication_policy.py:156`, character for character.
   - `PHONE_PATTERNS: Final[tuple[re.Pattern[str], ...]]`, in this order:
     - E.164: `r"(?<![\w+])\+[1-9]\d{7,14}(?!\d)"`;
     - North American: `r"(?<![\w+])(?:\+?1[ .-]?)?(?:\([2-9]\d{2}\)|[2-9]\d{2})[ .-][2-9]\d{2}[ .-]\d{4}(?!\d)"`.
   - `STREET_ADDRESS_PATTERN: Final = re.compile(r"(?<![\w-])\d{1,6}[A-Za-z]?\s+(?:[A-Z][A-Za-z'.-]*\s+){1,4}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl|Terrace|Ter|Circle|Cir|Highway|Hwy|Parkway|Pkwy)\b\.?")`.
     It is case-sensitive, with no `re.IGNORECASE`.
   - `PRIVATE_DETAIL_KEY_NAMES: Final = re.compile(r"^(?:e[_-]?mail|email[_-]?address|author[_-]?email|committer[_-]?email|phone|phone[_-]?number|mobile|telephone|home[_-]?address|street[_-]?address|postal[_-]?address|mailing[_-]?address|postal[_-]?code|postcode|zip[_-]?code)$", re.IGNORECASE)`.
     It is anchored, so `ip_address`, `bind_address`, `emailed_at` and `telemetry` do not match.
   - `DEFAULT_PUBLIC_ADDRESSES: Final[tuple[str, ...]] = (r"^no-?reply@", r"@users\.noreply\.github\.com$", r"^git@")`.
     These are role and transport addresses, not a person's private details.
   - `class PrivateDetailPatterns`, with
     `__init__(self, *, public_addresses: tuple[str, ...] = DEFAULT_PUBLIC_ADDRESSES) -> None`,
     which compiles each entry with `re.IGNORECASE`. It has three methods:
     - `is_private_key(self, key: str) -> bool`: `PRIVATE_DETAIL_KEY_NAMES.match(key) is not None`.
     - `find(self, text: str) -> tuple[PrivateDetailMatch, ...]`: every email match whose
       matched text matches none of the public-address patterns (`re.search`), every phone
       match, and every street-address match. Sort by `(start, -end)`. Then drop any match
       that overlaps an earlier kept one, so the result is non-overlapping and sorted by `start`.
     - `replace(self, text: str, marker: str) -> tuple[str, tuple[PrivateDetailClass, ...]]`:
       replaces each match from `find` with `marker`, working right to left so offsets hold.
       It returns the new text and the classes found, de-duplicated in order of first occurrence.
       With no match it returns `(text, ())` and `text` is unchanged.
   - `PRIVATE_DETAILS: Final[PrivateDetailPatternsInterface] = PrivateDetailPatterns()`.
   - `__all__` listing every public name above.
2. New interface `src/vibey/domain/interfaces/private_details_interface.py`:
   `class PrivateDetailPatternsInterface(Protocol)`, marked `@runtime_checkable`, declaring the
   three methods with the same signatures and one-line docstrings. It imports
   `PrivateDetailClass` and `PrivateDetailMatch` under `TYPE_CHECKING` only (copy the header
   and docstring style of `publication_policy_interface.py:1-13`). Export it from
   `src/vibey/domain/interfaces/__init__.py`, both the import block (beside `:49-56`) and
   `__all__`, in sorted position.
3. `src/vibey/domain/publication_policy.py:156` becomes `_EMAIL: Final = EMAIL_PATTERN`, with
   `from vibey.domain.private_details import EMAIL_PATTERN` added to the imports. Its behaviour
   is unchanged: the public export still strips every address, public ones included, and the
   publication policy's tests pass untouched.
4. No other file changes. The ledger redactor is changed by `gap-ledger-redact-pii-2`.

## Where to change
- New: `src/vibey/domain/private_details.py`; `src/vibey/domain/interfaces/private_details_interface.py`.
- Edit with edit_file: `src/vibey/domain/interfaces/__init__.py` (two insertions);
  `src/vibey/domain/publication_policy.py` (one import line, and line 156).
- New test file: `tests/domain/test_private_details.py`.
- Registry: this is a pure policy with no I/O, and the in-memory implementation is the real
  one. The fakes registry scans application ports only (`specs/fakes-registry.md:93-96`), so
  nothing needs registering.

## Acceptance criteria
- [ ] `PrivateDetailPatterns().find("mail jane.doe@example.org now")` returns one `EMAIL` match
      covering exactly `jane.doe@example.org`.
- [ ] `noreply@anthropic.com`, `No-Reply@example.org`,
      `12345678+vibey-bot@users.noreply.github.com` and `git@github.com` are not private.
      With `PrivateDetailPatterns(public_addresses=())`, `noreply@anthropic.com` is.
- [ ] Phone numbers found: `+14155550132`, `+442071838750`, `(415) 555-0132`, `415-555-0132`,
      `+1 415.555.0132`.
- [ ] Street addresses found: `1600 Pennsylvania Avenue`, `221B Baker Street`, `10 Downing St.`.
- [ ] Nothing is found in any of these: `2026-09-22T15:10:00Z`, `2026-09-22`,
      `550e8400-e29b-41d4-a716-446655440000`, `d3b4a3886f1e2c9b0a7d5e4f3c2b1a0987654321`,
      `3.0.0`, `src/vibey/cli/main.py:1059-1150`, `10.0.0.1`, `port 5432`, `PR #391`,
      `123-456-7890`, `cost 0.0125 usd`, `user@localhost`.
- [ ] `is_private_key` is True for `email`, `Email`, `author_email`, `phone_number`,
      `home_address` and `zip_code`, and False for `ip_address`, `bind_address`, `emailed_at`,
      `telemetry` and `phone_home`.
- [ ] `replace("call +14155550132 or jane@example.org", "[REDACTED]")` returns
      `("call [REDACTED] or [REDACTED]", (PrivateDetailClass.PHONE, PrivateDetailClass.EMAIL))`.
- [ ] `publication_policy._EMAIL is EMAIL_PATTERN`.
- [ ] `tests/domain/test_domain_purity.py` and `tests/domain/test_publication_policy.py` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
Create `tests/domain/test_private_details.py` (provenance header on line 1):
- `test_an_email_is_found_with_its_offsets`
- `test_public_addresses_are_not_private_details`
- `test_the_public_address_list_is_a_constructor_parameter`
- `test_e164_and_north_american_phone_numbers_are_found` (parametrized over the five numbers)
- `test_street_addresses_are_found` (parametrized)
- `test_look_alikes_are_not_private_details` (parametrized over the twelve strings; `find` returns `()`)
- `test_private_detail_key_names_are_anchored` (parametrized true and false cases)
- `test_overlapping_matches_keep_the_earliest_longest`: in `"+1 415.555.0132"` the E.164 and
  North American patterns can both start at `+`; exactly one `PHONE` match covers the whole string.
- `test_replace_reports_classes_in_order_of_first_occurrence`
- `test_replace_without_a_match_returns_the_text_unchanged`
- `test_the_publication_policy_shares_the_email_pattern`
- `test_the_default_patterns_satisfy_their_interface`: `isinstance(PRIVATE_DETAILS, PrivateDetailPatternsInterface)`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Applying the patterns in the ledger redactor or the log processor (`gap-ledger-redact-pii-2`).
- Recording redactions (`gap-ledger-redaction-recorded`).
- Locales beyond the North American phone plan and English street suffixes. Say so in the
  module docstring: the patterns are heuristics, and widening them is a follow-up.
- Docs.

Commit as `feat(domain): one pure catalogue of people's private details`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
