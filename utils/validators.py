import re


class ValidationError(Exception):
    """Excepción base para errores de validación."""
    pass


def validate_email(email: str) -> None:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError("El email ingresado no es válido.")


def validate_phone(phone: str) -> None:
    if not phone.isdigit():
        raise ValidationError("El teléfono solo debe contener dígitos.")
    if not (8 <= len(phone) <= 12):
        raise ValidationError("El teléfono debe tener entre 8 y 12 dígitos.")


def validate_ci(ci: str) -> None:
    ci = re.sub(r'\D', '', ci)
    if len(ci) != 8:
        raise ValidationError("La cédula debe tener 8 dígitos.")
    coef = [2, 9, 8, 7, 6, 3, 4]
    total = sum([int(ci[i]) * coef[i] for i in range(7)])
    remainder = total % 10
    dv = 0 if remainder == 0 else 10 - remainder
    if dv != int(ci[7]):
        raise ValidationError("La cédula ingresada no es válida.")
