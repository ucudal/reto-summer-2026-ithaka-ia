import re


def validate_input(value, validator_type):
    if validator_type == "email":
        return re.match(r"[^@]+@[^@]+\.[^@]+", value) is not None
    if validator_type == "phone":
        return re.match(r"^\+?\d{7,15}$", value) is not None
    return True
