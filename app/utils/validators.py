"""Validation helpers for personal data fields used in the conversation flow."""

from __future__ import annotations

import re


class ValidationError(ValueError):
    """Raised when a value does not match the expected validation rules."""


_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
_PHONE_PATTERN = re.compile(r"^\d{8,12}$")
_CI_PATTERN = re.compile(r"^\d{7,8}$")


def validate_email(email: str) -> bool:
    """Validate an email using a pragmatic RFC 5322-compatible pattern."""
    value = (email or "").strip()
    if not _EMAIL_PATTERN.fullmatch(value):
        raise ValidationError("Formato de correo invalido.")
    return True


def validate_phone(phone: str) -> bool:
    """Validate phone numbers with 8 to 12 digits."""
    value = re.sub(r"\D", "", phone or "")
    if not _PHONE_PATTERN.fullmatch(value):
        raise ValidationError("El telefono debe tener entre 8 y 12 digitos.")
    return True


def validate_ci(ci: str) -> bool:
    """Validate Uruguayan CI number using its check digit."""
    digits = re.sub(r"\D", "", ci or "")
    if not _CI_PATTERN.fullmatch(digits):
        raise ValidationError("La cedula debe tener 7 u 8 digitos.")

    padded = digits.zfill(8)
    base = padded[:-1]
    check_digit = int(padded[-1])
    weights = (2, 9, 8, 7, 6, 3, 4)
    total = sum(int(d) * w for d, w in zip(base, weights))
    verifier = (10 - (total % 10)) % 10

    if verifier != check_digit:
        raise ValidationError("Cedula invalida. Verifica el digito verificador.")
    return True

