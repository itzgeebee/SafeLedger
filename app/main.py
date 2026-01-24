from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.trace import get_current_span
from sqlalchemy import event

from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.transfers import router as transfers_router
from app.api.v1.webhooks import router as webhooks_router
from app.config import get_settings
from app.db.db import engine
from app.instrumentation import init_instrumentation, instrument_app_and_db
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        version="0.1.0",
        description="A secure, double-entry ledger system for fintech applications.",
    )

    # --------------------
    # Middleware (order matters: first added = last executed)
    # --------------------

    # CORS (tighten in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # replace with explicit domains in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Request logging with correlation ID
    app.add_middleware(RequestLoggingMiddleware)

    # --------------------
    # Routers
    # --------------------
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(transfers_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")
    app.include_router(accounts_router, prefix="/api/v1")

    return app


app = create_app()


@app.on_event("startup")
async def _startup_instrumentation() -> None:
    # Initialize Prometheus / OpenTelemetry exporters (best-effort)
    init_instrumentation()

    # Auto-instrument FastAPI and SQLAlchemy (best-effort)
    try:
        instrument_app_and_db(app=app, engine=engine)
    except Exception:
        # keep startup resilient if instrumentation fails
        pass

    # Attach SQL listeners to annotate spans with query metadata. Use the
    # engine's sync_engine when available (works for AsyncEngine).
    try:
        sync_engine = getattr(engine, "sync_engine", engine)

        def _before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            span = get_current_span()
            if span is None:
                return
            # Truncate statement for safety and length
            stmt = (statement or "")[:200]
            span.set_attribute("db.statement", stmt)
            # Do not attach full parameter values to avoid leaking secrets; attach count
            try:
                param_count = len(parameters) if hasattr(parameters, "__len__") else 0
            except Exception:
                param_count = 0
            span.set_attribute("db.params.count", int(param_count))

        def _after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            span = get_current_span()
            if span is None:
                return
            try:
                rowcount = int(cursor.rowcount)
            except Exception:
                rowcount = -1
            span.set_attribute("db.rowcount", rowcount)

        event.listen(sync_engine, "before_cursor_execute", _before_cursor_execute)
        event.listen(sync_engine, "after_cursor_execute", _after_cursor_execute)
    except Exception:
        # Non-fatal: instrumentation is best-effort
        pass
