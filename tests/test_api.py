from decimal import Decimal

import pytest

from app import create_app
from app.config import Settings


@pytest.fixture
def client():
    settings = Settings(
        fee_rate=Decimal("0.02"),
        exchange_rate=Decimal("655"),
        min_amount=Decimal("1"),
        max_amount=Decimal("10000"),
    )
    app = create_app(settings)
    app.testing = True
    return app.test_client()


def test_index_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Money Transfer Quote" in response.data
    assert b"Transfer fee (2%)" in response.data


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_quote_success(client):
    response = client.post("/api/quote", json={"amount": "100"})
    assert response.status_code == 200
    assert response.get_json() == {
        "send_currency": "USD",
        "receive_currency": "XAF",
        "send_amount": "100.00",
        "fee": "2.00",
        "total_to_pay": "102.00",
        "exchange_rate": "655",
        "receive_amount": "65500",
    }


@pytest.mark.parametrize(("amount", "fragment"), [("-5", "minimum"), ("abc", "number"), ("99999", "maximum")])
def test_quote_validation_errors(client, amount, fragment):
    response = client.post("/api/quote", json={"amount": amount})
    assert response.status_code == 422
    assert fragment in response.get_json()["error"]


def test_quote_requires_json_object(client):
    assert client.post("/api/quote", data="amount=100").status_code == 400
    assert client.post("/api/quote", json=["100"]).status_code == 400


def test_api_errors_are_json(client):
    response = client.get("/api/quote")  # wrong method
    assert response.status_code == 405
    assert "error" in response.get_json()


def test_oversized_body_rejected(client):
    response = client.post("/api/quote", json={"amount": "1" * 5000})
    assert response.status_code == 413


def test_non_api_404_is_not_json(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.content_type.startswith("text/html")


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
