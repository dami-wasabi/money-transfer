"""Prometheus metrics.

These are the service level indicators (SLIs) the platform's SLO is built on:
the request counter gives availability (share of non-5xx responses) and the
latency histogram gives the share of requests served under the threshold.

Gunicorn runs several worker processes, each with its own memory. When
PROMETHEUS_MULTIPROC_DIR is set (it is in the container image), every worker
writes its samples to files in that directory and /metrics aggregates them,
so a scrape sees the whole pod rather than whichever worker answered it.
"""

from __future__ import annotations

import os
import time

from flask import Flask, Response, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)

# Bucket edges include the SLO latency threshold (0.3s) so it can be queried exactly.
LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.5, 5.0)

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by route template and status code.",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Time spent handling HTTP requests.",
    ["method", "route"],
    buckets=LATENCY_BUCKETS,
)
QUOTES_ISSUED = Counter("quotes_issued_total", "Successful transfer quotes returned.")
FAULTS_INJECTED = Counter(
    "faults_injected_total", "Requests failed or delayed on purpose by chaos settings.", ["kind"]
)

# Not worth measuring: Prometheus scraping itself and kubelet probes.
_UNTRACKED_ROUTES = {"/metrics", "/healthz"}


def _route_label() -> str:
    # The route *template* (e.g. "/api/quote"), never the raw path, so a scanner
    # requesting thousands of random URLs can't create thousands of time series.
    return request.url_rule.rule if request.url_rule else "unmatched"


def init_app(app: Flask) -> None:
    @app.before_request
    def _start_timer():
        g.request_started = time.perf_counter()

    @app.after_request
    def _record(response):
        route = _route_label()
        if route not in _UNTRACKED_ROUTES:
            started = g.get("request_started")
            if started is not None:
                HTTP_LATENCY.labels(request.method, route).observe(time.perf_counter() - started)
            HTTP_REQUESTS.labels(request.method, route, str(response.status_code)).inc()
        return response

    @app.get("/metrics")
    def metrics():
        if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            registry = REGISTRY
        return Response(generate_latest(registry), mimetype=CONTENT_TYPE_LATEST)
