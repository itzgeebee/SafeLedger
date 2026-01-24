from fastapi import Request


def get_request_id(request: Request) -> str | None:
    """Extract request ID from headers for audit logging."""
    return request.headers.get("X-Request-ID")


def get_client_ip(request: Request) -> str | None:
    """Extract client IP for audit logging."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
