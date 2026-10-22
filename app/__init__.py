"""Flask application factory.

Run locally:      flask --app app run --debug
Run in a container: gunicorn "app:create_app()"  (see Dockerfile)
"""

from __future__ import annotations

import logging
import random
import time

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from . import metrics
from .config import Settings
from .quote import QuoteError, build_quote, parse_amount

# The page only loads its web font from Google Fonts; everything else is same-origin.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
)


def create_app(settings: Settings | None = None) -> Flask:
    app = Flask(__name__)
    settings = settings or Settings.from_env()
    app.config["SETTINGS"] = settings
    app.config["MAX_CONTENT_LENGTH"] = 1024  # quote requests are tiny; reject anything larger

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log = logging.getLogger("money_transfer")
    if settings.faults_enabled:
        log.warning(
            "FAULT INJECTION ENABLED: error_rate=%s latency_ms=%s - for chaos experiments only",
            settings.fault_error_rate,
            settings.fault_latency_ms,
        )

    metrics.init_app(app)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            fee_percent=f"{(settings.fee_rate * 100).normalize():f}",
            min_amount=settings.min_amount,
            max_amount=settings.max_amount,
        )

    @app.post("/api/quote")
    def quote():
        if settings.fault_latency_ms:
            metrics.FAULTS_INJECTED.labels("latency").inc()
            time.sleep(float(settings.fault_latency_ms) / 1000)
        # Not security-sensitive randomness, just a coin flip for the chaos experiment.
        if settings.fault_error_rate and random.random() < float(settings.fault_error_rate):  # noqa: S311
            metrics.FAULTS_INJECTED.labels("error").inc()
            return jsonify(error="Service temporarily unavailable. Please try again."), 503

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error='Send a JSON body like {"amount": "100.00"}.'), 400
        try:
            amount = parse_amount(payload.get("amount"), settings.min_amount, settings.max_amount)
        except QuoteError as exc:
            return jsonify(error=str(exc)), 422

        result = build_quote(amount, settings.fee_rate, settings.exchange_rate)
        metrics.QUOTES_ISSUED.inc()
        log.info("quote send_amount=%s total_to_pay=%s", result.send_amount, result.total_to_pay)
        return jsonify(result.as_dict())

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        # Keep API errors machine-readable; fall back to Flask's HTML page elsewhere.
        if request.path.startswith("/api/"):
            return jsonify(error=exc.description), exc.code
        return exc

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        return response

    return app
