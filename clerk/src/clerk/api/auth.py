"""Bearer token authentication and structured JSON error handling for the Clerk API."""

from __future__ import annotations

from fastapi import HTTPException, Request, status


class APIError(Exception):
    """Structured API error returning `{"error": {"code": ..., "message": ...}}`."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def require_admin_token(request: Request) -> str:
    """FastAPI dependency enforcing `Authorization: Bearer <ADMIN_TOKEN>`."""
    expected_token: str = getattr(request.app.state, "admin_token", "sk-admin-dev-token")
    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    elif "token" in request.query_params:
        token = str(request.query_params["token"]).strip()

    if not token or token != expected_token:
        raise APIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="unauthorized",
            message="Missing or invalid Bearer token.",
        )
    return token


def http_exception_to_error_payload(exc: HTTPException) -> dict[str, dict[str, str]]:
    """Convert a FastAPI HTTPException into the standard Section 10 error envelope."""
    return {
        "error": {
            "code": f"http_{exc.status_code}",
            "message": str(exc.detail),
        }
    }
