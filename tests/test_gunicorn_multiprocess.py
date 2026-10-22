"""Integration test: metrics must aggregate across gunicorn worker processes.

Each worker keeps its own counters; without multiprocess mode a scrape would
only see whichever worker answered it, and request totals would jump around.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _scrape_total(base_url: str) -> float:
    text = urllib.request.urlopen(f"{base_url}/metrics", timeout=5).read().decode()  # noqa: S310
    for line in text.splitlines():
        if (
            line.startswith("http_requests_total{")
            and 'route="/api/quote"' in line
            and 'status="200"' in line
        ):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


@pytest.fixture
def gunicorn_server(tmp_path):
    port = _free_port()
    env = {**os.environ, "PROMETHEUS_MULTIPROC_DIR": str(tmp_path / "prom"), "GUNICORN_WORKERS": "3"}
    proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
        [
            sys.executable,
            "-m",
            "gunicorn",
            "--config",
            str(ROOT / "gunicorn.conf.py"),
            "--bind",
            f"127.0.0.1:{port}",
            "--worker-tmp-dir",
            str(tmp_path),
            "app:create_app()",
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(f"{base_url}/healthz", timeout=1)  # noqa: S310
            break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail("gunicorn did not start")
    yield base_url
    proc.terminate()
    proc.wait(timeout=10)


def test_counts_from_every_worker_are_aggregated(gunicorn_server):
    body = json.dumps({"amount": "100"}).encode()
    for _ in range(30):
        req = urllib.request.Request(  # noqa: S310
            f"{gunicorn_server}/api/quote", data=body, headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)  # noqa: S310

    # Repeated scrapes land on different workers; each must report the same full total.
    totals = {_scrape_total(gunicorn_server) for _ in range(10)}
    assert totals == {30.0}
