"""Gunicorn settings for the container image."""

import os
import shutil

from prometheus_client import multiprocess

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
# The root filesystem is read-only; /dev/shm is a writable in-memory mount.
worker_tmp_dir = "/dev/shm"  # noqa: S108 - in-memory mount inside the container, not a shared host path
accesslog = "-"


def on_starting(server):
    # Start every pod with empty metric files so counters don't carry over a restart.
    path = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if path:
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path, exist_ok=True)


def child_exit(server, worker):
    # Drop a dead worker's live gauges; its counters are kept so totals never go backwards.
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.mark_process_dead(worker.pid)
