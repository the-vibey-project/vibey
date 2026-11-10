import re
from collections.abc import Callable

from signup.form import SignupForm

Validator = Callable[[SignupForm], list[str]]


class ValidatorPipeline:
    def __init__(self) -> None:
        self._validators: list[Validator] = []

    def add(self, validator: Validator) -> "ValidatorPipeline":
        self._validators.append(validator)
        return self

    def run(self, form: SignupForm) -> list[str]:
        errors: list[str] = []
        for validator in self._validators:
            errors.extend(validator(form))
        return errors


def validate_username(form: SignupForm) -> list[str]:
    errors: list[str] = []
    if not 3 <= len(form.username) <= 20:
        errors.append("username must be 3-20 characters")
    if not re.fullmatch(r"[A-Za-z0-9_]+", form.username):
        errors.append("username may only contain letters, digits and _")
    return errors


def validate_email(form: SignupForm) -> list[str]:
    local, at, domain = form.email.partition("@")
    ok = at == "@" and "@" not in domain and bool(local) and "." in domain[1:-1]
    return [] if ok else ["invalid email"]


def validate_age(form: SignupForm) -> list[str]:
    if 13 <= form.age <= 120:
        return []
    return ["age must be between 13 and 120"]


def default_pipeline() -> ValidatorPipeline:
    return ValidatorPipeline().add(validate_username).add(validate_email).add(validate_age)
