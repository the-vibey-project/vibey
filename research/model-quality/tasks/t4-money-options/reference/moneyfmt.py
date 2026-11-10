"""Format integer cents as a money string."""

from __future__ import annotations

from dataclasses import dataclass

SYMBOLS = {"USD": "$", "EUR": "€", "GBP": "£"}


@dataclass(frozen=True)
class MoneyFormat:
    """How to render money. Validation happens in format_amount, not here."""

    currency: str = "USD"
    symbol: bool = True
    thousands: str = ","
    decimals: int = 2
    negative_style: str = "minus"
    width: int = 0


def format_amount(amount_cents: int, options: MoneyFormat | None = None) -> str:
    """Render amount_cents. 123456 -> "$1,234.56"; -123456 with negative_style="parens" -> "($1,234.56)"."""
    opts = options if options is not None else MoneyFormat()
    if opts.decimals not in (0, 1, 2):
        raise ValueError("decimals must be 0, 1 or 2")
    if opts.negative_style not in ("minus", "parens"):
        raise ValueError("negative_style must be 'minus' or 'parens'")

    negative = amount_cents < 0
    scale = 10 ** (2 - opts.decimals)
    units = (abs(amount_cents) + scale // 2) // scale
    whole, frac = divmod(units, 10**opts.decimals)

    digits = f"{whole:,}".replace(",", opts.thousands)
    point = "," if opts.thousands == "." else "."
    body = digits
    if opts.decimals:
        body += point + str(frac).zfill(opts.decimals)

    code = opts.currency.upper()
    if opts.symbol:
        body = SYMBOLS[code] + body if code in SYMBOLS else code + " " + body
    else:
        body = body + " " + code

    if negative:
        body = "-" + body if opts.negative_style == "minus" else "(" + body + ")"
    return body.rjust(opts.width)


def format_money(
    amount_cents: int,
    currency: str = "USD",
    symbol: bool = True,
    thousands: str = ",",
    decimals: int = 2,
    negative_style: str = "minus",
    width: int = 0,
) -> str:
    """The original call form: the same arguments in the same order, now building a MoneyFormat."""
    options = MoneyFormat(currency, symbol, thousands, decimals, negative_style, width)
    return format_amount(amount_cents, options)
