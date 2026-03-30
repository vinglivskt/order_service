from app.domain.auth.exceptions import InvalidPasswordError


def validate_password(password: str) -> None:
    if not any(ch.isdigit() for ch in password) or not any(ch.isalpha() for ch in password):
        raise InvalidPasswordError("Пароль должен содержать буквы и цифры")
