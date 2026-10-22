from decimal import Decimal

import pytest

from app.config import ConfigError, Settings
from app.quote import QuoteError, build_quote, parse_amount

MIN = Decimal("1")
MAX = Decimal("10000")


class TestParseAmount:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("100", Decimal("100.00")),
            ("100.5", Decimal("100.50")),
            (" 25.75 ", Decimal("25.75")),
            (42, Decimal("42.00")),
            ("1", Decimal("1.00")),
            ("10000", Decimal("10000.00")),
        ],
    )
    def test_valid_amounts(self, raw, expected):
        assert parse_amount(raw, MIN, MAX) == expected

    @pytest.mark.parametrize(
        ("raw", "message"),
        [
            (None, "Enter an amount"),
            ("", "Enter an amount"),
            ("   ", "Enter an amount"),
            ("abc", "must be a number"),
            ("NaN", "must be a number"),
            ("Infinity", "must be a number"),
            (True, "must be a number"),
            ("10.001", "two decimal places"),
            ("0.99", "minimum"),
            ("-50", "minimum"),
            ("10000.01", "maximum"),
        ],
    )
    def test_rejects_invalid_amounts(self, raw, message):
        with pytest.raises(QuoteError, match=message):
            parse_amount(raw, MIN, MAX)


class TestBuildQuote:
    def test_standard_quote(self):
        q = build_quote(Decimal("100.00"), Decimal("0.02"), Decimal("655"))
        assert q.fee == Decimal("2.00")
        assert q.total_to_pay == Decimal("102.00")
        assert q.receive_amount == Decimal("65500")

    def test_fee_rounds_half_up_to_the_cent(self):
        # 2% of 10.25 is 0.205 -> 0.21 (a float would give 0.20499999...)
        q = build_quote(Decimal("10.25"), Decimal("0.02"), Decimal("655"))
        assert q.fee == Decimal("0.21")
        assert q.total_to_pay == Decimal("10.46")

    def test_received_amount_rounds_down_to_whole_francs(self):
        q = build_quote(Decimal("1.01"), Decimal("0.02"), Decimal("655.5"))
        assert q.receive_amount == Decimal("662")  # 662.055 -> 662, never rounded up

    def test_no_float_drift(self):
        q = build_quote(Decimal("0.30"), Decimal("0.10"), Decimal("1"))
        assert q.fee == Decimal("0.03")
        assert q.total_to_pay == Decimal("0.33")

    def test_serialises_money_as_strings(self):
        data = build_quote(Decimal("100.00"), Decimal("0.02"), Decimal("655")).as_dict()
        assert data["total_to_pay"] == "102.00"
        assert all(isinstance(v, str) for v in data.values())


class TestSettings:
    def test_defaults(self):
        s = Settings.from_env({})
        assert s.fee_rate == Decimal("0.02")
        assert s.exchange_rate == Decimal("655")

    def test_reads_environment(self):
        s = Settings.from_env({"FEE_RATE": "0.015", "EXCHANGE_RATE": "600"})
        assert s.fee_rate == Decimal("0.015")
        assert s.exchange_rate == Decimal("600")

    @pytest.mark.parametrize(
        "env",
        [
            {"FEE_RATE": "abc"},
            {"FEE_RATE": "1.5"},
            {"FEE_RATE": "-0.01"},
            {"EXCHANGE_RATE": "0"},
            {"EXCHANGE_RATE": "inf"},
            {"MIN_AMOUNT": "0"},
            {"MIN_AMOUNT": "100", "MAX_AMOUNT": "50"},
        ],
    )
    def test_rejects_bad_config(self, env):
        with pytest.raises(ConfigError):
            Settings.from_env(env)
