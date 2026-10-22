# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PROMETHEUS_MULTIPROC_DIR=/dev/shm/prometheus

WORKDIR /app

# Dependencies first so this layer is cached when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gunicorn.conf.py .
COPY app/ app/

# Run as an unprivileged user, never root.
RUN useradd --system --no-create-home --uid 10001 appuser
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
