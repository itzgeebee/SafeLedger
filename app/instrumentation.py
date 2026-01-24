import logging
import os

from app.observability import start_prometheus_http_server

logger = logging.getLogger("safeledger.instrumentation")

# Check availability of optional OpenTelemetry instrumentation modules so we
# avoid printing full tracebacks when they're not installed.
_ot_fastapi_available = False
_ot_sqlalchemy_available = False
try:
    import importlib

    _ot_fastapi_available = (
        importlib.util.find_spec("opentelemetry.instrumentation.fastapi") is not None
    )
except Exception:
    _ot_fastapi_available = False

try:
    import importlib

    _ot_sqlalchemy_available = (
        importlib.util.find_spec("opentelemetry.instrumentation.sqlalchemy") is not None
    )
except Exception:
    _ot_sqlalchemy_available = False


def init_instrumentation() -> None:
    """Initialize optional instrumentation: Prometheus HTTP server and OpenTelemetry.

    Activation is controlled by environment variables:
      - METRICS_PORT: if set, start Prometheus metrics server on that port
      - OTLP_ENDPOINT: if set, configure OpenTelemetry OTLP exporter to that endpoint

    This function is best-effort and will not raise if dependencies are missing.
    """
    # Prometheus
    try:
        port = int(os.environ.get("METRICS_PORT", "0") or 0)
    except Exception:
        port = 0

    if port:
        try:
            start_prometheus_http_server(port)
        except Exception:
            logger.exception("failed to start Prometheus server on %s", port)

    # OpenTelemetry (OTLP)
    otlp_endpoint = os.environ.get("OTLP_ENDPOINT") or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    if not otlp_endpoint:
        # Still allow Prometheus-only setup; nothing more to do for OTLP
        return

    try:
        # Lazy import so tests won't fail when package not installed
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "SafeLedger"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Set global tracer provider
        from opentelemetry import trace

        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry initialized with OTLP endpoint %s", otlp_endpoint)
    except Exception:
        logger.exception("failed to initialize OpenTelemetry OTLP exporter")


def instrument_fastapi(app) -> None:
    """Auto-instrument a FastAPI app with OpenTelemetry if available.

    This is best-effort and will not raise if the instrumentation package is missing.
    """
    if not _ot_fastapi_available:
        logger.info("opentelemetry FastAPI instrumentation not available; skipping")
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumentation enabled")
    except Exception as exc:
        logger.warning("FastAPI auto-instrumentation failed: %s", exc)


def instrument_sqlalchemy(engine) -> None:
    """Auto-instrument a SQLAlchemy engine (AsyncEngine or Engine).

    For async engines, the underlying sync engine is used when required.
    """
    if not _ot_sqlalchemy_available:
        logger.info("opentelemetry SQLAlchemy instrumentation not available; skipping")
        return

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        instr = SQLAlchemyInstrumentor()
        # AsyncEngine has a `sync_engine` attribute; prefer that for instrumentation
        try:
            sync_engine = getattr(engine, "sync_engine", engine)
            instr.instrument(engine=sync_engine)
        except Exception:
            # Fall back to instrumenting the engine directly
            instr.instrument(engine=engine)

        logger.info("SQLAlchemy auto-instrumentation enabled")
    except Exception as exc:
        logger.warning("SQLAlchemy auto-instrumentation failed: %s", exc)


def instrument_app_and_db(app=None, engine=None) -> None:
    """Convenience: instrument FastAPI app and SQLAlchemy engine if provided.

    Safe to call during startup; each operation is best-effort.
    """
    if app is not None:
        instrument_fastapi(app)
    if engine is not None:
        instrument_sqlalchemy(engine)
