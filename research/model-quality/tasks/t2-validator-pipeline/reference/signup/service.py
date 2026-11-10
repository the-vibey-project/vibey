from signup.form import SignupForm, User
from signup.validation import default_pipeline


class SignupError(ValueError):
    """Raised when a signup is refused. `errors` lists the reasons."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


class SignupService:
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def register(self, form: SignupForm) -> User:
        errors = default_pipeline().run(form)
        if errors:
            raise SignupError(errors)
        key = form.username.lower()
        if key in self._users:
            raise SignupError(["username already taken"])
        user = User(form.username, form.email, form.age)
        self._users[key] = user
        return user

    def count(self) -> int:
        return len(self._users)
