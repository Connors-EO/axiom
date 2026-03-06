class AdapterError(Exception):
    """Base exception for all adapter errors."""


class AdapterNotFoundError(AdapterError):
    """Raised when the remote resource returns 404."""


class AdapterAuthError(AdapterError):
    """Raised when authentication fails (401) or PAT is missing."""


class AdapterRateLimitError(AdapterError):
    """Raised when the remote resource returns 403 or 429."""
