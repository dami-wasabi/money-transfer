# Money Transfer Quote Service

[![CI](https://github.com/dami-wasabi/money-transfer/actions/workflows/ci.yml/badge.svg)](https://github.com/dami-wasabi/money-transfer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![Container](https://img.shields.io/badge/image-ghcr.io-2496ED?logo=docker&logoColor=white)

A small Flask web service that tells someone sending money from the US to Cameroon exactly what they'll pay and what their family will receive, in Central African francs (XAF).

The application is deliberately simple. The point of the repository is everything around it: correct money handling, input validation, a hardened container, and a CI pipeline that tests, scans and publishes the image on every merge. It's the sample workload I deploy in my Kubernetes and GitOps projects.

![Quote page](docs/screenshot.png)

## What it does

| | |
|---|---|
| **Web page** `GET /` | Enter a USD amount and get the fee, the total to pay, the exchange rate and the amount received |
| **API** `POST /api/quote` | Same calculation as JSON, for other services |
| **Health check** `GET /healthz` | Used by the container `HEALTHCHECK` and, later, Kubernetes probes |

```bash
$ curl -s -X POST localhost:8000/api/quote -H 'Content-Type: application/json' -d '{"amount": "250.50"}'
{
  "send_amount": "250.50",
  "fee": "5.01",
  "total_to_pay": "255.51",
  "exchange_rate": "655",
  "receive_amount": "164077",
  "send_currency": "USD",
  "receive_currency": "XAF"
}
```

Invalid input gets a `422` with a readable message (`"The minimum transfer is $1.00."`), and every `/api/*` error is returned as JSON, never as an HTML error page.

> **Note:** the exchange rate comes from configuration, not a live market feed. The page says so.

## Engineering decisions

**Money is never a float.** Every calculation uses Python's `Decimal`. Floats can't represent most cent values exactly: 2% of $10.25 is $0.205, which as a float rounds the wrong way. The fee rounds half-up to the cent. The received amount rounds *down* to a whole franc, so the service never promises more than is paid out. Amounts travel through the API as strings for the same reason.

**Validate everything at the boundary.** Amounts must be numeric, finite, positive, have at most two decimal places, and fall within configured limits. Request bodies over 1 KB are rejected outright.

**Fail fast on bad configuration.** `FEE_RATE`, `EXCHANGE_RATE`, `MIN_AMOUNT` and `MAX_AMOUNT` are read from the environment and validated at startup. A typo like `FEE_RATE=2` (meaning 200%) stops the container from starting instead of producing wrong quotes.

**Secure by default.** The app sends a strict Content-Security-Policy, `X-Content-Type-Options`, `X-Frame-Options` and `Referrer-Policy` headers. The page has no inline scripts or styles, so the CSP doesn't need `unsafe-inline`.

## Container

The image runs under **gunicorn** (not Flask's development server), as a **non-root user** (UID 10001), with a built-in **HEALTHCHECK**. It also works on a **read-only root filesystem**; CI runs it read-only with all Linux capabilities dropped. Dependencies are installed in their own layer, so code-only changes rebuild in seconds.

```bash
docker compose up --build      # http://localhost:8000
```

`docker-compose.yml` applies the same hardening locally: read-only filesystem, `no-new-privileges`, all capabilities dropped.

## CI pipeline

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every push and pull request:

| Stage | What it checks |
|---|---|
| **Lint and test** | `ruff` lint and format check · `pytest` with **42 tests**, failing the build under 95% coverage (currently 100%) |
| **Dockerfile lint** | `hadolint` |
| **Build and smoke test** | Builds the image, runs it read-only with no capabilities, calls `/healthz` and `/api/quote`, and asserts it runs as non-root |
| **Vulnerability scan** | **Trivy** fails the build on any fixable CRITICAL or HIGH vulnerability in the image |
| **Publish** | On merge to `main` only, pushes to **GitHub Container Registry**, tagged with the commit SHA and `latest` |

Third-party actions are pinned to full commit SHAs rather than tags, so a compromised or moved tag can't change what runs in the pipeline.

## Run it locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

python -m pytest                  # tests + coverage report
flask --app app run --debug       # http://localhost:5000
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `FEE_RATE` | `0.02` | Fee as a fraction of the amount (0.02 = 2%) |
| `EXCHANGE_RATE` | `655` | XAF per USD |
| `MIN_AMOUNT` | `1` | Smallest transfer in USD |
| `MAX_AMOUNT` | `10000` | Largest transfer in USD |

## Project layout

```
.
├── app/
│   ├── __init__.py        # app factory, routes, security headers, JSON errors
│   ├── quote.py           # validation + Decimal money maths (no Flask imports)
│   ├── config.py          # environment config, validated at startup
│   ├── templates/index.html
│   └── static/            # CSS + JS (no inline code, CSP-friendly)
├── tests/                 # 42 tests: money maths, validation, config, HTTP API
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Roadmap

- Helm chart, deployed to EKS by Argo CD from a separate GitOps repository
- Image signing with Cosign and an SBOM attached to each published image
- Live exchange rates from a provider, cached with a short TTL
- Prometheus metrics (`/metrics`) for request latency and quote volume
