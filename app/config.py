"""Runtime configuration, read from environment variables.

Invalid values fail fast at startup rather than producing wrong quotes later.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class ConfigError(ValueError):
    """Raised when an environment variable holds an unusable value."""


def _decimal(env: Mapping[str, str], name: str, default: str) -> Decimal:
    raw = env.get(name, default)
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc
    if not value.is_finite():
        raise ConfigError(f"{name} must be a finite number, got {raw!r}")
    return value


@dataclass(frozen=True)
class Settings:
    fee_rate: Decimal
    exchange_rate: Decimal
    min_amount: Decimal
    max_amount: Decimal

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        env = os.environ if env is None else env
        settings = cls(
            fee_rate=_decimal(env, "FEE_RATE", "0.02"),
            # Demo rate. In production this would come from a rates provider, not config.
            exchange_rate=_decimal(env, "EXCHANGE_RATE", "655"),
            min_amount=_decimal(env, "MIN_AMOUNT", "1"),
            max_amount=_decimal(env, "MAX_AMOUNT", "10000"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if not Decimal("0") <= self.fee_rate < Decimal("1"):
            raise ConfigError("FEE_RATE must be between 0 and 1 (e.g. 0.02 for 2%)")
        if self.exchange_rate <= 0:
            raise ConfigError("EXCHANGE_RATE must be greater than 0")
        if self.min_amount <= 0:
            raise ConfigError("MIN_AMOUNT must be greater than 0")
        if self.max_amount < self.min_amount:
            raise ConfigError("MAX_AMOUNT must be at least MIN_AMOUNT")
