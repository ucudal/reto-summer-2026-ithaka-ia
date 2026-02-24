"""
Utility validators for email, phone, and CI (cédula de identidad).

Raises ValidationError with a human-readable message on invalid input.
"""

import re


class ValidationError(ValueError):
    """Raised when a field value fails validation."""


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_email(value: str) -> str:
    """Return the normalised email or raise ValidationError."""
    v = value.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValidationError(f"'{value}' no es un correo electrónico válido")
    return v


# ---------------------------------------------------------------------------
# Phone  (Uruguay: 8 or 9 digits after stripping non-digits)
# ---------------------------------------------------------------------------

_PHONE_DIGITS_MIN = 8
_PHONE_DIGITS_MAX = 15


def validate_phone(value: str) -> str:
    """Return digits-only phone string or raise ValidationError."""
    digits = re.sub(r"\D", "", value)
    if not (_PHONE_DIGITS_MIN <= len(digits) <= _PHONE_DIGITS_MAX):
        raise ValidationError(
            f"'{value}' no parece un teléfono válido "
            f"(se esperan entre {_PHONE_DIGITS_MIN} y {_PHONE_DIGITS_MAX} dígitos)"
        )
    return digits


# ---------------------------------------------------------------------------
# CI  (Uruguay: 7 or 8 digits)
# ---------------------------------------------------------------------------

_CI_DIGITS = {7, 8}


def validate_ci(value: str) -> str:
    """Return digits-only CI string or raise ValidationError."""
    digits = re.sub(r"\D", "", value)
    if len(digits) not in _CI_DIGITS:
        raise ValidationError(
            f"'{value}' no es una cédula válida (se esperan 7 u 8 dígitos)"
        )
    return digits
