class SVVEError(Exception):
    """Base exception for svve_core."""


class QueryValidationError(SVVEError):
    """Raised when a query payload is invalid."""
