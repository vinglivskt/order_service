class DomainError(Exception):
    """Base exception for domain and application errors."""


class ValidationError(DomainError):
    """Raised when business validation fails."""


class NotFoundError(DomainError):
    """Raised when an entity is not found."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with current state."""


class PermissionDeniedError(DomainError):
    """Raised when access to an operation or resource is forbidden."""


class AuthenticationError(DomainError):
    """Raised when authentication fails."""
