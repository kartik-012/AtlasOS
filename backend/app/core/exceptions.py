"""
AtlasOS Structured Exception Hierarchy.

Defines a type-safe exception hierarchy that maps directly to HTTP error
responses. Each exception carries a machine-readable error_code, a
human-readable message, and an HTTP status_code.

Design decisions:
  - All exceptions inherit from AtlasOSError, which inherits from Exception.
    This allows catching all application errors with a single except clause
    while still supporting fine-grained handling.
  - error_code is a stable string identifier (e.g., 'ATLAS_NOT_FOUND') that
    API consumers can match on. Unlike messages, error codes never change
    across versions, making them safe for client-side error handling.
  - status_code maps directly to the HTTP response status code. This
    eliminates the need for exception-to-status mapping logic in API
    handlers — the exception handler middleware reads it directly.
  - detail (optional) provides additional structured context for debugging
    without exposing it in user-facing error messages.

Usage in FastAPI:
  A global exception handler (implemented in Phase 2) will catch
  AtlasOSError subclasses and return a standardized JSON error response:
  {
      "error": {"code": "ATLAS_NOT_FOUND", "message": "..."},
      "status_code": 404
  }
"""

from __future__ import annotations

from typing import Any


class AtlasOSError(Exception):
    """
    Base exception for all AtlasOS application errors.

    All domain-specific exceptions inherit from this class, enabling:
    - Centralized exception handling in FastAPI middleware.
    - Consistent error response formatting.
    - Clear separation between application errors and unexpected system errors.

    Attributes:
        message: Human-readable error description.
        error_code: Machine-readable error identifier for API consumers.
        status_code: HTTP status code for the error response.
        detail: Optional additional context for debugging.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        error_code: str = "ATLAS_INTERNAL_ERROR",
        status_code: int = 500,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the exception to a dictionary for JSON error responses.

        Returns:
            A dictionary with error code, message, and optional detail.
        """
        response: dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            },
            "status_code": self.status_code,
        }
        if self.detail:
            response["error"]["detail"] = self.detail
        return response


class NotFoundError(AtlasOSError):
    """
    Raised when a requested resource does not exist.

    Maps to HTTP 404 Not Found.
    """

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_NOT_FOUND",
            status_code=404,
            detail=detail,
        )


class ConflictError(AtlasOSError):
    """
    Raised when an operation conflicts with the current state.

    Examples: duplicate resource creation, concurrent modification.
    Maps to HTTP 409 Conflict.
    """

    def __init__(
        self,
        message: str = "The operation conflicts with the current resource state.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_CONFLICT",
            status_code=409,
            detail=detail,
        )


class ValidationError(AtlasOSError):
    """
    Raised when input validation fails beyond Pydantic schema validation.

    Used for business-rule validation that Pydantic cannot express
    (e.g., cross-field validation, database-dependent validation).
    Maps to HTTP 422 Unprocessable Entity.
    """

    def __init__(
        self,
        message: str = "Validation failed.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_VALIDATION_ERROR",
            status_code=422,
            detail=detail,
        )


class AuthenticationError(AtlasOSError):
    """
    Raised when authentication fails.

    Examples: invalid JWT, expired token, missing credentials.
    Maps to HTTP 401 Unauthorized.
    """

    def __init__(
        self,
        message: str = "Authentication required.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_AUTH_REQUIRED",
            status_code=401,
            detail=detail,
        )


class AuthorizationError(AtlasOSError):
    """
    Raised when the authenticated user lacks permission for an operation.

    Examples: read_only user attempting a write, member accessing admin settings.
    Maps to HTTP 403 Forbidden.
    """

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_FORBIDDEN",
            status_code=403,
            detail=detail,
        )


class RateLimitError(AtlasOSError):
    """
    Raised when a client exceeds their rate limit.

    Maps to HTTP 429 Too Many Requests. The detail dict should include
    'retry_after' indicating when the client can retry.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded. Please try again later.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_RATE_LIMITED",
            status_code=429,
            detail=detail,
        )


class ExternalServiceError(AtlasOSError):
    """
    Raised when an external service call fails.

    Examples: embedding service timeout, NLI service unavailable.
    Maps to HTTP 502 Bad Gateway.
    """

    def __init__(
        self,
        message: str = "An external service is unavailable.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_EXTERNAL_SERVICE_ERROR",
            status_code=502,
            detail=detail,
        )


class TenantIsolationError(AtlasOSError):
    """
    Raised when a cross-tenant access attempt is detected.

    This is a security-critical exception. It should trigger an audit log
    entry and potentially alert the security team.
    Maps to HTTP 403 Forbidden.
    """

    def __init__(
        self,
        message: str = "Cross-tenant access is not permitted.",
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code="ATLAS_TENANT_ISOLATION_VIOLATION",
            status_code=403,
            detail=detail,
        )
