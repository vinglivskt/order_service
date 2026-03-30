class AuthError(Exception):
    """Base authentication domain error."""


class InvalidCredentialsError(AuthError):
    """Raised when provided credentials are invalid."""


class UserAlreadyExistsError(AuthError):
    """Raised when user with the same email already exists."""


class InvalidPasswordError(AuthError):
    """Raised when password does not satisfy domain rules."""
