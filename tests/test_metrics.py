from decimal import Decimal

import pytest
from prometheus_client import REGISTRY

from app import create_app
from app.config import ConfigError, Settings


def make_client(**overrides):
    values = {
        "fee_rate": Decimal("0.02"),
        "exchange_rate": Decimal("655"),
        "min_amount": Decimal("1"),
        "max_amount": Decimal("10000"),
    }
    values.update(overrides)
    app = create_app(Settings(**values))
    app.testing = True
    return app.test_client()


def sample(name, **labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


def test_metrics_endpoint_exposes_prometheus_format():
    client = make_client()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b"http_requests_total" in response.data
    assert b"http_request_duration_seconds_bucket" in response.data


def test_requests_counted_by_route_template_and_status():
    client = make_client()
    ok_before = sample("http_requests_total", method="POST", route="/api/quote", status="200")
    bad_before = sample("http_requests_total", method="POST", route="/api/quote", status="422")

    client.post("/api/quote", json={"amount": "100"})
    client.post("/api/quote", json={"amount": "-1"})

    assert sample("http_requests_total", method="POST", route="/api/quote", status="200") == ok_before + 1
    assert sample("http_requests_total", method="POST", route="/api/quote", status="422") == bad_before + 1


def test_latency_histogram_observed():
    client = make_client()
    before = sample("http_request_duration_seconds_count", method="POST", route="/api/quote")
    client.post("/api/quote", json={"amount": "100"})
    assert sample("http_request_duration_seconds_count", method="POST", route="/api/quote") == before + 1


def test_unknown_paths_share_one_label():
    client = make_client()
    before = sample("http_requests_total", method="GET", route="unmatched", status="404")
    client.get("/random-scanner-path-1")
    client.get("/random-scanner-path-2")
    assert sample("http_requests_total", method="GET", route="unmatched", status="404") == before + 2


def test_probes_and_scrapes_not_counted():
    client = make_client()
    before = sample("http_requests_total", method="GET", route="/healthz", status="200")
    client.get("/healthz")
    client.get("/metrics")
    assert sample("http_requests_total", method="GET", route="/healthz", status="200") == before
    assert sample("http_requests_total", method="GET", route="/metrics", status="200") == 0


def test_quotes_issued_counter():
    client = make_client()
    before = sample("quotes_issued_total")
    client.post("/api/quote", json={"amount": "50"})
    client.post("/api/quote", json={"amount": "abc"})  # rejected, not issued
    assert sample("quotes_issued_total") == before + 1


class TestFaultInjection:
    def test_off_by_default(self):
        assert Settings.from_env({}).faults_enabled is False

    def test_error_rate_one_fails_every_quote(self):
        client = make_client(fault_error_rate=Decimal("1"))
        before = sample("faults_injected_total", kind="error")
        response = client.post("/api/quote", json={"amount": "100"})
        assert response.status_code == 503
        assert "temporarily unavailable" in response.get_json()["error"]
        assert sample("faults_injected_total", kind="error") == before + 1

    def test_injected_errors_count_against_the_sli(self):
        client = make_client(fault_error_rate=Decimal("1"))
        before = sample("http_requests_total", method="POST", route="/api/quote", status="503")
        client.post("/api/quote", json={"amount": "100"})
        assert sample("http_requests_total", method="POST", route="/api/quote", status="503") == before + 1

    def test_other_routes_unaffected(self):
        client = make_client(fault_error_rate=Decimal("1"))
        assert client.get("/healthz").status_code == 200
        assert client.get("/").status_code == 200

    def test_latency_injection(self, monkeypatch):
        slept = []
        monkeypatch.setattr("app.time.sleep", slept.append)
        client = make_client(fault_latency_ms=Decimal("250"))
        assert client.post("/api/quote", json={"amount": "100"}).status_code == 200
        assert slept == [0.25]

    def test_startup_warning_when_enabled(self, caplog):
        make_client(fault_error_rate=Decimal("0.1"))
        assert "FAULT INJECTION ENABLED" in caplog.text

    @pytest.mark.parametrize(
        "env",
        [
            {"FAULT_ERROR_RATE": "1.5"},
            {"FAULT_ERROR_RATE": "-0.1"},
            {"FAULT_LATENCY_MS": "-1"},
            {"FAULT_LATENCY_MS": "60000"},
        ],
    )
    def test_rejects_bad_fault_config(self, env):
        with pytest.raises(ConfigError):
            Settings.from_env(env)


def test_multiprocess_mode_reads_from_the_shared_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("PROMETHEUS_MULTIPROC_DIR", str(tmp_path))
    response = make_client().get("/metrics")
    assert response.status_code == 200  # empty directory: valid, just no samples yet
