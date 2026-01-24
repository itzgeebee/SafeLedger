import logging
import time
from typing import Optional

logger = logging.getLogger("safeledger.observability")

# Optional Prometheus integration: create metrics on demand so tests can run
# even when prometheus_client is not installed. Metrics are created lazily.
_prometheus_available = False
_metrics_registry = {}

try:
    from prometheus_client import Counter, Histogram, start_http_server

    _prometheus_available = True
except Exception:
    _prometheus_available = False


def _sanitize_metric_name(name: str) -> str:
    return name.replace(".", "_").replace("-", "_")


def record_metric(name: str, value: int = 1, tags: Optional[dict] = None) -> None:
    """Record a simple metric. When Prometheus is available, increment a Counter
    or observe a Histogram for duration metrics (name ending with `.duration_ms`).
    Otherwise, fallback to logging.
    """
    tags = tags or {}
    try:
        if _prometheus_available:
            key = _sanitize_metric_name(name)
            if name.endswith(".duration_ms"):
                # use histogram for timings
                metric = _metrics_registry.get((key, "histogram"))
                if metric is None:
                    metric = Histogram(key, f"Timing metric for {name}")
                    _metrics_registry[(key, "histogram")] = metric
                metric.observe(value)
            else:
                metric = _metrics_registry.get((key, "counter"))
                if metric is None:
                    metric = Counter(key, f"Counter metric for {name}")
                    _metrics_registry[(key, "counter")] = metric
                metric.inc(value)
        else:
            logger.info("metric %s=%s %s", name, value, tags)
    except Exception:
        # Keep metrics best-effort: never raise from instrumentation
        logger.exception("failed to record metric %s", name)


def timed(name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration_ms = int((time.time() - start) * 1000)
                record_metric(f"{name}.duration_ms", duration_ms)

        return wrapper

    return decorator


def start_prometheus_http_server(port: int = 8000) -> None:
    """Start a Prometheus metrics HTTP server if the prometheus client is available.

    This is best-effort and returns silently if prometheus_client is not installed.
    """
    if not _prometheus_available:
        logger.warning(
            "prometheus_client not available; metrics HTTP server not started"
        )
        return
    try:
        start_http_server(port)
        logger.info("Prometheus metrics HTTP server started on port %s", port)
    except Exception:
        logger.exception("failed to start Prometheus HTTP server on port %s", port)
