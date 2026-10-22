"""Transfer quote calculation.

Money is handled with Decimal throughout. Binary floats cannot represent most
cent values exactly (0.1 + 0.2 != 0.3), which is not acceptable for amounts a
customer is charged.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
WHOLE = Decimal("1")


class QuoteError(ValueError):
    """Raised when a requested amount cannot be quoted."""


@dataclass(frozen=True)
class Quote:
    send_amount: Decimal  # USD the recipient's money is based on
    fee: Decimal  # USD fee charged on top
    total_to_pay: Decimal  # USD the sender pays
    exchange_rate: Decimal  # XAF per USD
    receive_amount: Decimal  # XAF the recipient gets

    def as_dict(self) -> dict[str, str]:
        # Serialised as strings so JSON clients never round-trip money through floats.
        return {
            "send_currency": "USD",
            "receive_currency": "XAF",
            "send_amount": str(self.send_amount),
            "fee": str(self.fee),
            "total_to_pay": str(self.total_to_pay),
            "exchange_rate": str(self.exchange_rate),
            "receive_amount": str(self.receive_amount),
        }


def parse_amount(raw: object, minimum: Decimal, maximum: Decimal) -> Decimal:
    """Validate a user-supplied USD amount and normalise it to cents."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise QuoteError("Enter an amount to send.")
    if isinstance(raw, bool):  # bool is a subclass of int; reject it explicitly
        raise QuoteError("Amount must be a number.")
    try:
        amount = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise QuoteError("Amount must be a number.") from exc

    if not amount.is_finite():
        raise QuoteError("Amount must be a number.")
    if amount != amount.quantize(CENT):
        raise QuoteError("Amount can have at most two decimal places.")
    if amount < minimum:
        raise QuoteError(f"The minimum transfer is ${minimum:,.2f}.")
    if amount > maximum:
        raise QuoteError(f"The maximum transfer is ${maximum:,.2f}.")
    return amount.quantize(CENT)


def build_quote(amount: Decimal, fee_rate: Decimal, exchange_rate: Decimal) -> Quote:
    """Price a transfer of `amount` USD.

    The fee is added on top of the amount, so the recipient receives the full
    converted amount. XAF has no minor unit in everyday use, so the received
    amount is rounded down to a whole franc - we never promise more than is paid out.
    """
    fee = (amount * fee_rate).quantize(CENT, rounding=ROUND_HALF_UP)
    return Quote(
        send_amount=amount,
        fee=fee,
        total_to_pay=amount + fee,
        exchange_rate=exchange_rate,
        receive_amount=(amount * exchange_rate).quantize(WHOLE, rounding=ROUND_DOWN),
    )
