"""Exception classes for the Memic SDK."""

from typing import Optional


class MemicError(Exception):
    """Base exception for all Memic SDK errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthenticationError(MemicError):
    """Raised when API key is invalid or missing (401/403)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class NotFoundError(MemicError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class APIError(MemicError):
    """Raised for other HTTP errors from the API."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)
